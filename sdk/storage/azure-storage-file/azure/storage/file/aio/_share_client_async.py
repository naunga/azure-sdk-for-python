# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------

from typing import ( # pylint: disable=unused-import
    Optional, Union, Dict, Any, Iterable, TYPE_CHECKING
)

from azure.core.tracing.decorator import distributed_trace
from azure.core.tracing.decorator_async import distributed_trace_async
from azure.core.pipeline import AsyncPipeline
from .._shared.policies_async import ExponentialRetry
from .._shared.base_client_async import AsyncStorageAccountHostsMixin, AsyncTransportWrapper
from .._shared.request_handlers import add_metadata_headers, serialize_iso
from .._shared.response_handlers import (
    return_response_headers,
    process_storage_error,
    return_headers_and_deserialized)
from .._generated.aio import AzureFileStorage
from .._generated.version import VERSION
from .._generated.models import (
    StorageErrorException,
    SignedIdentifier,
    DeleteSnapshotsOptionType)
from .._deserialize import deserialize_share_properties, deserialize_permission
from .._share_client import ShareClient as ShareClientBase
from ._directory_client_async import DirectoryClient
from ._file_client_async import FileClient

if TYPE_CHECKING:
    from .._models import ShareProperties, AccessPolicy


class ShareClient(AsyncStorageAccountHostsMixin, ShareClientBase):
    """A client to interact with a specific share, although that share may not yet exist.

    For operations relating to a specific directory or file in this share, the clients for
    those entities can also be retrieved using the :func:`get_directory_client` and :func:`get_file_client` functions.

    :ivar str url:
        The full endpoint URL to the Share, including snapshot and SAS token if used. This could be
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
        The URI to the storage account. In order to create a client given the full URI to the share,
        use the :func:`from_share_url` classmethod.
    :param share_name:
        The name of the share with which to interact.
    :type share_name: str
    :param str snapshot:
        An optional share snapshot on which to operate. This can be the snapshot ID string
        or the response returned from :func:`create_snapshot`.
    :param credential:
        The credential with which to authenticate. This is optional if the
        account URL already has a SAS token. The value can be a SAS token string or an account
        shared access key.
    :keyword loop:
        The event loop to run the asynchronous tasks.
    """
    def __init__( # type: ignore
            self, account_url,  # type: str
            share_name,  # type: str
            snapshot=None,  # type: Optional[Union[str, Dict[str, Any]]]
            credential=None,  # type: Optional[Any]
            **kwargs  # type: Any
        ):
        # type: (...) -> None
        kwargs['retry_policy'] = kwargs.get('retry_policy') or ExponentialRetry(**kwargs)
        loop = kwargs.pop('loop', None)
        super(ShareClient, self).__init__(
            account_url,
            share_name=share_name,
            snapshot=snapshot,
            credential=credential,
            loop=loop,
            **kwargs)
        self._client = AzureFileStorage(version=VERSION, url=self.url, pipeline=self._pipeline, loop=loop)
        self._loop = loop

    def get_directory_client(self, directory_path=None):
        # type: (Optional[str]) -> DirectoryClient
        """Get a client to interact with the specified directory.
        The directory need not already exist.

        :param str directory_path:
            Path to the specified directory.
        :returns: A Directory Client.
        :rtype: ~azure.storage.file.aio.DirectoryClient
        """
        _pipeline = AsyncPipeline(
            transport=AsyncTransportWrapper(self._pipeline._transport), # pylint: disable = protected-access
            policies=self._pipeline._impl_policies # pylint: disable = protected-access
        )

        return DirectoryClient(
            self.url, share_name=self.share_name, directory_path=directory_path or "", snapshot=self.snapshot,
            credential=self.credential, _hosts=self._hosts, _configuration=self._config, _pipeline=_pipeline,
            _location_mode=self._location_mode, loop=self._loop)

    def get_file_client(self, file_path):
        # type: (str) -> FileClient
        """Get a client to interact with the specified file.
        The file need not already exist.

        :param str file_path:
            Path to the specified file.
        :returns: A File Client.
        :rtype: ~azure.storage.file.aio.FileClient
        """
        _pipeline = AsyncPipeline(
            transport=AsyncTransportWrapper(self._pipeline._transport), # pylint: disable = protected-access
            policies=self._pipeline._impl_policies # pylint: disable = protected-access
        )

        return FileClient(
            self.url, share_name=self.share_name, file_path=file_path, snapshot=self.snapshot,
            credential=self.credential, _hosts=self._hosts, _configuration=self._config,
            _pipeline=_pipeline, _location_mode=self._location_mode, loop=self._loop)

    @distributed_trace_async
    async def create_share(self, **kwargs):
        # type: (Any) -> Dict[str, Any]
        """Creates a new Share under the account. If a share with the
        same name already exists, the operation fails.

        :keyword dict(str,str) metadata:
            Name-value pairs associated with the share as metadata.
        :keyword int quota:
            The quota to be allotted.
        :keyword int timeout:
            The timeout parameter is expressed in seconds.
        :returns: Share-updated property dict (Etag and last modified).
        :rtype: dict(str, Any)

        .. admonition:: Example:

            .. literalinclude:: ../tests/test_file_samples_share_async.py
                :start-after: [START create_share]
                :end-before: [END create_share]
                :language: python
                :dedent: 8
                :caption: Creates a file share.
        """
        metadata = kwargs.pop('metadata', None)
        quota = kwargs.pop('quota', None)
        timeout = kwargs.pop('timeout', None)
        headers = kwargs.pop('headers', {})
        headers.update(add_metadata_headers(metadata)) # type: ignore

        try:
            return await self._client.share.create( # type: ignore
                timeout=timeout,
                metadata=metadata,
                quota=quota,
                cls=return_response_headers,
                headers=headers,
                **kwargs)
        except StorageErrorException as error:
            process_storage_error(error)

    @distributed_trace_async
    async def create_snapshot( # type: ignore
            self,
            **kwargs # type: Optional[Any]
        ):
        # type: (...) -> Dict[str, Any]
        """Creates a snapshot of the share.

        A snapshot is a read-only version of a share that's taken at a point in time.
        It can be read, copied, or deleted, but not modified. Snapshots provide a way
        to back up a share as it appears at a moment in time.

        A snapshot of a share has the same name as the base share from which the snapshot
        is taken, with a DateTime value appended to indicate the time at which the
        snapshot was taken.

        :keyword dict(str,str) metadata:
            Name-value pairs associated with the share as metadata.
        :keyword int timeout:
            The timeout parameter is expressed in seconds.
        :returns: Share-updated property dict (Snapshot ID, Etag, and last modified).
        :rtype: dict[str, Any]

        .. admonition:: Example:

            .. literalinclude:: ../tests/test_file_samples_share_async.py
                :start-after: [START create_share_snapshot]
                :end-before: [END create_share_snapshot]
                :language: python
                :dedent: 12
                :caption: Creates a snapshot of the file share.
        """
        metadata = kwargs.pop('metadata', None)
        timeout = kwargs.pop('timeout', None)
        headers = kwargs.pop('headers', {})
        headers.update(add_metadata_headers(metadata)) # type: ignore
        try:
            return await self._client.share.create_snapshot( # type: ignore
                timeout=timeout,
                cls=return_response_headers,
                headers=headers,
                **kwargs)
        except StorageErrorException as error:
            process_storage_error(error)

    @distributed_trace_async
    async def delete_share(
            self, delete_snapshots=False, # type: Optional[bool]
            **kwargs
        ):
        # type: (...) -> None
        """Marks the specified share for deletion. The share is
        later deleted during garbage collection.

        :param bool delete_snapshots:
            Indicates if snapshots are to be deleted.
        :keyword int timeout:
            The timeout parameter is expressed in seconds.
        :rtype: None

        .. admonition:: Example:

            .. literalinclude:: ../tests/test_file_samples_share_async.py
                :start-after: [START delete_share]
                :end-before: [END delete_share]
                :language: python
                :dedent: 12
                :caption: Deletes the share and any snapshots.
        """
        timeout = kwargs.pop('timeout', None)
        delete_include = None
        if delete_snapshots:
            delete_include = DeleteSnapshotsOptionType.include
        try:
            await self._client.share.delete(
                timeout=timeout,
                sharesnapshot=self.snapshot,
                delete_snapshots=delete_include,
                **kwargs)
        except StorageErrorException as error:
            process_storage_error(error)

    @distributed_trace_async
    async def get_share_properties(self, **kwargs):
        # type: (Any) -> ShareProperties
        """Returns all user-defined metadata and system properties for the
        specified share. The data returned does not include the shares's
        list of files or directories.

        :keyword int timeout:
            The timeout parameter is expressed in seconds.
        :returns: The share properties.
        :rtype: ~azure.storage.file.ShareProperties

        .. admonition:: Example:

            .. literalinclude:: ../tests/test_file_samples_hello_world_async.py
                :start-after: [START get_share_properties]
                :end-before: [END get_share_properties]
                :language: python
                :dedent: 12
                :caption: Gets the share properties.
        """
        timeout = kwargs.pop('timeout', None)
        try:
            props = await self._client.share.get_properties(
                timeout=timeout,
                sharesnapshot=self.snapshot,
                cls=deserialize_share_properties,
                **kwargs)
        except StorageErrorException as error:
            process_storage_error(error)
        props.name = self.share_name
        props.snapshot = self.snapshot
        return props # type: ignore

    @distributed_trace_async
    async def set_share_quota(self, quota, **kwargs):
        # type: (int, Any) ->  Dict[str, Any]
        """Sets the quota for the share.

        :param int quota:
            Specifies the maximum size of the share, in gigabytes.
            Must be greater than 0, and less than or equal to 5TB.
        :keyword int timeout:
            The timeout parameter is expressed in seconds.
        :returns: Share-updated property dict (Etag and last modified).
        :rtype: dict(str, Any)

        .. admonition:: Example:

            .. literalinclude:: ../tests/test_file_samples_share_async.py
                :start-after: [START set_share_quota]
                :end-before: [END set_share_quota]
                :language: python
                :dedent: 12
                :caption: Sets the share quota.
        """
        timeout = kwargs.pop('timeout', None)
        try:
            return await self._client.share.set_quota( # type: ignore
                timeout=timeout,
                quota=quota,
                cls=return_response_headers,
                **kwargs)
        except StorageErrorException as error:
            process_storage_error(error)

    @distributed_trace_async
    async def set_share_metadata(self, metadata, **kwargs):
        # type: (Dict[str, Any], Any) ->  Dict[str, Any]
        """Sets the metadata for the share.

        Each call to this operation replaces all existing metadata
        attached to the share. To remove all metadata from the share,
        call this operation with no metadata dict.

        :param metadata:
            Name-value pairs associated with the share as metadata.
        :type metadata: dict(str, str)
        :keyword int timeout:
            The timeout parameter is expressed in seconds.
        :returns: Share-updated property dict (Etag and last modified).
        :rtype: dict(str, Any)

        .. admonition:: Example:

            .. literalinclude:: ../tests/test_file_samples_share_async.py
                :start-after: [START set_share_metadata]
                :end-before: [END set_share_metadata]
                :language: python
                :dedent: 12
                :caption: Sets the share metadata.
        """
        timeout = kwargs.pop('timeout', None)
        headers = kwargs.pop('headers', {})
        headers.update(add_metadata_headers(metadata))
        try:
            return await self._client.share.set_metadata( # type: ignore
                timeout=timeout,
                cls=return_response_headers,
                headers=headers,
                **kwargs)
        except StorageErrorException as error:
            process_storage_error(error)

    @distributed_trace_async
    async def get_share_access_policy(self, **kwargs):
        # type: (Any) -> Dict[str, Any]
        """Gets the permissions for the share. The permissions
        indicate whether files in a share may be accessed publicly.

        :keyword int timeout:
            The timeout parameter is expressed in seconds.
        :returns: Access policy information in a dict.
        :rtype: dict[str, Any]
        """
        timeout = kwargs.pop('timeout', None)
        try:
            response, identifiers = await self._client.share.get_access_policy(
                timeout=timeout,
                cls=return_headers_and_deserialized,
                **kwargs)
        except StorageErrorException as error:
            process_storage_error(error)
        return {
            'public_access': response.get('share_public_access'),
            'signed_identifiers': identifiers or []
        }

    @distributed_trace_async
    async def set_share_access_policy(self, signed_identifiers, **kwargs):
        # type: (Dict[str, AccessPolicy], Any) -> Dict[str, str]
        """Sets the permissions for the share, or stored access
        policies that may be used with Shared Access Signatures. The permissions
        indicate whether files in a share may be accessed publicly.

        :param signed_identifiers:
            A dictionary of access policies to associate with the share. The
            dictionary may contain up to 5 elements. An empty dictionary
            will clear the access policies set on the service.
        :type signed_identifiers: dict(str, :class:`~azure.storage.file.AccessPolicy`)
        :keyword int timeout:
            The timeout parameter is expressed in seconds.
        :returns: Share-updated property dict (Etag and last modified).
        :rtype: dict(str, Any)
        """
        timeout = kwargs.pop('timeout', None)
        if len(signed_identifiers) > 5:
            raise ValueError(
                'Too many access policies provided. The server does not support setting '
                'more than 5 access policies on a single resource.')
        identifiers = []
        for key, value in signed_identifiers.items():
            if value:
                value.start = serialize_iso(value.start)
                value.expiry = serialize_iso(value.expiry)
            identifiers.append(SignedIdentifier(id=key, access_policy=value))
        signed_identifiers = identifiers # type: ignore

        try:
            return await self._client.share.set_access_policy( # type: ignore
                share_acl=signed_identifiers or None,
                timeout=timeout,
                cls=return_response_headers,
                **kwargs)
        except StorageErrorException as error:
            process_storage_error(error)

    @distributed_trace_async
    async def get_share_stats(self, **kwargs):
        # type: (Any) -> int
        """Gets the approximate size of the data stored on the share in bytes.

        Note that this value may not include all recently created
        or recently re-sized files.

        :keyword int timeout:
            The timeout parameter is expressed in seconds.
        :return: The approximate size of the data (in bytes) stored on the share.
        :rtype: int
        """
        timeout = kwargs.pop('timeout', None)
        try:
            stats = await self._client.share.get_statistics(
                timeout=timeout,
                **kwargs)
            return stats.share_usage_bytes # type: ignore
        except StorageErrorException as error:
            process_storage_error(error)

    @distributed_trace
    def list_directories_and_files( # type: ignore
            self, directory_name=None,  # type: Optional[str]
            name_starts_with=None,  # type: Optional[str]
            marker=None,  # type: Optional[str]
            **kwargs  # type: Any
        ):
        # type: (...) -> Iterable[Dict[str,str]]
        """Lists the directories and files under the share.

        :param str directory_name:
            Name of a directory.
        :param str name_starts_with:
            Filters the results to return only directories whose names
            begin with the specified prefix.
        :param str marker:
            An opaque continuation token. This value can be retrieved from the
            next_marker field of a previous generator object. If specified,
            this generator will begin returning results from this point.
        :keyword int timeout:
            The timeout parameter is expressed in seconds.
        :returns: An auto-paging iterable of dict-like DirectoryProperties and FileProperties

        .. admonition:: Example:

            .. literalinclude:: ../tests/test_file_samples_share_async.py
                :start-after: [START share_list_files_in_dir]
                :end-before: [END share_list_files_in_dir]
                :language: python
                :dedent: 12
                :caption: List directories and files in the share.
        """
        timeout = kwargs.pop('timeout', None)
        directory = self.get_directory_client(directory_name)
        return directory.list_directories_and_files(
            name_starts_with=name_starts_with, marker=marker, timeout=timeout, **kwargs)

    @distributed_trace_async
    async def create_permission_for_share(self, file_permission,  # type: str
                                          **kwargs  # type: Any
                                          ):
        # type: (...) -> str
        """Create a permission (a security descriptor) at the share level.

        This 'permission' can be used for the files/directories in the share.
        If a 'permission' already exists, it shall return the key of it, else
        creates a new permission at the share level and return its key.

        :param str file_permission:
            File permission, a Portable SDDL
        :keyword int timeout:
            The timeout parameter is expressed in seconds.
        :returns: A file permission key
        :rtype: str
        """
        timeout = kwargs.pop('timeout', None)
        options = self._create_permission_for_share_options(file_permission, timeout=timeout, **kwargs)
        try:
            return await self._client.share.create_permission(**options)
        except StorageErrorException as error:
            process_storage_error(error)

    @distributed_trace_async
    async def get_permission_for_share(  # type: ignore
            self, permission_key,  # type: str
            **kwargs  # type: Any
    ):
        # type: (...) -> str
        """Get a permission (a security descriptor) for a given key.

        This 'permission' can be used for the files/directories in the share.

        :param str permission_key:
            Key of the file permission to retrieve
        :keyword int timeout:
            The timeout parameter is expressed in seconds.
        :returns: A file permission (a portable SDDL)
        :rtype: str
        """
        timeout = kwargs.pop('timeout', None)
        try:
            return await self._client.share.get_permission(  # type: ignore
                file_permission_key=permission_key,
                cls=deserialize_permission,
                timeout=timeout,
                **kwargs)
        except StorageErrorException as error:
            process_storage_error(error)

    @distributed_trace_async
    async def create_directory(self, directory_name, **kwargs):
        # type: (str, Any) -> DirectoryClient
        """Creates a directory in the share and returns a client to interact
        with the directory.

        :param str directory_name:
            The name of the directory.
        :keyword dict(str,str) metadata:
            Name-value pairs associated with the directory as metadata.
        :keyword int timeout:
            The timeout parameter is expressed in seconds.
        :returns: DirectoryClient
        :rtype: ~azure.storage.file.aio.DirectoryClient
        """
        directory = self.get_directory_client(directory_name)
        kwargs.setdefault('merge_span', True)
        await directory.create_directory(**kwargs)
        return directory # type: ignore
