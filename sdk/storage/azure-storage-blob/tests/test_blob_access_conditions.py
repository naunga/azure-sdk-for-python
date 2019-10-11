# coding: utf-8

# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------
import pytest

import datetime
import os
import unittest

from azure.core.exceptions import HttpResponseError, ResourceNotFoundError, ResourceModifiedError
from devtools_testutils import ResourceGroupPreparer, StorageAccountPreparer
from azure.storage.blob import (
    BlobServiceClient,
    ContainerClient,
    BlobClient,
    LeaseClient,
    StorageErrorCode,
    BlobBlock,
    BlobType,
    ContentSettings,
    BlobProperties
)
from testcase import (
    StorageTestCase
)

# ------------------------------------------------------------------------------
LARGE_APPEND_BLOB_SIZE = 64 * 1024
# ------------------------------------------------------------------------------


class StorageBlobAccessConditionsTest(StorageTestCase):

    # --Helpers-----------------------------------------------------------------
    def _setup(self):
        self.container_name = self.get_resource_name('utcontainer')

    def _create_container(self, container_name, bsc):
        container = bsc.get_container_client(container_name)
        container.create_container()
        return container

    def _create_container_and_block_blob(self, container_name, blob_name,
                                         blob_data, bsc):
        container = self._create_container(container_name, bsc)
        blob = bsc.get_blob_client(container_name, blob_name)
        resp = blob.upload_blob(blob_data, length=len(blob_data))
        self.assertIsNotNone(resp.get('etag'))
        return container, blob

    def _create_container_and_page_blob(self, container_name, blob_name,
                                        content_length, bsc):
        container = self._create_container(container_name, bsc)
        blob = bsc.get_blob_client(container_name, blob_name)
        resp = blob.create_page_blob(str(content_length))
        return container, blob

    def _create_container_and_append_blob(self, container_name, blob_name, bsc):
        container = self._create_container(container_name, bsc)
        blob = bsc.get_blob_client(container_name, blob_name)
        resp = blob.create_append_blob()
        return container, blob

    # --Test cases for blob service --------------------------------------------
    @ResourceGroupPreparer()
    @StorageAccountPreparer(name_prefix='pyacrstorage')
    def test_set_container_metadata_with_if_modified(self, resource_group, location, storage_account, storage_account_key):
        bsc = BlobServiceClient(self._account_url(storage_account.name), storage_account_key, connection_data_block_size=4 * 1024)
        self._setup()
        container = self._create_container(self.container_name, bsc)
        test_datetime = (datetime.datetime.utcnow() -
                         datetime.timedelta(minutes=15))

        # Act
        metadata = {'hello': 'world', 'number': '43'}
        container.set_container_metadata(metadata, if_modified_since=test_datetime)

        # Assert
        md = container.get_container_properties().metadata
        self.assertDictEqual(metadata, md)

    @ResourceGroupPreparer()
    @StorageAccountPreparer(name_prefix='pyacrstorage')
    def test_set_container_metadata_with_if_modified_fail(self, resource_group, location, storage_account, storage_account_key):
        bsc = BlobServiceClient(self._account_url(storage_account.name), storage_account_key, connection_data_block_size=4 * 1024)
        self._setup()
        container = self._create_container(self.container_name, bsc)
        test_datetime = (datetime.datetime.utcnow() +
                         datetime.timedelta(minutes=15))

        # Act
        with self.assertRaises(ResourceModifiedError) as e:
            metadata = {'hello': 'world', 'number': '43'}
            container.set_container_metadata(metadata, if_modified_since=test_datetime)

        # Assert
        self.assertEqual(StorageErrorCode.condition_not_met, e.exception.error_code)

    @ResourceGroupPreparer()
    @StorageAccountPreparer(name_prefix='pyacrstorage')
    def test_set_container_acl_with_if_modified(self, resource_group, location, storage_account, storage_account_key):
        bsc = BlobServiceClient(self._account_url(storage_account.name), storage_account_key, connection_data_block_size=4 * 1024)
        self._setup()
        container = self._create_container(self.container_name, bsc)
        test_datetime = (datetime.datetime.utcnow() -
                         datetime.timedelta(minutes=15))
        # Act
        container.set_container_access_policy(if_modified_since=test_datetime)

        # Assert
        acl = container.get_container_access_policy()
        self.assertIsNotNone(acl)

    @ResourceGroupPreparer()
    @StorageAccountPreparer(name_prefix='pyacrstorage')
    def test_set_container_acl_with_if_modified_fail(self, resource_group, location, storage_account, storage_account_key):
        bsc = BlobServiceClient(self._account_url(storage_account.name), storage_account_key, connection_data_block_size=4 * 1024)
        self._setup()
        container = self._create_container(self.container_name, bsc)
        test_datetime = (datetime.datetime.utcnow() +
                         datetime.timedelta(minutes=15))
        # Act
        with self.assertRaises(ResourceModifiedError) as e:
            container.set_container_access_policy(if_modified_since=test_datetime)

        # Assert
        self.assertEqual(StorageErrorCode.condition_not_met, e.exception.error_code)

    @ResourceGroupPreparer()
    @StorageAccountPreparer(name_prefix='pyacrstorage')
    def test_set_container_acl_with_if_unmodified(self, resource_group, location, storage_account, storage_account_key):
        bsc = BlobServiceClient(self._account_url(storage_account.name), storage_account_key, connection_data_block_size=4 * 1024)
        self._setup()
        container = self._create_container(self.container_name, bsc)
        test_datetime = (datetime.datetime.utcnow() +
                         datetime.timedelta(minutes=15))
        # Act
        container.set_container_access_policy(if_unmodified_since=test_datetime)

        # Assert
        acl = container.get_container_access_policy()
        self.assertIsNotNone(acl)

    @ResourceGroupPreparer()
    @StorageAccountPreparer(name_prefix='pyacrstorage')
    def test_set_container_acl_with_if_unmodified_fail(self, resource_group, location, storage_account, storage_account_key):
        bsc = BlobServiceClient(self._account_url(storage_account.name), storage_account_key, connection_data_block_size=4 * 1024)
        self._setup()
        container = self._create_container(self.container_name, bsc)
        test_datetime = (datetime.datetime.utcnow() -
                         datetime.timedelta(minutes=15))
        # Act
        with self.assertRaises(ResourceModifiedError) as e:
            container.set_container_access_policy(if_unmodified_since=test_datetime)

        # Assert
        self.assertEqual(StorageErrorCode.condition_not_met, e.exception.error_code)

    @ResourceGroupPreparer()
    @StorageAccountPreparer(name_prefix='pyacrstorage')
    def test_lease_container_acquire_with_if_modified(self, resource_group, location, storage_account, storage_account_key):
        bsc = BlobServiceClient(self._account_url(storage_account.name), storage_account_key, connection_data_block_size=4 * 1024)
        self._setup()
        container = self._create_container(self.container_name, bsc)
        test_datetime = (datetime.datetime.utcnow() -
                         datetime.timedelta(minutes=15))

        # Act
        lease = container.acquire_lease(if_modified_since=test_datetime)
        lease.break_lease()

        # Assert

    @ResourceGroupPreparer()
    @StorageAccountPreparer(name_prefix='pyacrstorage')
    def test_lease_container_acquire_with_if_modified_fail(self, resource_group, location, storage_account, storage_account_key):
        bsc = BlobServiceClient(self._account_url(storage_account.name), storage_account_key, connection_data_block_size=4 * 1024)
        self._setup()
        container = self._create_container(self.container_name, bsc)
        test_datetime = (datetime.datetime.utcnow() +
                         datetime.timedelta(minutes=15))

        # Act
        with self.assertRaises(ResourceModifiedError) as e:
            container.acquire_lease(if_modified_since=test_datetime)

        # Assert
        self.assertEqual(StorageErrorCode.condition_not_met, e.exception.error_code)

    @ResourceGroupPreparer()
    @StorageAccountPreparer(name_prefix='pyacrstorage')
    def test_lease_container_acquire_with_if_unmodified(self, resource_group, location, storage_account, storage_account_key):
        bsc = BlobServiceClient(self._account_url(storage_account.name), storage_account_key, connection_data_block_size=4 * 1024)
        self._setup()
        container = self._create_container(self.container_name, bsc)
        test_datetime = (datetime.datetime.utcnow() +
                         datetime.timedelta(minutes=15))

        # Act
        lease = container.acquire_lease(if_unmodified_since=test_datetime)
        lease.break_lease()

        # Assert

    @ResourceGroupPreparer()
    @StorageAccountPreparer(name_prefix='pyacrstorage')
    def test_lease_container_acquire_with_if_unmodified_fail(self, resource_group, location, storage_account, storage_account_key):
        bsc = BlobServiceClient(self._account_url(storage_account.name), storage_account_key, connection_data_block_size=4 * 1024)
        self._setup()
        container = self._create_container(self.container_name, bsc)
        test_datetime = (datetime.datetime.utcnow() -
                         datetime.timedelta(minutes=15))

        # Act
        with self.assertRaises(ResourceModifiedError) as e:
            container.acquire_lease(if_unmodified_since=test_datetime)

        # Assert
        self.assertEqual(StorageErrorCode.condition_not_met, e.exception.error_code)

    @ResourceGroupPreparer()
    @StorageAccountPreparer(name_prefix='pyacrstorage')
    def test_delete_container_with_if_modified(self, resource_group, location, storage_account, storage_account_key):
        bsc = BlobServiceClient(self._account_url(storage_account.name), storage_account_key, connection_data_block_size=4 * 1024)
        self._setup()
        container = self._create_container(self.container_name, bsc)
        test_datetime = (datetime.datetime.utcnow() -
                         datetime.timedelta(minutes=15))
        # Act
        deleted = container.delete_container(if_modified_since=test_datetime)

        # Assert
        self.assertIsNone(deleted)
        with self.assertRaises(ResourceNotFoundError):
            container.get_container_properties()

    @ResourceGroupPreparer()
    @StorageAccountPreparer(name_prefix='pyacrstorage')
    def test_delete_container_with_if_modified_fail(self, resource_group, location, storage_account, storage_account_key):
        bsc = BlobServiceClient(self._account_url(storage_account.name), storage_account_key, connection_data_block_size=4 * 1024)
        self._setup()
        container = self._create_container(self.container_name, bsc)
        test_datetime = (datetime.datetime.utcnow() +
                         datetime.timedelta(minutes=15))
        # Act
        with self.assertRaises(ResourceModifiedError) as e:
            container.delete_container(if_modified_since=test_datetime)

        # Assert
        self.assertEqual(StorageErrorCode.condition_not_met, e.exception.error_code)

    @ResourceGroupPreparer()
    @StorageAccountPreparer(name_prefix='pyacrstorage')
    def test_delete_container_with_if_unmodified(self, resource_group, location, storage_account, storage_account_key):
        bsc = BlobServiceClient(self._account_url(storage_account.name), storage_account_key, connection_data_block_size=4 * 1024)
        self._setup()
        container = self._create_container(self.container_name, bsc)
        test_datetime = (datetime.datetime.utcnow() +
                         datetime.timedelta(minutes=15))
        # Act
        container.delete_container(if_unmodified_since=test_datetime)

        # Assert
        with self.assertRaises(ResourceNotFoundError):
            container.get_container_properties()

    @ResourceGroupPreparer()
    @StorageAccountPreparer(name_prefix='pyacrstorage')
    def test_delete_container_with_if_unmodified_fail(self, resource_group, location, storage_account, storage_account_key):
        bsc = BlobServiceClient(self._account_url(storage_account.name), storage_account_key, connection_data_block_size=4 * 1024)
        self._setup()
        container = self._create_container(self.container_name, bsc)
        test_datetime = (datetime.datetime.utcnow() -
                         datetime.timedelta(minutes=15))
        # Act
        with self.assertRaises(ResourceModifiedError) as e:
            container.delete_container(if_unmodified_since=test_datetime)

        self.assertEqual(StorageErrorCode.condition_not_met, e.exception.error_code)

    @ResourceGroupPreparer()
    @StorageAccountPreparer(name_prefix='pyacrstorage')
    def test_put_blob_with_if_modified(self, resource_group, location, storage_account, storage_account_key):
        bsc = BlobServiceClient(self._account_url(storage_account.name), storage_account_key, connection_data_block_size=4 * 1024)
        self._setup()
        data = b'hello world'
        container, blob = self._create_container_and_block_blob(
            self.container_name, 'blob1', data, bsc)
        test_datetime = (datetime.datetime.utcnow() -
                         datetime.timedelta(minutes=15))

        # Act
        resp = blob.upload_blob(data, length=len(data), if_modified_since=test_datetime)

        # Assert
        self.assertIsNotNone(resp.get('etag'))

    @ResourceGroupPreparer()
    @StorageAccountPreparer(name_prefix='pyacrstorage')
    def test_put_blob_with_if_modified_fail(self, resource_group, location, storage_account, storage_account_key):
        bsc = BlobServiceClient(self._account_url(storage_account.name), storage_account_key, connection_data_block_size=4 * 1024)
        self._setup()
        data = b'hello world'
        container, blob = self._create_container_and_block_blob(
            self.container_name, 'blob1', data, bsc)
        test_datetime = (datetime.datetime.utcnow() +
                         datetime.timedelta(minutes=15))

        # Act
        with self.assertRaises(ResourceModifiedError) as e:
            blob.upload_blob(data, length=len(data), if_modified_since=test_datetime, overwrite=True)

        # Assert
        self.assertEqual(StorageErrorCode.condition_not_met, e.exception.error_code)

    @ResourceGroupPreparer()
    @StorageAccountPreparer(name_prefix='pyacrstorage')
    def test_put_blob_with_if_unmodified(self, resource_group, location, storage_account, storage_account_key):
        bsc = BlobServiceClient(self._account_url(storage_account.name), storage_account_key, connection_data_block_size=4 * 1024)
        self._setup()
        data = b'hello world'
        container, blob = self._create_container_and_block_blob(
            self.container_name, 'blob1', data, bsc)
        test_datetime = (datetime.datetime.utcnow() +
                         datetime.timedelta(minutes=15))

        # Act
        resp = blob.upload_blob(data, length=len(data), if_unmodified_since=test_datetime)

        # Assert
        self.assertIsNotNone(resp.get('etag'))

    @ResourceGroupPreparer()
    @StorageAccountPreparer(name_prefix='pyacrstorage')
    def test_put_blob_with_if_unmodified_fail(self, resource_group, location, storage_account, storage_account_key):
        bsc = BlobServiceClient(self._account_url(storage_account.name), storage_account_key, connection_data_block_size=4 * 1024)
        self._setup()
        data = b'hello world'
        container, blob = self._create_container_and_block_blob(
            self.container_name, 'blob1', data, bsc)
        test_datetime = (datetime.datetime.utcnow() -
                         datetime.timedelta(minutes=15))

        # Act
        with self.assertRaises(ResourceModifiedError) as e:
            blob.upload_blob(data, length=len(data), if_unmodified_since=test_datetime, overwrite=True)

        # Assert
        self.assertEqual(StorageErrorCode.condition_not_met, e.exception.error_code)

    @ResourceGroupPreparer()
    @StorageAccountPreparer(name_prefix='pyacrstorage')
    def test_put_blob_with_if_match(self, resource_group, location, storage_account, storage_account_key):
        bsc = BlobServiceClient(self._account_url(storage_account.name), storage_account_key, connection_data_block_size=4 * 1024)
        self._setup()
        data = b'hello world'
        container, blob = self._create_container_and_block_blob(
            self.container_name, 'blob1', data, bsc)
        etag = blob.get_blob_properties().etag

        # Act
        resp = blob.upload_blob(data, length=len(data), if_match=etag)

        # Assert
        self.assertIsNotNone(resp.get('etag'))

    @ResourceGroupPreparer()
    @StorageAccountPreparer(name_prefix='pyacrstorage')
    def test_put_blob_with_if_match_fail(self, resource_group, location, storage_account, storage_account_key):
        bsc = BlobServiceClient(self._account_url(storage_account.name), storage_account_key, connection_data_block_size=4 * 1024)
        self._setup()
        data = b'hello world'
        container, blob = self._create_container_and_block_blob(
            self.container_name, 'blob1', data, bsc)

        # Act
        with self.assertRaises(ResourceModifiedError) as e:
            blob.upload_blob(data, length=len(data), if_match='0x111111111111111', overwrite=True)

        # Assert
        self.assertEqual(StorageErrorCode.condition_not_met, e.exception.error_code)

    @ResourceGroupPreparer()
    @StorageAccountPreparer(name_prefix='pyacrstorage')
    def test_put_blob_with_if_none_match(self, resource_group, location, storage_account, storage_account_key):
        bsc = BlobServiceClient(self._account_url(storage_account.name), storage_account_key, connection_data_block_size=4 * 1024)
        self._setup()
        data = b'hello world'
        container, blob = self._create_container_and_block_blob(
            self.container_name, 'blob1', data, bsc)

        # Act
        resp = blob.upload_blob(data, length=len(data), if_none_match='0x111111111111111')

        # Assert
        self.assertIsNotNone(resp.get('etag'))

    @ResourceGroupPreparer()
    @StorageAccountPreparer(name_prefix='pyacrstorage')
    def test_put_blob_with_if_none_match_fail(self, resource_group, location, storage_account, storage_account_key):
        bsc = BlobServiceClient(self._account_url(storage_account.name), storage_account_key, connection_data_block_size=4 * 1024)
        self._setup()
        data = b'hello world'
        container, blob = self._create_container_and_block_blob(
            self.container_name, 'blob1', data, bsc)
        etag = blob.get_blob_properties().etag

        # Act
        with self.assertRaises(ResourceModifiedError) as e:
            blob.upload_blob(data, length=len(data), if_none_match=etag, overwrite=True)

        # Assert
        self.assertEqual(StorageErrorCode.condition_not_met, e.exception.error_code)

    @ResourceGroupPreparer()
    @StorageAccountPreparer(name_prefix='pyacrstorage')
    def test_get_blob_with_if_modified(self, resource_group, location, storage_account, storage_account_key):
        bsc = BlobServiceClient(self._account_url(storage_account.name), storage_account_key, connection_data_block_size=4 * 1024)
        self._setup()
        container, blob = self._create_container_and_block_blob(
            self.container_name, 'blob1', b'hello world', bsc)
        test_datetime = (datetime.datetime.utcnow() -
                         datetime.timedelta(minutes=15))

        # Act
        content = blob.download_blob(if_modified_since=test_datetime)
        content = b"".join(list(content))

        # Assert
        self.assertEqual(content, b'hello world')

    @ResourceGroupPreparer()
    @StorageAccountPreparer(name_prefix='pyacrstorage')
    def test_get_blob_with_if_modified_fail(self, resource_group, location, storage_account, storage_account_key):
        bsc = BlobServiceClient(self._account_url(storage_account.name), storage_account_key, connection_data_block_size=4 * 1024)
        self._setup()
        container, blob = self._create_container_and_block_blob(
            self.container_name, 'blob1', b'hello world', bsc)
        test_datetime = (datetime.datetime.utcnow() +
                         datetime.timedelta(minutes=15))

        # Act
        with self.assertRaises(ResourceModifiedError) as e:
            blob.download_blob(if_modified_since=test_datetime)

        # Assert
        self.assertEqual(StorageErrorCode.condition_not_met, e.exception.error_code)

    @ResourceGroupPreparer()
    @StorageAccountPreparer(name_prefix='pyacrstorage')
    def test_get_blob_with_if_unmodified(self, resource_group, location, storage_account, storage_account_key):
        bsc = BlobServiceClient(self._account_url(storage_account.name), storage_account_key, connection_data_block_size=4 * 1024)
        self._setup()
        container, blob = self._create_container_and_block_blob(
            self.container_name, 'blob1', b'hello world', bsc)
        test_datetime = (datetime.datetime.utcnow() +
                         datetime.timedelta(minutes=15))

        # Act
        content = blob.download_blob(if_unmodified_since=test_datetime)
        content = b"".join(list(content))

        # Assert
        self.assertEqual(content, b'hello world')

    @ResourceGroupPreparer()
    @StorageAccountPreparer(name_prefix='pyacrstorage')
    def test_get_blob_with_if_unmodified_fail(self, resource_group, location, storage_account, storage_account_key):
        bsc = BlobServiceClient(self._account_url(storage_account.name), storage_account_key, connection_data_block_size=4 * 1024)
        self._setup()
        container, blob = self._create_container_and_block_blob(
            self.container_name, 'blob1', b'hello world', bsc)
        test_datetime = (datetime.datetime.utcnow() -
                         datetime.timedelta(minutes=15))

        # Act
        with self.assertRaises(ResourceModifiedError) as e:
            blob.download_blob(if_unmodified_since=test_datetime)

        # Assert
        self.assertEqual(StorageErrorCode.condition_not_met, e.exception.error_code)

    @ResourceGroupPreparer()
    @StorageAccountPreparer(name_prefix='pyacrstorage')
    def test_get_blob_with_if_match(self, resource_group, location, storage_account, storage_account_key):
        bsc = BlobServiceClient(self._account_url(storage_account.name), storage_account_key, connection_data_block_size=4 * 1024)
        self._setup()
        container, blob = self._create_container_and_block_blob(
            self.container_name, 'blob1', b'hello world', bsc)
        etag = blob.get_blob_properties().etag

        # Act
        content = blob.download_blob(if_match=etag)
        content = b"".join(list(content))

        # Assert
        self.assertEqual(content, b'hello world')

    @ResourceGroupPreparer()
    @StorageAccountPreparer(name_prefix='pyacrstorage')
    def test_get_blob_with_if_match_fail(self, resource_group, location, storage_account, storage_account_key):
        bsc = BlobServiceClient(self._account_url(storage_account.name), storage_account_key, connection_data_block_size=4 * 1024)
        self._setup()
        container, blob = self._create_container_and_block_blob(
            self.container_name, 'blob1', b'hello world', bsc)

        # Act
        with self.assertRaises(ResourceModifiedError) as e:
            blob.download_blob(if_match='0x111111111111111')

        # Assert
        self.assertEqual(StorageErrorCode.condition_not_met, e.exception.error_code)

    @ResourceGroupPreparer()
    @StorageAccountPreparer(name_prefix='pyacrstorage')
    def test_get_blob_with_if_none_match(self, resource_group, location, storage_account, storage_account_key):
        bsc = BlobServiceClient(self._account_url(storage_account.name), storage_account_key, connection_data_block_size=4 * 1024)
        self._setup()
        container, blob = self._create_container_and_block_blob(
            self.container_name, 'blob1', b'hello world', bsc)

        # Act
        content = blob.download_blob(if_none_match='0x111111111111111')
        content = b"".join(list(content))

        # Assert
        self.assertEqual(content, b'hello world')

    @ResourceGroupPreparer()
    @StorageAccountPreparer(name_prefix='pyacrstorage')
    def test_get_blob_with_if_none_match_fail(self, resource_group, location, storage_account, storage_account_key):
        bsc = BlobServiceClient(self._account_url(storage_account.name), storage_account_key, connection_data_block_size=4 * 1024)
        self._setup()
        container, blob = self._create_container_and_block_blob(
            self.container_name, 'blob1', b'hello world', bsc)
        etag = blob.get_blob_properties().etag

        # Act
        with self.assertRaises(ResourceModifiedError) as e:
            blob.download_blob(if_none_match=etag)

        # Assert
        self.assertEqual(StorageErrorCode.condition_not_met, e.exception.error_code)

    @ResourceGroupPreparer()
    @StorageAccountPreparer(name_prefix='pyacrstorage')
    def test_set_blob_properties_with_if_modified(self, resource_group, location, storage_account, storage_account_key):
        bsc = BlobServiceClient(self._account_url(storage_account.name), storage_account_key, connection_data_block_size=4 * 1024)
        self._setup()
        self._create_container_and_block_blob(
            self.container_name, 'blob1', b'hello world', bsc)
        test_datetime = (datetime.datetime.utcnow() -
                         datetime.timedelta(minutes=15))
        # Act
        content_settings = ContentSettings(
            content_language='spanish',
            content_disposition='inline')
        blob = bsc.get_blob_client(self.container_name, 'blob1')
        blob.set_http_headers(content_settings, if_modified_since=test_datetime)

        # Assert
        properties = blob.get_blob_properties()
        self.assertEqual(content_settings.content_language, properties.content_settings.content_language)
        self.assertEqual(content_settings.content_disposition, properties.content_settings.content_disposition)

    @ResourceGroupPreparer()
    @StorageAccountPreparer(name_prefix='pyacrstorage')
    def test_set_blob_properties_with_if_modified_fail(self, resource_group, location, storage_account, storage_account_key):
        bsc = BlobServiceClient(self._account_url(storage_account.name), storage_account_key, connection_data_block_size=4 * 1024)
        self._setup()
        self._create_container_and_block_blob(
            self.container_name, 'blob1', b'hello world', bsc)
        test_datetime = (datetime.datetime.utcnow() +
                         datetime.timedelta(minutes=15))
        # Act
        with self.assertRaises(ResourceModifiedError) as e:
            content_settings = ContentSettings(
                content_language='spanish',
                content_disposition='inline')
            blob = bsc.get_blob_client(self.container_name, 'blob1')
            blob.set_http_headers(content_settings, if_modified_since=test_datetime)

        # Assert
        self.assertEqual(StorageErrorCode.condition_not_met, e.exception.error_code)

    @ResourceGroupPreparer()
    @StorageAccountPreparer(name_prefix='pyacrstorage')
    def test_set_blob_properties_with_if_unmodified(self, resource_group, location, storage_account, storage_account_key):
        bsc = BlobServiceClient(self._account_url(storage_account.name), storage_account_key, connection_data_block_size=4 * 1024)
        self._setup()
        self._create_container_and_block_blob(
            self.container_name, 'blob1', b'hello world', bsc)
        test_datetime = (datetime.datetime.utcnow() +
                         datetime.timedelta(minutes=15))
        # Act
        content_settings = ContentSettings(
            content_language='spanish',
            content_disposition='inline')
        blob = bsc.get_blob_client(self.container_name, 'blob1')
        blob.set_http_headers(content_settings, if_unmodified_since=test_datetime)

        # Assert
        properties = blob.get_blob_properties()
        self.assertEqual(content_settings.content_language, properties.content_settings.content_language)
        self.assertEqual(content_settings.content_disposition, properties.content_settings.content_disposition)

    @ResourceGroupPreparer()
    @StorageAccountPreparer(name_prefix='pyacrstorage')
    def test_set_blob_properties_with_if_unmodified_fail(self, resource_group, location, storage_account, storage_account_key):
        bsc = BlobServiceClient(self._account_url(storage_account.name), storage_account_key, connection_data_block_size=4 * 1024)
        self._setup()
        self._create_container_and_block_blob(
            self.container_name, 'blob1', b'hello world', bsc)
        test_datetime = (datetime.datetime.utcnow() -
                         datetime.timedelta(minutes=15))
        # Act
        with self.assertRaises(ResourceModifiedError) as e:
            content_settings = ContentSettings(
                content_language='spanish',
                content_disposition='inline')
            blob = bsc.get_blob_client(self.container_name, 'blob1')
            blob.set_http_headers(content_settings, if_unmodified_since=test_datetime)

        # Assert
        self.assertEqual(StorageErrorCode.condition_not_met, e.exception.error_code)

    @ResourceGroupPreparer()
    @StorageAccountPreparer(name_prefix='pyacrstorage')
    def test_set_blob_properties_with_if_match(self, resource_group, location, storage_account, storage_account_key):
        bsc = BlobServiceClient(self._account_url(storage_account.name), storage_account_key, connection_data_block_size=4 * 1024)
        self._setup()
        self._create_container_and_block_blob(
            self.container_name, 'blob1', b'hello world', bsc)
        blob = bsc.get_blob_client(self.container_name, 'blob1')
        etag = blob.get_blob_properties().etag

        # Act
        content_settings = ContentSettings(
            content_language='spanish',
            content_disposition='inline')
        blob.set_http_headers(content_settings, if_match=etag)

        # Assert
        properties = blob.get_blob_properties()
        self.assertEqual(content_settings.content_language, properties.content_settings.content_language)
        self.assertEqual(content_settings.content_disposition, properties.content_settings.content_disposition)

    @ResourceGroupPreparer()
    @StorageAccountPreparer(name_prefix='pyacrstorage')
    def test_set_blob_properties_with_if_match_fail(self, resource_group, location, storage_account, storage_account_key):
        bsc = BlobServiceClient(self._account_url(storage_account.name), storage_account_key, connection_data_block_size=4 * 1024)
        self._setup()
        self._create_container_and_block_blob(
            self.container_name, 'blob1', b'hello world', bsc)

        # Act
        with self.assertRaises(ResourceModifiedError) as e:
            content_settings = ContentSettings(
                content_language='spanish',
                content_disposition='inline')
            blob = bsc.get_blob_client(self.container_name, 'blob1')
            blob.set_http_headers(content_settings, if_match='0x111111111111111')

        # Assert
        self.assertEqual(StorageErrorCode.condition_not_met, e.exception.error_code)

    @ResourceGroupPreparer()
    @StorageAccountPreparer(name_prefix='pyacrstorage')
    def test_set_blob_properties_with_if_none_match(self, resource_group, location, storage_account, storage_account_key):
        bsc = BlobServiceClient(self._account_url(storage_account.name), storage_account_key, connection_data_block_size=4 * 1024)
        self._setup()
        self._create_container_and_block_blob(
            self.container_name, 'blob1', b'hello world', bsc)

        # Act
        content_settings = ContentSettings(
            content_language='spanish',
            content_disposition='inline')
        blob = bsc.get_blob_client(self.container_name, 'blob1')
        blob.set_http_headers(content_settings, if_none_match='0x111111111111111')

        # Assert
        properties = blob.get_blob_properties()
        self.assertEqual(content_settings.content_language, properties.content_settings.content_language)
        self.assertEqual(content_settings.content_disposition, properties.content_settings.content_disposition)

    @ResourceGroupPreparer()
    @StorageAccountPreparer(name_prefix='pyacrstorage')
    def test_set_blob_properties_with_if_none_match_fail(self, resource_group, location, storage_account, storage_account_key):
        bsc = BlobServiceClient(self._account_url(storage_account.name), storage_account_key, connection_data_block_size=4 * 1024)
        self._setup()
        self._create_container_and_block_blob(
            self.container_name, 'blob1', b'hello world', bsc)
        blob = bsc.get_blob_client(self.container_name, 'blob1')
        etag = blob.get_blob_properties().etag

        # Act
        with self.assertRaises(ResourceModifiedError) as e:
            content_settings = ContentSettings(
                content_language='spanish',
                content_disposition='inline')
            blob.set_http_headers(content_settings, if_none_match=etag)

        # Assert
        self.assertEqual(StorageErrorCode.condition_not_met, e.exception.error_code)

    @ResourceGroupPreparer()
    @StorageAccountPreparer(name_prefix='pyacrstorage')
    def test_get_blob_properties_with_if_modified(self, resource_group, location, storage_account, storage_account_key):
        bsc = BlobServiceClient(self._account_url(storage_account.name), storage_account_key, connection_data_block_size=4 * 1024)
        self._setup()
        self._create_container_and_block_blob(
            self.container_name, 'blob1', b'hello world', bsc)
        test_datetime = (datetime.datetime.utcnow() -
                         datetime.timedelta(minutes=15))
        # Act
        blob = bsc.get_blob_client(self.container_name, 'blob1')
        properties = blob.get_blob_properties(if_modified_since=test_datetime)

        # Assert
        self.assertIsInstance(properties, BlobProperties)
        self.assertEqual(properties.blob_type.value, 'BlockBlob')
        self.assertEqual(properties.size, 11)
        self.assertEqual(properties.lease.status, 'unlocked')

    @ResourceGroupPreparer()
    @StorageAccountPreparer(name_prefix='pyacrstorage')
    def test_get_blob_properties_with_if_modified_fail(self, resource_group, location, storage_account, storage_account_key):
        bsc = BlobServiceClient(self._account_url(storage_account.name), storage_account_key, connection_data_block_size=4 * 1024)
        self._setup()
        self._create_container_and_block_blob(
            self.container_name, 'blob1', b'hello world', bsc)
        test_datetime = (datetime.datetime.utcnow() +
                         datetime.timedelta(minutes=15))
        # Act
        with self.assertRaises(ResourceModifiedError) as e:
            blob = bsc.get_blob_client(self.container_name, 'blob1')
            blob.get_blob_properties(if_modified_since=test_datetime)

        # Assert
        self.assertEqual(StorageErrorCode.condition_not_met, e.exception.error_code)

    @ResourceGroupPreparer()
    @StorageAccountPreparer(name_prefix='pyacrstorage')
    def test_get_blob_properties_with_if_unmodified(self, resource_group, location, storage_account, storage_account_key):
        bsc = BlobServiceClient(self._account_url(storage_account.name), storage_account_key, connection_data_block_size=4 * 1024)
        self._setup()
        self._create_container_and_block_blob(
            self.container_name, 'blob1', b'hello world', bsc)
        test_datetime = (datetime.datetime.utcnow() +
                         datetime.timedelta(minutes=15))
        # Act
        blob = bsc.get_blob_client(self.container_name, 'blob1')
        properties = blob.get_blob_properties(if_unmodified_since=test_datetime)

        # Assert
        self.assertIsNotNone(properties)
        self.assertEqual(properties.blob_type.value, 'BlockBlob')
        self.assertEqual(properties.size, 11)
        self.assertEqual(properties.lease.status, 'unlocked')

    @ResourceGroupPreparer()
    @StorageAccountPreparer(name_prefix='pyacrstorage')
    def test_get_blob_properties_with_if_unmodified_fail(self, resource_group, location, storage_account, storage_account_key):
        bsc = BlobServiceClient(self._account_url(storage_account.name), storage_account_key, connection_data_block_size=4 * 1024)
        self._setup()
        self._create_container_and_block_blob(
            self.container_name, 'blob1', b'hello world', bsc)
        test_datetime = (datetime.datetime.utcnow() -
                         datetime.timedelta(minutes=15))
        # Act
        with self.assertRaises(ResourceModifiedError) as e:
            blob = bsc.get_blob_client(self.container_name, 'blob1')
            blob.get_blob_properties(if_unmodified_since=test_datetime)

        # Assert
        self.assertEqual(StorageErrorCode.condition_not_met, e.exception.error_code)

    @ResourceGroupPreparer()
    @StorageAccountPreparer(name_prefix='pyacrstorage')
    def test_get_blob_properties_with_if_match(self, resource_group, location, storage_account, storage_account_key):
        bsc = BlobServiceClient(self._account_url(storage_account.name), storage_account_key, connection_data_block_size=4 * 1024)
        self._setup()
        self._create_container_and_block_blob(
            self.container_name, 'blob1', b'hello world', bsc)
        blob = bsc.get_blob_client(self.container_name, 'blob1')
        etag = blob.get_blob_properties().etag

        # Act
        properties = blob.get_blob_properties(if_match=etag)

        # Assert
        self.assertIsNotNone(properties)
        self.assertEqual(properties.blob_type.value, 'BlockBlob')
        self.assertEqual(properties.size, 11)
        self.assertEqual(properties.lease.status, 'unlocked')

    @ResourceGroupPreparer()
    @StorageAccountPreparer(name_prefix='pyacrstorage')
    def test_get_blob_properties_with_if_match_fail(self, resource_group, location, storage_account, storage_account_key):
        bsc = BlobServiceClient(self._account_url(storage_account.name), storage_account_key, connection_data_block_size=4 * 1024)
        self._setup()
        self._create_container_and_block_blob(
            self.container_name, 'blob1', b'hello world', bsc)

        # Act
        with self.assertRaises(ResourceModifiedError) as e:
            blob = bsc.get_blob_client(self.container_name, 'blob1')
            blob.get_blob_properties(if_match='0x111111111111111')

        # Assert
        self.assertEqual(StorageErrorCode.condition_not_met, e.exception.error_code)

    @ResourceGroupPreparer()
    @StorageAccountPreparer(name_prefix='pyacrstorage')
    def test_get_blob_properties_with_if_none_match(self, resource_group, location, storage_account, storage_account_key):
        bsc = BlobServiceClient(self._account_url(storage_account.name), storage_account_key, connection_data_block_size=4 * 1024)
        self._setup()
        self._create_container_and_block_blob(
            self.container_name, 'blob1', b'hello world', bsc)

        # Act
        blob = bsc.get_blob_client(self.container_name, 'blob1')
        properties = blob.get_blob_properties(if_none_match='0x111111111111111')

        # Assert
        self.assertIsNotNone(properties)
        self.assertEqual(properties.blob_type.value, 'BlockBlob')
        self.assertEqual(properties.size, 11)
        self.assertEqual(properties.lease.status, 'unlocked')

    @ResourceGroupPreparer()
    @StorageAccountPreparer(name_prefix='pyacrstorage')
    def test_get_blob_properties_with_if_none_match_fail(self, resource_group, location, storage_account, storage_account_key):
        bsc = BlobServiceClient(self._account_url(storage_account.name), storage_account_key, connection_data_block_size=4 * 1024)
        self._setup()
        self._create_container_and_block_blob(
            self.container_name, 'blob1', b'hello world', bsc)
        blob = bsc.get_blob_client(self.container_name, 'blob1')
        etag = blob.get_blob_properties().etag

        # Act
        with self.assertRaises(ResourceModifiedError) as e:
            blob.get_blob_properties(if_none_match=etag)

        # Assert
        self.assertEqual(StorageErrorCode.condition_not_met, e.exception.error_code)

    @ResourceGroupPreparer()
    @StorageAccountPreparer(name_prefix='pyacrstorage')
    def test_get_blob_metadata_with_if_modified(self, resource_group, location, storage_account, storage_account_key):
        bsc = BlobServiceClient(self._account_url(storage_account.name), storage_account_key, connection_data_block_size=4 * 1024)
        self._setup()
        self._create_container_and_block_blob(
            self.container_name, 'blob1', b'hello world', bsc)
        test_datetime = (datetime.datetime.utcnow() -
                         datetime.timedelta(minutes=15))

        # Act
        blob = bsc.get_blob_client(self.container_name, 'blob1')
        md = blob.get_blob_properties(if_modified_since=test_datetime).metadata

        # Assert
        self.assertIsNotNone(md)

    @ResourceGroupPreparer()
    @StorageAccountPreparer(name_prefix='pyacrstorage')
    def test_get_blob_metadata_with_if_modified_fail(self, resource_group, location, storage_account, storage_account_key):
        bsc = BlobServiceClient(self._account_url(storage_account.name), storage_account_key, connection_data_block_size=4 * 1024)
        self._setup()
        self._create_container_and_block_blob(
            self.container_name, 'blob1', b'hello world', bsc)
        test_datetime = (datetime.datetime.utcnow() +
                         datetime.timedelta(minutes=15))

        # Act
        with self.assertRaises(ResourceModifiedError) as e:
            blob = bsc.get_blob_client(self.container_name, 'blob1')
            blob.get_blob_properties(if_modified_since=test_datetime).metadata

        # Assert
        self.assertEqual(StorageErrorCode.condition_not_met, e.exception.error_code)

    @ResourceGroupPreparer()
    @StorageAccountPreparer(name_prefix='pyacrstorage')
    def test_get_blob_metadata_with_if_unmodified(self, resource_group, location, storage_account, storage_account_key):
        bsc = BlobServiceClient(self._account_url(storage_account.name), storage_account_key, connection_data_block_size=4 * 1024)
        self._setup()
        self._create_container_and_block_blob(
            self.container_name, 'blob1', b'hello world', bsc)
        test_datetime = (datetime.datetime.utcnow() +
                         datetime.timedelta(minutes=15))

        # Act
        blob = bsc.get_blob_client(self.container_name, 'blob1')
        md = blob.get_blob_properties(if_unmodified_since=test_datetime).metadata

        # Assert
        self.assertIsNotNone(md)

    @ResourceGroupPreparer()
    @StorageAccountPreparer(name_prefix='pyacrstorage')
    def test_get_blob_metadata_with_if_unmodified_fail(self, resource_group, location, storage_account, storage_account_key):
        bsc = BlobServiceClient(self._account_url(storage_account.name), storage_account_key, connection_data_block_size=4 * 1024)
        self._setup()
        self._create_container_and_block_blob(
            self.container_name, 'blob1', b'hello world', bsc)
        test_datetime = (datetime.datetime.utcnow() -
                         datetime.timedelta(minutes=15))

        # Act
        with self.assertRaises(ResourceModifiedError) as e:
            blob = bsc.get_blob_client(self.container_name, 'blob1')
            blob.get_blob_properties(if_unmodified_since=test_datetime).metadata

        # Assert
        self.assertEqual(StorageErrorCode.condition_not_met, e.exception.error_code)

    @ResourceGroupPreparer()
    @StorageAccountPreparer(name_prefix='pyacrstorage')
    def test_get_blob_metadata_with_if_match(self, resource_group, location, storage_account, storage_account_key):
        bsc = BlobServiceClient(self._account_url(storage_account.name), storage_account_key, connection_data_block_size=4 * 1024)
        self._setup()
        self._create_container_and_block_blob(
            self.container_name, 'blob1', b'hello world', bsc)
        blob = bsc.get_blob_client(self.container_name, 'blob1')
        etag = blob.get_blob_properties().etag

        # Act
        md = blob.get_blob_properties(if_match=etag).metadata

        # Assert
        self.assertIsNotNone(md)

    @ResourceGroupPreparer()
    @StorageAccountPreparer(name_prefix='pyacrstorage')
    def test_get_blob_metadata_with_if_match_fail(self, resource_group, location, storage_account, storage_account_key):
        bsc = BlobServiceClient(self._account_url(storage_account.name), storage_account_key, connection_data_block_size=4 * 1024)
        self._setup()
        self._create_container_and_block_blob(
            self.container_name, 'blob1', b'hello world', bsc)

        # Act
        with self.assertRaises(ResourceModifiedError) as e:
            blob = bsc.get_blob_client(self.container_name, 'blob1')
            blob.get_blob_properties(if_match='0x111111111111111').metadata

        # Assert
        self.assertEqual(StorageErrorCode.condition_not_met, e.exception.error_code)

    @ResourceGroupPreparer()
    @StorageAccountPreparer(name_prefix='pyacrstorage')
    def test_get_blob_metadata_with_if_none_match(self, resource_group, location, storage_account, storage_account_key):
        bsc = BlobServiceClient(self._account_url(storage_account.name), storage_account_key, connection_data_block_size=4 * 1024)
        self._setup()
        self._create_container_and_block_blob(
            self.container_name, 'blob1', b'hello world', bsc)

        # Act
        blob = bsc.get_blob_client(self.container_name, 'blob1')
        md = blob.get_blob_properties(if_none_match='0x111111111111111').metadata

        # Assert
        self.assertIsNotNone(md)

    @ResourceGroupPreparer()
    @StorageAccountPreparer(name_prefix='pyacrstorage')
    def test_get_blob_metadata_with_if_none_match_fail(self, resource_group, location, storage_account, storage_account_key):
        bsc = BlobServiceClient(self._account_url(storage_account.name), storage_account_key, connection_data_block_size=4 * 1024)
        self._setup()
        self._create_container_and_block_blob(
            self.container_name, 'blob1', b'hello world', bsc)
        blob = bsc.get_blob_client(self.container_name, 'blob1')
        etag = blob.get_blob_properties().etag

        # Act
        with self.assertRaises(ResourceModifiedError) as e:
            blob.get_blob_properties(if_none_match=etag).metadata

        # Assert
        self.assertEqual(StorageErrorCode.condition_not_met, e.exception.error_code)

    @ResourceGroupPreparer()
    @StorageAccountPreparer(name_prefix='pyacrstorage')
    def test_set_blob_metadata_with_if_modified(self, resource_group, location, storage_account, storage_account_key):
        bsc = BlobServiceClient(self._account_url(storage_account.name), storage_account_key, connection_data_block_size=4 * 1024)
        self._setup()
        self._create_container_and_block_blob(
            self.container_name, 'blob1', b'hello world', bsc)
        test_datetime = (datetime.datetime.utcnow() -
                         datetime.timedelta(minutes=15))

        # Act
        metadata = {'hello': 'world', 'number': '42'}
        blob = bsc.get_blob_client(self.container_name, 'blob1')
        blob.set_blob_metadata(metadata, if_modified_since=test_datetime)

        # Assert
        md = blob.get_blob_properties().metadata
        self.assertDictEqual(metadata, md)

    @ResourceGroupPreparer()
    @StorageAccountPreparer(name_prefix='pyacrstorage')
    def test_set_blob_metadata_with_if_modified_fail(self, resource_group, location, storage_account, storage_account_key):
        bsc = BlobServiceClient(self._account_url(storage_account.name), storage_account_key, connection_data_block_size=4 * 1024)
        self._setup()
        self._create_container_and_block_blob(
            self.container_name, 'blob1', b'hello world', bsc)
        test_datetime = (datetime.datetime.utcnow() +
                         datetime.timedelta(minutes=15))

        # Act
        with self.assertRaises(ResourceModifiedError) as e:
            metadata = {'hello': 'world', 'number': '42'}
            blob = bsc.get_blob_client(self.container_name, 'blob1')
            blob.set_blob_metadata(metadata, if_modified_since=test_datetime)

        # Assert
        self.assertEqual(StorageErrorCode.condition_not_met, e.exception.error_code)

    @ResourceGroupPreparer()
    @StorageAccountPreparer(name_prefix='pyacrstorage')
    def test_set_blob_metadata_with_if_unmodified(self, resource_group, location, storage_account, storage_account_key):
        bsc = BlobServiceClient(self._account_url(storage_account.name), storage_account_key, connection_data_block_size=4 * 1024)
        self._setup()
        self._create_container_and_block_blob(
            self.container_name, 'blob1', b'hello world', bsc)
        test_datetime = (datetime.datetime.utcnow() +
                         datetime.timedelta(minutes=15))

        # Act
        metadata = {'hello': 'world', 'number': '42'}
        blob = bsc.get_blob_client(self.container_name, 'blob1')
        blob.set_blob_metadata(metadata, if_unmodified_since=test_datetime)

        # Assert
        md = blob.get_blob_properties().metadata
        self.assertDictEqual(metadata, md)

    @ResourceGroupPreparer()
    @StorageAccountPreparer(name_prefix='pyacrstorage')
    def test_set_blob_metadata_with_if_unmodified_fail(self, resource_group, location, storage_account, storage_account_key):
        bsc = BlobServiceClient(self._account_url(storage_account.name), storage_account_key, connection_data_block_size=4 * 1024)
        self._setup()
        self._create_container_and_block_blob(
            self.container_name, 'blob1', b'hello world', bsc)
        test_datetime = (datetime.datetime.utcnow() -
                         datetime.timedelta(minutes=15))

        # Act
        with self.assertRaises(ResourceModifiedError) as e:
            metadata = {'hello': 'world', 'number': '42'}
            blob = bsc.get_blob_client(self.container_name, 'blob1')
            blob.set_blob_metadata(metadata, if_unmodified_since=test_datetime)

        # Assert
        self.assertEqual(StorageErrorCode.condition_not_met, e.exception.error_code)

    @ResourceGroupPreparer()
    @StorageAccountPreparer(name_prefix='pyacrstorage')
    def test_set_blob_metadata_with_if_match(self, resource_group, location, storage_account, storage_account_key):
        bsc = BlobServiceClient(self._account_url(storage_account.name), storage_account_key, connection_data_block_size=4 * 1024)
        self._setup()
        self._create_container_and_block_blob(
            self.container_name, 'blob1', b'hello world', bsc)
        blob = bsc.get_blob_client(self.container_name, 'blob1')
        etag = blob.get_blob_properties().etag

        # Act
        metadata = {'hello': 'world', 'number': '42'}
        blob.set_blob_metadata(metadata, if_match=etag)

        # Assert
        md = blob.get_blob_properties().metadata
        self.assertDictEqual(metadata, md)

    @ResourceGroupPreparer()
    @StorageAccountPreparer(name_prefix='pyacrstorage')
    def test_set_blob_metadata_with_if_match_fail(self, resource_group, location, storage_account, storage_account_key):
        bsc = BlobServiceClient(self._account_url(storage_account.name), storage_account_key, connection_data_block_size=4 * 1024)
        self._setup()
        self._create_container_and_block_blob(
            self.container_name, 'blob1', b'hello world', bsc)

        # Act
        with self.assertRaises(ResourceModifiedError) as e:
            metadata = {'hello': 'world', 'number': '42'}
            blob = bsc.get_blob_client(self.container_name, 'blob1')
            blob.set_blob_metadata(metadata, if_match='0x111111111111111')

        # Assert
        self.assertEqual(StorageErrorCode.condition_not_met, e.exception.error_code)

    @ResourceGroupPreparer()
    @StorageAccountPreparer(name_prefix='pyacrstorage')
    def test_set_blob_metadata_with_if_none_match(self, resource_group, location, storage_account, storage_account_key):
        bsc = BlobServiceClient(self._account_url(storage_account.name), storage_account_key, connection_data_block_size=4 * 1024)
        self._setup()
        self._create_container_and_block_blob(
            self.container_name, 'blob1', b'hello world', bsc)

        # Act
        metadata = {'hello': 'world', 'number': '42'}
        blob = bsc.get_blob_client(self.container_name, 'blob1')
        blob.set_blob_metadata(metadata, if_none_match='0x111111111111111')

        # Assert
        md = blob.get_blob_properties().metadata
        self.assertDictEqual(metadata, md)

    @ResourceGroupPreparer()
    @StorageAccountPreparer(name_prefix='pyacrstorage')
    def test_set_blob_metadata_with_if_none_match_fail(self, resource_group, location, storage_account, storage_account_key):
        bsc = BlobServiceClient(self._account_url(storage_account.name), storage_account_key, connection_data_block_size=4 * 1024)
        self._setup()
        self._create_container_and_block_blob(
            self.container_name, 'blob1', b'hello world', bsc)
        blob = bsc.get_blob_client(self.container_name, 'blob1')
        etag = blob.get_blob_properties().etag

        # Act
        with self.assertRaises(ResourceModifiedError) as e:
            metadata = {'hello': 'world', 'number': '42'}
            blob.set_blob_metadata(metadata, if_none_match=etag)

        # Assert
        self.assertEqual(StorageErrorCode.condition_not_met, e.exception.error_code)

    @ResourceGroupPreparer()
    @StorageAccountPreparer(name_prefix='pyacrstorage')
    def test_delete_blob_with_if_modified(self, resource_group, location, storage_account, storage_account_key):
        bsc = BlobServiceClient(self._account_url(storage_account.name), storage_account_key, connection_data_block_size=4 * 1024)
        self._setup()
        test_datetime = (datetime.datetime.utcnow() -
                         datetime.timedelta(minutes=15))
        self._create_container_and_block_blob(
            self.container_name, 'blob1', b'hello world', bsc)

        # Act
        blob = bsc.get_blob_client(self.container_name, 'blob1')
        resp = blob.delete_blob(if_modified_since=test_datetime)

        # Assert
        self.assertIsNone(resp)

    @ResourceGroupPreparer()
    @StorageAccountPreparer(name_prefix='pyacrstorage')
    def test_delete_blob_with_if_modified_fail(self, resource_group, location, storage_account, storage_account_key):
        bsc = BlobServiceClient(self._account_url(storage_account.name), storage_account_key, connection_data_block_size=4 * 1024)
        self._setup()
        test_datetime = (datetime.datetime.utcnow() +
                         datetime.timedelta(minutes=15))
        self._create_container_and_block_blob(
            self.container_name, 'blob1', b'hello world', bsc)

        # Act
        blob = bsc.get_blob_client(self.container_name, 'blob1')
        with self.assertRaises(ResourceModifiedError) as e:
            blob.delete_blob(if_modified_since=test_datetime)

        # Assert
        self.assertEqual(StorageErrorCode.condition_not_met, e.exception.error_code)

    @ResourceGroupPreparer()
    @StorageAccountPreparer(name_prefix='pyacrstorage')
    def test_delete_blob_with_if_unmodified(self, resource_group, location, storage_account, storage_account_key):
        bsc = BlobServiceClient(self._account_url(storage_account.name), storage_account_key, connection_data_block_size=4 * 1024)
        self._setup()
        test_datetime = (datetime.datetime.utcnow() +
                         datetime.timedelta(minutes=15))
        self._create_container_and_block_blob(
            self.container_name, 'blob1', b'hello world', bsc)

        # Act
        blob = bsc.get_blob_client(self.container_name, 'blob1')
        resp = blob.delete_blob(if_unmodified_since=test_datetime)

        # Assert
        self.assertIsNone(resp)

    @ResourceGroupPreparer()
    @StorageAccountPreparer(name_prefix='pyacrstorage')
    def test_delete_blob_with_if_unmodified_fail(self, resource_group, location, storage_account, storage_account_key):
        bsc = BlobServiceClient(self._account_url(storage_account.name), storage_account_key, connection_data_block_size=4 * 1024)
        self._setup()
        test_datetime = (datetime.datetime.utcnow() -
                         datetime.timedelta(minutes=15))
        self._create_container_and_block_blob(
            self.container_name, 'blob1', b'hello world', bsc)

        # Act
        blob = bsc.get_blob_client(self.container_name, 'blob1')
        with self.assertRaises(ResourceModifiedError) as e:
            blob.delete_blob(if_unmodified_since=test_datetime)

        # Assert
        self.assertEqual(StorageErrorCode.condition_not_met, e.exception.error_code)

    @ResourceGroupPreparer()
    @StorageAccountPreparer(name_prefix='pyacrstorage')
    def test_delete_blob_with_if_match(self, resource_group, location, storage_account, storage_account_key):
        bsc = BlobServiceClient(self._account_url(storage_account.name), storage_account_key, connection_data_block_size=4 * 1024)
        self._setup()
        self._create_container_and_block_blob(
            self.container_name, 'blob1', b'hello world', bsc)
        blob = bsc.get_blob_client(self.container_name, 'blob1')
        etag = blob.get_blob_properties().etag

        # Act

        resp = blob.delete_blob(if_match=etag)

        # Assert
        self.assertIsNone(resp)

    @ResourceGroupPreparer()
    @StorageAccountPreparer(name_prefix='pyacrstorage')
    def test_delete_blob_with_if_match_fail(self, resource_group, location, storage_account, storage_account_key):
        bsc = BlobServiceClient(self._account_url(storage_account.name), storage_account_key, connection_data_block_size=4 * 1024)
        self._setup()
        self._create_container_and_block_blob(
            self.container_name, 'blob1', b'hello world', bsc)

        # Act
        blob = bsc.get_blob_client(self.container_name, 'blob1')
        with self.assertRaises(ResourceModifiedError) as e:
            blob.delete_blob(if_match='0x111111111111111')

        # Assert
        self.assertEqual(StorageErrorCode.condition_not_met, e.exception.error_code)

    @ResourceGroupPreparer()
    @StorageAccountPreparer(name_prefix='pyacrstorage')
    def test_delete_blob_with_if_none_match(self, resource_group, location, storage_account, storage_account_key):
        bsc = BlobServiceClient(self._account_url(storage_account.name), storage_account_key, connection_data_block_size=4 * 1024)
        self._setup()
        self._create_container_and_block_blob(
            self.container_name, 'blob1', b'hello world', bsc)

        # Act
        blob = bsc.get_blob_client(self.container_name, 'blob1')
        resp = blob.delete_blob(if_none_match='0x111111111111111')

        # Assert
        self.assertIsNone(resp)

    @ResourceGroupPreparer()
    @StorageAccountPreparer(name_prefix='pyacrstorage')
    def test_delete_blob_with_if_none_match_fail(self, resource_group, location, storage_account, storage_account_key):
        bsc = BlobServiceClient(self._account_url(storage_account.name), storage_account_key, connection_data_block_size=4 * 1024)
        self._setup()
        self._create_container_and_block_blob(
            self.container_name, 'blob1', b'hello world', bsc)
        blob = bsc.get_blob_client(self.container_name, 'blob1')
        etag = blob.get_blob_properties().etag

        # Act
        with self.assertRaises(ResourceModifiedError) as e:
            blob.delete_blob(if_none_match=etag)

        # Assert
        self.assertEqual(StorageErrorCode.condition_not_met, e.exception.error_code)

    @ResourceGroupPreparer()
    @StorageAccountPreparer(name_prefix='pyacrstorage')
    def test_snapshot_blob_with_if_modified(self, resource_group, location, storage_account, storage_account_key):
        bsc = BlobServiceClient(self._account_url(storage_account.name), storage_account_key, connection_data_block_size=4 * 1024)
        self._setup()
        self._create_container_and_block_blob(
            self.container_name, 'blob1', b'hello world', bsc)
        test_datetime = (datetime.datetime.utcnow() -
                         datetime.timedelta(minutes=15))

        # Act
        blob = bsc.get_blob_client(self.container_name, 'blob1')
        resp = blob.create_snapshot(if_modified_since=test_datetime)

        # Assert
        self.assertIsNotNone(resp)
        self.assertIsNotNone(resp['snapshot'])

    @ResourceGroupPreparer()
    @StorageAccountPreparer(name_prefix='pyacrstorage')
    def test_snapshot_blob_with_if_modified_fail(self, resource_group, location, storage_account, storage_account_key):
        bsc = BlobServiceClient(self._account_url(storage_account.name), storage_account_key, connection_data_block_size=4 * 1024)
        self._setup()
        self._create_container_and_block_blob(
            self.container_name, 'blob1', b'hello world', bsc)
        test_datetime = (datetime.datetime.utcnow() +
                         datetime.timedelta(minutes=15))

        # Act
        with self.assertRaises(ResourceModifiedError) as e:
            blob = bsc.get_blob_client(self.container_name, 'blob1')
            blob.create_snapshot(if_modified_since=test_datetime)

        # Assert
        self.assertEqual(StorageErrorCode.condition_not_met, e.exception.error_code)

    @ResourceGroupPreparer()
    @StorageAccountPreparer(name_prefix='pyacrstorage')
    def test_snapshot_blob_with_if_unmodified(self, resource_group, location, storage_account, storage_account_key):
        bsc = BlobServiceClient(self._account_url(storage_account.name), storage_account_key, connection_data_block_size=4 * 1024)
        self._setup()
        self._create_container_and_block_blob(
            self.container_name, 'blob1', b'hello world', bsc)
        test_datetime = (datetime.datetime.utcnow() +
                         datetime.timedelta(minutes=15))

        # Act
        blob = bsc.get_blob_client(self.container_name, 'blob1')
        resp = blob.create_snapshot(if_unmodified_since=test_datetime)

        # Assert
        self.assertIsNotNone(resp)
        self.assertIsNotNone(resp['snapshot'])

    @ResourceGroupPreparer()
    @StorageAccountPreparer(name_prefix='pyacrstorage')
    def test_snapshot_blob_with_if_unmodified_fail(self, resource_group, location, storage_account, storage_account_key):
        bsc = BlobServiceClient(self._account_url(storage_account.name), storage_account_key, connection_data_block_size=4 * 1024)
        self._setup()
        self._create_container_and_block_blob(
            self.container_name, 'blob1', b'hello world', bsc)
        test_datetime = (datetime.datetime.utcnow() -
                         datetime.timedelta(minutes=15))

        # Act
        with self.assertRaises(ResourceModifiedError) as e:
            blob = bsc.get_blob_client(self.container_name, 'blob1')
            blob.create_snapshot(if_unmodified_since=test_datetime)

        # Assert
        self.assertEqual(StorageErrorCode.condition_not_met, e.exception.error_code)

    @ResourceGroupPreparer()
    @StorageAccountPreparer(name_prefix='pyacrstorage')
    def test_snapshot_blob_with_if_match(self, resource_group, location, storage_account, storage_account_key):
        bsc = BlobServiceClient(self._account_url(storage_account.name), storage_account_key, connection_data_block_size=4 * 1024)
        self._setup()
        self._create_container_and_block_blob(
            self.container_name, 'blob1', b'hello world', bsc)
        blob = bsc.get_blob_client(self.container_name, 'blob1')
        etag = blob.get_blob_properties().etag

        # Act
        resp = blob.create_snapshot(if_match=etag)

        # Assert
        self.assertIsNotNone(resp)
        self.assertIsNotNone(resp['snapshot'])

    @ResourceGroupPreparer()
    @StorageAccountPreparer(name_prefix='pyacrstorage')
    def test_snapshot_blob_with_if_match_fail(self, resource_group, location, storage_account, storage_account_key):
        bsc = BlobServiceClient(self._account_url(storage_account.name), storage_account_key, connection_data_block_size=4 * 1024)
        self._setup()
        self._create_container_and_block_blob(
            self.container_name, 'blob1', b'hello world', bsc)

        # Act
        with self.assertRaises(ResourceModifiedError) as e:
            blob = bsc.get_blob_client(self.container_name, 'blob1')
            blob.create_snapshot(if_match='0x111111111111111')

        # Assert
        self.assertEqual(StorageErrorCode.condition_not_met, e.exception.error_code)

    @ResourceGroupPreparer()
    @StorageAccountPreparer(name_prefix='pyacrstorage')
    def test_snapshot_blob_with_if_none_match(self, resource_group, location, storage_account, storage_account_key):
        bsc = BlobServiceClient(self._account_url(storage_account.name), storage_account_key, connection_data_block_size=4 * 1024)
        self._setup()
        self._create_container_and_block_blob(
            self.container_name, 'blob1', b'hello world', bsc)

        # Act
        blob = bsc.get_blob_client(self.container_name, 'blob1')
        resp = blob.create_snapshot(if_none_match='0x111111111111111')

        # Assert
        self.assertIsNotNone(resp)
        self.assertIsNotNone(resp['snapshot'])

    @ResourceGroupPreparer()
    @StorageAccountPreparer(name_prefix='pyacrstorage')
    def test_snapshot_blob_with_if_none_match_fail(self, resource_group, location, storage_account, storage_account_key):
        bsc = BlobServiceClient(self._account_url(storage_account.name), storage_account_key, connection_data_block_size=4 * 1024)
        self._setup()
        self._create_container_and_block_blob(
            self.container_name, 'blob1', b'hello world', bsc)
        blob = bsc.get_blob_client(self.container_name, 'blob1')
        etag = blob.get_blob_properties().etag

        # Act
        with self.assertRaises(ResourceModifiedError) as e:
            blob.create_snapshot(if_none_match=etag)

        # Assert
        self.assertEqual(StorageErrorCode.condition_not_met, e.exception.error_code)

    @ResourceGroupPreparer()
    @StorageAccountPreparer(name_prefix='pyacrstorage')
    def test_lease_blob_with_if_modified(self, resource_group, location, storage_account, storage_account_key):
        bsc = BlobServiceClient(self._account_url(storage_account.name), storage_account_key, connection_data_block_size=4 * 1024)
        self._setup()
        self._create_container_and_block_blob(
            self.container_name, 'blob1', b'hello world', bsc)
        test_lease_id = '00000000-1111-2222-3333-444444444444'
        test_datetime = (datetime.datetime.utcnow() -
                         datetime.timedelta(minutes=15))

        # Act
        blob = bsc.get_blob_client(self.container_name, 'blob1')
        lease = blob.acquire_lease(
            if_modified_since=test_datetime,
            lease_id=test_lease_id)

        lease.break_lease()

        # Assert
        self.assertIsInstance(lease, LeaseClient)
        self.assertIsNotNone(lease.id)

    @ResourceGroupPreparer()
    @StorageAccountPreparer(name_prefix='pyacrstorage')
    def test_lease_blob_with_if_modified_fail(self, resource_group, location, storage_account, storage_account_key):
        bsc = BlobServiceClient(self._account_url(storage_account.name), storage_account_key, connection_data_block_size=4 * 1024)
        self._setup()
        self._create_container_and_block_blob(
            self.container_name, 'blob1', b'hello world', bsc)
        test_datetime = (datetime.datetime.utcnow() +
                         datetime.timedelta(minutes=15))

        # Act
        with self.assertRaises(ResourceModifiedError) as e:
            blob = bsc.get_blob_client(self.container_name, 'blob1')
            blob.acquire_lease(if_modified_since=test_datetime)

        # Assert
        self.assertEqual(StorageErrorCode.condition_not_met, e.exception.error_code)

    @ResourceGroupPreparer()
    @StorageAccountPreparer(name_prefix='pyacrstorage')
    def test_lease_blob_with_if_unmodified(self, resource_group, location, storage_account, storage_account_key):
        bsc = BlobServiceClient(self._account_url(storage_account.name), storage_account_key, connection_data_block_size=4 * 1024)
        self._setup()
        self._create_container_and_block_blob(
            self.container_name, 'blob1', b'hello world', bsc)
        test_lease_id = '00000000-1111-2222-3333-444444444444'
        test_datetime = (datetime.datetime.utcnow() +
                         datetime.timedelta(minutes=15))

        # Act
        blob = bsc.get_blob_client(self.container_name, 'blob1')
        lease = blob.acquire_lease(
            if_unmodified_since=test_datetime,
            lease_id=test_lease_id)

        lease.break_lease()

        # Assert
        self.assertIsInstance(lease, LeaseClient)
        self.assertIsNotNone(lease.id)

    @ResourceGroupPreparer()
    @StorageAccountPreparer(name_prefix='pyacrstorage')
    def test_lease_blob_with_if_unmodified_fail(self, resource_group, location, storage_account, storage_account_key):
        bsc = BlobServiceClient(self._account_url(storage_account.name), storage_account_key, connection_data_block_size=4 * 1024)
        self._setup()
        self._create_container_and_block_blob(
            self.container_name, 'blob1', b'hello world', bsc)
        test_datetime = (datetime.datetime.utcnow() -
                         datetime.timedelta(minutes=15))

        # Act
        blob = bsc.get_blob_client(self.container_name, 'blob1')
        with self.assertRaises(ResourceModifiedError) as e:
            blob.acquire_lease(if_unmodified_since=test_datetime)

        # Assert
        self.assertEqual(StorageErrorCode.condition_not_met, e.exception.error_code)

    @ResourceGroupPreparer()
    @StorageAccountPreparer(name_prefix='pyacrstorage')
    def test_lease_blob_with_if_match(self, resource_group, location, storage_account, storage_account_key):
        bsc = BlobServiceClient(self._account_url(storage_account.name), storage_account_key, connection_data_block_size=4 * 1024)
        self._setup()
        self._create_container_and_block_blob(
            self.container_name, 'blob1', b'hello world', bsc)
        blob = bsc.get_blob_client(self.container_name, 'blob1')
        etag = blob.get_blob_properties().etag
        test_lease_id = '00000000-1111-2222-3333-444444444444'

        # Act
        lease = blob.acquire_lease(
            lease_id=test_lease_id,
            if_match=etag)

        lease.break_lease()

        # Assert
        self.assertIsInstance(lease, LeaseClient)
        self.assertIsNotNone(lease.id)

    @ResourceGroupPreparer()
    @StorageAccountPreparer(name_prefix='pyacrstorage')
    def test_lease_blob_with_if_match_fail(self, resource_group, location, storage_account, storage_account_key):
        bsc = BlobServiceClient(self._account_url(storage_account.name), storage_account_key, connection_data_block_size=4 * 1024)
        self._setup()
        self._create_container_and_block_blob(
            self.container_name, 'blob1', b'hello world', bsc)

        # Act
        blob = bsc.get_blob_client(self.container_name, 'blob1')
        with self.assertRaises(ResourceModifiedError) as e:
            blob.acquire_lease(if_match='0x111111111111111')

        # Assert
        self.assertEqual(StorageErrorCode.condition_not_met, e.exception.error_code)

    @ResourceGroupPreparer()
    @StorageAccountPreparer(name_prefix='pyacrstorage')
    def test_lease_blob_with_if_none_match(self, resource_group, location, storage_account, storage_account_key):
        bsc = BlobServiceClient(self._account_url(storage_account.name), storage_account_key, connection_data_block_size=4 * 1024)
        self._setup()
        self._create_container_and_block_blob(
            self.container_name, 'blob1', b'hello world', bsc)
        test_lease_id = '00000000-1111-2222-3333-444444444444'

        # Act
        blob = bsc.get_blob_client(self.container_name, 'blob1')
        lease = blob.acquire_lease(
            lease_id=test_lease_id,
            if_none_match='0x111111111111111')

        lease.break_lease()

        # Assert
        self.assertIsInstance(lease, LeaseClient)
        self.assertIsNotNone(lease.id)

    @ResourceGroupPreparer()
    @StorageAccountPreparer(name_prefix='pyacrstorage')
    def test_lease_blob_with_if_none_match_fail(self, resource_group, location, storage_account, storage_account_key):
        bsc = BlobServiceClient(self._account_url(storage_account.name), storage_account_key, connection_data_block_size=4 * 1024)
        self._setup()
        self._create_container_and_block_blob(
            self.container_name, 'blob1', b'hello world', bsc)
        blob = bsc.get_blob_client(self.container_name, 'blob1')
        etag = blob.get_blob_properties().etag

        # Act
        with self.assertRaises(ResourceModifiedError) as e:
            blob.acquire_lease(if_none_match=etag)

        # Assert
        self.assertEqual(StorageErrorCode.condition_not_met, e.exception.error_code)

    @ResourceGroupPreparer()
    @StorageAccountPreparer(name_prefix='pyacrstorage')
    def test_put_block_list_with_if_modified(self, resource_group, location, storage_account, storage_account_key):
        bsc = BlobServiceClient(self._account_url(storage_account.name), storage_account_key, connection_data_block_size=4 * 1024)
        self._setup()
        container, blob = self._create_container_and_block_blob(
            self.container_name, 'blob1', b'', bsc)
        blob.stage_block('1', b'AAA')
        blob.stage_block('2', b'BBB')
        blob.stage_block('3', b'CCC')
        test_datetime = (datetime.datetime.utcnow() -
                         datetime.timedelta(minutes=15))

        # Act
        block_list = [BlobBlock(block_id='1'), BlobBlock(block_id='2'), BlobBlock(block_id='3')]
        blob.commit_block_list(block_list, if_modified_since=test_datetime)

        # Assert
        content = blob.download_blob()
        self.assertEqual(b"".join(list(content)), b'AAABBBCCC')

    @ResourceGroupPreparer()
    @StorageAccountPreparer(name_prefix='pyacrstorage')
    def test_put_block_list_with_if_modified_fail(self, resource_group, location, storage_account, storage_account_key):
        bsc = BlobServiceClient(self._account_url(storage_account.name), storage_account_key, connection_data_block_size=4 * 1024)
        self._setup()
        container, blob = self._create_container_and_block_blob(
            self.container_name, 'blob1', b'', bsc)
        blob.stage_block('1', b'AAA')
        blob.stage_block('2', b'BBB')
        blob.stage_block('3', b'CCC')
        test_datetime = (datetime.datetime.utcnow() +
                         datetime.timedelta(minutes=15))

        # Act
        with self.assertRaises(ResourceModifiedError) as e:
            blob.commit_block_list(
                [BlobBlock(block_id='1'), BlobBlock(block_id='2'), BlobBlock(block_id='3')],
                if_modified_since=test_datetime)

        # Assert
        self.assertEqual(StorageErrorCode.condition_not_met, e.exception.error_code)

    @ResourceGroupPreparer()
    @StorageAccountPreparer(name_prefix='pyacrstorage')
    def test_put_block_list_with_if_unmodified(self, resource_group, location, storage_account, storage_account_key):
        bsc = BlobServiceClient(self._account_url(storage_account.name), storage_account_key, connection_data_block_size=4 * 1024)
        self._setup()
        container, blob = self._create_container_and_block_blob(
            self.container_name, 'blob1', b'', bsc)
        blob.stage_block('1', b'AAA')
        blob.stage_block('2', b'BBB')
        blob.stage_block('3', b'CCC')
        test_datetime = (datetime.datetime.utcnow() +
                         datetime.timedelta(minutes=15))

        # Act
        block_list = [BlobBlock(block_id='1'), BlobBlock(block_id='2'), BlobBlock(block_id='3')]
        blob.commit_block_list(block_list, if_unmodified_since=test_datetime)

        # Assert
        content = blob.download_blob()
        self.assertEqual(b"".join(list(content)), b'AAABBBCCC')

    @ResourceGroupPreparer()
    @StorageAccountPreparer(name_prefix='pyacrstorage')
    def test_put_block_list_with_if_unmodified_fail(self, resource_group, location, storage_account, storage_account_key):
        bsc = BlobServiceClient(self._account_url(storage_account.name), storage_account_key, connection_data_block_size=4 * 1024)
        self._setup()
        container, blob = self._create_container_and_block_blob(
            self.container_name, 'blob1', b'', bsc)
        blob.stage_block('1', b'AAA')
        blob.stage_block('2', b'BBB')
        blob.stage_block('3', b'CCC')
        test_datetime = (datetime.datetime.utcnow() -
                         datetime.timedelta(minutes=15))

        # Act
        with self.assertRaises(ResourceModifiedError) as e:
            blob.commit_block_list(
                [BlobBlock(block_id='1'), BlobBlock(block_id='2'), BlobBlock(block_id='3')],
                if_unmodified_since=test_datetime)

        # Assert
        self.assertEqual(StorageErrorCode.condition_not_met, e.exception.error_code)

    @ResourceGroupPreparer()
    @StorageAccountPreparer(name_prefix='pyacrstorage')
    def test_put_block_list_with_if_match(self, resource_group, location, storage_account, storage_account_key):
        bsc = BlobServiceClient(self._account_url(storage_account.name), storage_account_key, connection_data_block_size=4 * 1024)
        self._setup()
        container, blob = self._create_container_and_block_blob(
            self.container_name, 'blob1', b'', bsc)
        blob.stage_block('1', b'AAA')
        blob.stage_block('2', b'BBB')
        blob.stage_block('3', b'CCC')
        etag = blob.get_blob_properties().etag

        # Act
        block_list = [BlobBlock(block_id='1'), BlobBlock(block_id='2'), BlobBlock(block_id='3')]
        blob.commit_block_list(block_list, if_match=etag)

        # Assert
        content = blob.download_blob()
        self.assertEqual(b"".join(list(content)), b'AAABBBCCC')

    @ResourceGroupPreparer()
    @StorageAccountPreparer(name_prefix='pyacrstorage')
    def test_put_block_list_with_if_match_fail(self, resource_group, location, storage_account, storage_account_key):
        bsc = BlobServiceClient(self._account_url(storage_account.name), storage_account_key, connection_data_block_size=4 * 1024)
        self._setup()
        container, blob = self._create_container_and_block_blob(
            self.container_name, 'blob1', b'', bsc)
        blob.stage_block('1', b'AAA')
        blob.stage_block('2', b'BBB')
        blob.stage_block('3', b'CCC')

        # Act
        with self.assertRaises(ResourceModifiedError) as e:
            blob.commit_block_list(
                [BlobBlock(block_id='1'), BlobBlock(block_id='2'), BlobBlock(block_id='3')],
                if_match='0x111111111111111')

        # Assert
        self.assertEqual(StorageErrorCode.condition_not_met, e.exception.error_code)

    @ResourceGroupPreparer()
    @StorageAccountPreparer(name_prefix='pyacrstorage')
    def test_put_block_list_with_if_none_match(self, resource_group, location, storage_account, storage_account_key):
        bsc = BlobServiceClient(self._account_url(storage_account.name), storage_account_key, connection_data_block_size=4 * 1024)
        self._setup()
        container, blob = self._create_container_and_block_blob(
            self.container_name, 'blob1', b'', bsc)
        blob.stage_block('1', b'AAA')
        blob.stage_block('2', b'BBB')
        blob.stage_block('3', b'CCC')

        # Act
        block_list = [BlobBlock(block_id='1'), BlobBlock(block_id='2'), BlobBlock(block_id='3')]
        blob.commit_block_list(block_list, if_none_match='0x111111111111111')

        # Assert
        content = blob.download_blob()
        self.assertEqual(b"".join(list(content)), b'AAABBBCCC')

    @ResourceGroupPreparer()
    @StorageAccountPreparer(name_prefix='pyacrstorage')
    def test_put_block_list_with_if_none_match_fail(self, resource_group, location, storage_account, storage_account_key):
        bsc = BlobServiceClient(self._account_url(storage_account.name), storage_account_key, connection_data_block_size=4 * 1024)
        self._setup()
        container, blob = self._create_container_and_block_blob(
            self.container_name, 'blob1', b'', bsc)
        blob.stage_block('1', b'AAA')
        blob.stage_block('2', b'BBB')
        blob.stage_block('3', b'CCC')
        etag = blob.get_blob_properties().etag

        # Act
        with self.assertRaises(ResourceModifiedError) as e:
            block_list = [BlobBlock(block_id='1'), BlobBlock(block_id='2'), BlobBlock(block_id='3')]
            blob.commit_block_list(block_list, if_none_match=etag)

        # Assert
        self.assertEqual(StorageErrorCode.condition_not_met, e.exception.error_code)

    @ResourceGroupPreparer()
    @StorageAccountPreparer(name_prefix='pyacrstorage')
    def test_update_page_with_if_modified(self, resource_group, location, storage_account, storage_account_key):
        bsc = BlobServiceClient(self._account_url(storage_account.name), storage_account_key, connection_data_block_size=4 * 1024)
        self._setup()
        self._create_container_and_page_blob(
            self.container_name, 'blob1', 1024, bsc)
        test_datetime = (datetime.datetime.utcnow() -
                         datetime.timedelta(minutes=15))
        data = b'abcdefghijklmnop' * 32

        # Act
        blob = bsc.get_blob_client(self.container_name, 'blob1')
        blob.upload_page(data, offset=0, length=512, if_modified_since=test_datetime)

        # Assert

    @ResourceGroupPreparer()
    @StorageAccountPreparer(name_prefix='pyacrstorage')
    def test_update_page_with_if_modified_fail(self, resource_group, location, storage_account, storage_account_key):
        bsc = BlobServiceClient(self._account_url(storage_account.name), storage_account_key, connection_data_block_size=4 * 1024)
        self._setup()
        self._create_container_and_page_blob(
            self.container_name, 'blob1', 1024, bsc)
        test_datetime = (datetime.datetime.utcnow() +
                         datetime.timedelta(minutes=15))
        data = b'abcdefghijklmnop' * 32

        # Act
        blob = bsc.get_blob_client(self.container_name, 'blob1')
        with self.assertRaises(ResourceModifiedError) as e:
            blob.upload_page(data, offset=0, length=512, if_modified_since=test_datetime)

        # Assert
        self.assertEqual(StorageErrorCode.condition_not_met, e.exception.error_code)

    @ResourceGroupPreparer()
    @StorageAccountPreparer(name_prefix='pyacrstorage')
    def test_update_page_with_if_unmodified(self, resource_group, location, storage_account, storage_account_key):
        bsc = BlobServiceClient(self._account_url(storage_account.name), storage_account_key, connection_data_block_size=4 * 1024)
        self._setup()
        self._create_container_and_page_blob(
            self.container_name, 'blob1', 1024, bsc)
        test_datetime = (datetime.datetime.utcnow() +
                         datetime.timedelta(minutes=15))
        data = b'abcdefghijklmnop' * 32

        # Act
        blob = bsc.get_blob_client(self.container_name, 'blob1')
        blob.upload_page(data, offset=0, length=512, if_unmodified_since=test_datetime)

        # Assert

    @ResourceGroupPreparer()
    @StorageAccountPreparer(name_prefix='pyacrstorage')
    def test_update_page_with_if_unmodified_fail(self, resource_group, location, storage_account, storage_account_key):
        bsc = BlobServiceClient(self._account_url(storage_account.name), storage_account_key, connection_data_block_size=4 * 1024)
        self._setup()
        self._create_container_and_page_blob(
            self.container_name, 'blob1', 1024, bsc)
        test_datetime = (datetime.datetime.utcnow() -
                         datetime.timedelta(minutes=15))
        data = b'abcdefghijklmnop' * 32

        # Act
        blob = bsc.get_blob_client(self.container_name, 'blob1')
        with self.assertRaises(ResourceModifiedError) as e:
            blob.upload_page(data, offset=0, length=512, if_unmodified_since=test_datetime)

        # Assert
        self.assertEqual(StorageErrorCode.condition_not_met, e.exception.error_code)

    @ResourceGroupPreparer()
    @StorageAccountPreparer(name_prefix='pyacrstorage')
    def test_update_page_with_if_match(self, resource_group, location, storage_account, storage_account_key):
        bsc = BlobServiceClient(self._account_url(storage_account.name), storage_account_key, connection_data_block_size=4 * 1024)
        self._setup()
        self._create_container_and_page_blob(
            self.container_name, 'blob1', 1024, bsc)
        data = b'abcdefghijklmnop' * 32
        blob = bsc.get_blob_client(self.container_name, 'blob1')
        etag = blob.get_blob_properties().etag

        # Act
        blob.upload_page(data, offset=0, length=512, if_match=etag)

        # Assert

    @ResourceGroupPreparer()
    @StorageAccountPreparer(name_prefix='pyacrstorage')
    def test_update_page_with_if_match_fail(self, resource_group, location, storage_account, storage_account_key):
        bsc = BlobServiceClient(self._account_url(storage_account.name), storage_account_key, connection_data_block_size=4 * 1024)
        self._setup()
        self._create_container_and_page_blob(
            self.container_name, 'blob1', 1024, bsc)
        data = b'abcdefghijklmnop' * 32

        # Act
        blob = bsc.get_blob_client(self.container_name, 'blob1')
        with self.assertRaises(ResourceModifiedError) as e:
            blob.upload_page(data, offset=0, length=512, if_match='0x111111111111111')

        # Assert
        self.assertEqual(StorageErrorCode.condition_not_met, e.exception.error_code)

    @ResourceGroupPreparer()
    @StorageAccountPreparer(name_prefix='pyacrstorage')
    def test_update_page_with_if_none_match(self, resource_group, location, storage_account, storage_account_key):
        bsc = BlobServiceClient(self._account_url(storage_account.name), storage_account_key, connection_data_block_size=4 * 1024)
        self._setup()
        self._create_container_and_page_blob(
            self.container_name, 'blob1', 1024, bsc)
        data = b'abcdefghijklmnop' * 32

        # Act
        blob = bsc.get_blob_client(self.container_name, 'blob1')
        blob.upload_page(data, offset=0, length=512, if_none_match='0x111111111111111')

        # Assert

    @ResourceGroupPreparer()
    @StorageAccountPreparer(name_prefix='pyacrstorage')
    def test_update_page_with_if_none_match_fail(self, resource_group, location, storage_account, storage_account_key):
        bsc = BlobServiceClient(self._account_url(storage_account.name), storage_account_key, connection_data_block_size=4 * 1024)
        self._setup()
        self._create_container_and_page_blob(
            self.container_name, 'blob1', 1024, bsc)
        data = b'abcdefghijklmnop' * 32
        blob = bsc.get_blob_client(self.container_name, 'blob1')
        etag = blob.get_blob_properties().etag

        # Act
        with self.assertRaises(ResourceModifiedError) as e:
            blob.upload_page(data, offset=0, length=512, if_none_match=etag)

        # Assert
        self.assertEqual(StorageErrorCode.condition_not_met, e.exception.error_code)

    @ResourceGroupPreparer()
    @StorageAccountPreparer(name_prefix='pyacrstorage')
    def test_get_page_ranges_iter_with_if_modified(self, resource_group, location, storage_account, storage_account_key):
        bsc = BlobServiceClient(self._account_url(storage_account.name), storage_account_key, connection_data_block_size=4 * 1024)
        self._setup()
        container, blob = self._create_container_and_page_blob(
            self.container_name, 'blob1', 2048, bsc)
        data = b'abcdefghijklmnop' * 32
        test_datetime = (datetime.datetime.utcnow() -
                         datetime.timedelta(minutes=15))
        blob.upload_page(data, offset=0, length=512)
        blob.upload_page(data, offset=1024, length=512)

        # Act
        ranges = blob.get_page_ranges(if_modified_since=test_datetime)

        # Assert
        self.assertEqual(len(ranges[0]), 2)
        self.assertEqual(ranges[0][0], {'start': 0, 'end': 511})
        self.assertEqual(ranges[0][1], {'start': 1024, 'end': 1535})

    @ResourceGroupPreparer()
    @StorageAccountPreparer(name_prefix='pyacrstorage')
    def test_get_page_ranges_iter_with_if_modified_fail(self, resource_group, location, storage_account, storage_account_key):
        bsc = BlobServiceClient(self._account_url(storage_account.name), storage_account_key, connection_data_block_size=4 * 1024)
        self._setup()
        container, blob = self._create_container_and_page_blob(
            self.container_name, 'blob1', 2048, bsc)
        data = b'abcdefghijklmnop' * 32
        test_datetime = (datetime.datetime.utcnow() +
                         datetime.timedelta(minutes=15))
        blob.upload_page(data, offset=0, length=512)
        blob.upload_page(data, offset=1024, length=512)

        # Act
        with self.assertRaises(ResourceModifiedError) as e:
            blob.get_page_ranges(if_modified_since=test_datetime)

        # Assert
        self.assertEqual(StorageErrorCode.condition_not_met, e.exception.error_code)

    @ResourceGroupPreparer()
    @StorageAccountPreparer(name_prefix='pyacrstorage')
    def test_get_page_ranges_iter_with_if_unmodified(self, resource_group, location, storage_account, storage_account_key):
        bsc = BlobServiceClient(self._account_url(storage_account.name), storage_account_key, connection_data_block_size=4 * 1024)
        self._setup()
        container, blob = self._create_container_and_page_blob(
            self.container_name, 'blob1', 2048, bsc)
        data = b'abcdefghijklmnop' * 32
        test_datetime = (datetime.datetime.utcnow() +
                         datetime.timedelta(minutes=15))
        blob.upload_page(data, offset=0, length=512)
        blob.upload_page(data, offset=1024, length=512)

        # Act
        ranges = blob.get_page_ranges(if_unmodified_since=test_datetime)

        # Assert
        self.assertEqual(len(ranges[0]), 2)
        self.assertEqual(ranges[0][0], {'start': 0, 'end': 511})
        self.assertEqual(ranges[0][1], {'start': 1024, 'end': 1535})

    @ResourceGroupPreparer()
    @StorageAccountPreparer(name_prefix='pyacrstorage')
    def test_get_page_ranges_iter_with_if_unmodified_fail(self, resource_group, location, storage_account, storage_account_key):
        bsc = BlobServiceClient(self._account_url(storage_account.name), storage_account_key, connection_data_block_size=4 * 1024)
        self._setup()
        container, blob = self._create_container_and_page_blob(
            self.container_name, 'blob1', 2048, bsc)
        data = b'abcdefghijklmnop' * 32
        test_datetime = (datetime.datetime.utcnow() -
                         datetime.timedelta(minutes=15))
        blob.upload_page(data, offset=0, length=512)
        blob.upload_page(data, offset=1024, length=512)

        # Act
        with self.assertRaises(ResourceModifiedError) as e:
            blob.get_page_ranges(if_unmodified_since=test_datetime)

        # Assert
        self.assertEqual(StorageErrorCode.condition_not_met, e.exception.error_code)

    @ResourceGroupPreparer()
    @StorageAccountPreparer(name_prefix='pyacrstorage')
    def test_get_page_ranges_iter_with_if_match(self, resource_group, location, storage_account, storage_account_key):
        bsc = BlobServiceClient(self._account_url(storage_account.name), storage_account_key, connection_data_block_size=4 * 1024)
        self._setup()
        container, blob = self._create_container_and_page_blob(
            self.container_name, 'blob1', 2048, bsc)
        data = b'abcdefghijklmnop' * 32
        blob.upload_page(data, offset=0, length=512)
        blob.upload_page(data, offset=1024, length=512)
        etag = blob.get_blob_properties().etag

        # Act
        ranges = blob.get_page_ranges(if_match=etag)

        # Assert
        self.assertEqual(len(ranges[0]), 2)
        self.assertEqual(ranges[0][0], {'start': 0, 'end': 511})
        self.assertEqual(ranges[0][1], {'start': 1024, 'end': 1535})

    @ResourceGroupPreparer()
    @StorageAccountPreparer(name_prefix='pyacrstorage')
    def test_get_page_ranges_iter_with_if_match_fail(self, resource_group, location, storage_account, storage_account_key):
        bsc = BlobServiceClient(self._account_url(storage_account.name), storage_account_key, connection_data_block_size=4 * 1024)
        self._setup()
        container, blob = self._create_container_and_page_blob(
            self.container_name, 'blob1', 2048, bsc)
        data = b'abcdefghijklmnop' * 32
        blob.upload_page(data, offset=0, length=512)
        blob.upload_page(data, offset=1024, length=512)

        # Act
        with self.assertRaises(ResourceModifiedError) as e:
            blob.get_page_ranges(if_match='0x111111111111111')

        # Assert
        self.assertEqual(StorageErrorCode.condition_not_met, e.exception.error_code)

    @ResourceGroupPreparer()
    @StorageAccountPreparer(name_prefix='pyacrstorage')
    def test_get_page_ranges_iter_with_if_none_match(self, resource_group, location, storage_account, storage_account_key):
        bsc = BlobServiceClient(self._account_url(storage_account.name), storage_account_key, connection_data_block_size=4 * 1024)
        self._setup()
        container, blob = self._create_container_and_page_blob(
            self.container_name, 'blob1', 2048, bsc)
        data = b'abcdefghijklmnop' * 32
        blob.upload_page(data, offset=0, length=512)
        blob.upload_page(data, offset=1024, length=512)

        # Act
        ranges = blob.get_page_ranges(if_none_match='0x111111111111111')

        # Assert
        self.assertEqual(len(ranges[0]), 2)
        self.assertEqual(ranges[0][0], {'start': 0, 'end': 511})
        self.assertEqual(ranges[0][1], {'start': 1024, 'end': 1535})

    @ResourceGroupPreparer()
    @StorageAccountPreparer(name_prefix='pyacrstorage')
    def test_get_page_ranges_iter_with_if_none_match_fail(self, resource_group, location, storage_account, storage_account_key):
        bsc = BlobServiceClient(self._account_url(storage_account.name), storage_account_key, connection_data_block_size=4 * 1024)
        self._setup()
        container, blob = self._create_container_and_page_blob(
            self.container_name, 'blob1', 2048, bsc)
        data = b'abcdefghijklmnop' * 32

        blob.upload_page(data, offset=0, length=512)
        blob.upload_page(data, offset=1024, length=512)
        etag = blob.get_blob_properties().etag

        # Act
        with self.assertRaises(ResourceModifiedError) as e:
            blob.get_page_ranges(if_none_match=etag)

        # Assert
        self.assertEqual(StorageErrorCode.condition_not_met, e.exception.error_code)

    @ResourceGroupPreparer()
    @StorageAccountPreparer(name_prefix='pyacrstorage')
    def test_append_block_with_if_modified(self, resource_group, location, storage_account, storage_account_key):
        bsc = BlobServiceClient(self._account_url(storage_account.name), storage_account_key, connection_data_block_size=4 * 1024)
        self._setup()
        container, blob = self._create_container_and_append_blob(self.container_name, 'blob1', bsc)
        test_datetime = (datetime.datetime.utcnow() -
                         datetime.timedelta(minutes=15))
        # Act
        for i in range(5):
            resp = blob.append_block(u'block {0}'.format(i), if_modified_since=test_datetime)
            self.assertIsNotNone(resp)

        # Assert
        content = b"".join(list(blob.download_blob()))
        self.assertEqual(b'block 0block 1block 2block 3block 4', content)

    @ResourceGroupPreparer()
    @StorageAccountPreparer(name_prefix='pyacrstorage')
    def test_append_block_with_if_modified_fail(self, resource_group, location, storage_account, storage_account_key):
        bsc = BlobServiceClient(self._account_url(storage_account.name), storage_account_key, connection_data_block_size=4 * 1024)
        self._setup()
        container, blob = self._create_container_and_append_blob(self.container_name, 'blob1', bsc)
        test_datetime = (datetime.datetime.utcnow() +
                         datetime.timedelta(minutes=15))
        # Act
        with self.assertRaises(ResourceModifiedError) as e:
            for i in range(5):
                resp = blob.append_block(u'block {0}'.format(i), if_modified_since=test_datetime)

        # Assert
        self.assertEqual(StorageErrorCode.condition_not_met, e.exception.error_code)

    @ResourceGroupPreparer()
    @StorageAccountPreparer(name_prefix='pyacrstorage')
    def test_append_block_with_if_unmodified(self, resource_group, location, storage_account, storage_account_key):
        bsc = BlobServiceClient(self._account_url(storage_account.name), storage_account_key, connection_data_block_size=4 * 1024)
        self._setup()
        container, blob = self._create_container_and_append_blob(self.container_name, 'blob1', bsc)
        test_datetime = (datetime.datetime.utcnow() +
                         datetime.timedelta(minutes=15))
        # Act
        for i in range(5):
            resp = blob.append_block(u'block {0}'.format(i), if_unmodified_since=test_datetime)
            self.assertIsNotNone(resp)

        # Assert
        content = b"".join(list(blob.download_blob()))
        self.assertEqual(b'block 0block 1block 2block 3block 4', content)

    @ResourceGroupPreparer()
    @StorageAccountPreparer(name_prefix='pyacrstorage')
    def test_append_block_with_if_unmodified_fail(self, resource_group, location, storage_account, storage_account_key):
        bsc = BlobServiceClient(self._account_url(storage_account.name), storage_account_key, connection_data_block_size=4 * 1024)
        self._setup()
        container, blob = self._create_container_and_append_blob(self.container_name, 'blob1', bsc)
        test_datetime = (datetime.datetime.utcnow() -
                         datetime.timedelta(minutes=15))
        # Act
        with self.assertRaises(ResourceModifiedError) as e:
            for i in range(5):
                resp = blob.append_block(u'block {0}'.format(i), if_unmodified_since=test_datetime)

        # Assert
        self.assertEqual(StorageErrorCode.condition_not_met, e.exception.error_code)

    @ResourceGroupPreparer()
    @StorageAccountPreparer(name_prefix='pyacrstorage')
    def test_append_block_with_if_match(self, resource_group, location, storage_account, storage_account_key):
        bsc = BlobServiceClient(self._account_url(storage_account.name), storage_account_key, connection_data_block_size=4 * 1024)
        self._setup()
        container, blob = self._create_container_and_append_blob(self.container_name, 'blob1', bsc)

        # Act
        for i in range(5):
            etag = blob.get_blob_properties().etag
            resp = blob.append_block(u'block {0}'.format(i), if_match=etag)
            self.assertIsNotNone(resp)

        # Assert
        content = b"".join(list(blob.download_blob()))
        self.assertEqual(b'block 0block 1block 2block 3block 4', content)

    @ResourceGroupPreparer()
    @StorageAccountPreparer(name_prefix='pyacrstorage')
    def test_append_block_with_if_match_fail(self, resource_group, location, storage_account, storage_account_key):
        bsc = BlobServiceClient(self._account_url(storage_account.name), storage_account_key, connection_data_block_size=4 * 1024)
        self._setup()
        container, blob = self._create_container_and_append_blob(self.container_name, 'blob1', bsc)

        # Act
        with self.assertRaises(HttpResponseError) as e:
            for i in range(5):
                resp = blob.append_block(u'block {0}'.format(i), if_match='0x111111111111111')

        # Assert
        #self.assertEqual(StorageErrorCode.condition_not_met, e.exception.error_code)

    @ResourceGroupPreparer()
    @StorageAccountPreparer(name_prefix='pyacrstorage')
    def test_append_block_with_if_none_match(self, resource_group, location, storage_account, storage_account_key):
        bsc = BlobServiceClient(self._account_url(storage_account.name), storage_account_key, connection_data_block_size=4 * 1024)
        self._setup()
        container, blob = self._create_container_and_append_blob(self.container_name, 'blob1', bsc)

        # Act
        for i in range(5):
            resp = blob.append_block(u'block {0}'.format(i), if_none_match='0x8D2C9167D53FC2C')
            self.assertIsNotNone(resp)

        # Assert
        content = b"".join(list(blob.download_blob()))
        self.assertEqual(b'block 0block 1block 2block 3block 4', content)

    @ResourceGroupPreparer()
    @StorageAccountPreparer(name_prefix='pyacrstorage')
    def test_append_block_with_if_none_match_fail(self, resource_group, location, storage_account, storage_account_key):
        bsc = BlobServiceClient(self._account_url(storage_account.name), storage_account_key, connection_data_block_size=4 * 1024)
        self._setup()
        container, blob = self._create_container_and_append_blob(self.container_name, 'blob1', bsc)

        # Act
        with self.assertRaises(ResourceModifiedError) as e:
            for i in range(5):
                etag = blob.get_blob_properties().etag
                resp = blob.append_block(u'block {0}'.format(i), if_none_match=etag)

        # Assert
        self.assertEqual(StorageErrorCode.condition_not_met, e.exception.error_code)

    @ResourceGroupPreparer()
    @StorageAccountPreparer(name_prefix='pyacrstorage')
    def test_append_blob_from_bytes_with_if_modified(self, resource_group, location, storage_account, storage_account_key):
        bsc = BlobServiceClient(self._account_url(storage_account.name), storage_account_key, connection_data_block_size=4 * 1024)
        self._setup()
        blob_name = self.get_resource_name("blob")
        container, blob = self._create_container_and_append_blob(self.container_name, blob_name, bsc)
        test_datetime = (datetime.datetime.utcnow() - datetime.timedelta(minutes=15))

        # Act
        data = self.get_random_bytes(LARGE_APPEND_BLOB_SIZE)
        blob.upload_blob(data, blob_type=BlobType.AppendBlob, if_modified_since=test_datetime)

        # Assert
        content = b"".join(list(blob.download_blob()))
        self.assertEqual(data, content)

    @ResourceGroupPreparer()
    @StorageAccountPreparer(name_prefix='pyacrstorage')
    def test_append_blob_from_bytes_with_if_modified_fail(self, resource_group, location, storage_account, storage_account_key):
        bsc = BlobServiceClient(self._account_url(storage_account.name), storage_account_key, connection_data_block_size=4 * 1024)
        self._setup()
        blob_name = self.get_resource_name("blob")
        container, blob = self._create_container_and_append_blob(self.container_name, blob_name, bsc)
        test_datetime = (datetime.datetime.utcnow() + datetime.timedelta(minutes=15))

        # Act
        with self.assertRaises(ResourceModifiedError) as e:
            data = self.get_random_bytes(LARGE_APPEND_BLOB_SIZE)
            blob.upload_blob(data, blob_type=BlobType.AppendBlob, if_modified_since=test_datetime)

        self.assertEqual(StorageErrorCode.condition_not_met, e.exception.error_code)

    @ResourceGroupPreparer()
    @StorageAccountPreparer(name_prefix='pyacrstorage')
    def test_append_blob_from_bytes_with_if_unmodified(self, resource_group, location, storage_account, storage_account_key):
        bsc = BlobServiceClient(self._account_url(storage_account.name), storage_account_key, connection_data_block_size=4 * 1024)
        self._setup()
        blob_name = self.get_resource_name("blob")
        container, blob = self._create_container_and_append_blob(self.container_name, blob_name, bsc)
        test_datetime = (datetime.datetime.utcnow() + datetime.timedelta(minutes=15))

        # Act
        data = self.get_random_bytes(LARGE_APPEND_BLOB_SIZE)
        blob.upload_blob(data, blob_type=BlobType.AppendBlob, if_unmodified_since=test_datetime)

        # Assert
        content = b"".join(list(blob.download_blob()))
        self.assertEqual(data, content)

    @ResourceGroupPreparer()
    @StorageAccountPreparer(name_prefix='pyacrstorage')
    def test_append_blob_from_bytes_with_if_unmodified_fail(self, resource_group, location, storage_account, storage_account_key):
        bsc = BlobServiceClient(self._account_url(storage_account.name), storage_account_key, connection_data_block_size=4 * 1024)
        self._setup()
        blob_name = self.get_resource_name("blob")
        container, blob = self._create_container_and_append_blob(self.container_name, blob_name, bsc)
        test_datetime = (datetime.datetime.utcnow() - datetime.timedelta(minutes=15))

        # Act
        with self.assertRaises(ResourceModifiedError) as e:
            data = self.get_random_bytes(LARGE_APPEND_BLOB_SIZE)
            blob.upload_blob(data, blob_type=BlobType.AppendBlob, if_unmodified_since=test_datetime)

        self.assertEqual(StorageErrorCode.condition_not_met, e.exception.error_code)

    @ResourceGroupPreparer()
    @StorageAccountPreparer(name_prefix='pyacrstorage')
    def test_append_blob_from_bytes_with_if_match(self, resource_group, location, storage_account, storage_account_key):
        bsc = BlobServiceClient(self._account_url(storage_account.name), storage_account_key, connection_data_block_size=4 * 1024)
        self._setup()
        blob_name = self.get_resource_name("blob")
        container, blob = self._create_container_and_append_blob(self.container_name, blob_name, bsc)
        test_etag = blob.get_blob_properties().etag

        # Act
        data = self.get_random_bytes(LARGE_APPEND_BLOB_SIZE)
        blob.upload_blob(data, blob_type=BlobType.AppendBlob, if_match=test_etag)

        # Assert
        content = b"".join(list(blob.download_blob()))
        self.assertEqual(data, content)

    @ResourceGroupPreparer()
    @StorageAccountPreparer(name_prefix='pyacrstorage')
    def test_append_blob_from_bytes_with_if_match_fail(self, resource_group, location, storage_account, storage_account_key):
        bsc = BlobServiceClient(self._account_url(storage_account.name), storage_account_key, connection_data_block_size=4 * 1024)
        self._setup()
        blob_name = self.get_resource_name("blob")
        container, blob = self._create_container_and_append_blob(self.container_name, blob_name, bsc)
        test_etag = '0x8D2C9167D53FC2C'

        # Act
        with self.assertRaises(ResourceModifiedError) as e:
            data = self.get_random_bytes(LARGE_APPEND_BLOB_SIZE)
            blob.upload_blob(data, blob_type=BlobType.AppendBlob, if_match=test_etag)

        self.assertEqual(StorageErrorCode.condition_not_met, e.exception.error_code)

    @ResourceGroupPreparer()
    @StorageAccountPreparer(name_prefix='pyacrstorage')
    def test_append_blob_from_bytes_with_if_none_match(self, resource_group, location, storage_account, storage_account_key):
        bsc = BlobServiceClient(self._account_url(storage_account.name), storage_account_key, connection_data_block_size=4 * 1024)
        self._setup()
        blob_name = self.get_resource_name("blob")
        container, blob = self._create_container_and_append_blob(self.container_name, blob_name, bsc)
        test_etag = '0x8D2C9167D53FC2C'

        # Act
        data = self.get_random_bytes(LARGE_APPEND_BLOB_SIZE)
        blob.upload_blob(data, blob_type=BlobType.AppendBlob, if_none_match=test_etag)

        # Assert
        content = b"".join(list(blob.download_blob()))
        self.assertEqual(data, content)

    @ResourceGroupPreparer()
    @StorageAccountPreparer(name_prefix='pyacrstorage')
    def test_append_blob_from_bytes_with_if_none_match_fail(self, resource_group, location, storage_account, storage_account_key):
        bsc = BlobServiceClient(self._account_url(storage_account.name), storage_account_key, connection_data_block_size=4 * 1024)
        self._setup()
        blob_name = self.get_resource_name("blob")
        container, blob = self._create_container_and_append_blob(self.container_name, blob_name, bsc)
        test_etag = blob.get_blob_properties().etag

        # Act
        with self.assertRaises(ResourceModifiedError) as e:
            data = self.get_random_bytes(LARGE_APPEND_BLOB_SIZE)
            blob.upload_blob(data, blob_type=BlobType.AppendBlob, if_none_match=test_etag)

        self.assertEqual(StorageErrorCode.condition_not_met, e.exception.error_code)


# ------------------------------------------------------------------------------
