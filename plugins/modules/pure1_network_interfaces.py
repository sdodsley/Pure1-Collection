#!/usr/bin/python
# -*- coding: utf-8 -*-

# (c) 2021, Simon Dodsley (simon@everpuredata.com)
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

ANSIBLE_METADATA = {
    "metadata_version": "1.1",
    "status": ["deprecated"],
    "supported_by": "community",
}

DOCUMENTATION = r"""
---
module: pure1_network_interfaces
version_added: '1.1.0'
deprecated:
  removed_in: '2.0.0'
  why: Replaced by more functional module
  alternative: Use M(everpure.pure1.pure1_nics) instead
short_description: Collect array netowrk interface details from Pure1
description:
  - Collect array network interface details from a Pure1.
author:
  - Everpure Ansible Team (@sdodsley) <pure-ansible-team@everpuredata.com>
options:
  name:
    description:
      - Name of appliance to obtain network interface drtails.
    type: str
    required: true
extends_documentation_fragment:
  - everpure.pure1.everpure.p1
"""

EXAMPLES = r"""
- name: collect network interface details for array foo
  everpure.pure1.pure1_network_interfaces:
    name: foo
"""

RETURN = r"""
network_info:
  description: Returns information on appliance network port configurations
  returned: always
  type: dict
"""


from ansible.module_utils.basic import AnsibleModule
from ansible_collections.everpure.pure1.plugins.module_utils.pure1 import (
    get_pure1,
    pure1_argument_spec,
)


def main():
    argument_spec = pure1_argument_spec()
    argument_spec.update(dict(name=dict(type="str", required=True)))

    module = AnsibleModule(argument_spec, supports_check_mode=True)
    pure_1 = get_pure1(module)

    network_info = {}

    interfaces = list(
        pure_1.get_network_interfaces(
            filter="arrays.name='" + module.params["name"] + "'"
        ).items
    )
    if not interfaces:
        module.fail_json(
            msg="Failed to get netowrk interfaces information. Check provided array name."
        )
    network_info[module.params["name"]] = {}

    for iface in range(0, len(interfaces)):
        port_name = interfaces[iface].name
        network_info[module.params["name"]][port_name] = {
            "services": interfaces[iface].services,
            "enabled": interfaces[iface].enabled,
            "gateway": getattr(interfaces[iface], "gateway", ""),
            "mtu": getattr(interfaces[iface], "mtu", ""),
            "netmask": getattr(interfaces[iface], "netmask", ""),
            "address": getattr(interfaces[iface], "address", ""),
            "subinterfaces": interfaces[iface].subinterfaces,
            "mac_address": getattr(interfaces[iface], "hwaddr", ""),
            "speed": round(getattr(interfaces[iface], "speed", 0) / 1000000000),
        }

    module.exit_json(changed=False, network_info=network_info)


if __name__ == "__main__":
    main()
