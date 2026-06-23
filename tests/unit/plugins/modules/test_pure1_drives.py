# Copyright: (c) 2026, Everpure Ansible Team <pure-ansible-team@everpuredata.com>
# GNU General Public License v3.0+ (see COPYING.GPLv3 or https://www.gnu.org/licenses/gpl-3.0.txt)

"""Unit tests for the pure1_drives module."""

from __future__ import absolute_import, division, print_function

__metaclass__ = type

import sys
import types
import pytest
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

from plugins.modules.pure1_drives import generate_drives_dict


def _make_drive(array_name="array1", **overrides):
    drive = types.SimpleNamespace(
        name="drive0",
        capacity=1099511627776,
        protocol="NVMe",
        status="healthy",
        type="SSD",
        arrays=[types.SimpleNamespace(name=array_name)],
    )
    for key, value in overrides.items():
        setattr(drive, key, value)
    return drive


class TestGenerateDrivesDict:
    """Tests for generate_drives_dict."""

    def test_basic_mapping_grouped_by_array(self):
        module = Mock()
        module.params = {"array": None}
        client = Mock()
        client.get_drives.return_value = Mock(items=[_make_drive()])

        result = generate_drives_dict(module, client)

        client.get_drives.assert_called_once_with()
        assert "array1" in result
        assert result["array1"] == [
            {
                "drive0": {
                    "capacity": 1099511627776,
                    "protocol": "NVMe",
                    "status": "healthy",
                    "type": "SSD",
                }
            }
        ]

    def test_array_filter_applied_with_results(self):
        module = Mock()
        module.params = {"array": "myarray"}
        client = Mock()
        client.get_drives.return_value = Mock(
            status_code=200, total_item_count=1, items=[_make_drive("myarray")]
        )

        result = generate_drives_dict(module, client)

        client.get_drives.assert_called_once_with(filter="arrays.name='myarray'")
        assert "myarray" in result

    def test_array_filter_no_results_warns_and_exits(self):
        module = Mock()
        module.params = {"array": "myarray"}
        module.exit_json.side_effect = SystemExit("exit_json called")
        client = Mock()
        client.get_drives.return_value = Mock(
            status_code=200, total_item_count=0, items=[]
        )

        with pytest.raises(SystemExit):
            generate_drives_dict(module, client)

        module.warn.assert_called_once()
        module.exit_json.assert_called_once_with(changed=False)

    def test_multiple_drives_same_array_grouped(self):
        module = Mock()
        module.params = {"array": None}
        client = Mock()
        client.get_drives.return_value = Mock(
            items=[
                _make_drive("array1", name="drive0"),
                _make_drive("array1", name="drive1"),
            ]
        )

        result = generate_drives_dict(module, client)

        assert set(result.keys()) == {"array1"}
        assert len(result["array1"]) == 2

    def test_missing_attributes_default_to_none(self):
        module = Mock()
        module.params = {"array": None}
        bare = types.SimpleNamespace(
            name="drive0", arrays=[types.SimpleNamespace(name="array1")]
        )
        client = Mock()
        client.get_drives.return_value = Mock(items=[bare])

        result = generate_drives_dict(module, client)

        assert result["array1"][0]["drive0"] == {
            "capacity": None,
            "protocol": None,
            "status": None,
            "type": None,
        }
