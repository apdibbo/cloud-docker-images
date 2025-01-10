# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2023 United Kingdom Research and Innovation
"""
Test the consumer config class, this handles the environment variables
that are used to configure the consumer.
"""
import pytest

from rabbit_consumer.consumer_config import ConsumerConfig

AQ_FIELDS = [
    ("aq_prefix", "AQ_PREFIX"),
    ("aq_url", "AQ_URL"),
]

OPENSTACK_FIELDS = [
    ("openstack_auth_url", "OPENSTACK_AUTH_URL"),
    ("openstack_compute_url", "OPENSTACK_COMPUTE_URL"),
    ("openstack_username", "OPENSTACK_USERNAME"),
    ("openstack_password", "OPENSTACK_PASSWORD"),
]

RABBIT_FIELDS = [
    ("rabbit_hosts", "RABBIT_HOST"),
    ("rabbit_port", "RABBIT_PORT"),
    ("rabbit_username", "RABBIT_USERNAME"),
    ("rabbit_password", "RABBIT_PASSWORD"),
]


@pytest.mark.parametrize(
    "config_name,env_var", AQ_FIELDS + OPENSTACK_FIELDS + RABBIT_FIELDS
)
def test_config_gets_os_env_vars(monkeypatch, config_name, env_var):
    """
    Test that the config class pulls the correct values from the environment.
    """
    expected = "MOCK_ENV"
    monkeypatch.setenv(env_var, expected)
    assert getattr(ConsumerConfig(), config_name) == expected
