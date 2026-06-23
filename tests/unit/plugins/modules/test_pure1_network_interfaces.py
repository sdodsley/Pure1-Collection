# Copyright: (c) 2026, Everpure Ansible Team <pure-ansible-team@everpuredata.com>
# GNU General Public License v3.0+ (see COPYING.GPLv3 or https://www.gnu.org/licenses/gpl-3.0.txt)

"""Unit tests for the (deprecated) pure1_network_interfaces module."""

from __future__ import absolute_import, division, print_function

__metaclass__ = type

import sys
import types
import pytest
from unittest.mock import Mock, patch, MagicMock

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

from plugins.modules import pure1_network_interfaces


def _make_iface(**overrides):
    iface = types.SimpleNamespace(
        name="ct0.eth0",
        services=["management"],
        enabled=True,
        gateway="10.0.0.1",
        mtu=1500,
        netmask="255.255.255.0",
        address="10.0.0.10",
        subinterfaces=[],
        hwaddr="aa:bb:cc:dd:ee:ff",
        speed=25000000000,  # 25 Gb/s in bits/s
    )
    for key, value in overrides.items():
        setattr(iface, key, value)
    return iface


class TestPure1NetworkInterfacesMain:
    """Tests for the pure1_network_interfaces main() flow."""

    @patch("plugins.modules.pure1_network_interfaces.get_pure1")
    @patch("plugins.modules.pure1_network_interfaces.AnsibleModule")
    def test_collects_interface_details(self, mock_am, mock_get_pure1):
        module = Mock()
        module.params = {"name": "foo"}
        mock_am.return_value = module
        client = Mock()
        client.get_network_interfaces.return_value = Mock(items=[_make_iface()])
        mock_get_pure1.return_value = client

        pure1_network_interfaces.main()

        client.get_network_interfaces.assert_called_once_with(
            filter="arrays.name='foo'"
        )
        module.exit_json.assert_called_once()
        network_info = module.exit_json.call_args[1]["network_info"]
        port = network_info["foo"]["ct0.eth0"]
        assert port["address"] == "10.0.0.10"
        assert port["mac_address"] == "aa:bb:cc:dd:ee:ff"
        assert port["speed"] == 25  # 25000000000 / 1e9 rounded
        assert port["services"] == ["management"]
        assert port["enabled"] is True

    @patch("plugins.modules.pure1_network_interfaces.get_pure1")
    @patch("plugins.modules.pure1_network_interfaces.AnsibleModule")
    def test_no_interfaces_fails(self, mock_am, mock_get_pure1):
        module = Mock()
        module.params = {"name": "foo"}
        module.fail_json.side_effect = SystemExit("fail_json called")
        mock_am.return_value = module
        client = Mock()
        client.get_network_interfaces.return_value = Mock(items=[])
        mock_get_pure1.return_value = client

        with pytest.raises(SystemExit):
            pure1_network_interfaces.main()

        module.fail_json.assert_called_once()
