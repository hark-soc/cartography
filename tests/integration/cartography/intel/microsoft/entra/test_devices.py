from unittest.mock import patch

import pytest

import cartography.intel.microsoft.entra.devices
import cartography.intel.microsoft.entra.users
from cartography.intel.microsoft.entra.devices import sync_entra_devices
from cartography.intel.microsoft.entra.users import load_tenant
from cartography.intel.microsoft.entra.users import sync_entra_users
from tests.data.microsoft.entra.devices import HOMER_USER_ID
from tests.data.microsoft.entra.devices import MOCK_ENTRA_DEVICES
from tests.data.microsoft.entra.devices import TEST_TENANT_ID
from tests.data.microsoft.entra.devices import TEST_USER_1_ID
from tests.data.microsoft.entra.users import MOCK_ENTRA_USERS
from tests.integration.util import check_nodes
from tests.integration.util import check_rels

TEST_UPDATE_TAG = 1234567890

DEVICE_1_ID = "eecf6cc6-7bef-4be8-a0d1-0a6f8a0a0001"
DEVICE_2_ID = "eecf6cc6-7bef-4be8-a0d1-0a6f8a0a0002"


async def _mock_get_users(client):
    """Mock async generator for get_users"""
    for user in MOCK_ENTRA_USERS:
        yield user


async def _mock_get_devices(client):
    """Mock async generator for get_devices"""
    for device in MOCK_ENTRA_DEVICES:
        yield device


@patch.object(
    cartography.intel.microsoft.entra.users,
    "get_users",
    side_effect=_mock_get_users,
)
@patch.object(
    cartography.intel.microsoft.entra.devices,
    "get_devices",
    side_effect=_mock_get_devices,
)
@pytest.mark.asyncio
async def test_sync_entra_devices(
    mock_get_devices,
    mock_get_users,
    neo4j_session,
):
    """
    Ensure that devices get loaded and linked to their tenant and owners.
    """
    # Arrange: Load tenant and users as prerequisites (owners are EntraUsers)
    load_tenant(neo4j_session, {"id": TEST_TENANT_ID}, TEST_UPDATE_TAG)
    await sync_entra_users(
        neo4j_session,
        TEST_TENANT_ID,
        "test-client-id",
        "test-client-secret",
        TEST_UPDATE_TAG,
        {"UPDATE_TAG": TEST_UPDATE_TAG, "TENANT_ID": TEST_TENANT_ID},
    )

    # Act
    await sync_entra_devices(
        neo4j_session,
        TEST_TENANT_ID,
        "test-client-id",
        "test-client-secret",
        TEST_UPDATE_TAG,
        {"UPDATE_TAG": TEST_UPDATE_TAG, "TENANT_ID": TEST_TENANT_ID},
    )

    # Assert Devices exist with their core properties
    expected_nodes = {
        (
            DEVICE_1_ID,
            "HOMER-LAPTOP",
            "Windows",
            True,
            True,
        ),
        (
            DEVICE_2_ID,
            "TESTUSER1-IPHONE",
            "iOS",
            False,
            True,
        ),
    }
    assert (
        check_nodes(
            neo4j_session,
            "EntraDevice",
            ["id", "display_name", "operating_system", "is_compliant", "is_managed"],
        )
        == expected_nodes
    )

    # Assert Devices are connected with Tenant
    expected_tenant_rels = {
        (DEVICE_1_ID, TEST_TENANT_ID),
        (DEVICE_2_ID, TEST_TENANT_ID),
    }
    assert (
        check_rels(
            neo4j_session,
            "EntraDevice",
            "id",
            "AzureTenant",
            "id",
            "RESOURCE",
            rel_direction_right=False,
        )
        == expected_tenant_rels
    )

    # Assert Devices are owned by their registered owners
    expected_owner_rels = {
        (HOMER_USER_ID, DEVICE_1_ID),
        (TEST_USER_1_ID, DEVICE_2_ID),
    }
    assert (
        check_rels(
            neo4j_session,
            "EntraUser",
            "id",
            "EntraDevice",
            "id",
            "OWNS",
            rel_direction_right=True,
        )
        == expected_owner_rels
    )
