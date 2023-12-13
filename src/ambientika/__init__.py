import requests

from typing import (Any, TypedDict)
from enum import IntEnum

class AmbientikaApi:
    host: str
    id: int
    token: str

    def __init__(self, username: str, password: str, host: str) -> None:
        self.host = host

        login_data = {
            'username': username,
            'password': password
        }
        response = requests.post(url = "{host}/users/authenticate".format(host = host), json = login_data)

        response_data = response.json()
        self.id = response_data['id']
        self.token = response_data['jwtToken']

    def get(self, path: str, params: dict[str, Any] = {}) -> Any:
        headers = {
            'Authorization': "Bearer {token}".format(token = self.token)
        }
        response = requests.get(url = f"{self.host}/{path}", headers = headers, params = params)
        return response.json()
    
    def post(self, path: str, body: dict[str, Any]) -> None:
        headers = {
            'Authorization': "Bearer {token}".format(token = self.token)
        }
        requests.post(url = f"{self.host}/{path}", headers = headers, json = body)
    
class OperatingMode(IntEnum):
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
    Low = 0
    Medium = 1
    High = 2

class HumidityLevel(IntEnum):
    Dry = 0
    Normal = 1
    Moist = 2
    
DeviceStatus = TypedDict('DeviceStatus', {
    'operating_mode': OperatingMode,
    'fan_speed': FanSpeed,
    'humidity_level': HumidityLevel,
    'temperature': int,
    'humidity': int,
    'air_quality': str,
    'humidity_alarm': bool,
    'filters_status': str,
    'night_alarm': bool,
    'device_role': str,
    'last_operating_mode': OperatingMode,
    'packet_type': str,
    'device_type': str,
    'device_serial_number': str
})

DeviceMode = TypedDict('DeviceMode', {
    'operating_mode': OperatingMode,
    'fan_speed': FanSpeed,
    'humidity_level': HumidityLevel
})

class Device:
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
        self.api = api

        self.id = data['id']
        self.device_type = data['deviceType']
        self.serial_number = data['serialNumber']
        self.user_id = data['userId']
        self.name = data['name']
        self.role = data['role']
        self.zone_index = data['zoneIndex']
        self.installation = data['installation']
        self.room_id = data['roomId']

    def status(self) -> DeviceStatus:
        data = self.api.get("device/device-status", {'deviceSerialNumber': self.serial_number})
        return {
            'operating_mode': OperatingMode[data['operatingMode']],
            'fan_speed': FanSpeed[data['fanSpeed']],
            'humidity_level': HumidityLevel[data['humidityLevel']],
            'temperature': data['temperature'],
            'humidity': data['humidity'],
            'air_quality': data['airQuality'],
            'humidity_alarm': data['humidityAlarm'],
            'filters_status': data['filtersStatus'],
            'night_alarm': data['nightAlarm'],
            'device_role': data['deviceRole'],
            'last_operating_mode': OperatingMode[data['lastOperatingMode']],
            'packet_type': data['packetType'],
            'device_type': data['deviceType'],
            'device_serial_number': data['deviceSerialNumber']
        }
    
    def change_mode(self, mode: DeviceMode):
        data = {
            'deviceSerialNumber': self.serial_number,
            'operatingMode': str(mode['operating_mode'].value),
            'fanSpeed': mode['fan_speed'].value,
            'humidityLevel': mode['humidity_level'].value
        }
        self.api.post("device/change-mode", data)
        

class Room:
    id: int
    name: str
    house_id: int
    user_id: int
    devices: list[Any]

    api: AmbientikaApi

    def __init__(self, data: dict[str, Any], api: AmbientikaApi):
        self.api = api

        self.id = data['id']
        self.name = data['name']
        self.house_id = data['houseId']
        self.user_id = data['userId']
        self.devices = list(map(lambda device: Device(device, api), data['devices']))

class House:
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
        self.user_id = data['userId']
        self.id = data['id']
        self.name = data['name']
        self.zones = data['zones']
        self.rooms = list(map(lambda room: Room(room, api), data['rooms']))
        self.has_zones = data['hasZones']
        self.has_devices = data['hasDevices']
        self.address = data['address']
        self.latitude = data['latitude']
        self.longitude = data['longitude']

class Ambientika:
    api: AmbientikaApi

    def __init__(self, username: str, password: str, host: str = "https://app.ambientika.eu:4521"):
        self.api = AmbientikaApi(username, password, host)

    def house_complete_info(self, house_id: int) -> House:
        house_data = self.api.get("house/house-complete-info", {'houseId': house_id})
        return House(house_data, self.api)

    def houses(self) -> list[House]:
        houses = self.api.get("house/houses-info")

        def fetch_house(house: dict[str, Any]):
            id = house['houseId']
            return self.house_complete_info(id)
        
        return list(map(fetch_house, houses))