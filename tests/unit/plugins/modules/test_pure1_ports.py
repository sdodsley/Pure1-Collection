# Copyright: (c) 2026, Everpure Ansible Team <pure-ansible-team@everpuredata.com>
# GNU General Public License v3.0+ (see COPYING.GPLv3 or https://www.gnu.org/licenses/gpl-3.0.txt)

"""Unit tests for the pure1_ports module."""

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
sys.modules["ansible_collections.everpure"] = MagicMock()
sys.modules["ansible_collections.everpure.pure1"] = MagicMock()
sys.modules["ansible_collections.everpure.pure1.plugins"] = MagicMock()
sys.modules["ansible_collections.everpure.pure1.plugins.module_utils"] = MagicMock()
sys.modules["ansible_collections.everpure.pure1.plugins.module_utils.pure1"] = (
    MagicMock()
)

from plugins.modules.pure1_ports import generate_ports_dict


def _make_port(array_name="array1", **overrides):
    port = types.SimpleNamespace(
        name="CT0.FC0",
        iqn=None,
        nqn=None,
        wwn="21000024FF000001",
        portal=None,
        failover=None,
        arrays=[types.SimpleNamespace(name=array_name)],
    )
    for key, value in overrides.items():
        setattr(port, key, value)
    return port


class TestGeneratePortsDict:
    """Tests for generate_ports_dict."""

    def test_basic_mapping(self):
        module = Mock()
        module.params = {"array": None}
        client = Mock()
        client.get_ports.return_value = Mock(items=[_make_port()])

        result = generate_ports_dict(module, client)

        client.get_ports.assert_called_once_with()
        assert result["array1"] == [
            {
                "CT0.FC0": {
                    "iqn": None,
                    "nqn": None,
                    "wwn": "21000024FF000001",
                    "portal": None,
                    "failover": None,
                }
            }
        ]

    def test_iscsi_port_fields(self):
        module = Mock()
        module.params = {"array": None}
        port = _make_port(
            name="CT0.ETH4",
            iqn="iqn.2010-06.com.purestorage:flasharray.1",
            wwn=None,
            portal="10.0.0.20:3260",
        )
        client = Mock()
        client.get_ports.return_value = Mock(items=[port])

        result = generate_ports_dict(module, client)

        details = result["array1"][0]["CT0.ETH4"]
        assert details["iqn"] == "iqn.2010-06.com.purestorage:flasharray.1"
        assert details["portal"] == "10.0.0.20:3260"
        assert details["wwn"] is None

    def test_array_filter_applied(self):
        module = Mock()
        module.params = {"array": "myarray"}
        client = Mock()
        client.get_ports.return_value = Mock(items=[_make_port("myarray")])

        generate_ports_dict(module, client)

        client.get_ports.assert_called_once_with(filter="arrays.name='myarray'")

    def test_grouping_across_arrays(self):
        module = Mock()
        module.params = {"array": None}
        client = Mock()
        client.get_ports.return_value = Mock(
            items=[_make_port("array1"), _make_port("array2")]
        )

        result = generate_ports_dict(module, client)

        assert set(result.keys()) == {"array1", "array2"}
