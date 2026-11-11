# Changelog

## 0.1.13

- Climate entity: use the `native_*` temperature properties (`_attr_native_temperature_unit`, `native_current_temperature`, `native_target_temperature`). The old ones are deprecated in Home Assistant and stop working in 2027.11.
- A failed command (Auto, Heat, Off, temperature) is now written to the log as a warning with the command name, the entity and the error. The error shown in the UI was not logged before.
- Connections now go through `bleak_retry_connector.establish_connection()`, as Home Assistant recommends. This removes the "BleakClient.connect() called without bleak-retry-connector" warning logged on every connection. The library is already provided by Home Assistant's Bluetooth integration.
- A command that fails because of a connection error is sent again up to 3 times (5 s pause) before the error is raised to the Climate entity. Each failed attempt is logged as a warning.
- After a failed read or write the cached GATT services are dropped, so a stale handle (GATT error 133 on the write, seen on Bath 0) cannot repeat on the next attempt.
- README: HACS references renamed to Marketplace (the My Home Assistant button still works).

## 0.1.12

- After connecting, all four GATT characteristics the integration uses are checked (not only the first one). A partial service discovery, which showed up as "Characteristic ... not found" after a restart, now clears the cache and retries instead of failing the poll.

## 0.1.11

- Fix: every command (Auto, Heat, Off, temperature) carries the whole configuration table of the radiator, which includes the weekly program. The table used to hold the program captured at development time, so a command could overwrite the program set in the IRSAP NOW app. Commands now send back the weekly program read from the radiator at the last poll.
- The weekly program is still edited only in the IRSAP NOW app (Comfort preset temperature excluded, see README).

## 0.1.10

- Mode `heat` is labelled "Heat" (entity translations).
- Temperature step is now 1 C (was 0.5 C).
- Fix: the timed mode (`heat`) was shown as `auto` because the radiator keeps reporting "program" during a temporary setpoint. It is now recognised from the end time of the temporary setpoint (record 07), so the HVAC mode and the remaining time are correct.
- New attributes `remaining_minutes` and `remaining` (h:mm) in timed mode (`heat`), refreshed every minute without Bluetooth traffic.

## 0.1.9
- README: Bluetooth-only notice, automatic (Marketplace and My Home Assistant buttons) and manual installation, trademark disclaimer.
- New original integration icon (the IRSAP NOW app icon was removed).

## 0.1.8
- HVAC modes: `off`, `auto` (radiator program, as `heat` was before) and `heat` (timed mode, default 24 C for 2 h).
- `set_temperature` now starts a timed setpoint for the configured hours (0 hours = manual setpoint with no expiry, as before).
- New options: timed mode temperature and duration.

## 0.1.7
- README and error message: Shelly and other advertisement-only gateways cannot be used, an active connection is required.
- Repository owner renamed to Heimdallr72.

## 0.1.6
- Connection attempt timeout 30 s, 4 attempts, 5 s pause between attempts.
- Statistics attributes on the climate entity: `polls_ok`, `polls_failed`, `last_success`.

## 0.1.5
- Retry with a cleared service cache when the GATT services are incomplete after connecting.
- Error messages always include the exception type.

## 0.1.4
- Own connection logic with a longer timeout (90 s) and device re-lookup at every attempt.

## 0.1.3
- Shared Bluetooth lock: radiators are polled one at a time.

## 0.1.2
- Integration icon.

## 0.1.1
- First refresh in the background so the config flow does not block.

## 0.1.0
- First version: climate entity per radiator, Bluetooth scan in the config flow, options flow.
