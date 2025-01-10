# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2023 United Kingdom Research and Innovation
"""
Tests the AQ metadata dataclass, including
init from environment variables, and overriding values
"""

from typing import Dict

import pytest

from rabbit_consumer.aq_metadata import AqMetadata


@pytest.fixture(name="image_metadata")
def fixture_image_metadata() -> Dict[str, str]:
    """
    Creates a dictionary with mock data
    which represents an example OpenStack image's metadata
    """
    return {
        "AQ_ARCHETYPE": "archetype_mock",
        "AQ_DOMAIN": "domain_mock",
        "AQ_PERSONALITY": "personality_mock",
        "AQ_OS": "os_mock",
        "AQ_OSVERSION": "osversion_mock",
    }


def test_aq_metadata_from_initial_dict(image_metadata):
    """
    Tests creating an AQ metadata object from an initial dictionary
    """
    returned = AqMetadata.from_dict(image_metadata)

    assert returned.aq_archetype == "archetype_mock"
    assert returned.aq_domain == "domain_mock"
    assert returned.aq_personality == "personality_mock"
    assert returned.aq_os == "os_mock"
    assert returned.aq_os_version == "osversion_mock"


def test_aq_metadata_override_all(image_metadata):
    """
    Tests overriding all values in an AQ metadata object
    """
    returned = AqMetadata.from_dict(image_metadata)
    returned.override_from_vm_meta(
        {
            "AQ_ARCHETYPE": "archetype_mock_override",
            "AQ_DOMAIN": "domain_mock_override",
            "AQ_PERSONALITY": "personality_mock_override",
        }
    )

    assert returned.aq_archetype == "archetype_mock_override"
    assert returned.aq_domain == "domain_mock_override"
    assert returned.aq_personality == "personality_mock_override"

    # Check the original values are still there
    assert returned.aq_os == "os_mock"
    assert returned.aq_os_version == "osversion_mock"


def test_aq_metadata_override_with_none_values(image_metadata):
    """
    Tests that any invalid values, such as none, null or
    whitespace are all ignored when overriding from the image
    layer
    """
    returned = AqMetadata.from_dict(image_metadata)
    returned.override_from_vm_meta(
        {
            "AQ_ARCHETYPE": "archetype_mock_override",
            "AQ_DOMAIN": "None",
            "AQ_PERSONALITY": "null",
            "AQ_OS": "none",
            "AQ_OSVERSION": " ",  # Space intentionally left
            "AQ_SANDBOX": None,
        }
    )

    assert returned.aq_archetype == "archetype_mock_override"

    reference_metadata = AqMetadata.from_dict(image_metadata)
    assert returned.aq_domain == reference_metadata.aq_domain
    assert returned.aq_os == reference_metadata.aq_os
    assert returned.aq_os_version == reference_metadata.aq_os_version
    assert returned.aq_sandbox == reference_metadata.aq_sandbox


def test_aq_metadata_sandbox(image_metadata):
    """
    Tests the sandbox value in an AQ metadata object
    maps correctly onto the sandbox value
    """
    returned = AqMetadata.from_dict(image_metadata)
    returned.override_from_vm_meta(
        {
            "AQ_SANDBOX": "sandbox_mock",
        }
    )
    # This should be the only value that has changed
    assert returned.aq_sandbox == "sandbox_mock"

    assert returned.aq_archetype == "archetype_mock"
    assert returned.aq_personality == "personality_mock"
    assert returned.aq_os == "os_mock"
    assert returned.aq_os_version == "osversion_mock"
