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

from msrest.serialization import Model


class InvoiceSectionWithCreateSubPermission(Model):
    """Invoice section properties with create subscription permission.

    Variables are only populated by the server, and will be ignored when
    sending a request.

    :ivar invoice_section_id: Invoice Section Id.
    :vartype invoice_section_id: str
    :ivar invoice_section_display_name: Invoice Section display name.
    :vartype invoice_section_display_name: str
    :ivar billing_profile_id: Billing profile Id.
    :vartype billing_profile_id: str
    :ivar billing_profile_display_name: Billing profile display name.
    :vartype billing_profile_display_name: str
    :param enabled_azure_plans: Enabled azure plans for the associated billing
     profile.
    :type enabled_azure_plans: list[~azure.mgmt.billing.models.AzurePlan]
    """

    _validation = {
        'invoice_section_id': {'readonly': True},
        'invoice_section_display_name': {'readonly': True},
        'billing_profile_id': {'readonly': True},
        'billing_profile_display_name': {'readonly': True},
    }

    _attribute_map = {
        'invoice_section_id': {'key': 'invoiceSectionId', 'type': 'str'},
        'invoice_section_display_name': {'key': 'invoiceSectionDisplayName', 'type': 'str'},
        'billing_profile_id': {'key': 'billingProfileId', 'type': 'str'},
        'billing_profile_display_name': {'key': 'billingProfileDisplayName', 'type': 'str'},
        'enabled_azure_plans': {'key': 'enabledAzurePlans', 'type': '[AzurePlan]'},
    }

    def __init__(self, *, enabled_azure_plans=None, **kwargs) -> None:
        super(InvoiceSectionWithCreateSubPermission, self).__init__(**kwargs)
        self.invoice_section_id = None
        self.invoice_section_display_name = None
        self.billing_profile_id = None
        self.billing_profile_display_name = None
        self.enabled_azure_plans = enabled_azure_plans
