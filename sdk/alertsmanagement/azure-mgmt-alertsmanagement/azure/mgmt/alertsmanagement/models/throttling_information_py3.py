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


class ThrottlingInformation(Model):
    """Optional throttling information for the alert rule.

    :param duration: The required duration (in ISO8601 format) to wait before
     notifying on the alert rule again. The time granularity must be in minutes
     and minimum value is 0 minutes
    :type duration: timedelta
    """

    _attribute_map = {
        'duration': {'key': 'duration', 'type': 'duration'},
    }

    def __init__(self, *, duration=None, **kwargs) -> None:
        super(ThrottlingInformation, self).__init__(**kwargs)
        self.duration = duration
