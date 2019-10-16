# coding=utf-8
# --------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
#
# Code generated by Microsoft (R) AutoRest Code Generator.
# Changes may cause incorrect behavior and will be lost if the code is
# regenerated.
# --------------------------------------------------------------------------

from msrest.service_client import SDKClient
from msrest import Serializer, Deserializer

from ._configuration import AttestationClientConfiguration
from .operations import AttestationClientOperationsMixin
from . import models


class AttestationClient(AttestationClientOperationsMixin, SDKClient):
    """Describes the interface for the per-tenant enclave service.

    :ivar config: Configuration for client.
    :vartype config: AttestationClientConfiguration

    :param credentials: Credentials needed for the client to connect to Azure.
    :type credentials: :mod:`A msrestazure Credentials
     object<msrestazure.azure_active_directory>`
    """

    def __init__(
            self, credentials):

        self.config = AttestationClientConfiguration(credentials)
        super(AttestationClient, self).__init__(self.config.credentials, self.config)

        client_models = {k: v for k, v in models.__dict__.items() if isinstance(v, type)}
        self.api_version = '2018-09-01-preview'
        self._serialize = Serializer(client_models)
        self._deserialize = Deserializer(client_models)

