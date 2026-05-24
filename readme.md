# PV Charge Control

!! This is not a working implementation. Use at your own risk! !!

PV Charge Control is a small Python service for PV surplus charging. It reads
power data from the energy system, calculates the available surplus, and adjusts
the maximum charging current of an Easee wallbox.

## Current Purpose

The project is intended to run on a Raspberry Pi as a `systemd` service without
a web server, database, or container orchestration. The runtime logic is
synchronous and single-threaded:

1. Read NEOOM BEAAM
2. Normalize PV power and house consumption
3. Calculate surplus power
4. Maintain a floating mean
5. Calculate the target current
6. Apply the current limit to Easee with a short time-to-live

Example log (probably outdated state):

```text
PV=3200W House=1100W Surplus=2100W FloatingMean=1850W TargetCurrent=8A State=CHARGING
```

## Architecture

```text
.
|-- readme.md
|-- .env.example
|-- scripts/
|   `-- install.sh
|-- systemd/
|   `-- pv-charge-control.service
|-- doc/
|   |-- Pv Charge Control Project Blueprint And Download Links.pdf
|   `-- Solax-Register.txt
`-- src/
    |-- main.py
    |-- config.py
    |-- config.yaml
    |-- controller.py
    |-- mqtt.py
    |-- inverter/
    |   |-- base.py
    |   |-- models.py
    |   |-- neoom_beaam.py
    |   `-- solax_modbus.py
    `-- wallbox/
        |-- base.py
        |-- models.py
        |-- easee_cloud.py
        |-- easee_cloud_naive.py
        `-- easee_local.py
```

### Entry Point

`src/main.py` is the application entry point. It:

- loads `config.yaml` and `.env`
- creates a `NeoomBeaamClient`
- creates the `PVController`
- creates an Easee wallbox client
- starts `controller.run()`

The current implementation may temporarily run in dry-run mode while validating
BEAAM readings and controller behavior. In that mode the wallbox is not passed
to the controller and Easee calls remain commented out.

### Configuration

`src/config.py` loads `.env` first and YAML afterwards. Environment values
override the corresponding YAML fields. This currently applies to:

```text
NEOOM_BEAAM_HOST
NEOOM_BEAAM_API_TOKEN
SOLAX_MODBUS_HOST
EASEE_LOCAL_HOST
EASEE_API_KEY
```

The `.env` file is intentionally not versioned. `.env.example` documents only
the required variables.

### Inverter Layer

All inverter and energy-system clients should implement the interface from
`src/inverter/base.py`:

```python
read_power_data() -> PowerData
```

`PowerData` lives in `src/inverter/models.py` and contains:

- `pv_power`
- `house_power`
- `surplus_power`
- `timestamp`

The active implementation is `src/inverter/neoom_beaam.py`. It calls the BEAAM
endpoint `/api/v1/site/state` and reads the configured `energyFlow.states` keys:

- `POWER_PRODUCTION` for PV power
- `POWER_CONSUMPTION_CALC` for house consumption

`src/inverter/solax_modbus.py` remains available as an alternative
implementation. The register idea comes from `doc/Solax-Register.txt`; relevant
values include PV power and feed-in/meter power. SolaX is not the active path at
the moment.

### Controller

`src/controller.py` contains the control logic:

- polling with `control.poll_interval`
- buffer length from `control.averaging_window`
- floating mean over surplus power
- start/stop hysteresis via `surplus_start_threshold` and
  `surplus_stop_threshold`
- target current calculation with `amps = int(avg_surplus / voltage)`
- limit to `control.max_current`
- minimum current check against `control.min_current`

The wallbox is not updated on every polling cycle. It has a separate heartbeat
interval, `control.wallbox_update_interval`. The controller refreshes the Easee
dynamic current limit periodically and starts or stops charging based on the
hysteresis state.

The intended Easee command is TTL-based: the dynamic current limit is set with a
10-minute validity. If the service stops, crashes, or loses connectivity, Easee
does not keep an old limit forever; the limit expires automatically after the
TTL unless the controller refreshes it.

### Wallbox Layer

The wallbox abstraction lives in `src/wallbox/base.py`. The `ChargerState` data
model lives in `src/wallbox/models.py`.

Implemented clients:

- `src/wallbox/easee_cloud.py`: cloud API with dynamic charging current and TTL
- `src/wallbox/easee_local.py`: placeholder for local HTTP control
- `src/wallbox/easee_cloud_naive.py`: older naive variant

The Easee cloud implementation is the intended production path. The local Easee
client exists as an extension point if a stable local API is available.

### MQTT

`src/mqtt.py` is prepared as an optional integration point. The intended use is
to publish PV power, house consumption, surplus power, floating mean, target
current, and wallbox state for Home Assistant, MQTT Explorer, or logging
systems.

## Installation

The target system is a Raspberry Pi or similar Linux machine with:

- Python 3.11+
- `systemd`
- network access to NEOOM BEAAM
- network/API access to Easee

### Place the Repository

The systemd service and install script assume this target path:

```text
/opt/pv-charge-control
```

Example:

```bash
sudo mkdir -p /opt/pv-charge-control
sudo chown "$USER:$USER" /opt/pv-charge-control
git clone <repo-url> /opt/pv-charge-control
cd /opt/pv-charge-control
```

### Run the Base Installer

```bash
chmod +x scripts/install.sh
./scripts/install.sh
```

The script installs system packages, creates a virtual environment in `venv/`,
installs the Python dependencies, and registers the systemd service.

Note: the script currently creates a local `requirements.txt` in the target
directory if needed. The repository itself does not yet contain a committed
`requirements.txt`.

### Configure `.env`

After installation, edit the local `.env`:

```bash
nano /opt/pv-charge-control/.env
```

Minimum configuration:

```env
NEOOM_BEAAM_HOST=192.168.x.x
NEOOM_BEAAM_API_TOKEN=...
EASEE_API_KEY=...
```

Optional or alternative paths:

```env
SOLAX_MODBUS_HOST=192.168.x.x
EASEE_LOCAL_HOST=192.168.x.x
```

Do not commit `.env`. It is excluded via `.gitignore`.

### Check YAML Configuration

The functional configuration lives at the repository top level:

```text
config.yaml
```

Important values:

```yaml
control:
  poll_interval: 20
  wallbox_update_interval: 240
  averaging_window: 12
  voltage: 230.0
  min_current: 6
  max_current: 16
  surplus_start_threshold: 1500
  surplus_stop_threshold: 1200
```

With `poll_interval: 20` and `averaging_window: 12`, the floating mean covers
about four minutes.

### Start the Service

```bash
sudo systemctl daemon-reload
sudo systemctl enable pv-charge-control.service
sudo systemctl start pv-charge-control.service
```

View logs:

```bash
journalctl -u pv-charge-control -f
```

The service starts:

```text
/opt/pv-charge-control/venv/bin/python src/main.py
```

and additionally loads:

```text
EnvironmentFile=-/opt/pv-charge-control/.env
```

## Local Development

On Windows/PyCharm, the project can be started directly with the existing
`.venv`. Make sure `.env` is in the project root or set the variables in the run
configuration.

Example:

```powershell
.\.venv\Scripts\python.exe src\main.py
```

`src/config.py` searches for configuration and `.env` in the usual working
directories: current directory, `src/`, and project root.

## Tests

The project uses Python's built-in `unittest` framework. No additional test
dependency is required.

The tests use local mock implementations for the parts of the NEOOM BEAAM and
Easee HTTP APIs that the clients call. This keeps the tests deterministic and
prevents network access during test runs.

Run the test suite from the repository root:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests
```

On Linux:

```bash
./venv/bin/python -m unittest discover -s tests
```

## Design Decisions

- No web server: the service is a small background process.
- No database: current values are enough for the control loop.
- No asyncio: synchronous polling is easier to debug and sufficient for the
  slow control intervals.
- journald instead of custom log files: systemd collects stdout/stderr.
- Secrets and local network addresses in `.env`: no private details in Git.
- Domain-local models: `PowerData` lives with `inverter`, `ChargerState` lives
  with `wallbox`.
- Shared interfaces: inverter and wallbox implementations can be swapped
  without rewriting the controller.
- Hysteresis and floating mean: reduce switching caused by clouds and short
  power spikes.
- No PID or PI control: unlike the original ChatGPT proposal, this is not
  implemented as a closed-loop control system. The service derives an output
  from measured PV surplus and applies that as a wallbox current limit. Debounce
  and delay compensation are handled by the floating mean, hysteresis, and
  deliberately long update intervals. This should sufficiently cover the
  response delays in inverter measurement, cloud/API communication, and wallbox
  behavior without adding PID tuning complexity (in a first try).
- TTL-based Easee control: the dynamic current limit is set with a 10-minute
  validity and refreshed by the controller. A service failure should therefore
  not keep an old charging current active indefinitely.

## Current Implementation Note

The intended state is active Easee control. During bring-up, the runtime may be
left in dry-run mode to validate BEAAM readings and controller behavior first.
In that mode:

- read NEOOM BEAAM and EASEE
- calculate surplus power
- maintain floating mean
- calculate target current
- log the current that would be sent to Easee, but do not actually send

### TODOs
- Bearer Token management. You need to get a valid bearer token by loggin in to https://developer.easee.com/reference/account_authenticate . This token will have a short living expiration time. Logging in again will give you an updated token. An automatic refresh in time needs to be implemented.
- Enabling production control, activate Easee wallbox client to
by uncommenting the calls in `wallbox/easee_cloud.py`. To be validated, if the currently implemented (commented out) api calls do as expected.
- There still seems to be an error: charging is not stopped, when surplus is too low -> examine