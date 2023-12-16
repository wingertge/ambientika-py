"""API wrapper for the Ambientika air conditioning smart devices."""
from enum import IntEnum
from typing import Any, Optional, TypedDict

import aiohttp
from returns.result import Failure, Result, Success


class HttpError(TypedDict):
    """An HTTP Error returned from the API."""

    status_code: int
    data: Optional[Any]


class AmbientikaApi:
    """An authenticated API connection."""

    host: str
    id: int
    token: str

    def __init__(self, host: str, id: int, token: str) -> None:
        """Initialize the connection with an auth token."""
        self.host = host
        self.id = id
        self.token = token

    async def get(
        self, path: str, params: dict[str, Any] = {}
    ) -> Result[Any, HttpError]:
        """Fetch JSON data from an authenticated API endpoint."""
        headers = {"Authorization": f"Bearer {self.token}"}
        async with aiohttp.ClientSession() as session, session.get(
            url=f"{self.host}/{path}", headers=headers, params=params
        ) as response:
            if response.status == 200:
                return Success(await response.json())
            else:
                if (
                    response.headers.get("Content-Type", "").lower()
                    == "application/json"
                ):
                    data = await response.json()
                else:
                    data = None
                return Failure({"status_code": response.status, "data": data})

    async def post(self, path: str, body: dict[str, Any]) -> Result[None, HttpError]:
        """Post JSON data to an authenticated API endpoint."""
        headers = {"Authorization": f"Bearer {self.token}"}
        async with aiohttp.ClientSession() as session, session.post(
            url=f"{self.host}/{path}", headers=headers, json=body
        ) as response:
            if response.status == 200:
                return Success(None)
            else:
                if (
                    response.headers.get("Content-Type", "").lower()
                    == "application/json"
                ):
                    data = await response.json()
                else:
                    data = None
                return Failure({"status_code": response.status, "data": data})


class OperatingMode(IntEnum):
    """The operating mode of the device."""

    Smart = 0
    Auto = 1
    ManualHeatRecovery = 2
    Night = 3
    AwayHome = 4
    Surveillance = 5
    TimedExpulsion = 6
    Expulsion = 7
    Intake = 8
    MasterSlaveFlow = 9
    SlaveMasterFlow = 10
    Off = 11


class FanSpeed(IntEnum):
    """The fan speed of the device."""

    Low = 0
    Medium = 1
    High = 2


class HumidityLevel(IntEnum):
    """The humidity level targeted by the device."""

    Dry = 0
    Normal = 1
    Moist = 2


class DeviceStatus(TypedDict):
    """A status packet published by the device."""

    operating_mode: OperatingMode
    fan_speed: FanSpeed
    humidity_level: HumidityLevel
    temperature: int
    humidity: int
    air_quality: str
    humidity_alarm: bool
    filters_status: str
    night_alarm: bool
    device_role: str
    last_operating_mode: OperatingMode
    packet_type: str
    device_type: str
    device_serial_number: str

class DeviceMode(TypedDict):
    """A user settings change set for updating the device."""

    operating_mode: OperatingMode
    fan_speed: FanSpeed
    humidity_level: HumidityLevel


class Device:
    """An Ambientika device."""

    id: int
    device_type: str
    serial_number: str
    user_id: int
    name: str
    role: str
    zone_index: int
    installation: str
    room_id: int

    api: AmbientikaApi

    def __init__(self, data: dict[str, Any], api: AmbientikaApi) -> None:
        """Initialize a new device from API data."""
        self.api = api

        self.id = data["id"]
        self.device_type = data["deviceType"]
        self.serial_number = data["serialNumber"]
        self.user_id = data["userId"]
        self.name = data["name"]
        self.role = data["role"]
        self.zone_index = data["zoneIndex"]
        self.installation = data["installation"]
        self.room_id = data["roomId"]

    async def status(self) -> Result[DeviceStatus, HttpError]:
        """Retrieve the current status of the device."""
        res = await self.api.get(
            "device/device-status", {"deviceSerialNumber": self.serial_number}
        )
        match res:
            case Success(data):
                return Success(
                    {
                        "operating_mode": OperatingMode[data["operatingMode"]],
                        "fan_speed": FanSpeed[data["fanSpeed"]],
                        "humidity_level": HumidityLevel[data["humidityLevel"]],
                        "temperature": data["temperature"],
                        "humidity": data["humidity"],
                        "air_quality": data["airQuality"],
                        "humidity_alarm": data["humidityAlarm"],
                        "filters_status": data["filtersStatus"],
                        "night_alarm": data["nightAlarm"],
                        "device_role": data["deviceRole"],
                        "last_operating_mode": OperatingMode[data["lastOperatingMode"]],
                        "packet_type": data["packetType"],
                        "device_type": data["deviceType"],
                        "device_serial_number": data["deviceSerialNumber"],
                    }
                )
            case Failure(error):
                return Failure(error)
            case _:
                raise NotImplementedError

    async def change_mode(self, mode: DeviceMode) -> Result[None, HttpError]:
        """Change the operating mode, fan speed or targeted temperature of the device."""
        data = {
            "deviceSerialNumber": self.serial_number,
            "operatingMode": str(mode["operating_mode"].value),
            "fanSpeed": mode["fan_speed"].value,
            "humidityLevel": mode["humidity_level"].value,
        }
        return await self.api.post("device/change-mode", data)


class Room:
    """A room containing Ambientika devices."""

    id: int
    name: str
    house_id: int
    user_id: int
    devices: list[Any]

    api: AmbientikaApi

    def __init__(self, data: dict[str, Any], api: AmbientikaApi):
        """Initialize a new room from API data."""
        self.api = api

        self.id = data["id"]
        self.name = data["name"]
        self.house_id = data["houseId"]
        self.user_id = data["userId"]
        self.devices = [Device(device, api) for device in data["devices"]]


class House:
    """A house containing rooms and zones."""

    user_id: int
    id: int
    name: str
    zones: list[Any]
    rooms: list[Room]
    has_zones: bool
    has_devices: bool
    address: str
    latitude: float
    longitude: float

    api: AmbientikaApi

    def __init__(self, data: dict[str, Any], api: AmbientikaApi) -> None:
        """Initialize a new house from API data."""
        self.user_id = data["userId"]
        self.id = data["id"]
        self.name = data["name"]
        self.zones = data["zones"]
        self.rooms = [Room(room, api) for room in data["rooms"]]
        self.has_zones = data["hasZones"]
        self.has_devices = data["hasDevices"]
        self.address = data["address"]
        self.latitude = data["latitude"]
        self.longitude = data["longitude"]


class Ambientika:
    """An authenticated instance of the Ambientika API."""

    _api: AmbientikaApi

    def __init__(self, host: str, id: int, token: str):
        """Initialize the API with an auth token."""
        self._api = AmbientikaApi(host, id, token)

    async def house_complete_info(self, house_id: int) -> Result[House, HttpError]:
        """Retrieve the complete information for a house."""
        res = await self._api.get("house/house-complete-info", {"houseId": house_id})
        match res:
            case Success(house_data):
                return Success(House(house_data, self._api))
            case Failure(error):
                return Failure(error)
            case _:
                raise NotImplementedError

    async def houses(self) -> Result[list[House], HttpError]:
        """Retrieve the complete information about all houses on the Ambientika account."""
        res = await self._api.get("house/houses-info")

        async def fetch_house(house: dict[str, Any]) -> Optional[House]:
            id = house["houseId"]
            res = await self.house_complete_info(id)
            return res.value_or(None)

        match res:
            case Success(houses):
                return Success([x for x in [await fetch_house(house) for house in houses] if x is not None])
            case Failure(error):
                return Failure(error)
            case _:
                raise NotImplementedError


async def authenticate(
    username: str, password: str, host: str = "https://app.ambientika.eu:4521"
) -> Result[Ambientika, HttpError]:
    """Request an authorization token and create an authenticated API instance."""
    login_data = {"username": username, "password": password}
    async with aiohttp.ClientSession() as session, session.post(
        url=f"{host}/users/authenticate", json=login_data
    ) as response:
        if response.status == 200:
            response_data = await response.json()
            return Success(
                Ambientika(host, response_data["id"], response_data["jwtToken"])
            )
        else:
            if (
                response.headers.get("Content-Type", "").lower()
                == "application/json"
            ):
                data = await response.json()
            else:
                data = None
            return Failure({"status_code": response.status, "data": data})
