# Copyright: (c) 2026, Everpure Ansible Team <pure-ansible-team@everpuredata.com>
# GNU General Public License v3.0+ (see COPYING.GPLv3 or https://www.gnu.org/licenses/gpl-3.0.txt)

"""Unit tests for the pure1_alerts module."""

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

from plugins.modules import pure1_alerts


def _make_alert(**overrides):
    alert = types.SimpleNamespace(
        component_type="hardware",
        component_name="ct0.fan0",
        code=42,
        category="array",
        summary="Fan failure",
        created=0,
        updated=0,
        notified=0,
        arrays=[types.SimpleNamespace(name="foo")],
    )
    for key, value in overrides.items():
        setattr(alert, key, value)
    return alert


class TestPure1AlertsMain:
    """Tests for the pure1_alerts main() flow."""

    @patch("plugins.modules.pure1_alerts.get_pure1")
    @patch("plugins.modules.pure1_alerts.AnsibleModule")
    def test_named_array_alerts_are_collected(self, mock_am, mock_get_pure1):
        module = Mock()
        module.params = {"name": "foo", "severity": "critical", "state": "open"}
        mock_am.return_value = module
        client = Mock()
        client.get_alerts.return_value = Mock(items=[_make_alert()])
        mock_get_pure1.return_value = client

        pure1_alerts.main()

        client.get_alerts.assert_called_once_with(
            filter="arrays.name='foo' and severity='critical' and state='open'"
        )
        module.exit_json.assert_called_once()
        alert_info = module.exit_json.call_args[1]["alert_info"]
        assert alert_info[0]["code"] == 42
        assert alert_info[0]["summary"] == "Fan failure"
        # appliance_name is only added for fleet-wide (no name) queries
        assert "appliance_name" not in alert_info[0]

    @patch("plugins.modules.pure1_alerts.get_pure1")
    @patch("plugins.modules.pure1_alerts.AnsibleModule")
    def test_fleet_alerts_include_appliance_name(self, mock_am, mock_get_pure1):
        module = Mock()
        module.params = {"name": None, "severity": "warning", "state": "open"}
        mock_am.return_value = module
        client = Mock()
        client.get_alerts.return_value = Mock(items=[_make_alert()])
        mock_get_pure1.return_value = client

        pure1_alerts.main()

        client.get_alerts.assert_called_once_with(
            filter="severity='warning' and state='open'"
        )
        alert_info = module.exit_json.call_args[1]["alert_info"]
        assert alert_info[0]["appliance_name"] == "foo"

    @patch("plugins.modules.pure1_alerts.get_pure1")
    @patch("plugins.modules.pure1_alerts.AnsibleModule")
    def test_no_alerts_for_named_array_fails(self, mock_am, mock_get_pure1):
        module = Mock()
        module.params = {"name": "foo", "severity": "critical", "state": "open"}
        module.fail_json.side_effect = SystemExit("fail_json called")
        mock_am.return_value = module
        client = Mock()
        client.get_alerts.return_value = Mock(items=[])
        mock_get_pure1.return_value = client

        with pytest.raises(SystemExit):
            pure1_alerts.main()

        module.fail_json.assert_called_once()
