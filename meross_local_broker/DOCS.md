# Home Assistant Add-on: Meross Local Broker

This addon provides lan-local MQTT capabilities in combination with a fully home-assistant integrated web-ui. 

## Configuration

### Option: `device_timezone`

Timezone (IANA name, e.g. `Europe/Rome`) pushed to the Meross devices together with the daylight-saving rules,
exactly like the Meross cloud does when a device connects. Leave it empty to use the Home Assistant timezone.

Devices paired to a local broker never receive a timezone, and power-metering plugs (mss310, mss210p, ...) do
not report any electricity or consumption data until they get one. The agent checks the timezone reported by
each device (`Appliance.System.All`, polled at startup, on device messages and every 60 seconds when stale) and
sends `Appliance.System.Time` only when it is missing or different.
