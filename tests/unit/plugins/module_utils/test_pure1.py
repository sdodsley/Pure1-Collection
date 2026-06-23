# Copyright: (c) 2026, Everpure Ansible Team <pure-ansible-team@everpuredata.com>
# GNU General Public License v3.0+ (see COPYING.GPLv3 or https://www.gnu.org/licenses/gpl-3.0.txt)

"""Unit tests for pure1 module utilities."""

from __future__ import absolute_import, division, print_function

__metaclass__ = type

import sys
from unittest.mock import Mock, patch, MagicMock

# Mock external dependencies before importing pure1
sys.modules["pypureclient"] = MagicMock()
sys.modules["pypureclient.pure1"] = MagicMock()

from plugins.module_utils.pure1 import get_pure1, pure1_argument_spec


class TestPure1ArgumentSpec:
    """Tests for pure1_argument_spec function."""

    def test_returns_dict(self):
        """Test that the function returns a dictionary."""
        assert isinstance(pure1_argument_spec(), dict)

    def test_all_expected_keys(self):
        """Test that spec contains exactly the expected keys."""
        result = pure1_argument_spec()
        assert set(result.keys()) == {"app_id", "key_file", "password"}

    def test_app_id_required_and_no_log(self):
        """app_id must be required and marked no_log."""
        result = pure1_argument_spec()
        assert result["app_id"]["required"] is True
        assert result["app_id"]["no_log"] is True

    def test_key_file_required_and_not_no_log(self):
        """key_file is required but is a path, not a secret."""
        result = pure1_argument_spec()
        assert result["key_file"]["required"] is True
        assert result["key_file"]["no_log"] is False

    def test_password_is_secret(self):
        """password must be marked no_log."""
        result = pure1_argument_spec()
        assert result["password"]["no_log"] is True


class TestGetPure1:
    """Tests for get_pure1 function."""

    @patch("plugins.module_utils.pure1.pure1.Client")
    @patch("plugins.module_utils.pure1.HAS_PYPURECLIENT", True)
    def test_with_module_params(self, mock_client_class):
        """Test get_pure1 with app_id/key_file module parameters."""
        mock_module = Mock()
        mock_module.params = {
            "app_id": "pure1-app-id",
            "key_file": "/run/secrets/pure1.pem",
            "password": None,
        }
        mock_client = Mock()
        mock_client.get_arrays.return_value = Mock(status_code=200)
        mock_client_class.return_value = mock_client

        result = get_pure1(mock_module)

        call_kwargs = mock_client_class.call_args[1]
        assert call_kwargs["app_id"] == "pure1-app-id"
        assert call_kwargs["private_key_file"] == "/run/secrets/pure1.pem"
        assert "private_key_password" not in call_kwargs
        mock_client.get_arrays.assert_called_once()
        assert result == mock_client

    @patch("plugins.module_utils.pure1.pure1.Client")
    @patch("plugins.module_utils.pure1.HAS_PYPURECLIENT", True)
    def test_with_password(self, mock_client_class):
        """A supplied password is forwarded as private_key_password."""
        mock_module = Mock()
        mock_module.params = {
            "app_id": "pure1-app-id",
            "key_file": "/run/secrets/pure1.pem",
            "password": "s3cret",
        }
        mock_client = Mock()
        mock_client.get_arrays.return_value = Mock(status_code=200)
        mock_client_class.return_value = mock_client

        result = get_pure1(mock_module)

        call_kwargs = mock_client_class.call_args[1]
        assert call_kwargs["private_key_password"] == "s3cret"
        assert result == mock_client

    @patch("plugins.module_utils.pure1.pure1.Client")
    @patch("plugins.module_utils.pure1.HAS_PYPURECLIENT", True)
    @patch("plugins.module_utils.pure1.environ")
    def test_with_environment_vars(self, mock_environ, mock_client_class):
        """Test get_pure1 falls back to environment variables."""
        mock_module = Mock()
        mock_module.params = {
            "app_id": None,
            "key_file": None,
            "password": "envpass",
        }
        env_vars = {
            "PURE1_APP_ID": "env-app-id",
            "PURE1_PRIVATE_KEY_FILE": "/env/pure1.pem",
            "PURE1_PRIVATE_PASSWORD": "envpass",
        }
        mock_environ.get.side_effect = env_vars.get
        mock_client = Mock()
        mock_client.get_arrays.return_value = Mock(status_code=200)
        mock_client_class.return_value = mock_client

        result = get_pure1(mock_module)

        call_kwargs = mock_client_class.call_args[1]
        assert call_kwargs["app_id"] == "env-app-id"
        assert call_kwargs["private_key_file"] == "/env/pure1.pem"
        assert call_kwargs["private_key_password"] == "envpass"
        assert result == mock_client

    @patch("plugins.module_utils.pure1.HAS_PYPURECLIENT", True)
    @patch("plugins.module_utils.pure1.environ")
    def test_missing_credentials(self, mock_environ):
        """Test that missing credentials causes a clean failure."""
        mock_module = Mock()
        mock_module.params = {"app_id": None, "key_file": None, "password": None}
        mock_module.fail_json.side_effect = SystemExit("fail_json called")
        mock_environ.get.return_value = None

        try:
            get_pure1(mock_module)
        except SystemExit:
            pass

        mock_module.fail_json.assert_called_once()
        msg = mock_module.fail_json.call_args[1]["msg"]
        assert "PURE1_APP_ID" in msg
        assert "PURE1_PRIVATE_KEY_FILE" in msg

    @patch("plugins.module_utils.pure1.HAS_PYPURECLIENT", False)
    def test_missing_pypureclient(self):
        """Test that a missing py-pure-client causes failure."""
        mock_module = Mock()
        mock_module.params = {
            "app_id": "pure1-app-id",
            "key_file": "/run/secrets/pure1.pem",
            "password": None,
        }
        mock_module.fail_json.side_effect = SystemExit("fail_json called")

        try:
            get_pure1(mock_module)
        except SystemExit:
            pass

        mock_module.fail_json.assert_called_once()
        assert "py-pure-client" in mock_module.fail_json.call_args[1]["msg"]

    @patch("plugins.module_utils.pure1.pure1.Client")
    @patch("plugins.module_utils.pure1.HAS_PYPURECLIENT", True)
    def test_authentication_failure_status(self, mock_client_class):
        """A non-200 from get_arrays must surface as an auth failure."""
        mock_module = Mock()
        mock_module.params = {
            "app_id": "pure1-app-id",
            "key_file": "/run/secrets/pure1.pem",
            "password": None,
        }
        mock_module.fail_json.side_effect = SystemExit("fail_json called")
        mock_client = Mock()
        mock_client.get_arrays.return_value = Mock(status_code=401)
        mock_client_class.return_value = mock_client

        try:
            get_pure1(mock_module)
        except SystemExit:
            pass

        mock_module.fail_json.assert_called_once()
        assert (
            "authentication failed" in mock_module.fail_json.call_args[1]["msg"].lower()
        )
