# Changelog

## 0.1.10
- Temperature step is now 1 C (was 0.5 C).
- Fix: the timed mode (`heat`) was shown as `auto` because the radiator keeps reporting "program" during a temporary setpoint. It is now recognised from the end time and the setpoint, so the HVAC mode and the remaining time are correct.
- New attributes `remaining_minutes` and `remaining` (h:mm) in timed mode (`heat`), refreshed every minute without Bluetooth traffic.

## 0.1.9
- README: Bluetooth-only notice, automatic (HACS and My Home Assistant buttons) and manual installation, trademark disclaimer.
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
