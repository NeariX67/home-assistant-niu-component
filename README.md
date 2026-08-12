# Niu E-scooter Home Assistant integration

This is a custom component for Home Assistant to integrate your Niu Scooter.

Now this integration is _asynchronous_ and it is easy installable via config flow.

## Changes:
* All entities are now built on a `DataUpdateCoordinator`, polling the Niu cloud API once per cycle instead of each entity polling independently.
* Exposes essentially every field the Niu app's cloud API returns: per-battery health/temperature/charge-cycles/energy-used-today (including a third battery compartment on scooters that support it), GPS/GSM signal, tire-pressure sensors (for equipped models), seat and battery-compartment lock state, alarm and dash-cam status, last-trip and lifetime statistics, and more. Entities that don't apply to your scooter (e.g. TPMS wheel sensors) simply aren't created.
* Added a `device_tracker` entity so the scooter shows up on the map, replacing separate latitude/longitude sensors.
* Added a lock entity that remotely arms/disarms the scooter's anti-theft alarm ("fortification" in Niu's API) — unlock to disarm, lock to arm.
* Added a switch entity that remotely wakes up the scooter's electronics (turn on) or powers them back down (turn off), using the same cloud command the Niu app uses when out of Bluetooth range.
* Added a number entity to remotely set the charging power to any value within the scooter's reported range, for scooters that support it.
* Added a select entity to remotely set the charging limit percentage (80/85/90/95/100%), for scooters that support it.
* Added disabled-by-default diagnostic sensors for the scooter's reported minimum/maximum charging power range, for scooters that expose a charging power setting.
* Added a number entity to remotely set the scooter's horn/alert volume, for scooters that report a maximum volume.
* Now it will generate automatically a Niu device so all the sensors and the camera will grouped
![auto device](images/niu_integration_device.png)
* A camera entity is created automatically, showing the rendered image of your last track.
![last track camera](images/niu_integration_camera.png)

With the thanks to pikka97 !!!

## Setup
1. In Home Assistant's settings under "device and services" click on the "Add integration" button.
2. Search for "Niu Scooters" and click on it.
3. Insert your Niu app companion's credentials.
![config flow](images/config_flow_niu_integration.png)
4. Enjoy your new Niu integration :-) All available entities are created automatically — disable any you don't want from the entity list.

## Upgrading from an older version

This version renames every entity's unique ID, so Home Assistant will treat existing entities as removed and create new ones alongside them. After upgrading, remove the old (unavailable) entities from **Settings → Devices & Services → Entities** and re-add any of the new ones to your dashboards/automations.

## Known bugs

some people had problems with this version please take the latest 1.o  versions
See https://github.com/marcelwestrahome/home-assistant-niu-component repository
