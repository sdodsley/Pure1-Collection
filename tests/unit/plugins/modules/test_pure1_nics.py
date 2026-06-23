# Copyright: (c) 2026, Everpure Ansible Team <pure-ansible-team@everpuredata.com>
# GNU General Public License v3.0+ (see COPYING.GPLv3 or https://www.gnu.org/licenses/gpl-3.0.txt)

"""Unit tests for the pure1_nics module."""

from __future__ import absolute_import, division, print_function

__metaclass__ = type

import sys
import types
from unittest.mock import Mock, MagicMock

# Mock external dependencies before importing the module
sys.modules["ansible"] = MagicMock()
sys.modules["ansible.module_utils"] = MagicMock()
sys.modules["ansible.module_utils.basic"] = MagicMock()
sys.modules["pypureclient"] = MagicMock()
sys.modules["pypureclient.pure1"] = MagicMock()
sys.modules["ansible_collections"] = MagicMock()
sys.modules["ansible_collections.purestorage"] = MagicMock()
sys.modules["ansible_collections.purestorage.pure1"] = MagicMock()
sys.modules["ansible_collections.purestorage.pure1.plugins"] = MagicMock()
sys.modules["ansible_collections.purestorage.pure1.plugins.module_utils"] = MagicMock()
sys.modules["ansible_collections.purestorage.pure1.plugins.module_utils.pure1"] = (
    MagicMock()
)

from plugins.modules.pure1_nics import generate_nics_dict


def _make_nic(array_name="array1", **overrides):
    nic = types.SimpleNamespace(
        name="ct0.eth0",
        address="10.0.0.10",
        gateway="10.0.0.1",
        hwaddr="aa:bb:cc:dd:ee:ff",
        netmask="255.255.255.0",
        mtu=1500,
        speed=10000000000,  # 10 Gb/s in bits/s
        enabled=True,
        arrays=[types.SimpleNamespace(name=array_name)],
    )
    for key, value in overrides.items():
        setattr(nic, key, value)
    return nic


class TestGenerateNicsDict:
    """Tests for generate_nics_dict."""

    def test_basic_mapping_and_speed_rounding(self):
        module = Mock()
        module.params = {"array": None}
        client = Mock()
        client.get_network_interfaces.return_value = Mock(items=[_make_nic()])

        result = generate_nics_dict(module, client)

        client.get_network_interfaces.assert_called_once_with()
        details = result["array1"][0]["ct0.eth0"]
        assert details["address"] == "10.0.0.10"
        assert details["mtu"] == 1500
        assert details["speed"] == 10  # 10000000000 / 1e9 rounded
        assert details["enabled"] is True
        assert details["services"] == []
        assert details["subinterfaces"] == []

    def test_services_and_subinterfaces_populated(self):
        module = Mock()
        module.params = {"array": None}
        nic = _make_nic(services=["management"], subinterfaces=["ct0.eth1"])
        client = Mock()
        client.get_network_interfaces.return_value = Mock(items=[nic])

        result = generate_nics_dict(module, client)

        details = result["array1"][0]["ct0.eth0"]
        assert details["services"] == ["management"]
        assert details["subinterfaces"] == ["ct0.eth1"]

    def test_array_filter_applied(self):
        module = Mock()
        module.params = {"array": "myarray"}
        client = Mock()
        client.get_network_interfaces.return_value = Mock(items=[_make_nic("myarray")])

        generate_nics_dict(module, client)

        client.get_network_interfaces.assert_called_once_with(
            filter="arrays.name='myarray'"
        )

    def test_grouping_across_arrays(self):
        module = Mock()
        module.params = {"array": None}
        client = Mock()
        client.get_network_interfaces.return_value = Mock(
            items=[_make_nic("array1"), _make_nic("array2")]
        )

        result = generate_nics_dict(module, client)

        assert set(result.keys()) == {"array1", "array2"}

    def test_zero_speed_rounds_to_zero(self):
        module = Mock()
        module.params = {"array": None}
        client = Mock()
        client.get_network_interfaces.return_value = Mock(items=[_make_nic(speed=0)])

        result = generate_nics_dict(module, client)

        assert result["array1"][0]["ct0.eth0"]["speed"] == 0
