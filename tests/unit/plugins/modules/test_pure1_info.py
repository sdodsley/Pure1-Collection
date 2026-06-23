# Copyright: (c) 2026, Everpure Ansible Team <pure-ansible-team@everpuredata.com>
# GNU General Public License v3.0+ (see COPYING.GPLv3 or https://www.gnu.org/licenses/gpl-3.0.txt)

"""Unit tests for the pure1_info module."""

from __future__ import absolute_import, division, print_function

__metaclass__ = type

import sys
import time
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

from plugins.modules.pure1_info import (
    generate_default_dict,
    generate_subscriptions_dict,
    generate_subscription_assets_dict,
    generate_subscription_licenses_dict,
    generate_contract_dict,
    generate_invoices_dict,
)


class _Item:
    """A namespace that also supports dict-style ['key'] access.

    The pure1_info module reaches into invoice lines with both attribute
    access (``line.item``) and subscript access (``line["components"]``).
    """

    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)

    def __getitem__(self, key):
        return getattr(self, key)


# 2021-01-01 00:00:00 UTC expressed in milliseconds
JAN_2021_MS = 1609459200000


class TestGenerateDefaultDict:
    """Tests for generate_default_dict."""

    def test_counts_appliances_by_os_and_totals(self):
        client = Mock()
        client.get_arrays.return_value = Mock(
            items=[
                types.SimpleNamespace(os="Purity//FA"),
                types.SimpleNamespace(os="Purity"),
                types.SimpleNamespace(os="Purity//FB"),
                types.SimpleNamespace(os="Elasticity"),
            ]
        )
        client.get_volumes.return_value = Mock(total_item_count=5)
        client.get_volume_snapshots.return_value = Mock(total_item_count=6)
        client.get_file_systems.return_value = Mock(total_item_count=7)
        client.get_file_system_snapshots.return_value = Mock(total_item_count=8)
        client.get_buckets.return_value = Mock(total_item_count=9)
        client.get_directories.return_value = Mock(total_item_count=10)
        client.get_pods.return_value = Mock(total_item_count=11)
        client.get_object_store_accounts.return_value = Mock(total_item_count=12)

        result = generate_default_dict(client)

        assert result["FlashArrays"] == 2  # Purity//FA + Purity
        assert result["FlashBlades"] == 1
        assert result["ObjectEngines"] == 1
        assert result["volumes"] == 5
        assert result["volume_snapshots"] == 6
        assert result["filesystems"] == 7
        assert result["filesystem_snapshots"] == 8
        assert result["buckets"] == 9
        assert result["directories"] == 10
        assert result["pods"] == 11
        assert result["object_store_accounts"] == 12


class TestGenerateSubscriptionsDict:
    """Tests for generate_subscriptions_dict."""

    def test_maps_subscription_fields_and_dates(self):
        client = Mock()
        client.get_subscriptions.return_value = Mock(
            items=[
                types.SimpleNamespace(
                    name="sub1",
                    start_date=JAN_2021_MS,
                    expiration_date=JAN_2021_MS,
                    service="Evergreen",
                    status="active",
                    org_name="ACME",
                    partner_name="PartnerCo",
                    subscription_term="36 months",
                )
            ]
        )

        result = generate_subscriptions_dict(client)

        assert result["sub1"]["service"] == "Evergreen"
        assert result["sub1"]["status"] == "active"
        assert result["sub1"]["org_name"] == "ACME"
        assert result["sub1"]["start_date"] == "2021-01-01 00:00:00 UTC"
        assert result["sub1"]["expiration_date"] == "2021-01-01 00:00:00 UTC"

    def test_optional_fields_default_to_none(self):
        client = Mock()
        client.get_subscriptions.return_value = Mock(
            items=[
                types.SimpleNamespace(
                    name="sub1",
                    start_date=JAN_2021_MS,
                    expiration_date=JAN_2021_MS,
                    service="Evergreen",
                    status="active",
                )
            ]
        )

        result = generate_subscriptions_dict(client)

        assert result["sub1"]["org_name"] is None
        assert result["sub1"]["partner_name"] is None
        assert result["sub1"]["subscription_term"] is None

    def test_empty_subscriptions_returns_empty_dict(self):
        client = Mock()
        client.get_subscriptions.return_value = Mock(items=[])

        assert generate_subscriptions_dict(client) == {}


class TestGenerateSubscriptionAssetsDict:
    """Tests for generate_subscription_assets_dict."""

    def test_maps_asset_fields_and_activation_date(self):
        client = Mock()
        client.get_subscription_assets.return_value = Mock(
            items=[
                types.SimpleNamespace(
                    name="asset1",
                    install_location="DC1",
                    activation_date=JAN_2021_MS,
                    version="1.2.3",
                    model="FA-X70",
                    chassis_serial_number="CH-001",
                    effective_use=10,
                    utilization=0.5,
                    total_usable=1000,
                    total_reduction=3.5,
                    subscription=types.SimpleNamespace(name="sub1", id="sid-1"),
                    license=types.SimpleNamespace(name="lic1", id="lid-1"),
                )
            ]
        )

        result = generate_subscription_assets_dict(client)

        assert result["asset1"]["install_location"] == "DC1"
        assert result["asset1"]["activation_date"] == "2021-01-01 00:00:00 UTC"
        assert result["asset1"]["model"] == "FA-X70"
        assert result["asset1"]["subscription_name"] == "sub1"
        assert result["asset1"]["subscription_id"] == "sid-1"
        assert result["asset1"]["license_name"] == "lic1"

    def test_empty_assets_returns_empty_dict(self):
        client = Mock()
        client.get_subscription_assets.return_value = Mock(items=[])

        assert generate_subscription_assets_dict(client) == {}


class TestGenerateContractDict:
    """Tests for generate_contract_dict (contract_state logic)."""

    def _client_with_contract(self, start_ms, end_ms):
        client = Mock()
        client.get_arrays.return_value = Mock(items=[types.SimpleNamespace(name="foo")])
        client.get_arrays_support_contracts.return_value = Mock(
            items=[types.SimpleNamespace(start_date=start_ms, end_date=end_ms)]
        )
        return client

    def test_active_contract(self):
        now = int(time.time() * 1000)
        client = self._client_with_contract(now - 1000, now + 86400000)

        result = generate_contract_dict(client)

        assert result["foo"]["contract_state"] == "Active"

    def test_grace_period_contract(self):
        now = int(time.time() * 1000)
        # ended 1 day ago, well within the 30-day grace window
        client = self._client_with_contract(now - 86400000 * 365, now - 86400000)

        result = generate_contract_dict(client)

        assert result["foo"]["contract_state"] == "Grace Period"

    def test_expired_contract(self):
        now = int(time.time() * 1000)
        # ended 60 days ago, past the 30-day grace window
        client = self._client_with_contract(now - 86400000 * 365, now - 86400000 * 60)

        result = generate_contract_dict(client)

        assert result["foo"]["contract_state"] == "Expired"

    def test_no_contract_data_is_expired(self):
        client = Mock()
        client.get_arrays.return_value = Mock(items=[types.SimpleNamespace(name="foo")])
        client.get_arrays_support_contracts.return_value = Mock(items=[])

        result = generate_contract_dict(client)

        assert result["foo"] == {"contract_state": "Expired"}


def _metric(data, unit, metric_name):
    return types.SimpleNamespace(
        data=data, unit=unit, metric=types.SimpleNamespace(name=metric_name)
    )


class TestGenerateSubscriptionLicensesDict:
    """Tests for generate_subscription_licenses_dict."""

    def _license(self):
        resource = types.SimpleNamespace(
            name="res1",
            activation_time=JAN_2021_MS,
            resource_type="array",
            fqdn="array1.example.com",
            usage=_metric(10, "TiB", "used"),
        )
        return types.SimpleNamespace(
            name="lic1",
            start_date=JAN_2021_MS,
            expiration_date=JAN_2021_MS,
            last_updated_date=JAN_2021_MS,
            marketplace_partner=types.SimpleNamespace(name="AWS"),
            service_tier="premium",
            location="us-west",
            pre_ratio=2.0,
            energy_usage=100,
            subscription=types.SimpleNamespace(name="sub1"),
            average_on_demand=_metric(1, "TiB", "avg"),
            reservation=_metric(2, "TiB", "res"),
            usage=_metric(3, "TiB", "use"),
            quarter_on_demand=_metric(4, "TiB", "qod"),
            resources=[resource],
        )

    def test_maps_license_fields(self):
        client = Mock()
        client.get_subscription_licenses.return_value = Mock(items=[self._license()])

        result = generate_subscription_licenses_dict(client)

        assert result["lic1"]["service_tier"] == "premium"
        assert result["lic1"]["marketplace_partner"] == "AWS"
        assert result["lic1"]["subscription"] == "sub1"
        assert result["lic1"]["usage"]["metric"] == "use"
        assert result["lic1"]["start_date"] == "2021-01-01 00:00:00 UTC"

    def test_resources_are_nested_under_the_license(self):
        client = Mock()
        client.get_subscription_licenses.return_value = Mock(items=[self._license()])

        result = generate_subscription_licenses_dict(client)

        resources = result["lic1"]["resources"]
        assert "res1" in resources
        assert resources["res1"]["resource_type"] == "array"
        assert resources["res1"]["fqdn"] == "array1.example.com"
        assert resources["res1"]["activation_time"] == "2021-01-01 00:00:00 UTC"
        assert resources["res1"]["usage"]["data"] == 10

    def test_empty_licenses_returns_empty_dict(self):
        client = Mock()
        client.get_subscription_licenses.return_value = Mock(items=[])

        assert generate_subscription_licenses_dict(client) == {}


class TestGenerateInvoicesDict:
    """Tests for generate_invoices_dict."""

    def _invoice(self):
        line = _Item(
            start_date=JAN_2021_MS,
            end_date=JAN_2021_MS,
            item="FA-X70",
            quantity=2,
            description="Flash storage",
            components={"a": 1},
            unit_price=1000,
            amount=2000,
            tax=types.SimpleNamespace(
                percentage=10, amount=200, exemption_statement=None
            ),
        )
        return types.SimpleNamespace(
            id="INV-001",
            date=JAN_2021_MS,
            due_date=JAN_2021_MS,
            ship_date=JAN_2021_MS,
            status="paid",
            amount=2000,
            payment_terms="NET30",
            sales_representative="Jane Rep",
            partner_purchase_order="PO-1",
            end_user_purchase_order="PO-2",
            end_user_purchase_name="ACME",
            subscription=types.SimpleNamespace(id="sid-1", name="sub1"),
            lines=[line],
        )

    def test_maps_invoice_header_fields(self):
        module = Mock()
        client = Mock()
        client.get_invoices.return_value = Mock(
            status_code=200, items=[self._invoice()]
        )

        result = generate_invoices_dict(module, client)

        assert "INV-001" in result
        invoice = result["INV-001"]
        assert invoice["status"] == "paid"
        assert invoice["amount"] == 2000
        assert invoice["sales_rep"] == "Jane Rep"
        assert invoice["subscription_id"] == "sid-1"
        assert invoice["subscription_name"] == "sub1"

    def test_invoice_lines_are_appended(self):
        module = Mock()
        client = Mock()
        client.get_invoices.return_value = Mock(
            status_code=200, items=[self._invoice()]
        )

        result = generate_invoices_dict(module, client)

        lines = result["INV-001"]["lines"]
        assert isinstance(lines, list)
        assert len(lines) == 1
        assert lines[0]["item"] == "FA-X70"
        assert lines[0]["quantity"] == 2
        assert lines[0]["components"] == {"a": 1}
        assert lines[0]["tax_percentage"] == 10
        assert lines[0]["start_date"] is not None

    def test_non_200_response_returns_empty_dict(self):
        module = Mock()
        client = Mock()
        client.get_invoices.return_value = Mock(status_code=500)

        assert generate_invoices_dict(module, client) == {}
