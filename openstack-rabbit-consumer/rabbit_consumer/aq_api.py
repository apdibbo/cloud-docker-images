# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2023 United Kingdom Research and Innovation
"""
This file defines methods to be used to interact with the 
Aquilon API
"""
import logging
import subprocess
from typing import Optional, List

import requests
from requests.adapters import HTTPAdapter
from requests_kerberos import HTTPKerberosAuth
from urllib3.util.retry import Retry

from rabbit_consumer.consumer_config import ConsumerConfig
from rabbit_consumer.aq_metadata import AqMetadata
from rabbit_consumer.openstack_address import OpenstackAddress
from rabbit_consumer.rabbit_message import RabbitMessage
from rabbit_consumer.vm_data import VmData

HOST_CHECK_SUFFIX = "/host/{0}"

UPDATE_INTERFACE_SUFFIX = "/machine/{0}/interface/{1}?boot&default_route"

DELETE_HOST_SUFFIX = "/host/{0}"
DELETE_MACHINE_SUFFIX = "/machine/{0}"

logger = logging.getLogger(__name__)


class AquilonError(Exception):
    """
    Base class for Aquilon errors
    """


def verify_kerberos_ticket() -> bool:
    """
    Check for a valid Kerberos ticket from a sidecar, or on the host
    Raises a RuntimeError if no ticket is found
    """
    logger.debug("Checking for valid Kerberos Ticket")

    if subprocess.call(["klist", "-s"]) == 1:
        raise RuntimeError("No shared Kerberos ticket found.")

    logger.debug("Kerberos ticket success")
    return True


def setup_requests(
    url: str, method: str, desc: str, params: Optional[dict] = None
) -> str:
    """
    Passes a request to the Aquilon API
    """
    verify_kerberos_ticket()
    logger.debug("%s: %s - params: %s", method, url, params)

    session = requests.Session()
    session.verify = "/etc/grid-security/certificates/aquilon-gridpp-rl-ac-uk-chain.pem"
    retries = Retry(total=5, backoff_factor=0.1, status_forcelist=[503])
    session.mount("https://", HTTPAdapter(max_retries=retries))
    if method == "post":
        response = session.post(url, auth=HTTPKerberosAuth(), params=params)
    elif method == "put":
        response = session.put(url, auth=HTTPKerberosAuth(), params=params)
    elif method == "delete":
        response = session.delete(url, auth=HTTPKerberosAuth(), params=params)
    else:
        response = session.get(url, auth=HTTPKerberosAuth(), params=params)

    if response.status_code == 400:
        # This might be an expected error, so don't log it
        logger.debug("AQ Error Response: %s", response.text)
        raise AquilonError(response.text)

    if response.status_code != 200:
        logger.error("%s: Failed: %s", desc, response.text)
        logger.error(url)
        raise ConnectionError(
            f"Failed {desc}: {response.status_code} -" "{response.text}"
        )

    logger.debug("Success: %s ", desc)
    logger.debug("AQ Response: %s", response.text)
    return response.text


def aq_make(addresses: List[OpenstackAddress]) -> None:
    """
    Runs AQ make against a list of addresses passed to refresh
    the given host
    """
    # Manage and make these back to default domain and personality
    address = addresses[0]
    hostname = address.hostname
    logger.debug("Attempting to make templates for %s", hostname)

    if not hostname or not hostname.strip():
        raise ValueError("Hostname cannot be empty")

    url = ConsumerConfig().aq_url + f"/host/{hostname}/command/make"
    try:
        setup_requests(url, "post", "Make Template")
    # suppressing 400 error that occurs - the VM gets created fine
    # TODO: find out why this occurs
    except AquilonError:
        logger.debug("make request failed, continuing")


def aq_manage(addresses: List[OpenstackAddress], image_meta: AqMetadata) -> None:
    """
    Manages the list of Aquilon addresses passed to it back to the production domain
    """
    address = addresses[0]
    hostname = address.hostname
    logger.debug("Attempting to manage %s", hostname)

    params = {
        "hostname": hostname,
        "force": True,
    }
    if image_meta.aq_sandbox:
        params["sandbox"] = image_meta.aq_sandbox
    else:
        params["domain"] = image_meta.aq_domain

    url = ConsumerConfig().aq_url + f"/host/{hostname}/command/manage"
    setup_requests(url, "post", "Manage Host", params=params)


def create_machine(message: RabbitMessage, vm_data: VmData) -> str:
    """
    Creates a machine in Aquilon. Returns the machine name
    """
    logger.debug("Attempting to create machine for %s ", vm_data.virtual_machine_id)

    params = {
        "model": "vm-openstack",
        "serial": vm_data.virtual_machine_id,
        "vmhost": message.payload.vm_host,
        "cpucount": message.payload.vcpus,
        "memory": message.payload.memory_mb,
    }

    url = ConsumerConfig().aq_url + f"/next_machine/{ConsumerConfig().aq_prefix}"
    response = setup_requests(url, "put", "Create Machine", params=params)
    return response


def delete_machine(machine_name: str) -> None:
    """
    Deletes a machine in Aquilon
    """
    logger.debug("Attempting to delete machine for %s", machine_name)

    url = ConsumerConfig().aq_url + DELETE_MACHINE_SUFFIX.format(machine_name)

    setup_requests(url, "delete", "Delete Machine")


def create_host(
    image_meta: AqMetadata, addresses: List[OpenstackAddress], machine_name: str
) -> None:
    """
    Creates a host in Aquilon
    """
    config = ConsumerConfig()

    address = addresses[0]
    params = {
        "machine": machine_name,
        "ip": address.addr,
        "archetype": image_meta.aq_archetype,
        "personality": image_meta.aq_personality,
        "osname": image_meta.aq_os,
        "osversion": image_meta.aq_os_version,
    }

    if image_meta.aq_sandbox:
        params["sandbox"] = image_meta.aq_sandbox
    else:
        params["domain"] = image_meta.aq_domain

    logger.debug("Attempting to create host for %s ", address.hostname)
    url = config.aq_url + f"/host/{address.hostname}"
    setup_requests(url, "put", "Host Create", params=params)


def delete_host(hostname: str) -> None:
    """
    Deletes a host in Aquilon
    """
    logger.debug("Attempting to delete host for %s ", hostname)
    url = ConsumerConfig().aq_url + DELETE_HOST_SUFFIX.format(hostname)
    setup_requests(url, "delete", "Host Delete")


def delete_address(address: str, machine_name: str) -> None:
    """
    Deletes an address in Aquilon
    """
    logger.debug("Attempting to delete address for %s ", address)
    url = ConsumerConfig().aq_url + "/interface_address"
    params = {"ip": address, "machine": machine_name, "interface": "eth0"}
    setup_requests(url, "delete", "Address Delete", params=params)


def delete_interface(machine_name: str) -> None:
    """
    Deletes a host interface in Aquilon
    """
    logger.debug("Attempting to delete interface for %s ", machine_name)
    url = ConsumerConfig().aq_url + "/interface/command/del"
    params = {"interface": "eth0", "machine": machine_name}
    setup_requests(url, "post", "Interface Delete", params=params)


def add_machine_nics(machine_name: str, addresses: List[OpenstackAddress]) -> None:
    """
    Adds NICs to a given machine in Aquilon based on the VM addresses
    """
    # We only add the first host interface for now
    # this avoids having to do a lot of work to figure out
    # which interface names we have to use to clean-up
    address = addresses[0]
    interface_name = "eth0"

    logger.debug(
        "Attempting to add interface %s to machine %s ",
        interface_name,
        machine_name,
    )
    url = (
        ConsumerConfig().aq_url + f"/machine/{machine_name}/interface/{interface_name}"
    )
    setup_requests(
        url, "put", "Add Machine Interface", params={"mac": address.mac_addr}
    )


def set_interface_bootable(machine_name: str, interface_name: str) -> None:
    """
    Sets a given interface on a machine to be bootable
    """
    logger.debug("Attempting to bootable %s ", machine_name)

    url = ConsumerConfig().aq_url + UPDATE_INTERFACE_SUFFIX.format(
        machine_name, interface_name
    )

    setup_requests(url, "post", "Update Machine Interface")


def search_machine_by_serial(vm_data: VmData) -> Optional[str]:
    """
    Searches for a machine in Aquilon based on a serial number
    """
    logger.debug("Searching for host with serial %s", vm_data.virtual_machine_id)
    url = ConsumerConfig().aq_url + "/find/machine"
    params = {"serial": vm_data.virtual_machine_id}
    response = setup_requests(url, "get", "Search Host", params=params).strip()

    if response:
        return response
    return None


def search_host_by_machine(machine_name: str) -> Optional[str]:
    """
    Searches for a host in Aquilon based on a machine name
    """
    logger.debug("Searching for host with machine name %s", machine_name)
    url = ConsumerConfig().aq_url + "/find/host"
    params = {"machine": machine_name}
    response = setup_requests(url, "get", "Search Host", params=params).strip()

    if response:
        return response
    return None


def get_machine_details(machine_name: str) -> str:
    """
    Gets a machine's details as a string
    """
    logger.debug("Getting machine details for %s", machine_name)
    url = ConsumerConfig().aq_url + f"/machine/{machine_name}"
    return setup_requests(url, "get", "Get machine details").strip()


def check_host_exists(hostname: str) -> bool:
    """
    Checks if a host exists in Aquilon
    """
    logger.debug("Checking if hostname exists: %s", hostname)
    url = ConsumerConfig().aq_url + HOST_CHECK_SUFFIX.format(hostname)
    try:
        setup_requests(url, "get", "Check Host")
    except AquilonError as err:
        if f"Host {hostname} not found." in str(err):
            return False
        raise
    return True
