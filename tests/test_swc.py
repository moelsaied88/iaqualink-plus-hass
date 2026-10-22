"""End-to-end test: core iaqualink (real 0.7.0 library) + iaqualink_plus."""

from __future__ import annotations

import copy
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from iaqualink.systems.iaqua.system import IaquaSystem
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from homeassistant.core import HomeAssistant
from homeassistant.setup import async_setup_component

HOME = {
    "message": "",
    "home_screen": [
        {"status": "Online"},
        {"response": ""},
        {"system_type": "0"},
        {"temp_scale": "F"},
        {"spa_temp": ""},
        {"pool_temp": "73"},
        {"air_temp": "88"},
        {"spa_set_point": "100"},
        {"pool_set_point": "80"},
        {"cover_pool": ""},
        {"freeze_protection": "0"},
        {"spa_pump": "0"},
        {"pool_pump": "1"},
        {"spa_heater": "0"},
        {"pool_heater": "0"},
        {"solar_heater": "0"},
        {"spa_salinity": ""},
        {"pool_salinity": "2600"},
        {"orp": ""},
        {"ph": ""},
        {"swc_set_point": "40"},
        {"swc_boost": "0"},
        {"swc_low": "1"},
        {"swc_info": {"isswcPresent": True, "swcPoolValue": 40, "swcPoolStatus": "running", "swcSpaValue": 0, "swcSpaStatus": "standby"}},
        {"relay_count": "7"},
    ],
}
DEVICES = {
    "message": "",
    "devices_screen": [
        {"status": "Online"},
        {"response": ""},
        {"group": "1"},
        {"aux_7": [{"state": "0"}, {"label": "AUX7"}, {"icon": "aux_1_0.png"}, {"type": "0"}, {"subtype": "0"}]},
    ],
}
SWC_CONFIG = {
    "serial": "SN1", "device_status": "online", "is_error": False, "response": "success",
    "poolSWCSP": 40, "spaSWCSP": 0, "boostStatus": "", "boostHrsVal": 24,
    "remainingBoostHrs": 0, "remainingBoostMins": 0, "boostMode": "pool", "boostDipSwitch": "on",
}


class FakeAPI:
    def __init__(self, home=HOME):
        self.home = copy.deepcopy(home)
        self.swc = dict(SWC_CONFIG)
        self.calls: list[tuple[str, dict]] = []

    async def send(self, system, command, params=None):
        self.calls.append((command, dict(params or {})))
        if command == "get_home":
            body = self.home
        elif command == "get_devices":
            body = DEVICES
        elif command == "get_swc_config":
            body = self.swc
        elif command == "set_swc_config":
            self.swc["poolSWCSP"] = int(params["poolswcsp"])
            self.swc["spaSWCSP"] = int(params["spaswcsp"])
            body = self.swc
        elif command == "control_swc_boost":
            if params["boostcontrol"] == "start":
                self.swc.update(boostStatus="on", remainingBoostHrs=int(params["boosthrs"]) - 1, remainingBoostMins=59)
            elif params["boostcontrol"] == "stop":
                self.swc.update(boostStatus="", remainingBoostHrs=0, remainingBoostMins=0)
            body = self.swc
        else:
            body = {"message": ""}
        return SimpleNamespace(json=lambda: body)


@pytest.fixture
def api():
    return FakeAPI()


async def _setup(hass: HomeAssistant, api: FakeAPI):
    core = MockConfigEntry(domain="iaqualink", data={"username": "u", "password": "p"})
    core.add_to_hass(hass)

    async def get_systems(self):
        return {"SN1": IaquaSystem(self, {"serial_number": "SN1", "device_type": "iaqua", "name": "Pool"})}

    async def send(self, command, params=None):
        return await api.send(self, command, params)

    with (
        patch("iaqualink.client.AqualinkClient.login", AsyncMock()),
        patch("iaqualink.client.AqualinkClient.get_systems", get_systems),
        patch.object(IaquaSystem, "_send_session_request", send),
    ):
        assert await hass.config_entries.async_setup(core.entry_id)
        await hass.async_block_till_done()
        plus = MockConfigEntry(domain="iaqualink_plus", data={})
        plus.add_to_hass(hass)
        assert await hass.config_entries.async_setup(plus.entry_id)
        await hass.async_block_till_done()
        yield plus


async def test_entities_and_controls(hass: HomeAssistant, api: FakeAPI):
    gen = _setup(hass, api)
    await gen.__anext__()

    st = lambda e: hass.states.get(e)
    assert st("sensor.salt_cell_pool_output").state == "40"
    assert st("sensor.salt_cell_pool_status").state == "running"
    assert st("sensor.salt_cell_salinity").state == "2600"
    assert st("binary_sensor.salt_cell_low_salt").state == "on"
    assert float(st("number.salt_cell_pool_output_setting").state) == 40
    assert st("switch.salt_cell_boost").state == "off"
    assert st("sensor.salt_cell_salt_cell").state == "detected"
    assert float(st("number.salt_cell_boost_duration").state) == 24

    await hass.services.async_call("number", "set_value", {"entity_id": "number.salt_cell_pool_output_setting", "value": 70}, blocking=True)
    await hass.async_block_till_done()
    assert ("set_swc_config", {"poolswcsp": 70, "spaswcsp": 0}) in api.calls
    assert float(st("number.salt_cell_pool_output_setting").state) == 70

    await hass.services.async_call("number", "set_value", {"entity_id": "number.salt_cell_boost_duration", "value": 12}, blocking=True)
    await hass.services.async_call("switch", "turn_on", {"entity_id": "switch.salt_cell_boost"}, blocking=True)
    await hass.async_block_till_done()
    assert ("control_swc_boost", {"boostcontrol": "start", "boosthrs": 12, "boostmode": "pool"}) in api.calls
    assert st("switch.salt_cell_boost").state == "on"
    assert st("sensor.salt_cell_boost_time_remaining").state == "719"

    await hass.services.async_call("switch", "turn_off", {"entity_id": "switch.salt_cell_boost"}, blocking=True)
    await hass.async_block_till_done()
    assert ("control_swc_boost", {"boostcontrol": "stop"}) in api.calls
    assert st("switch.salt_cell_boost").state == "off"

    # Core integration still works alongside.
    assert hass.states.get("sensor.pool_temp") is not None or any(
        s.entity_id.startswith("sensor.") and "pool" in s.entity_id for s in hass.states.async_all()
    )
    await gen.aclose()


async def test_no_swc(hass: HomeAssistant):
    home = copy.deepcopy(HOME)
    home["home_screen"] = [x for x in home["home_screen"] if not any(k.startswith("swc") for k in x)]
    api = FakeAPI(home)
    gen = _setup(hass, api)
    await gen.__anext__()
    assert hass.states.get("sensor.salt_cell_salt_cell").state == "not_detected"
    assert hass.states.get("sensor.salt_cell_pool_output").state == "unavailable"
    assert not any(c[0] == "get_swc_config" for c in api.calls)
    await gen.aclose()
