# ------------------------------------
# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.
# ------------------------------------
import os

from ..._constants import EnvironmentVariables
from .chained import ChainedTokenCredential
from .environment import EnvironmentCredential
from .managed_identity import ManagedIdentityCredential
from .user import SharedTokenCacheCredential


class DefaultAzureCredential(ChainedTokenCredential):
    """A default credential capable of handling most Azure SDK authentication scenarios.

    The identity it uses depends on the environment. When an access token is needed, it requests one using these
    identities in turn, stopping when one provides a token:

    1. A service principal configured by environment variables. See :class:`~azure.identity.aio.EnvironmentCredential`
       for more details.
    2. An Azure managed identity. See :class:`~azure.identity.aio.ManagedIdentityCredential` for more details.
    3. On Windows only: a user who has signed in with a Microsoft application, such as Visual Studio. This requires a
       value for the environment variable ``AZURE_USERNAME``. See
       :class:`~azure.identity.aio.SharedTokenCacheCredential` for more details.

    Keyword arguments
        - **authority** (str): Authority of an Azure Active Directory endpoint, for example 'login.microsoftonline.com',
          the authority for Azure Public Cloud (which is the default). :class:`~azure.identity.KnownAuthorities`
          defines authorities for other clouds. Managed identities ignore this because they reside in a single cloud.
    """

    def __init__(self, **kwargs):
        authority = kwargs.pop("authority", None)
        credentials = [EnvironmentCredential(authority=authority, **kwargs), ManagedIdentityCredential(**kwargs)]

        # SharedTokenCacheCredential is part of the default only on supported platforms, when $AZURE_USERNAME has a
        # value (because the cache may contain tokens for multiple identities and we can only choose one arbitrarily
        # without more information from the user), and when $AZURE_PASSWORD has no value (because when $AZURE_USERNAME
        # and $AZURE_PASSWORD are set, EnvironmentCredential will be used instead)
        if (
            SharedTokenCacheCredential.supported()
            and EnvironmentVariables.AZURE_USERNAME in os.environ
            and EnvironmentVariables.AZURE_PASSWORD not in os.environ
        ):
            credentials.append(
                SharedTokenCacheCredential(
                    username=os.environ.get(EnvironmentVariables.AZURE_USERNAME), authority=authority, **kwargs
                )
            )

        super().__init__(*credentials)
