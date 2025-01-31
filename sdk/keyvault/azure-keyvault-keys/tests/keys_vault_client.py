# ------------------------------------
# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.
# ------------------------------------
try:
    from typing import TYPE_CHECKING
except ImportError:
    TYPE_CHECKING = False

from azure.keyvault.keys._shared import KeyVaultClientBase
from azure.keyvault.keys import KeyClient
from azure.keyvault.keys.crypto import CryptographyClient

if TYPE_CHECKING:
    # pylint:disable=unused-import
    from azure.core import Configuration
    from azure.core.credentials import TokenCredential
    from azure.core.pipeline.transport import HttpTransport
    from typing import Any, Optional


class VaultClient(KeyVaultClientBase):
    def __init__(self, vault_endpoint, credential, transport=None, api_version=None, **kwargs):
        # type: (str, TokenCredential, Optional[HttpTransport], Optional[str], **Any) -> None
        super(VaultClient, self).__init__(
            vault_endpoint, credential, transport=transport, api_version=api_version, **kwargs
        )
        self._credential = credential
        self._keys = KeyClient(self.vault_endpoint, credential, generated_client=self._client, **kwargs)

    def get_cryptography_client(self, key):
        return CryptographyClient(key, self._credential)

    @property
    def keys(self):
        """
        :rtype: ~azure.keyvault.keys.KeyClient
        """
        return self._keys
