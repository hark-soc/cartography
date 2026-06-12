import datetime

from msgraph.generated.models.device import Device
from msgraph.generated.models.directory_object import DirectoryObject

# Reuse the same fake tenant guid as the users test data.
TEST_TENANT_ID = "02b2b7cc-fb03-4324-bf6b-eb207b39c479"

# These owner ids match MOCK_ENTRA_USERS in tests/data/microsoft/entra/users.py so
# that the (:EntraUser)-[:OWNS]->(:EntraDevice) relationships can be asserted in
# tests.
HOMER_USER_ID = "ae4ac864-4433-4ba6-96a6-20f8cffdadcb"
TEST_USER_1_ID = "11dca63b-cb03-4e53-bb75-fa8060285550"

MOCK_ENTRA_DEVICES = [
    Device(
        id="eecf6cc6-7bef-4be8-a0d1-0a6f8a0a0001",
        odata_type="#microsoft.graph.device",
        device_id="d1d1d1d1-0000-0000-0000-000000000001",
        display_name="HOMER-LAPTOP",
        operating_system="Windows",
        operating_system_version="10.0.19045",
        trust_type="AzureAd",
        is_compliant=True,
        is_managed=True,
        is_management_restricted=False,
        management_type="MDM",
        manufacturer="Dell Inc.",
        model="Latitude 7420",
        profile_type="RegisteredDevice",
        device_version=2,
        enrollment_type="AzureDomainJoined",
        enrollment_profile_name=None,
        account_enabled=True,
        approximate_last_sign_in_date_time=datetime.datetime(
            2025, 4, 16, 3, 44, 33, tzinfo=datetime.timezone.utc
        ),
        registered_owners=[
            DirectoryObject(
                id=HOMER_USER_ID,
                odata_type="#microsoft.graph.user",
            ),
        ],
    ),
    Device(
        id="eecf6cc6-7bef-4be8-a0d1-0a6f8a0a0002",
        odata_type="#microsoft.graph.device",
        device_id="d1d1d1d1-0000-0000-0000-000000000002",
        display_name="TESTUSER1-IPHONE",
        operating_system="iOS",
        operating_system_version="17.4.1",
        trust_type="Workplace",
        is_compliant=False,
        is_managed=True,
        is_management_restricted=False,
        management_type="MDM",
        manufacturer="Apple",
        model="iPhone15,2",
        profile_type="RegisteredDevice",
        device_version=2,
        enrollment_type="UserEnrollment",
        enrollment_profile_name=None,
        account_enabled=True,
        approximate_last_sign_in_date_time=datetime.datetime(
            2025, 4, 16, 3, 44, 33, tzinfo=datetime.timezone.utc
        ),
        registered_owners=[
            DirectoryObject(
                id=TEST_USER_1_ID,
                odata_type="#microsoft.graph.user",
            ),
        ],
    ),
]
