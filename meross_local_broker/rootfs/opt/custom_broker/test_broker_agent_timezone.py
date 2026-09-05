"""Tests for the device timezone sync performed by the broker agent.

Run with: python3 -m unittest test_broker_agent_timezone
(requires the agent runtime dependencies: paho-mqtt, expiringdict, SQLAlchemy, meross_iot)
"""
import json
import time
import unittest
from types import SimpleNamespace
from unittest import mock

import broker_agent

DEVICE_UUID = "2310184977069551370248e1e9de3638"
DEVICE_KEY = "7b9ebd3edc1f13c6cb3f0d70d4ce066f"


class FakeMqttClient:
    def __init__(self):
        self.published = []

    def publish(self, topic, payload):
        self.published.append((topic, json.loads(payload)))


class FakeDbHelper:
    """Just enough of DbHelper for _handle_message_to_agent on a plain plug (no hub)."""

    def __init__(self):
        self.device = SimpleNamespace(uuid=DEVICE_UUID, owner_user=SimpleNamespace(mqtt_key=DEVICE_KEY),
                                      child_subdevices=[])

    def get_device_by_uuid(self, device_uuid):
        return self.device

    def get_all_devices(self):
        return [self.device]

    def update_device(self, device):
        return device

    def update_device_channel(self, device_uuid, channel_id):
        return None


def make_broker(device_timezone):
    broker = broker_agent.Broker(hostname="localhost", port=2001, username="u", password="p", cert_ca=None,
                                 enable_bridging=False, device_timezone=device_timezone)
    broker.c = FakeMqttClient()
    return broker


def time_set_messages(broker):
    return [(topic, msg) for topic, msg in broker.c.published
            if msg["header"]["namespace"] == "Appliance.System.Time" and msg["header"]["method"] == "SET"]


def system_all_gets(broker):
    return [(topic, msg) for topic, msg in broker.c.published
            if msg["header"]["namespace"] == "Appliance.System.All" and msg["header"]["method"] == "GET"]


def system_all_getack(timezone):
    return {
        "header": {"namespace": "Appliance.System.All", "method": "GETACK",
                   "from": "/appliance/%s/publish" % DEVICE_UUID},
        "payload": {"all": {
            "system": {
                "hardware": {"type": "mss210p", "subType": "un", "version": "7.0.0"},
                "firmware": {"version": "7.3.3", "server": "homeassistant.local", "port": 2001, "innerIp": "10.0.0.5"},
                "time": {"timestamp": 1788556880, "timezone": timezone, "timeRule": []},
                "online": {"status": 1},
            },
            "digest": {"togglex": [{"channel": 0, "onoff": 1}]},
        }},
    }


class SyncDeviceTimezoneTest(unittest.TestCase):
    def test_publishes_time_set_when_device_has_no_timezone(self):
        broker = make_broker("Europe/Rome")
        published = broker._sync_device_timezone(DEVICE_UUID, {"timezone": "", "timeRule": []}, DEVICE_KEY)
        self.assertTrue(published)
        topic, msg = time_set_messages(broker)[0]
        self.assertEqual(topic, "/appliance/%s/subscribe" % DEVICE_UUID)
        self.assertEqual(msg["header"]["from"], "/_agent")
        self.assertEqual(msg["payload"]["time"]["timezone"], "Europe/Rome")
        self.assertGreater(len(msg["payload"]["time"]["timeRule"]), 0)
        self.assertAlmostEqual(msg["payload"]["time"]["timestamp"], time.time(), delta=5)

    def test_skips_when_device_timezone_matches(self):
        broker = make_broker("Europe/Rome")
        self.assertFalse(broker._sync_device_timezone(DEVICE_UUID, {"timezone": "Europe/Rome"}, DEVICE_KEY))
        self.assertEqual(time_set_messages(broker), [])

    def test_skips_when_no_timezone_configured(self):
        broker = make_broker(None)
        self.assertFalse(broker._sync_device_timezone(DEVICE_UUID, {"timezone": ""}, DEVICE_KEY))
        self.assertEqual(time_set_messages(broker), [])

    def test_does_not_repeat_within_cooldown(self):
        broker = make_broker("Europe/Rome")
        broker._sync_device_timezone(DEVICE_UUID, {"timezone": ""}, DEVICE_KEY)
        broker._sync_device_timezone(DEVICE_UUID, {"timezone": ""}, DEVICE_KEY)
        self.assertEqual(len(time_set_messages(broker)), 1)

    def test_retries_after_cooldown(self):
        broker = make_broker("Europe/Rome")
        broker._sync_device_timezone(DEVICE_UUID, {"timezone": ""}, DEVICE_KEY)
        broker._timezone_sync_attempts[DEVICE_UUID] -= broker_agent._TIMEZONE_SYNC_COOLDOWN_SECONDS + 1
        broker._sync_device_timezone(DEVICE_UUID, {"timezone": ""}, DEVICE_KEY)
        self.assertEqual(len(time_set_messages(broker)), 2)

    def test_invalid_configured_timezone_disables_sync(self):
        broker = make_broker("Mars/Olympus_Mons")
        self.assertIsNone(broker.device_timezone)
        self.assertFalse(broker._sync_device_timezone(DEVICE_UUID, {"timezone": ""}, DEVICE_KEY))


class PeriodicRefreshTest(unittest.TestCase):
    """Devices reconnecting after a broker restart publish nothing, so the agent must poll System.All periodically."""

    def test_refreshes_device_never_seen(self):
        broker = make_broker("Europe/Rome")
        with mock.patch.object(broker_agent, "dbhelper", FakeDbHelper()):
            refreshed = broker.refresh_stale_devices()
        self.assertEqual(refreshed, [DEVICE_UUID])
        topic, msg = system_all_gets(broker)[0]
        self.assertEqual(topic, "/appliance/%s/subscribe" % DEVICE_UUID)
        self.assertEqual(msg["header"]["from"], "/_agent")

    def test_skips_device_with_fresh_info(self):
        broker = make_broker("Europe/Rome")
        broker._devices_sys_info_timestamp[DEVICE_UUID] = broker_agent.datetime.now()
        with mock.patch.object(broker_agent, "dbhelper", FakeDbHelper()):
            self.assertEqual(broker.refresh_stale_devices(), [])
        self.assertEqual(system_all_gets(broker), [])

    def test_refreshes_device_with_stale_info(self):
        broker = make_broker("Europe/Rome")
        stale = broker_agent.datetime.now() - broker_agent.timedelta(
            seconds=broker_agent._DEVICE_UPDATE_CACHE_INTERVAL_SECONDS + 1)
        broker._devices_sys_info_timestamp[DEVICE_UUID] = stale
        with mock.patch.object(broker_agent, "dbhelper", FakeDbHelper()):
            self.assertEqual(broker.refresh_stale_devices(), [DEVICE_UUID])
        self.assertEqual(len(system_all_gets(broker)), 1)


class AgentMessageHandlingTest(unittest.TestCase):
    def test_system_all_getack_without_timezone_triggers_sync(self):
        broker = make_broker("Europe/Rome")
        with mock.patch.object(broker_agent, "dbhelper", FakeDbHelper()):
            broker._handle_message_to_agent("/_agent", system_all_getack(timezone=""))
        self.assertEqual(len(time_set_messages(broker)), 1)

    def test_system_all_getack_with_matching_timezone_does_not_sync(self):
        broker = make_broker("Europe/Rome")
        with mock.patch.object(broker_agent, "dbhelper", FakeDbHelper()):
            broker._handle_message_to_agent("/_agent", system_all_getack(timezone="Europe/Rome"))
        self.assertEqual(time_set_messages(broker), [])

    def test_time_setack_is_accepted_without_publishing(self):
        broker = make_broker("Europe/Rome")
        setack = {"header": {"namespace": "Appliance.System.Time", "method": "SETACK",
                             "from": "/appliance/%s/publish" % DEVICE_UUID}, "payload": {}}
        with mock.patch.object(broker_agent, "dbhelper", FakeDbHelper()):
            broker._handle_message_to_agent("/_agent", setack)
        self.assertEqual(broker.c.published, [])


if __name__ == "__main__":
    unittest.main()
