# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2023 United Kingdom Research and Innovation
"""
Tests that we perform the correct REST requests against
the Aquilon API
"""
from unittest import mock
from unittest.mock import patch, call, NonCallableMock

import pytest

# noinspection PyUnresolvedReferences
from rabbit_consumer.aq_api import (
    verify_kerberos_ticket,
    setup_requests,
    aq_make,
    aq_manage,
    create_machine,
    delete_machine,
    create_host,
    delete_host,
    set_interface_bootable,
    check_host_exists,
    AquilonError,
    add_machine_nics,
    search_machine_by_serial,
    search_host_by_machine,
)


def test_verify_kerberos_ticket_valid():
    """
    Test that verify_kerberos_ticket returns True when the ticket is valid
    """
    with patch("rabbit_consumer.aq_api.subprocess.call") as mocked_call:
        # Exit code 0 - i.e. valid ticket
        mocked_call.return_value = 0
        assert verify_kerberos_ticket()
        mocked_call.assert_called_once_with(["klist", "-s"])


@patch("rabbit_consumer.aq_api.subprocess.call")
def test_verify_kerberos_ticket_invalid(subprocess):
    """
    Test that verify_kerberos_ticket raises an exception when the ticket is invalid
    """
    # Exit code 1 - i.e. invalid ticket
    # Then 0 (kinit), 0 (klist -s)
    subprocess.side_effect = [1]

    with pytest.raises(RuntimeError):
        verify_kerberos_ticket()

    subprocess.assert_called_once_with(["klist", "-s"])


@patch("rabbit_consumer.aq_api.requests")
@patch("rabbit_consumer.aq_api.Retry")
@patch("rabbit_consumer.aq_api.HTTPAdapter")
@patch("rabbit_consumer.aq_api.verify_kerberos_ticket")
def test_setup_requests(verify_kerb, adapter, retry, requests):
    """
    Test that setup_requests sets up the Kerberos ticket and the requests session
    correctly
    """
    session = requests.Session.return_value
    response = session.get.return_value
    response.status_code = 200

    setup_requests(NonCallableMock(), NonCallableMock(), NonCallableMock())
    assert (
        session.verify
        == "/etc/grid-security/certificates/aquilon-gridpp-rl-ac-uk-chain.pem"
    )

    verify_kerb.assert_called_once()
    retry.assert_called_once_with(total=5, backoff_factor=0.1, status_forcelist=[503])
    adapter.assert_called_once_with(max_retries=retry.return_value)
    session.mount.assert_called_once_with("https://", adapter.return_value)


@patch("rabbit_consumer.aq_api.requests")
@patch("rabbit_consumer.aq_api.Retry")
@patch("rabbit_consumer.aq_api.HTTPAdapter")
@patch("rabbit_consumer.aq_api.verify_kerberos_ticket")
def test_setup_requests_throws_for_failed(verify_kerb, adapter, retry, requests):
    """
    Test that setup_requests throws an exception when the connection fails
    """
    session = requests.Session.return_value
    response = session.get.return_value
    response.status_code = 500

    with pytest.raises(ConnectionError):
        setup_requests(NonCallableMock(), NonCallableMock(), NonCallableMock())

    assert (
        session.verify
        == "/etc/grid-security/certificates/aquilon-gridpp-rl-ac-uk-chain.pem"
    )

    verify_kerb.assert_called_once()
    retry.assert_called_once_with(total=5, backoff_factor=0.1, status_forcelist=[503])
    adapter.assert_called_once_with(max_retries=retry.return_value)
    session.mount.assert_called_once_with("https://", adapter.return_value)
    session.get.assert_called_once()


@pytest.mark.parametrize("rest_verb", ["get", "post", "put", "delete"])
@patch("rabbit_consumer.aq_api.requests")
@patch("rabbit_consumer.aq_api.HTTPKerberosAuth")
@patch("rabbit_consumer.aq_api.verify_kerberos_ticket")
def test_setup_requests_rest_methods(_, kerb_auth, requests, rest_verb):
    """
    Test that setup_requests calls the correct REST method
    """
    url, desc, params = NonCallableMock(), NonCallableMock(), NonCallableMock()

    session = requests.Session.return_value

    rest_method = getattr(session, rest_verb)
    response = rest_method.return_value
    response.status_code = 200

    assert setup_requests(url, rest_verb, desc, params) == response.text
    rest_method.assert_called_once_with(url, auth=kerb_auth.return_value, params=params)


@patch("rabbit_consumer.aq_api.setup_requests")
@patch("rabbit_consumer.aq_api.ConsumerConfig")
def test_aq_make_calls(config, setup, openstack_address_list):
    """
    Test that aq_make calls the correct URLs with the correct parameters
    """
    domain = "domain"
    config.return_value.aq_url = domain

    aq_make(openstack_address_list)

    expected_url = f"{domain}/host/{openstack_address_list[0].hostname}/command/make"
    setup.assert_called_once_with(expected_url, "post", mock.ANY)


@patch("rabbit_consumer.aq_api.setup_requests")
@patch("rabbit_consumer.aq_api.ConsumerConfig")
def test_aq_make_aquilon_error(config, setup, openstack_address_list):
    """
    Test that aq_make doesn't fail when aquilon error raised
    """
    domain = "domain"
    config.return_value.aq_url = domain
    setup.side_effect = AquilonError()

    # pylint:disable=bare-except
    try:
        aq_make(openstack_address_list)
    except:
        assert False, "exception was raised when it should have been ignored"

    expected_url = f"{domain}/host/{openstack_address_list[0].hostname}/command/make"
    setup.assert_called_once_with(expected_url, "post", mock.ANY)


@pytest.mark.parametrize("hostname", ["  ", "", None])
@patch("rabbit_consumer.aq_api.setup_requests")
@patch("rabbit_consumer.aq_api.ConsumerConfig")
def test_aq_make_none_hostname(config, setup, openstack_address, hostname):
    """
    Test that aq_make throws an exception if the field is missing
    """
    domain = "https://example.com"
    config.return_value.aq_url = domain

    address = openstack_address
    address.hostname = hostname

    with pytest.raises(ValueError):
        aq_make([address])

    setup.assert_not_called()


@patch("rabbit_consumer.aq_api.setup_requests")
@patch("rabbit_consumer.aq_api.ConsumerConfig")
def test_aq_manage(config, setup, openstack_address_list, image_metadata):
    """
    Test that aq_manage calls the correct URLs with the correct parameters
    """
    config.return_value.aq_url = "https://example.com"

    aq_manage(openstack_address_list, image_metadata)
    address = openstack_address_list[0]

    expected_param = {
        "hostname": address.hostname,
        "domain": image_metadata.aq_domain,
        "force": True,
    }

    expected_url = f"https://example.com/host/{address.hostname}/command/manage"
    setup.assert_called_once_with(expected_url, "post", mock.ANY, params=expected_param)


@patch("rabbit_consumer.aq_api.setup_requests")
@patch("rabbit_consumer.aq_api.ConsumerConfig")
def test_aq_manage_with_sandbox(config, setup, openstack_address_list, image_metadata):
    """
    Test that aq_manage calls the correct URLs with the sandbox
    instead of the domain
    """
    config.return_value.aq_url = "https://example.com"

    image_metadata.aq_sandbox = "some_sandbox"

    aq_manage(openstack_address_list, image_metadata)
    address = openstack_address_list[0]

    expected_param = {
        "hostname": address.hostname,
        "sandbox": image_metadata.aq_sandbox,
        "force": True,
    }

    expected_url = f"https://example.com/host/{address.hostname}/command/manage"
    setup.assert_called_once_with(expected_url, "post", mock.ANY, params=expected_param)


@patch("rabbit_consumer.aq_api.ConsumerConfig")
@patch("rabbit_consumer.aq_api.setup_requests")
def test_aq_create_machine(setup, config, rabbit_message, vm_data):
    """
    Test that aq_create_machine calls the correct URL with the correct parameters
    """
    config.return_value.aq_url = "https://example.com"
    config.return_value.aq_prefix = "prefix_mock"

    returned = create_machine(rabbit_message, vm_data)

    expected_args = {
        "model": "vm-openstack",
        "serial": vm_data.virtual_machine_id,
        "vmhost": rabbit_message.payload.vm_host,
        "cpucount": rabbit_message.payload.vcpus,
        "memory": rabbit_message.payload.memory_mb,
    }

    expected_url = "https://example.com/next_machine/prefix_mock"
    assert setup.call_args == call(expected_url, "put", mock.ANY, params=expected_args)
    assert returned == setup.return_value


@patch("rabbit_consumer.aq_api.setup_requests")
@patch("rabbit_consumer.aq_api.ConsumerConfig")
def test_aq_delete_machine(config, setup):
    """
    Test that aq_delete_machine calls the correct URL with the correct parameters
    """
    machine_name = "name_mock"

    config.return_value.aq_url = "https://example.com"
    delete_machine(machine_name)

    setup.assert_called_once()
    expected_url = "https://example.com/machine/name_mock"
    assert setup.call_args == call(expected_url, "delete", mock.ANY)


@patch("rabbit_consumer.aq_api.setup_requests")
@patch("rabbit_consumer.aq_api.ConsumerConfig")
def test_aq_create_host(config, setup, openstack_address_list, image_metadata):
    """
    Test that aq_create_host calls the correct URL with the correct parameters
    """
    machine_name = "machine_name_str"

    env_config = config.return_value
    env_config.aq_url = "https://example.com"

    create_host(image_metadata, openstack_address_list, machine_name)
    address = openstack_address_list[0]

    expected_params = {
        "machine": machine_name,
        "ip": address.addr,
        "archetype": image_metadata.aq_archetype,
        "domain": image_metadata.aq_domain,
        "personality": image_metadata.aq_personality,
        "osname": image_metadata.aq_os,
        "osversion": image_metadata.aq_os_version,
    }

    expected_url = f"https://example.com/host/{address.hostname}"
    setup.assert_called_once_with(expected_url, "put", mock.ANY, params=expected_params)


@patch("rabbit_consumer.aq_api.setup_requests")
@patch("rabbit_consumer.aq_api.ConsumerConfig")
def test_aq_create_host_with_sandbox(
    config, setup, openstack_address_list, image_metadata
):
    """
    Test that aq_create_host calls the correct URL with the correct parameters
    """
    machine_name = "machine_name_str"

    env_config = config.return_value
    env_config.aq_url = "https://example.com"

    image_metadata.aq_domain = "example_domain"
    image_metadata.aq_sandbox = "example/sandbox"

    create_host(image_metadata, openstack_address_list, machine_name)
    address = openstack_address_list[0]

    expected_params = {
        "machine": machine_name,
        "ip": address.addr,
        "archetype": image_metadata.aq_archetype,
        "personality": image_metadata.aq_personality,
        "osname": image_metadata.aq_os,
        "osversion": image_metadata.aq_os_version,
        "sandbox": image_metadata.aq_sandbox,
    }

    expected_url = f"https://example.com/host/{address.hostname}"
    setup.assert_called_once_with(expected_url, "put", mock.ANY, params=expected_params)


@patch("rabbit_consumer.aq_api.setup_requests")
@patch("rabbit_consumer.aq_api.ConsumerConfig")
def test_aq_delete_host(config, setup):
    """
    Test that aq_delete_host calls the correct URL with the correct parameters
    """
    machine_name = "name_mock"

    config.return_value.aq_url = "https://example.com"
    delete_host(machine_name)

    setup.assert_called_once()
    expected_url = "https://example.com/host/name_mock"
    assert setup.call_args == call(expected_url, "delete", mock.ANY)


@patch("rabbit_consumer.aq_api.setup_requests")
@patch("rabbit_consumer.aq_api.ConsumerConfig")
def test_add_machine_nic(config, setup, openstack_address_list):
    """
    Test that add_machine_interface calls the correct URL with the correct parameters
    """
    config.return_value.aq_url = "https://example.com"

    machine_name = "name_str"
    add_machine_nics(machine_name, openstack_address_list)

    iface_creation_url = f"https://example.com/machine/{machine_name}/interface/eth0"

    setup.assert_called_once_with(
        iface_creation_url,
        "put",
        mock.ANY,
        params={"mac": openstack_address_list[0].mac_addr},
    )


@patch("rabbit_consumer.aq_api.setup_requests")
@patch("rabbit_consumer.aq_api.ConsumerConfig")
def test_update_machine_interface(config, setup):
    """
    Test that update_machine_interface calls the correct URL with the correct parameters
    """
    machine_name = "machine_str"
    interface_name = "iface_name"

    config.return_value.aq_url = "https://example.com"
    set_interface_bootable(machine_name=machine_name, interface_name=interface_name)

    setup.assert_called_once()
    expected_url = "https://example.com/machine/machine_str/interface/iface_name?boot&default_route"
    assert setup.call_args == call(expected_url, "post", mock.ANY)


@patch("rabbit_consumer.aq_api.setup_requests")
@patch("rabbit_consumer.aq_api.ConsumerConfig")
def test_check_host_exists(config, setup):
    """
    Test that check_host_exists calls the correct URL with the correct parameters
    and detects the host exists based on the response
    """
    hostname = "host_str"

    config.return_value.aq_url = "https://example.com"
    assert check_host_exists(hostname)

    expected_url = f"https://example.com/host/{hostname}"
    setup.assert_called_once_with(expected_url, "get", mock.ANY)


@patch("rabbit_consumer.aq_api.setup_requests")
@patch("rabbit_consumer.aq_api.ConsumerConfig")
def test_check_host_exists_returns_false(config, setup):
    """
    Test that check_host_exists calls the correct URL with the correct parameters
    and detects the host does not exist based on the response
    """
    hostname = "host_str"
    config.return_value.aq_url = "https://example.com"
    setup.side_effect = AquilonError(f"Error:\n Host {hostname} not found.")

    assert not check_host_exists(hostname)


@patch("rabbit_consumer.aq_api.setup_requests")
@patch("rabbit_consumer.aq_api.ConsumerConfig")
def test_search_machine_by_serial(config, setup, vm_data):
    """
    Test that search_machine_by_serial calls the correct URL with the correct parameters
    """
    config.return_value.aq_url = "https://example.com"
    response = search_machine_by_serial(vm_data)

    expected_url = "https://example.com/find/machine"
    expected_args = {"serial": vm_data.virtual_machine_id}
    setup.assert_called_once_with(expected_url, "get", mock.ANY, params=expected_args)
    assert response == setup.return_value.strip.return_value


@patch("rabbit_consumer.aq_api.setup_requests")
@patch("rabbit_consumer.aq_api.ConsumerConfig")
def test_search_machine_by_serial_not_found(config, setup, vm_data):
    """
    Test that search_machine_by_serial calls the correct URL with the correct parameters
    """
    config.return_value.aq_url = "https://example.com"
    setup.return_value = ""
    response = search_machine_by_serial(vm_data)

    expected_url = "https://example.com/find/machine"
    expected_args = {"serial": vm_data.virtual_machine_id}
    setup.assert_called_once_with(expected_url, "get", mock.ANY, params=expected_args)
    assert response is None


@patch("rabbit_consumer.aq_api.setup_requests")
@patch("rabbit_consumer.aq_api.ConsumerConfig")
def test_search_host_by_machine(config, setup):
    """
    Test that search_host_by_machine calls the correct URL with the correct parameters
    to return the host name
    """
    config.return_value.aq_url = "https://example.com"
    response = search_host_by_machine("machine_name")

    expected_url = "https://example.com/find/host"
    expected_args = {"machine": "machine_name"}
    setup.assert_called_once_with(expected_url, "get", mock.ANY, params=expected_args)
    assert response == setup.return_value.strip.return_value


@patch("rabbit_consumer.aq_api.setup_requests")
@patch("rabbit_consumer.aq_api.ConsumerConfig")
def test_search_host_by_machine_not_found(config, setup):
    """
    Test that search_host_by_machine calls the correct URL with the correct parameters
    to return the host name
    """
    config.return_value.aq_url = "https://example.com"
    setup.return_value = ""
    response = search_host_by_machine("machine_name")

    expected_url = "https://example.com/find/host"
    expected_args = {"machine": "machine_name"}
    setup.assert_called_once_with(expected_url, "get", mock.ANY, params=expected_args)
    assert response is None
