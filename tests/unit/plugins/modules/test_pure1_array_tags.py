# Copyright: (c) 2026, Everpure Ansible Team <pure-ansible-team@everpuredata.com>
# GNU General Public License v3.0+ (see COPYING.GPLv3 or https://www.gnu.org/licenses/gpl-3.0.txt)

"""Unit tests for the pure1_array_tags module."""

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

from plugins.modules.pure1_array_tags import create_tag, update_tag, delete_tag


def _ok():
    return Mock(status_code=200)


def _err(message="boom"):
    return Mock(status_code=400, errors=[types.SimpleNamespace(message=message)])


class TestCreateTag:
    """Tests for create_tag."""

    def test_check_mode_makes_no_api_call(self):
        module = Mock()
        module.check_mode = True
        module.params = {"name": "foo", "tag": ["key1:value1"]}
        client = Mock()

        create_tag(module, client)

        client.put_arrays_tags.assert_not_called()
        module.exit_json.assert_called_once_with(changed=True)

    def test_creates_tag_with_parsed_key_value(self):
        module = Mock()
        module.check_mode = False
        module.params = {"name": "foo", "tag": ["key1:value1"]}
        client = Mock()
        client.put_arrays_tags.return_value = _ok()

        create_tag(module, client)

        client.put_arrays_tags.assert_called_once_with(
            resource_names=["foo"], tag={"key": "key1", "value": "value1"}
        )
        module.exit_json.assert_called_once_with(changed=True)

    def test_api_failure_calls_fail_json(self):
        module = Mock()
        module.check_mode = False
        module.params = {"name": "foo", "tag": ["key1:value1"]}
        module.fail_json.side_effect = SystemExit("fail_json called")
        client = Mock()
        client.put_arrays_tags.return_value = _err()

        with pytest.raises(SystemExit):
            create_tag(module, client)

        module.fail_json.assert_called_once()


class TestUpdateTag:
    """Tests for update_tag."""

    def test_existing_tag_same_value_no_change(self):
        module = Mock()
        module.check_mode = False
        module.params = {"name": "foo", "tag": ["key1:value1"]}
        current = [types.SimpleNamespace(key="key1", value="value1")]
        client = Mock()

        update_tag(module, client, current)

        client.put_arrays_tags.assert_not_called()
        module.exit_json.assert_called_once_with(changed=False)

    def test_existing_tag_changed_value_updates(self):
        module = Mock()
        module.check_mode = False
        module.params = {"name": "foo", "tag": ["key1:value2"]}
        current = [types.SimpleNamespace(key="key1", value="value1")]
        client = Mock()
        client.put_arrays_tags.return_value = _ok()

        update_tag(module, client, current)

        client.put_arrays_tags.assert_called_once_with(
            resource_names=["foo"], tag={"key": "key1", "value": "value2"}
        )
        module.exit_json.assert_called_once_with(changed=True)

    def test_new_tag_is_added(self):
        module = Mock()
        module.check_mode = False
        module.params = {"name": "foo", "tag": ["key2:value2"]}
        current = [types.SimpleNamespace(key="key1", value="value1")]
        client = Mock()
        client.put_arrays_tags.return_value = _ok()

        update_tag(module, client, current)

        client.put_arrays_tags.assert_called_once_with(
            resource_names=["foo"], tag={"key": "key2", "value": "value2"}
        )
        module.exit_json.assert_called_once_with(changed=True)


class TestDeleteTag:
    """Tests for delete_tag."""

    def test_matching_tag_is_deleted(self):
        module = Mock()
        module.check_mode = False
        module.params = {"name": "foo", "tag": ["key1:value1"]}
        current = [types.SimpleNamespace(key="key1", value="value1")]
        client = Mock()
        client.delete_arrays_tags.return_value = _ok()

        delete_tag(module, client, current)

        client.delete_arrays_tags.assert_called_once_with(
            resource_names=["foo"], keys="key1"
        )
        module.exit_json.assert_called_once_with(changed=True)

    def test_non_matching_tag_is_not_deleted(self):
        module = Mock()
        module.check_mode = False
        module.params = {"name": "foo", "tag": ["key2:value2"]}
        current = [types.SimpleNamespace(key="key1", value="value1")]
        client = Mock()

        delete_tag(module, client, current)

        client.delete_arrays_tags.assert_not_called()
        module.exit_json.assert_called_once_with(changed=False)

    def test_check_mode_makes_no_api_call(self):
        module = Mock()
        module.check_mode = True
        module.params = {"name": "foo", "tag": ["key1:value1"]}
        current = [types.SimpleNamespace(key="key1", value="value1")]
        client = Mock()

        delete_tag(module, client, current)

        client.delete_arrays_tags.assert_not_called()
        module.exit_json.assert_called_once_with(changed=False)
