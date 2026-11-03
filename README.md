# IRSAP BLE Radiator (Home Assistant custom integration)

Local Bluetooth control for **IRSAP electric towel warmers that have no Wi-Fi** (Ares, advertised as
`IRSAP_RS_xxxxxxx`). One `climate` entity per radiator, no cloud, no IRSAP NOW account.

> **Bluetooth only.** This integration supports only the Bluetooth models. Radiators with Wi-Fi that appear in the
> IRSAP NOW cloud are not supported here; for those, a separate cloud integration exists
> ([hexCut/irsap-ha](https://github.com/hexCut/irsap-ha)).
>
> Unofficial and experimental. Reliability depends on the Bluetooth signal between the adapter and the radiator
> (about -60 dBm or better is recommended).

## Requirements
Reading the state and sending commands need a Bluetooth *connection* (the advertisements carry no state data).
Gateways that only forward advertisements, such as Shelly devices, are **not** enough. Use a local Bluetooth adapter
or an ESPHome Bluetooth proxy with `bluetooth_proxy: active: true`. Close the IRSAP NOW phone app while Home
Assistant is connecting: the radiator accepts one connection at a time.

## Installation

### Option 1: automatic (HACS)
1. Add the repository to HACS and download the integration:

   [![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=Heimdallr72&repository=irsap_ble&category=integration)

2. Restart Home Assistant.
3. Start the setup (the integration scans for radiators in range, lets you tick the ones to add and asks a name for
   each, for example the room):

   [![Open your Home Assistant instance and start setting up a new integration.](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start/?domain=irsap_ble)

### Option 2: manual
1. Download the latest release and copy the folder `custom_components/irsap_ble` into `/config/custom_components/`
   (create the folder if needed).
2. Restart Home Assistant.
3. Go to Settings > Devices & services > Add integration and choose **IRSAP BLE Radiator**. Radiators in range are
   also offered automatically in the "Discovered" section.

## Entity
| Home Assistant | Radiator |
|---|---|
| `hvac_mode` `auto` | on, back to the normal program (Comfort preset rewritten, see options) |
| `hvac_mode` `heat` | timed mode: heats to the timed temperature for the configured hours (default 24 C, 2 h), then the program resumes |
| `hvac_mode` `off` | off, antifreeze 5 C |
| `set_temperature` | timed setpoint for the configured hours (0 hours: manual setpoint with no expiry) |
| `current_temperature` | measured temperature |
| `target_temperature` | effective setpoint (the temperature step is 1 C) |
| attribute `control_mode` | `manual` or `program` |
| attribute `remaining_minutes`, `remaining` | timed mode (`heat`) only: time left until the program resumes, in minutes and as `h:mm` (updated every minute) |
| attribute `until` | program: next program change; manual with timer: end of the timer |

Options (per radiator): Comfort temperature written back when you choose `auto` (default 24.0 C), timed mode
temperature (24.0 C) and duration (2 h, 0 = no expiry), polling interval
(default 300 s). The integration connects only for a few seconds per poll or command, so the phone app keeps working
between two operations.

## Icon and trademarks
The integration icon is an original image made for this project. It is not the IRSAP logo.

IRSAP and IRSAP NOW are trademarks of their respective owners. All product and company names are used for
identification purposes only, to say which devices the integration works with. Their use does not imply any
affiliation with, or endorsement by, the trademark owners. This project is independent and unofficial.

## Known limits
* Eco / Comfort / antifreeze presets cannot be changed over Bluetooth (the app keeps them locally). Choosing `auto`
  writes back the Comfort value set in the options.
* Setting a temperature (or choosing `heat`) starts the timed mode; with 0 hours it switches to manual mode until the next change. Use `auto` to return to the program.
* Temperature range 5-30 C is a safe guess, the real limits were not verified.
* Tested on the protocol level only (captures from one model, firmware 01.0.55). Writes use the full configuration
  table captured from the app: if your firmware differs, check before using it on other models.
