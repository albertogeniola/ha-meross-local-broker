## 0.0.1-alpha52
- Push the timezone and DST rules (`Appliance.System.Time`) to devices whose reported timezone is empty or
  different from the configured one, as the Meross cloud does on every connection. Without it, power-metering
  plugs (e.g. mss310, mss210p) keep reporting 0 V / 0 A / 0 W and an empty consumption history (#42).
  New optional `device_timezone` setting, defaulting to the Home Assistant timezone.
- The agent now polls `Appliance.System.All` every 60 seconds from devices whose info is stale. Devices
  reconnecting after a broker restart publish nothing on their own, so without this poll their online status
  (and the timezone check above) never refreshed.
- Fix CICD bulding pipeline

## 0.0.1-alpha46

- Dropped support for armhf platform
- Improved s6 restart procedure
- Updated dependency with meross_iot low level library

## 0.0.1-alpha46

- Add new endpoint to support latest version of MerossIot library version

## 0.0.1-alpha45

- Fix meross link parameter being ingored at configuration phase
