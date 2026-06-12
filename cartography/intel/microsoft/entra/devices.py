import logging
from typing import Any
from typing import AsyncGenerator
from typing import Generator

import neo4j
from azure.identity import ClientSecretCredential
from msgraph import GraphServiceClient
from msgraph.generated.models.device import Device

from cartography.client.core.tx import load
from cartography.graph.job import GraphJob
from cartography.intel.microsoft.entra.utils import call_with_retries
from cartography.models.microsoft.entra.device import EntraDeviceSchema
from cartography.util import timeit

logger = logging.getLogger(__name__)

# NOTE:
# As with users (see cartography/intel/microsoft/entra/users.py), Microsoft Graph
# imposes limits on the length of the $select clause and the number of properties
# that can be selected in a single request.  We therefore only request a *core*
# subset of device attributes that are most useful in downstream analysis.  The
# transform() function tolerates missing attributes (the generated MS Graph SDK
# returns `None` for properties not present in the payload), so fetching fewer
# fields is safe.
#
# Keep the total character count of the comma-separated list comfortably below
# 500 and stay within the official v1.0 contract (beta-only fields cause 400
# Bad Request responses). 20-25 fields is a good rule-of-thumb.
#
# References:
#   • https://learn.microsoft.com/graph/query-parameters#select-parameter
#   • https://learn.microsoft.com/graph/api/device-list?view=graph-rest-1.0
#
DEVICE_SELECT_FIELDS = [
    "id",
    "deviceId",
    "displayName",
    "operatingSystem",
    "operatingSystemVersion",
    "trustType",
    "isCompliant",
    "isManaged",
    "isManagementRestricted",
    "managementType",
    "manufacturer",
    "model",
    "profileType",
    "deviceVersion",
    "enrollmentType",
    "enrollmentProfileName",
    "accountEnabled",
    "approximateLastSignInDateTime",
]


@timeit
async def get_devices(client: GraphServiceClient) -> AsyncGenerator[Device, None]:
    """Fetch all devices with their registered owners in as few requests as possible.

    We leverage `$expand=registeredOwners($select=id)` so the owners' *ids* are
    hydrated alongside every device record.  This avoids making a second
    round-trip per device, mirroring the `$expand=manager` approach used for
    users.
    """

    request_configuration = client.devices.DevicesRequestBuilderGetRequestConfiguration(
        query_parameters=client.devices.DevicesRequestBuilderGetQueryParameters(
            top=999,
            select=DEVICE_SELECT_FIELDS,
            expand=["registeredOwners($select=id)"],
        ),
    )

    try:
        page = await call_with_retries(
            lambda: client.devices.get(request_configuration=request_configuration),
        )
    except Exception:
        logger.exception("Failed to fetch Entra devices")
        raise

    while page:
        if page.value:
            for device in page.value:
                yield device
        if not page.odata_next_link:
            break

        try:
            page = await call_with_retries(
                lambda: client.devices.with_url(page.odata_next_link).get(),
            )
        except Exception as e:
            logger.error(
                "Failed to fetch next page of Entra devices – stopping pagination early: %s",
                e,
            )
            break


@timeit
def transform_devices(devices: list[Device]) -> Generator[dict[str, Any], None, None]:
    """Convert MS Graph SDK `Device` models into dicts matching our schema."""

    for device in devices:
        # The registered owners are hydrated by the `$expand` above.  Only users
        # can own a device, so we keep `#microsoft.graph.user` objects.
        registered_owner_ids: list[str] = []
        for owner in getattr(device, "registered_owners", None) or []:
            if getattr(owner, "odata_type", "") == "#microsoft.graph.user":
                registered_owner_ids.append(owner.id)

        yield {
            "id": device.id,
            "device_id": device.device_id,
            "display_name": device.display_name,
            "operating_system": device.operating_system,
            "operating_system_version": device.operating_system_version,
            "trust_type": device.trust_type,
            "is_compliant": device.is_compliant,
            "is_managed": device.is_managed,
            "is_management_restricted": device.is_management_restricted,
            "management_type": device.management_type,
            "manufacturer": device.manufacturer,
            "model": device.model,
            "profile_type": device.profile_type,
            "device_version": device.device_version,
            "enrollment_type": device.enrollment_type,
            "enrollment_profile_name": device.enrollment_profile_name,
            "account_enabled": device.account_enabled,
            "approximate_last_sign_in_date_time": device.approximate_last_sign_in_date_time,
            "registered_owner_ids": registered_owner_ids,
        }


@timeit
def load_devices(
    neo4j_session: neo4j.Session,
    devices: list[dict[str, Any]],
    tenant_id: str,
    update_tag: int,
) -> None:
    logger.info(f"Loading {len(devices)} Entra devices")
    load(
        neo4j_session,
        EntraDeviceSchema(),
        devices,
        lastupdated=update_tag,
        TENANT_ID=tenant_id,
    )


def cleanup(
    neo4j_session: neo4j.Session, common_job_parameters: dict[str, Any]
) -> None:
    GraphJob.from_node_schema(EntraDeviceSchema(), common_job_parameters).run(
        neo4j_session
    )


@timeit
async def sync_entra_devices(
    neo4j_session: neo4j.Session,
    tenant_id: str,
    client_id: str,
    client_secret: str,
    update_tag: int,
    common_job_parameters: dict[str, Any],
) -> None:
    """
    Sync Entra devices.

    Must run after `sync_entra_users` so that the (:EntraUser)-[:OWNS]->(:EntraDevice)
    relationships can match already-loaded EntraUser nodes.

    :param neo4j_session: Neo4J session for database interface
    :param tenant_id: Entra tenant ID
    :param client_id: Entra application client ID
    :param client_secret: Entra application client secret
    :param update_tag: Timestamp used to determine data freshness
    :param common_job_parameters: dict of other job parameters to carry to sub-jobs
    :return: None
    """
    # Initialize Graph client
    credential = ClientSecretCredential(
        tenant_id=tenant_id,
        client_id=client_id,
        client_secret=client_secret,
    )
    client = GraphServiceClient(
        credential, scopes=["https://graph.microsoft.com/.default"]
    )

    # Process devices in batches to reduce memory consumption
    batch_size = 500
    devices_batch = []

    async for device in get_devices(client):
        devices_batch.append(device)

        if len(devices_batch) >= batch_size:
            transformed_devices = list(transform_devices(devices_batch))
            load_devices(neo4j_session, transformed_devices, tenant_id, update_tag)
            devices_batch.clear()

    # Process any remaining devices
    if devices_batch:
        transformed_devices = list(transform_devices(devices_batch))
        load_devices(neo4j_session, transformed_devices, tenant_id, update_tag)

    cleanup(neo4j_session, common_job_parameters)
