from dataclasses import dataclass

from cartography.models.core.common import PropertyRef
from cartography.models.core.nodes import CartographyNodeProperties
from cartography.models.core.nodes import CartographyNodeSchema
from cartography.models.core.relationships import CartographyRelProperties
from cartography.models.core.relationships import CartographyRelSchema
from cartography.models.core.relationships import LinkDirection
from cartography.models.core.relationships import make_target_node_matcher
from cartography.models.core.relationships import OtherRelationships
from cartography.models.core.relationships import TargetNodeMatcher

# The device resource in Microsoft Graph exposes many properties but, in
# practice, only a small subset is populated/useful in most tenants.  We
# deliberately model *just* the commonly-used attributes to keep the graph lean,
# mirroring the approach taken for EntraUser.


@dataclass(frozen=True)
class EntraDeviceNodeProperties(CartographyNodeProperties):
    # `id` is the directory object id (GUID); `device_id` is the separate Azure AD device id.
    id: PropertyRef = PropertyRef(
        "id", description="Entra directory object ID of the device (GUID)."
    )
    device_id: PropertyRef = PropertyRef(
        "device_id",
        extra_index=True,
        description="Azure AD device ID (distinct from the directory object `id`).",
    )
    display_name: PropertyRef = PropertyRef(
        "display_name", description="Display name of the device."
    )
    operating_system: PropertyRef = PropertyRef(
        "operating_system", description="Operating system of the device."
    )
    operating_system_version: PropertyRef = PropertyRef(
        "operating_system_version",
        description="Operating system version of the device.",
    )
    trust_type: PropertyRef = PropertyRef(
        "trust_type",
        description="Trust type of the device (e.g. `AzureAd`, `ServerAd`, `Workplace`).",
    )
    is_compliant: PropertyRef = PropertyRef(
        "is_compliant", description="Whether the device is compliant with policy."
    )
    is_managed: PropertyRef = PropertyRef(
        "is_managed", description="Whether the device is managed."
    )
    is_management_restricted: PropertyRef = PropertyRef(
        "is_management_restricted",
        description="Whether management of the device is restricted.",
    )
    management_type: PropertyRef = PropertyRef(
        "management_type",
        description="Management channel of the device (e.g. `MDM`).",
    )
    manufacturer: PropertyRef = PropertyRef(
        "manufacturer", description="Manufacturer of the device."
    )
    model: PropertyRef = PropertyRef("model", description="Model of the device.")
    profile_type: PropertyRef = PropertyRef(
        "profile_type",
        description="Profile type of the device (e.g. `RegisteredDevice`).",
    )
    device_version: PropertyRef = PropertyRef(
        "device_version", description="Device version."
    )
    enrollment_type: PropertyRef = PropertyRef(
        "enrollment_type", description="Enrollment type of the device."
    )
    enrollment_profile_name: PropertyRef = PropertyRef(
        "enrollment_profile_name",
        description="Enrollment profile name of the device.",
    )
    account_enabled: PropertyRef = PropertyRef(
        "account_enabled", description="Whether the device account is enabled."
    )
    approximate_last_sign_in_date_time: PropertyRef = PropertyRef(
        "approximate_last_sign_in_date_time",
        description="Approximate date and time of the device's last sign-in.",
    )
    lastupdated: PropertyRef = PropertyRef("lastupdated", set_in_kwargs=True)


@dataclass(frozen=True)
class EntraTenantToDeviceRelProperties(CartographyRelProperties):
    lastupdated: PropertyRef = PropertyRef("lastupdated", set_in_kwargs=True)


@dataclass(frozen=True)
# (:EntraDevice)<-[:RESOURCE]-(:AzureTenant)
class EntraDeviceToTenantRel(CartographyRelSchema):
    target_node_label: str = "AzureTenant"
    target_node_matcher: TargetNodeMatcher = make_target_node_matcher(
        {"id": PropertyRef("TENANT_ID", set_in_kwargs=True)},
    )
    direction: LinkDirection = LinkDirection.INWARD
    rel_label: str = "RESOURCE"
    properties: EntraTenantToDeviceRelProperties = EntraTenantToDeviceRelProperties()


@dataclass(frozen=True)
class EntraDeviceToOwnerRelProperties(CartographyRelProperties):
    lastupdated: PropertyRef = PropertyRef("lastupdated", set_in_kwargs=True)


@dataclass(frozen=True)
# (:EntraUser)-[:OWNS]->(:EntraDevice)
class EntraDeviceToOwnerRel(CartographyRelSchema):
    target_node_label: str = "EntraUser"
    target_node_matcher: TargetNodeMatcher = make_target_node_matcher(
        {"id": PropertyRef("registered_owner_ids", one_to_many=True)},
    )
    direction: LinkDirection = LinkDirection.INWARD
    rel_label: str = "OWNS"
    properties: EntraDeviceToOwnerRelProperties = EntraDeviceToOwnerRelProperties()


@dataclass(frozen=True)
class EntraDeviceSchema(CartographyNodeSchema):
    label: str = "EntraDevice"
    properties: EntraDeviceNodeProperties = EntraDeviceNodeProperties()
    sub_resource_relationship: EntraDeviceToTenantRel = EntraDeviceToTenantRel()
    other_relationships: OtherRelationships = OtherRelationships(
        [
            EntraDeviceToOwnerRel(),
        ]
    )
