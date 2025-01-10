# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2023 United Kingdom Research and Innovation
"""
This file defines the class to handle deserialised metadata for 
Aquilon
"""
import logging
from dataclasses import dataclass
from typing import Dict, Optional, Union

from mashumaro import DataClassDictMixin
from mashumaro.config import BaseConfig

logger = logging.getLogger(__name__)


# Case in-sensitive values that are considered invalid
_INVALID_VALUES = ["none", "null", ""]


@dataclass
class AqMetadata(DataClassDictMixin):
    """
    Deserialised metadata that is set either on an Openstack image
    or a VM's metadata
    """

    aq_archetype: str
    aq_domain: str

    aq_personality: str
    aq_os_version: str
    aq_os: str

    aq_sandbox: Optional[str] = None

    # pylint: disable=too-few-public-methods
    class Config(BaseConfig):
        """
        Sets the aliases for the metadata keys
        """

        aliases = {
            "aq_archetype": "AQ_ARCHETYPE",
            "aq_domain": "AQ_DOMAIN",
            "aq_sandbox": "AQ_SANDBOX",
            "aq_personality": "AQ_PERSONALITY",
            "aq_os_version": "AQ_OSVERSION",
            "aq_os": "AQ_OS",
        }

    def override_from_vm_meta(self, vm_meta: Dict[str, str]):
        """
        Overrides the values in the metadata with the values from the VM's
        metadata if they are present and sane
        """
        for attr, alias in self.Config.aliases.items():
            if alias not in vm_meta:
                continue

            if not self._is_metadata_val_valid(vm_meta[alias]):
                logger.warning(
                    "Invalid metadata value '%s' found for metadata property '%s', skipping",
                    vm_meta[alias],
                    alias,
                )
                continue

            setattr(self, attr, vm_meta[alias])

    @staticmethod
    def _is_metadata_val_valid(val: Union[str, None]) -> bool:
        """
        Tests if an individual metadata value is sane, i.e.
        a str which is not null, or a blocked value.
        If this is valid, it returns true
        """
        if not val:
            return False

        user_val = val.lower().strip()
        if user_val in _INVALID_VALUES:
            return False
        return True
