# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------

import functools
import time
from io import BytesIO
from typing import Optional, Union, IO, List, Dict, Any, Iterable, TYPE_CHECKING  # pylint: disable=unused-import

import six
from azure.core.async_paging import AsyncItemPaged

from azure.core.tracing.decorator import distributed_trace
from azure.core.tracing.decorator_async import distributed_trace_async
from .._parser import _datetime_to_str, _get_file_permission
from .._shared.parser import _str

from .._generated.aio import AzureFileStorage
from .._generated.version import VERSION
from .._generated.models import StorageErrorException, FileHTTPHeaders
from .._shared.policies_async import ExponentialRetry
from .._shared.uploads_async import upload_data_chunks, FileChunkUploader, IterStreamer
from .._shared.base_client_async import AsyncStorageAccountHostsMixin
from .._shared.request_handlers import add_metadata_headers, get_length
from .._shared.response_handlers import return_response_headers, process_storage_error
from .._deserialize import deserialize_file_properties, deserialize_file_stream
from .._file_client import FileClient as FileClientBase
from ._models import HandlesPaged
from ._download_async import StorageStreamDownloader

if TYPE_CHECKING:
    from datetime import datetime
    from .._models import ShareProperties, ContentSettings, FileProperties, NTFSAttributes
    from .._generated.models import HandleItem


async def _upload_file_helper(
    client,
    stream,
    size,
    metadata,
    content_settings,
    validate_content,
    timeout,
    max_concurrency,
    file_settings,
    file_attributes="none",
    file_creation_time="now",
    file_last_write_time="now",
    file_permission=None,
    file_permission_key=None,
    **kwargs
):
    try:
        if size is None or size < 0:
            raise ValueError("A content size must be specified for a File.")
        response = await client.create_file(
            size, content_settings=content_settings, metadata=metadata,
            file_attributes=file_attributes,
            file_creation_time=file_creation_time,
            file_last_write_time=file_last_write_time,
            file_permission=file_permission,
            permission_key=file_permission_key,
            timeout=timeout,
            **kwargs
        )
        if size == 0:
            return response

        responses = await upload_data_chunks(
            service=client,
            uploader_class=FileChunkUploader,
            total_size=size,
            chunk_size=file_settings.max_range_size,
            stream=stream,
            max_concurrency=max_concurrency,
            validate_content=validate_content,
            timeout=timeout,
            **kwargs
        )
        return sorted(responses, key=lambda r: r.get('last_modified'))[-1]
    except StorageErrorException as error:
        process_storage_error(error)


class FileClient(AsyncStorageAccountHostsMixin, FileClientBase):
    """A client to interact with a specific file, although that file may not yet exist.

    :ivar str url:
        The full endpoint URL to the File, including SAS token if used. This could be
        either the primary endpoint, or the secondary endpoint depending on the current `location_mode`.
    :ivar str primary_endpoint:
        The full primary endpoint URL.
    :ivar str primary_hostname:
        The hostname of the primary endpoint.
    :ivar str secondary_endpoint:
        The full secondary endpoint URL if configured. If not available
        a ValueError will be raised. To explicitly specify a secondary hostname, use the optional
        `secondary_hostname` keyword argument on instantiation.
    :ivar str secondary_hostname:
        The hostname of the secondary endpoint. If not available this
        will be None. To explicitly specify a secondary hostname, use the optional
        `secondary_hostname` keyword argument on instantiation.
    :ivar str location_mode:
        The location mode that the client is currently using. By default
        this will be "primary". Options include "primary" and "secondary".
    :param str account_url:
        The URI to the storage account. In order to create a client given the full URI to the
        file, use the :func:`from_file_url` classmethod.
    :param share_name:
        The name of the share for the file.
    :type share_name: str
    :param str file_path:
        The file path to the file with which to interact. If specified, this value will override
        a file value specified in the file URL.
    :param str snapshot:
        An optional file snapshot on which to operate. This can be the snapshot ID string
        or the response returned from :func:`ShareClient.create_snapshot`.
    :param credential:
        The credential with which to authenticate. This is optional if the
        account URL already has a SAS token. The value can be a SAS token string or an account
        shared access key.
    :keyword loop:
        The event loop to run the asynchronous tasks.
    """

    def __init__(  # type: ignore
        self,
        account_url,  # type: str
        share_name,  # type: str
        file_path,  # type: str
        snapshot=None,  # type: Optional[Union[str, Dict[str, Any]]]
        credential=None,  # type: Optional[Any]
        **kwargs  # type: Any
    ):
        # type: (...) -> None
        kwargs["retry_policy"] = kwargs.get("retry_policy") or ExponentialRetry(**kwargs)
        loop = kwargs.pop('loop', None)
        super(FileClient, self).__init__(
            account_url, share_name=share_name, file_path=file_path, snapshot=snapshot,
            credential=credential, loop=loop, **kwargs
        )
        self._client = AzureFileStorage(version=VERSION, url=self.url, pipeline=self._pipeline, loop=loop)
        self._loop = loop

    @distributed_trace_async
    async def create_file(  # type: ignore
        self,
        size,  # type: int
        file_attributes="none",  # type: Union[str, NTFSAttributes]
        file_creation_time="now",  # type: Union[str, datetime]
        file_last_write_time="now",  # type: Union[str, datetime]
        file_permission=None,  # type: Optional[str]
        permission_key=None,  # type: Optional[str]
        **kwargs  # type: Any
    ):
        # type: (...) -> Dict[str, Any]
        """Creates a new file.

        Note that it only initializes the file with no content.

        :param int size: Specifies the maximum size for the file,
            up to 1 TB.
        :param file_attributes:
            The file system attributes for files and directories.
            If not set, the default value would be "None" and the attributes will be set to "Archive".
            Here is an example for when the var type is str: 'Temporary|Archive'.
            file_attributes value is not case sensitive.
        :type file_attributes: str or :class:`~azure.storage.file.NTFSAttributes`
        :param file_creation_time: Creation time for the file
            Default value: Now.
        :type file_creation_time: str or ~datetime.datetime
        :param file_last_write_time: Last write time for the file
            Default value: Now.
        :type file_last_write_time: str or ~datetime.datetime
        :param file_permission: If specified the permission (security
            descriptor) shall be set for the directory/file. This header can be
            used if Permission size is <= 8KB, else x-ms-file-permission-key
            header shall be used. Default value: Inherit. If SDDL is specified as
            input, it must have owner, group and dacl. Note: Only one of the
            x-ms-file-permission or x-ms-file-permission-key should be specified.
        :type file_permission: str
        :param permission_key: Key of the permission to be set for the
            directory/file. Note: Only one of the x-ms-file-permission or
            x-ms-file-permission-key should be specified.
        :type permission_key: str
        :keyword ~azure.storage.file.ContentSettings content_settings:
            ContentSettings object used to set file properties. Used to set content type, encoding,
            language, disposition, md5, and cache control.
        :keyword dict(str,str) metadata:
            Name-value pairs associated with the file as metadata.
        :keyword int timeout:
            The timeout parameter is expressed in seconds.
        :returns: File-updated property dict (Etag and last modified).
        :rtype: dict(str, Any)

        .. admonition:: Example:

            .. literalinclude:: ../tests/test_file_samples_file_async.py
                :start-after: [START create_file]
                :end-before: [END create_file]
                :language: python
                :dedent: 12
                :caption: Create a file.
        """
        content_settings = kwargs.pop('content_settings', None)
        metadata = kwargs.pop('metadata', None)
        timeout = kwargs.pop('timeout', None)
        if self.require_encryption and not self.key_encryption_key:
            raise ValueError("Encryption required but no key was provided.")

        headers = kwargs.pop("headers", {})
        headers.update(add_metadata_headers(metadata))
        file_http_headers = None
        if content_settings:
            file_http_headers = FileHTTPHeaders(
                file_cache_control=content_settings.cache_control,
                file_content_type=content_settings.content_type,
                file_content_md5=bytearray(content_settings.content_md5) if content_settings.content_md5 else None,
                file_content_encoding=content_settings.content_encoding,
                file_content_language=content_settings.content_language,
                file_content_disposition=content_settings.content_disposition,
            )
        file_permission = _get_file_permission(file_permission, permission_key, 'Inherit')
        try:
            return await self._client.file.create(  # type: ignore
                file_content_length=size,
                metadata=metadata,
                file_attributes=_str(file_attributes),
                file_creation_time=_datetime_to_str(file_creation_time),
                file_last_write_time=_datetime_to_str(file_last_write_time),
                file_permission=file_permission,
                file_permission_key=permission_key,
                file_http_headers=file_http_headers,
                headers=headers,
                timeout=timeout,
                cls=return_response_headers,
                **kwargs
            )
        except StorageErrorException as error:
            process_storage_error(error)

    @distributed_trace_async
    async def upload_file(
        self, data,  # type: Any
        length=None,  # type: Optional[int]
        file_attributes="none",  # type: Union[str, NTFSAttributes]
        file_creation_time="now",  # type: Union[str, datetime]
        file_last_write_time="now",  # type: Union[str, datetime]
        file_permission=None,  # type: Optional[str]
        permission_key=None,  # type: Optional[str]
        **kwargs  # type: Any
    ):
        # type: (...) -> Dict[str, Any]
        """Uploads a new file.

        :param Any data:
            Content of the file.
        :param int length:
            Length of the file in bytes. Specify its maximum size, up to 1 TiB.
        :param file_attributes:
            The file system attributes for files and directories.
            If not set, the default value would be "None" and the attributes will be set to "Archive".
            Here is an example for when the var type is str: 'Temporary|Archive'.
            file_attributes value is not case sensitive.
        :type file_attributes: str or ~azure.storage.file.NTFSAttributes
        :param file_creation_time: Creation time for the file
            Default value: Now.
        :type file_creation_time: str or ~datetime.datetime
        :param file_last_write_time: Last write time for the file
            Default value: Now.
        :type file_last_write_time: str or ~datetime.datetime
        :param file_permission: If specified the permission (security
            descriptor) shall be set for the directory/file. This header can be
            used if Permission size is <= 8KB, else x-ms-file-permission-key
            header shall be used. Default value: Inherit. If SDDL is specified as
            input, it must have owner, group and dacl. Note: Only one of the
            x-ms-file-permission or x-ms-file-permission-key should be specified.
        :type file_permission: str
        :param permission_key: Key of the permission to be set for the
            directory/file. Note: Only one of the x-ms-file-permission or
            x-ms-file-permission-key should be specified.
        :type permission_key: str
        :keyword dict(str,str) metadata:
            Name-value pairs associated with the file as metadata.
        :keyword ~azure.storage.file.ContentSettings content_settings:
            ContentSettings object used to set file properties. Used to set content type, encoding,
            language, disposition, md5, and cache control.
        :keyword bool validate_content:
            If true, calculates an MD5 hash for each range of the file. The storage
            service checks the hash of the content that has arrived with the hash
            that was sent. This is primarily valuable for detecting bitflips on
            the wire if using http instead of https as https (the default) will
            already validate. Note that this MD5 hash is not stored with the
            file.
        :keyword int max_concurrency:
            Maximum number of parallel connections to use.
        :keyword str encoding:
            Defaults to UTF-8.
        :keyword int timeout:
            The timeout parameter is expressed in seconds.
        :returns: File-updated property dict (Etag and last modified).
        :rtype: dict(str, Any)

        .. admonition:: Example:

            .. literalinclude:: ../tests/test_file_samples_file_async.py
                :start-after: [START upload_file]
                :end-before: [END upload_file]
                :language: python
                :dedent: 12
                :caption: Upload a file.
        """
        metadata = kwargs.pop('metadata', None)
        content_settings = kwargs.pop('content_settings', None)
        max_concurrency = kwargs.pop('max_concurrency', 1)
        validate_content = kwargs.pop('validate_content', False)
        timeout = kwargs.pop('timeout', None)
        encoding = kwargs.pop('encoding', 'UTF-8')
        if self.require_encryption or (self.key_encryption_key is not None):
            raise ValueError("Encryption not supported.")

        if isinstance(data, six.text_type):
            data = data.encode(encoding)
        if length is None:
            length = get_length(data)
        if isinstance(data, bytes):
            data = data[:length]

        if isinstance(data, bytes):
            stream = BytesIO(data)
        elif hasattr(data, "read"):
            stream = data
        elif hasattr(data, "__iter__"):
            stream = IterStreamer(data, encoding=encoding)  # type: ignore
        else:
            raise TypeError("Unsupported data type: {}".format(type(data)))
        return await _upload_file_helper(  # type: ignore
            self,
            stream,
            length,
            metadata,
            content_settings,
            validate_content,
            timeout,
            max_concurrency,
            self._config,
            file_attributes=file_attributes,
            file_creation_time=file_creation_time,
            file_last_write_time=file_last_write_time,
            file_permission=file_permission,
            file_permission_key=permission_key,
            **kwargs
        )

    @distributed_trace_async
    async def start_copy_from_url(
        self,
        source_url,  # type: str
        **kwargs  # type: Any
    ):
        # type: (...) -> Any
        """Initiates the copying of data from a source URL into the file
        referenced by the client.

        The status of this copy operation can be found using the `get_properties`
        method.

        :param str source_url:
            Specifies the URL of the source file.
        :keyword dict(str,str) metadata:
            Name-value pairs associated with the file as metadata.
        :keyword int timeout:
            The timeout parameter is expressed in seconds.
        :rtype: dict(str, Any)

        .. admonition:: Example:

            .. literalinclude:: ../tests/test_file_samples_file_async.py
                :start-after: [START copy_file_from_url]
                :end-before: [END copy_file_from_url]
                :language: python
                :dedent: 12
                :caption: Copy a file from a URL
        """
        metadata = kwargs.pop('metadata', None)
        timeout = kwargs.pop('timeout', None)
        headers = kwargs.pop("headers", {})
        headers.update(add_metadata_headers(metadata))

        try:
            return await self._client.file.start_copy(
                source_url, timeout=timeout, metadata=metadata, headers=headers, cls=return_response_headers, **kwargs
            )
        except StorageErrorException as error:
            process_storage_error(error)

    @distributed_trace_async
    async def abort_copy(self, copy_id, **kwargs):
        # type: (Union[str, FileProperties], Any) -> None
        """Abort an ongoing copy operation.

        This will leave a destination file with zero length and full metadata.
        This will raise an error if the copy operation has already ended.

        :param copy_id:
            The copy operation to abort. This can be either an ID, or an
            instance of FileProperties.
        :type copy_id: str or ~azure.storage.file.FileProperties
        :keyword int timeout:
            The timeout parameter is expressed in seconds.
        :rtype: None
        """
        timeout = kwargs.pop('timeout', None)
        try:
            copy_id = copy_id.copy.id
        except AttributeError:
            try:
                copy_id = copy_id["copy_id"]
            except TypeError:
                pass
        try:
            await self._client.file.abort_copy(copy_id=copy_id, timeout=timeout, **kwargs)
        except StorageErrorException as error:
            process_storage_error(error)

    @distributed_trace_async
    async def download_file(
        self,
        offset=None,  # type: Optional[int]
        length=None,  # type: Optional[int]
        **kwargs
    ):
        # type: (...) -> Iterable[bytes]
        """Downloads a file to a stream with automatic chunking.

        :param int offset:
            Start of byte range to use for downloading a section of the file.
            Must be set if length is provided.
        :param int length:
            Number of bytes to read from the stream. This is optional, but
            should be supplied for optimal performance.
        :keyword int max_concurrency:
            Maximum number of parallel connections to use.
        :keyword bool validate_content:
            If true, calculates an MD5 hash for each chunk of the file. The storage
            service checks the hash of the content that has arrived with the hash
            that was sent. This is primarily valuable for detecting bitflips on
            the wire if using http instead of https as https (the default) will
            already validate. Note that this MD5 hash is not stored with the
            file. Also note that if enabled, the memory-efficient upload algorithm
            will not be used, because computing the MD5 hash requires buffering
            entire blocks, and doing so defeats the purpose of the memory-efficient algorithm.
        :keyword int timeout:
            The timeout parameter is expressed in seconds.
        :returns: A iterable data generator (stream)

        .. admonition:: Example:

            .. literalinclude:: ../tests/test_file_samples_file_async.py
                :start-after: [START download_file]
                :end-before: [END download_file]
                :language: python
                :dedent: 12
                :caption: Download a file.
        """
        if self.require_encryption or (self.key_encryption_key is not None):
            raise ValueError("Encryption not supported.")
        if length is not None and offset is None:
            raise ValueError("Offset value must not be None if length is set.")

        range_end = None
        if length is not None:
            range_end = offset + length - 1  # Service actually uses an end-range inclusive index
        downloader = StorageStreamDownloader(
            client=self._client.file,
            config=self._config,
            start_range=offset,
            end_range=range_end,
            encryption_options=None,
            name=self.file_name,
            path='/'.join(self.file_path),
            share=self.share_name,
            cls=deserialize_file_stream,
            **kwargs
        )
        await downloader._setup()  # pylint: disable=protected-access
        return downloader

    @distributed_trace_async
    async def delete_file(self, **kwargs):
        # type: (Any) -> None
        """Marks the specified file for deletion. The file is
        later deleted during garbage collection.

        :keyword int timeout:
            The timeout parameter is expressed in seconds.
        :rtype: None

        .. admonition:: Example:

            .. literalinclude:: ../tests/test_file_samples_file_async.py
                :start-after: [START delete_file]
                :end-before: [END delete_file]
                :language: python
                :dedent: 12
                :caption: Delete a file.
        """
        timeout = kwargs.pop('timeout', None)
        try:
            await self._client.file.delete(timeout=timeout, **kwargs)
        except StorageErrorException as error:
            process_storage_error(error)

    @distributed_trace_async
    async def get_file_properties(self, **kwargs):
        # type: (Any) -> FileProperties
        """Returns all user-defined metadata, standard HTTP properties, and
        system properties for the file.

        :keyword int timeout:
            The timeout parameter is expressed in seconds.
        :returns: FileProperties
        :rtype: ~azure.storage.file.FileProperties
        """
        timeout = kwargs.pop('timeout', None)
        try:
            file_props = await self._client.file.get_properties(
                sharesnapshot=self.snapshot, timeout=timeout, cls=deserialize_file_properties, **kwargs
            )
        except StorageErrorException as error:
            process_storage_error(error)
        file_props.name = self.file_name
        file_props.share = self.share_name
        file_props.snapshot = self.snapshot
        file_props.path = "/".join(self.file_path)
        return file_props  # type: ignore

    @distributed_trace_async
    async def set_http_headers(self, content_settings,  # type: ContentSettings
                               file_attributes="preserve",  # type: Union[str, NTFSAttributes]
                               file_creation_time="preserve",  # type: Union[str, datetime]
                               file_last_write_time="preserve",  # type: Union[str, datetime]
                               file_permission=None,  # type: Optional[str]
                               permission_key=None,  # type: Optional[str]
                               **kwargs  # type: Any
                               ):
        # type: (...) -> Dict[str, Any]
        """Sets HTTP headers on the file.

        :param ~azure.storage.file.ContentSettings content_settings:
            ContentSettings object used to set file properties. Used to set content type, encoding,
            language, disposition, md5, and cache control.
        :param file_attributes:
            The file system attributes for files and directories.
            If not set, indicates preservation of existing values.
            Here is an example for when the var type is str: 'Temporary|Archive'
        :type file_attributes: str or :class:`~azure.storage.file.NTFSAttributes`
        :param file_creation_time: Creation time for the file
            Default value: Preserve.
        :type file_creation_time: str or ~datetime.datetime
        :param file_last_write_time: Last write time for the file
            Default value: Preserve.
        :type file_last_write_time: str or ~datetime.datetime
        :param file_permission: If specified the permission (security
            descriptor) shall be set for the directory/file. This header can be
            used if Permission size is <= 8KB, else x-ms-file-permission-key
            header shall be used. Default value: Inherit. If SDDL is specified as
            input, it must have owner, group and dacl. Note: Only one of the
            x-ms-file-permission or x-ms-file-permission-key should be specified.
        :type file_permission: str
        :param permission_key: Key of the permission to be set for the
            directory/file. Note: Only one of the x-ms-file-permission or
            x-ms-file-permission-key should be specified.
        :type permission_key: str
        :keyword int timeout:
            The timeout parameter is expressed in seconds.
        :returns: File-updated property dict (Etag and last modified).
        :rtype: dict(str, Any)
        """
        timeout = kwargs.pop('timeout', None)
        file_content_length = kwargs.pop("size", None)
        file_http_headers = FileHTTPHeaders(
            file_cache_control=content_settings.cache_control,
            file_content_type=content_settings.content_type,
            file_content_md5=bytearray(content_settings.content_md5) if content_settings.content_md5 else None,
            file_content_encoding=content_settings.content_encoding,
            file_content_language=content_settings.content_language,
            file_content_disposition=content_settings.content_disposition,
        )
        file_permission = _get_file_permission(file_permission, permission_key, 'preserve')
        try:
            return await self._client.file.set_http_headers(  # type: ignore
                file_content_length=file_content_length,
                file_http_headers=file_http_headers,
                file_attributes=_str(file_attributes),
                file_creation_time=_datetime_to_str(file_creation_time),
                file_last_write_time=_datetime_to_str(file_last_write_time),
                file_permission=file_permission,
                file_permission_key=permission_key,
                timeout=timeout,
                cls=return_response_headers,
                **kwargs
            )
        except StorageErrorException as error:
            process_storage_error(error)

    @distributed_trace_async
    async def set_file_metadata(self, metadata=None, **kwargs):  # type: ignore
        # type: (Optional[Dict[str, Any]], Any) -> Dict[str, Any]
        """Sets user-defined metadata for the specified file as one or more
        name-value pairs.

        Each call to this operation replaces all existing metadata
        attached to the file. To remove all metadata from the file,
        call this operation with no metadata dict.

        :param metadata:
            Name-value pairs associated with the file as metadata.
        :type metadata: dict(str, str)
        :keyword int timeout:
            The timeout parameter is expressed in seconds.
        :returns: File-updated property dict (Etag and last modified).
        :rtype: dict(str, Any)
        """
        timeout = kwargs.pop('timeout', None)
        headers = kwargs.pop("headers", {})
        headers.update(add_metadata_headers(metadata))  # type: ignore
        try:
            return await self._client.file.set_metadata(  # type: ignore
                timeout=timeout, cls=return_response_headers, headers=headers, metadata=metadata, **kwargs
            )
        except StorageErrorException as error:
            process_storage_error(error)

    @distributed_trace_async
    async def upload_range(  # type: ignore
        self,
        data,  # type: bytes
        offset,  # type: int
        length,  # type: int
        **kwargs
    ):
        # type: (...) -> Dict[str, Any]
        """Upload a range of bytes to a file.

        :param bytes data:
            The data to upload.
        :param int offset:
            Start of byte range to use for uploading a section of the file.
            The range can be up to 4 MB in size.
        :param int length:
            Number of bytes to use for uploading a section of the file.
            The range can be up to 4 MB in size.
        :keyword bool validate_content:
            If true, calculates an MD5 hash of the page content. The storage
            service checks the hash of the content that has arrived
            with the hash that was sent. This is primarily valuable for detecting
            bitflips on the wire if using http instead of https as https (the default)
            will already validate. Note that this MD5 hash is not stored with the
            file.
        :keyword int timeout:
            The timeout parameter is expressed in seconds.
        :keyword str encoding:
            Defaults to UTF-8.
        :returns: File-updated property dict (Etag and last modified).
        :rtype: Dict[str, Any]
        """
        validate_content = kwargs.pop('validate_content', False)
        timeout = kwargs.pop('timeout', None)
        encoding = kwargs.pop('encoding', 'UTF-8')
        if self.require_encryption or (self.key_encryption_key is not None):
            raise ValueError("Encryption not supported.")
        if isinstance(data, six.text_type):
            data = data.encode(encoding)
        end_range = offset + length - 1  # Reformat to an inclusive range index
        content_range = 'bytes={0}-{1}'.format(offset, end_range)
        try:
            return await self._client.file.upload_range(  # type: ignore
                range=content_range,
                content_length=length,
                optionalbody=data,
                timeout=timeout,
                validate_content=validate_content,
                cls=return_response_headers,
                **kwargs
            )
        except StorageErrorException as error:
            process_storage_error(error)

    @distributed_trace_async
    async def upload_range_from_url(self, source_url,
                                    offset,
                                    length,
                                    source_offset,
                                    **kwargs
                                    ):
        # type: (str, int, int, int, **Any) -> Dict[str, Any]
        """
        Writes the bytes from one Azure File endpoint into the specified range of another Azure File endpoint.

        :param int offset:
            Start of byte range to use for updating a section of the file.
            The range can be up to 4 MB in size.
        :param int length:
            Number of bytes to use for updating a section of the file.
            The range can be up to 4 MB in size.
        :param str source_url:
            A URL of up to 2 KB in length that specifies an Azure file or blob.
            The value should be URL-encoded as it would appear in a request URI.
            If the source is in another account, the source must either be public
            or must be authenticated via a shared access signature. If the source
            is public, no authentication is required.
            Examples:
            https://myaccount.file.core.windows.net/myshare/mydir/myfile
            https://otheraccount.file.core.windows.net/myshare/mydir/myfile?sastoken
        :param int source_offset:
            This indicates the start of the range of bytes(inclusive) that has to be taken from the copy source.
            The service will read the same number of bytes as the destination range (length-offset).
        :keyword int timeout:
            The timeout parameter is expressed in seconds.
        """
        options = self._upload_range_from_url_options(
            source_url=source_url,
            offset=offset,
            length=length,
            source_offset=source_offset,
            **kwargs
        )
        try:
            return await self._client.file.upload_range_from_url(**options)  # type: ignore
        except StorageErrorException as error:
            process_storage_error(error)

    @distributed_trace_async
    async def get_ranges(  # type: ignore
        self,
        offset=None,  # type: Optional[int]
        length=None,  # type: Optional[int]
        **kwargs
    ):
        # type: (...) -> List[Dict[str, int]]
        """Returns the list of valid ranges of a file.

        :param int offset:
            Specifies the start offset of bytes over which to get ranges.
        :param int length:
            Number of bytes to use over which to get ranges.
        :keyword int timeout:
            The timeout parameter is expressed in seconds.
        :returns: A list of valid ranges.
        :rtype: List[dict[str, int]]
        """
        timeout = kwargs.pop('timeout', None)
        if self.require_encryption or (self.key_encryption_key is not None):
            raise ValueError("Unsupported method for encryption.")

        content_range = None
        if offset is not None:
            if length is not None:
                end_range = offset + length - 1  # Reformat to an inclusive range index
                content_range = "bytes={0}-{1}".format(offset, end_range)
            else:
                content_range = "bytes={0}-".format(offset)
        try:
            ranges = await self._client.file.get_range_list(
                sharesnapshot=self.snapshot, timeout=timeout, range=content_range, **kwargs
            )
        except StorageErrorException as error:
            process_storage_error(error)
        return [{"start": b.start, "end": b.end} for b in ranges]

    @distributed_trace_async
    async def clear_range(  # type: ignore
        self,
        offset,  # type: int
        length,  # type: int
        **kwargs
    ):
        # type: (...) -> Dict[str, Any]
        """Clears the specified range and releases the space used in storage for
        that range.

        :param int offset:
            Start of byte range to use for clearing a section of the file.
            The range can be up to 4 MB in size.
        :param int length:
            Number of bytes to use for clearing a section of the file.
            The range can be up to 4 MB in size.
        :keyword int timeout:
            The timeout parameter is expressed in seconds.
        :returns: File-updated property dict (Etag and last modified).
        :rtype: Dict[str, Any]
        """
        timeout = kwargs.pop('timeout', None)
        if self.require_encryption or (self.key_encryption_key is not None):
            raise ValueError("Unsupported method for encryption.")

        if offset is None or offset % 512 != 0:
            raise ValueError("offset must be an integer that aligns with 512 bytes file size")
        if length is None or length % 512 != 0:
            raise ValueError("length must be an integer that aligns with 512 bytes file size")
        end_range = length + offset - 1  # Reformat to an inclusive range index
        content_range = "bytes={0}-{1}".format(offset, end_range)
        try:
            return await self._client.file.upload_range(  # type: ignore
                timeout=timeout,
                cls=return_response_headers,
                content_length=0,
                file_range_write="clear",
                range=content_range,
                **kwargs
            )
        except StorageErrorException as error:
            process_storage_error(error)

    @distributed_trace_async
    async def resize_file(self, size, **kwargs):
        # type: (int, Any) -> Dict[str, Any]
        """Resizes a file to the specified size.

        :param int size:
            Size to resize file to (in bytes)
        :keyword int timeout:
            The timeout parameter is expressed in seconds.
        :returns: File-updated property dict (Etag and last modified).
        :rtype: Dict[str, Any]
        """
        timeout = kwargs.pop('timeout', None)
        try:
            return await self._client.file.set_http_headers(  # type: ignore
                file_content_length=size,
                file_attributes="preserve",
                file_creation_time="preserve",
                file_last_write_time="preserve",
                file_permission="preserve",
                cls=return_response_headers,
                timeout=timeout,
                **kwargs
            )
        except StorageErrorException as error:
            process_storage_error(error)

    @distributed_trace
    def list_handles(self, **kwargs):
        # type: (Any) -> AsyncItemPaged
        """Lists handles for file.

        :keyword int timeout:
            The timeout parameter is expressed in seconds.
        :returns: An auto-paging iterable of HandleItem
        :rtype: ~azure.core.async_paging.AsyncItemPaged[~azure.storage.file.HandleItem]
        """
        timeout = kwargs.pop('timeout', None)
        results_per_page = kwargs.pop("results_per_page", None)
        command = functools.partial(
            self._client.file.list_handles,
            sharesnapshot=self.snapshot,
            timeout=timeout,
            **kwargs)
        return AsyncItemPaged(
            command, results_per_page=results_per_page,
            page_iterator_class=HandlesPaged)

    @distributed_trace_async
    async def close_handle(self, handle, **kwargs):
        # type: (Union[str, HandleItem], Any) -> int
        """Close an open file handle.

        :param handle:
            A specific handle to close.
        :type handle: str or ~azure.storage.file.Handle
        :keyword int timeout:
            The timeout parameter is expressed in seconds.
        :returns:
            The total number of handles closed. This could be 0 if the supplied
            handle was not found.
        :rtype: int
        """
        try:
            handle_id = handle.id # type: ignore
        except AttributeError:
            handle_id = handle
        if handle_id == '*':
            raise ValueError("Handle ID '*' is not supported. Use 'close_all_handles' instead.")
        try:
            response = await self._client.file.force_close_handles(
                handle_id,
                marker=None,
                sharesnapshot=self.snapshot,
                cls=return_response_headers,
                **kwargs
            )
            return response.get('number_of_handles_closed', 0)
        except StorageErrorException as error:
            process_storage_error(error)

    @distributed_trace_async
    async def close_all_handles(self, **kwargs):
        # type: (Any) -> int
        """Close any open file handles.

        This operation will block until the service has closed all open handles.

        :keyword int timeout:
            The timeout parameter is expressed in seconds.
        :returns: The total number of handles closed.
        :rtype: int
        """
        timeout = kwargs.pop('timeout', None)
        start_time = time.time()

        try_close = True
        continuation_token = None
        total_handles = 0
        while try_close:
            try:
                response = await self._client.file.force_close_handles(
                    handle_id='*',
                    timeout=timeout,
                    marker=continuation_token,
                    sharesnapshot=self.snapshot,
                    cls=return_response_headers,
                    **kwargs
                )
            except StorageErrorException as error:
                process_storage_error(error)
            continuation_token = response.get('marker')
            try_close = bool(continuation_token)
            total_handles += response.get('number_of_handles_closed', 0)
            if timeout:
                timeout = max(0, timeout - (time.time() - start_time))
        return total_handles
