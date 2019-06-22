# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------

import functools
from typing import (  # pylint: disable=unused-import
    Union, Optional, Any, Iterable, Dict, List,
    TYPE_CHECKING
)
try:
    from urllib.parse import urlparse
except ImportError:
    from urlparse import urlparse

from ._shared.shared_access_signature import SharedAccessSignature
from ._shared.models import LocationMode, Services
from ._shared.utils import (
    StorageAccountHostsMixin,
    return_response_headers,
    parse_connection_str,
    process_storage_error,
    parse_query)
from ._generated import AzureBlobStorage
from ._generated.models import StorageErrorException, StorageServiceProperties
from .container_client import ContainerClient
from .blob_client import BlobClient
from .models import ContainerProperties, ContainerPropertiesPaged

if TYPE_CHECKING:
    from datetime import datetime
    from azure.core.pipeline.transport import HttpTransport
    from azure.core.pipeline.policies import HTTPPolicy
    from ._shared.models import AccountPermissions, ResourceTypes
    from .lease import LeaseClient
    from .models import (
        BlobProperties,
        Logging,
        Metrics,
        RetentionPolicy,
        StaticWebsite,
        CorsRule
    )


class BlobServiceClient(StorageAccountHostsMixin):
    """ A client interact with the Blob Service at the account level.

    This client provides operations to retrieve and configure the account properties
    as well as list, create and delete containers within the account.
    For operations relating to a specific container or blob, clients for those entities
    can also be retrieved using the `get_client` functions.

    :param str account_url:
        The URL to the blob storage account. Any other entities included
        in the URL path (e.g. container or blob) will be discarded. This URL can be optionally
        authenticated with a SAS token.
    :param credential:
        The credentials with which to authenticate. This is optional if the
        account URL already has a SAS token. The value can be a SAS token string, and account
        shared access key, or an instance of a TokenCredentials class from azure.identity.
    """

    def __init__(
            self, account_url,  # type: str
            credential=None,  # type: Optional[Any]
            **kwargs  # type: Any
        ):
        # type: (...) -> None
        try:
            if not account_url.lower().startswith('http'):
                account_url = "https://" + account_url
        except AttributeError:
            raise ValueError("Account URL must be a string.")
        parsed_url = urlparse(account_url.rstrip('/'))
        if not parsed_url.netloc:
            raise ValueError("Invalid URL: {}".format(account_url))

        _, sas_token = parse_query(parsed_url.query)
        self._query_str, credential = self._format_query_string(sas_token, credential)
        super(BlobServiceClient, self).__init__(parsed_url, 'blob', credential, **kwargs)
        self._client = AzureBlobStorage(self.url, pipeline=self._pipeline)

    def _format_url(self, hostname):
        """Format the endpoint URL according to the current location
        mode hostname.
        """
        return "{}://{}/{}".format(self.scheme, hostname, self._query_str)

    @classmethod
    def from_connection_string(
            cls, conn_str,  # type: str
            credential=None,  # type: Optional[Any]
            **kwargs  # type: Any
        ):
        """Create BlobServiceClient from a Connection String.

        :param str conn_str:
            A connection string to an Azure Storage account.
        :param credential:
            The credentials with which to authenticate. This is optional if the
            account URL already has a SAS token, or the connection string already has shared
            access key values. The value can be a SAS token string, and account shared access
            key, or an instance of a TokenCredentials class from azure.identity.
        """
        account_url, secondary, credential = parse_connection_str(conn_str, credential, 'blob')
        if 'secondary_hostname' not in kwargs:
            kwargs['secondary_hostname'] = secondary
        return cls(account_url, credential=credential, **kwargs)

    def generate_shared_access_signature(
            self, resource_types,  # type: Union[ResourceTypes, str]
            permission,  # type: Union[AccountPermissions, str]
            expiry,  # type: Optional[Union[datetime, str]]
            start=None,  # type: Optional[Union[datetime, str]]
            ip=None,  # type: Optional[str]
            protocol=None  # type: Optional[str]
        ):
        """
        Generates a shared access signature for the blob service.
        Use the returned signature with the credential parameter of any BlobServiceClient,
        ContainerClient or BlobClient.

        :param ~azure.storage.blob.models.ResourceTypes resource_types:
            Specifies the resource types that are accessible with the account SAS.
        :param ~azure.storage.blob.models.AccountPermissions permission:
            The permissions associated with the shared access signature. The
            user is restricted to operations allowed by the permissions.
            Required unless an id is given referencing a stored access policy
            which contains this field. This field must be omitted if it has been
            specified in an associated stored access policy.
        :param expiry:
            The time at which the shared access signature becomes invalid.
            Required unless an id is given referencing a stored access policy
            which contains this field. This field must be omitted if it has
            been specified in an associated stored access policy. Azure will always
            convert values to UTC. If a date is passed in without timezone info, it
            is assumed to be UTC.
        :type expiry: datetime or str
        :param start:
            The time at which the shared access signature becomes valid. If
            omitted, start time for this call is assumed to be the time when the
            storage service receives the request. Azure will always convert values
            to UTC. If a date is passed in without timezone info, it is assumed to
            be UTC.
        :type start: datetime or str
        :param str ip:
            Specifies an IP address or a range of IP addresses from which to accept requests.
            If the IP address from which the request originates does not match the IP address
            or address range specified on the SAS token, the request is not authenticated.
            For example, specifying sip=168.1.5.65 or sip=168.1.5.60-168.1.5.70 on the SAS
            restricts the request to those IP addresses.
        :param str protocol:
            Specifies the protocol permitted for a request made. The default value is https.
        :return: A Shared Access Signature (sas) token.
        :rtype: str
        """
        if not hasattr(self.credential, 'account_key') and not self.credential.account_key:
            raise ValueError("No account SAS key available.")

        sas = SharedAccessSignature(self.credential.account_name, self.credential.account_key)
        return sas.generate_account(
            Services.BLOB, resource_types, permission, expiry, start=start, ip=ip, protocol=protocol)

    def get_account_information(self, **kwargs):
        # type: (Optional[int]) -> Dict[str, str]
        """Gets information related to the storage account.
        The information can also be retrieved if the user has a SAS to a container or blob.

        :returns: A dict of account information (SKU and account type).
        :rtype: dict(str, str)
        """
        try:
            return self._client.service.get_account_info(cls=return_response_headers, **kwargs)
        except StorageErrorException as error:
            process_storage_error(error)

    def get_service_stats(self, timeout=None, **kwargs):
        # type: (Optional[int], **Any) -> Dict[str, Any]
        """Retrieves statistics related to replication for the Blob service. It is
        only available when read-access geo-redundant replication is enabled for
        the storage account.

        With geo-redundant replication, Azure Storage maintains your data durable
        in two locations. In both locations, Azure Storage constantly maintains
        multiple healthy replicas of your data. The location where you read,
        create, update, or delete data is the primary storage account location.
        The primary location exists in the region you choose at the time you
        create an account via the Azure Management Azure classic portal, for
        example, North Central US. The location to which your data is replicated
        is the secondary location. The secondary location is automatically
        determined based on the location of the primary; it is in a second data
        center that resides in the same region as the primary location. Read-only
        access is available from the secondary location, if read-access geo-redundant
        replication is enabled for your storage account.

        :param int timeout:
            The timeout parameter is expressed in seconds.
        :return: The blob service stats.
        :rtype: ~azure.storage.blob._generated.models.StorageServiceStats
        """
        try:
            return self._client.service.get_statistics(
                timeout=timeout, use_location=LocationMode.SECONDARY, **kwargs)
        except StorageErrorException as error:
            process_storage_error(error)

    def get_service_properties(self, timeout=None, **kwargs):
        # type(Optional[int]) -> Dict[str, Any]
        """Gets the properties of a storage account's Blob service, including
        Azure Storage Analytics.

        :param int timeout:
            The timeout parameter is expressed in seconds.
        :rtype: ~azure.storage.blob._generated.models.StorageServiceProperties
        """
        try:
            return self._client.service.get_properties(timeout=timeout, **kwargs)
        except StorageErrorException as error:
            process_storage_error(error)

    def set_service_properties(
            self, logging=None,  # type: Optional[Logging]
            hour_metrics=None,  # type: Optional[Metrics]
            minute_metrics=None,  # type: Optional[Metrics]
            cors=None,  # type: Optional[List[CorsRule]]
            target_version=None,  # type: Optional[str]
            delete_retention_policy=None,  # type: Optional[RetentionPolicy]
            static_website=None,  # type: Optional[StaticWebsite]
            timeout=None,  # type: Optional[int]
            **kwargs
        ):
        # type: (...) -> None
        """Sets the properties of a storage account's Blob service, including
        Azure Storage Analytics. If an element (e.g. Logging) is left as None, the
        existing settings on the service for that functionality are preserved.

        :param logging:
            Groups the Azure Analytics Logging settings.
        :type logging:
            :class:`~azure.storage.blob.models.Logging`
        :param hour_metrics:
            The hour metrics settings provide a summary of request
            statistics grouped by API in hourly aggregates for blobs.
        :type hour_metrics:
            :class:`~azure.storage.blob.models.Metrics`
        :param minute_metrics:
            The minute metrics settings provide request statistics
            for each minute for blobs.
        :type minute_metrics:
            :class:`~azure.storage.blob.models.Metrics`
        :param cors:
            You can include up to five CorsRule elements in the
            list. If an empty list is specified, all CORS rules will be deleted,
            and CORS will be disabled for the service.
        :type cors: list(:class:`~azure.storage.blob.models.CorsRule`)
        :param str target_version:
            Indicates the default version to use for requests if an incoming
            request's version is not specified.
        :param delete_retention_policy:
            The delete retention policy specifies whether to retain deleted blobs.
            It also specifies the number of days and versions of blob to keep.
        :type delete_retention_policy:
            :class:`~azure.storage.blob.models.RetentionPolicy`
        :param static_website:
            Specifies whether the static website feature is enabled,
            and if yes, indicates the index document and 404 error document to use.
        :type static_website:
            :class:`~azure.storage.blob.models.StaticWebsite`
        :param int timeout:
            The timeout parameter is expressed in seconds.
        :rtype: None
        """
        props = StorageServiceProperties(
            logging=logging,
            hour_metrics=hour_metrics,
            minute_metrics=minute_metrics,
            cors=cors,
            default_service_version=target_version,
            delete_retention_policy=delete_retention_policy,
            static_website=static_website
        )
        try:
            self._client.service.set_properties(props, timeout=timeout, **kwargs)
        except StorageErrorException as error:
            process_storage_error(error)

    def list_containers(
            self, name_starts_with=None,  # type: Optional[str]
            include_metadata=False,  # type: Optional[bool]
            marker=None,  # type: Optional[str]
            results_per_page=None,  # type: Optional[int]
            timeout=None,  # type: Optional[int]
            **kwargs
        ):
        # type: (...) -> ContainerPropertiesPaged
        """Returns a generator to list the containers under the specified account.
        The generator will lazily follow the continuation tokens returned by
        the service and stop when all containers have been returned.

        :param str name_starts_with:
            Filters the results to return only containers whose names
            begin with the specified prefix.
        :param bool include_metadata:
            Specifies that container metadata be returned in the response.
        :param str marker:
            An opaque continuation token. This value can be retrieved from the
            next_marker field of a previous generator object. If specified,
            this generator will begin returning results from this point.
        :param int results_per_page:
            The maximum number of container names to retrieve per API
            call. If the request does not specify the server will return up to 5,000 items.
        :param int timeout:
            The timeout parameter is expressed in seconds.
        :returns: An iterable (auto-paging) of ContainerProperties.
        :rtype: ~azure.core.blob.models.ContainerPropertiesPaged
        """
        include = 'metadata' if include_metadata else None
        command = functools.partial(
            self._client.service.list_containers_segment,
            prefix=name_starts_with,
            include=include,
            timeout=timeout,
            **kwargs)
        return ContainerPropertiesPaged(
            command, prefix=name_starts_with, results_per_page=results_per_page, marker=marker)

    def create_container(
            self, name,  # type: str
            metadata=None,  # type: Optional[Dict[str, str]]
            public_access=None,  # type: Optional[Union[PublicAccess, str]]
            timeout=None,  # type: Optional[int]
            **kwargs
        ):
        # type: (...) -> ContainerClient
        """Creates a new container under the specified account. If the container
        with the same name already exists, the operation fails. Returns a client with
        which to interact with the newly created container.

        :param str name: The name of the container to create.
        :param metadata:
            A dict with name_value pairs to associate with the
            container as metadata. Example:{'Category':'test'}
        :type metadata: dict(str, str)
        :param ~azure.storage.blob.common.PublicAccess public_access:
            Possible values include: container, blob.
        :param int timeout:
            The timeout parameter is expressed in seconds.
        :rtype: ~azure.storage.blob.container_client.ContainerClient
        """
        container = self.get_container_client(name)
        container.create_container(
            metadata=metadata, public_access=public_access, timeout=timeout, **kwargs)
        return container

    def delete_container(
            self, container,  # type: Union[ContainerProperties, str]
            lease=None,  # type: Optional[Union[LeaseClient, str]]
            if_modified_since=None,  # type: Optional[datetime]
            if_unmodified_since=None,  # type: Optional[datetime]
            if_match=None,  # type: Optional[str]
            if_none_match=None,  # type: Optional[str]
            timeout=None,  # type: Optional[int]
            **kwargs
        ):
        # type: (...) -> None
        """Marks the specified container for deletion. The container and any blobs
        contained within it are later deleted during garbage collection.

        :param container:
            The container to delete. This can either be the name of the container,
            or an instance of ContainerProperties.
        :type container: str or ~azure.storage.blob.models.ContainerProperties
        :param ~azure.storage.blob.lease.LeaseClient lease:
            If specified, delete_container only succeeds if the
            container's lease is active and matches this ID.
            Required if the container has an active lease.
        :param datetime if_modified_since:
            A DateTime value. Azure expects the date value passed in to be UTC.
            If timezone is included, any non-UTC datetimes will be converted to UTC.
            If a date is passed in without timezone info, it is assumed to be UTC.
            Specify this header to perform the operation only
            if the resource has been modified since the specified time.
        :param datetime if_unmodified_since:
            A DateTime value. Azure expects the date value passed in to be UTC.
            If timezone is included, any non-UTC datetimes will be converted to UTC.
            If a date is passed in without timezone info, it is assumed to be UTC.
            Specify this header to perform the operation only if
            the resource has not been modified since the specified date/time.
        :param str if_match:
            An ETag value, or the wildcard character (*). Specify this header to perform
            the operation only if the resource's ETag matches the value specified.
        :param str if_none_match:
            An ETag value, or the wildcard character (*). Specify this header
            to perform the operation only if the resource's ETag does not match
            the value specified. Specify the wildcard character (*) to perform
            the operation only if the resource does not exist, and fail the
            operation if it does exist.
        :param int timeout:
            The timeout parameter is expressed in seconds.
        :rtype: None
        """
        container = self.get_container_client(container)
        container.delete_container(
            lease=lease,
            if_modified_since=if_modified_since,
            if_unmodified_since=if_unmodified_since,
            if_match=if_match,
            if_none_match=if_none_match,
            timeout=timeout,
            **kwargs)

    def get_container_client(self, container):
        # type: (Union[ContainerProperties, str]) -> ContainerClient
        """Get a client to interact with the specified container.
        The container need not already exist.

        :param container:
            The container. This can either be the name of the container,
            or an instance of ContainerProperties.
        :type container: str or ~azure.storage.blob.models.ContainerProperties
        :returns: A ContainerClient.
        :rtype: ~azure.core.blob.container_client.ContainerClient
        """
        return ContainerClient(
            self.url, container=container,
            credential=self.credential, _configuration=self._config,
            _pipeline=self._pipeline, _location_mode=self._location_mode, _hosts=self._hosts,
            require_encryption=self.require_encryption, key_encryption_key=self.key_encryption_key,
            key_resolver_function=self.key_resolver_function)

    def get_blob_client(
            self, container,  # type: Union[ContainerProperties, str]
            blob,  # type: Union[BlobProperties, str]
            snapshot=None  # type: Optional[Union[SnapshotProperties, str]]
        ):
        # type: (...) -> BlobClient
        """Get a client to interact with the specified blob.
        The blob need not already exist.

        :param container:
            The container that the blob is in. This can either be the name of the container,
            or an instance of ContainerProperties.
        :type container: str or ~azure.storage.blob.models.ContainerProperties
        :param blob:
            The blob with which to interact. This can either be the name of the blob,
            or an instance of BlobProperties.
        :type blob: str or ~azure.storage.blob.models.BlobProperties
        :param str snapshot:
            The optional blob snapshot on which to operate.
        :returns: A BlobClient.
        :rtype: ~azure.core.blob.blob_client.BlobClient
        """
        return BlobClient(
            self.url, container=container, blob=blob, snapshot=snapshot,
            credential=self.credential, _configuration=self._config,
            _pipeline=self._pipeline, _location_mode=self._location_mode, _hosts=self._hosts,
            require_encryption=self.require_encryption, key_encryption_key=self.key_encryption_key,
            key_resolver_function=self.key_resolver_function)
