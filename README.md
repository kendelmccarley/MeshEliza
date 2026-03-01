# MeshEliza

**MeshEliza runs the [Eliza](https://en.wikipedia.org/wiki/ELIZA) chatbot on a
Meshtastic node, responding to direct messages over the mesh radio network.**
A session starts automatically the first time a remote node sends a direct
message — no trigger word required.  On the first message Eliza introduces
herself, delivers her opening greeting, and then responds to the message.
Subsequent messages receive a direct response.  Send "bye" or "quit" to end
the session; a new session starts on the next incoming DM.  Sessions that have
been idle for 30 minutes are silently expired and restarted on the next
message.

> **⚠ UNTESTED — this code has not been run against real hardware and may not
> work.**  It is a development prototype published for tracking purposes only.
> Expect bugs, incomplete features, and breaking changes between commits.
> Do not rely on it for real mesh-radio operations.

MeshEliza is a terminal-based (TUI) client for Meshtastic LoRa mesh radio
networks, designed to run on a Raspberry Pi or any Linux system with a
terminal.  It is built with the [Textual](https://textual.textualize.io/)
framework and communicates with a Meshtastic node over USB/serial, TCP/WiFi,
or Bluetooth (BLE).

---

## Table of Contents

1. [Installation](#1-installation)
2. [Running MeshEliza](#2-running-mesheliza)
3. [Command-Line Flags](#3-command-line-flags)
4. [Connection Screen](#4-connection-screen)
5. [Main Screen](#5-main-screen)
   - 5.1 [Messages Tab](#51-messages-tab)
   - 5.2 [Channels Tab](#52-channels-tab)
   - 5.3 [Nodes Tab](#53-nodes-tab)
   - 5.4 [Node Detail Modal](#54-node-detail-modal)
   - 5.5 [Settings Tab](#55-settings-tab)
   - 5.6 [DM Slash Commands](#56-dm-slash-commands)
6. [Keyboard Shortcuts](#6-keyboard-shortcuts)
7. [Configuration File](#7-configuration-file)
8. [Message & Node Database](#8-message--node-database)
9. [Themes](#9-themes)
10. [Debug Logging](#10-debug-logging)
11. [Serial Port Permissions (Linux)](#11-serial-port-permissions-linux)
12. [Known Issues & Missing Features](#12-known-issues--missing-features)
13. [Troubleshooting](#13-troubleshooting)
14. [Headless / Kiosk Operation (Raspberry Pi)](#14-headless--kiosk-operation-raspberry-pi)

---

## 1. Installation

Use the provided install script (recommended on Raspberry Pi):

```
bash install.sh
```

Or install manually into a virtual environment:

```
python3 -m venv ~/.venv/mesheliza
source ~/.venv/mesheliza/bin/activate
pip install -e .
```

**Dependencies installed automatically:**

| Package       | Purpose                                         |
|---------------|-------------------------------------------------|
| textual ≥ 8   | TUI framework (rendering, widgets, key bindings)|
| meshtastic    | Meshtastic Python library (serial/TCP/BLE)      |
| bleak         | Bluetooth BLE scanning                          |
| pyserial      | Serial port enumeration and communication       |
| pypubsub      | Event pub/sub (used internally by meshtastic)   |
| protobuf      | Meshtastic protocol buffer serialization        |
| anyio         | Async I/O support                               |

Python 3.11 or newer is required.

---

## 2. Running MeshEliza

```
mesheliza
```

or

```
python -m meshtty.main
```

The app starts on the **Connection Screen**.  Once connected it switches
automatically to the **Main Screen**.

---

## 3. Command-Line Flags

```
mesheliza [--debug] [--bot] [--log] [--noargs]
```

| Flag       | Description                                                  |
|------------|--------------------------------------------------------------|
| `--debug`  | Enable DEBUG-level logging to `/tmp/mesheliza.log`.          |
| `--bot`    | Enable the DM slash-command bot (see section 5.6).           |
| `--log`    | Log all inbound and outbound messages to `/tmp/mesheliza-messages.log`. |
| `--noargs` | Clear saved startup flags (`~/.config/mesheliza/last_flags`) and launch with no flags active. Useful if the auto-launch wrapper gets stuck replaying a bad flag. |
| `-h`       | Print help and exit.                                         |

---

## 4. Connection Screen

The first screen shown on launch.  Choose how to connect to your radio node.

### Tabs

#### Serial / USB

- The app scans for serial ports whose USB vendor ID matches common Meshtastic
  chips and lists them in a table.
- Click a row to copy that port path into the input field, or type it manually
  (e.g. `/dev/ttyUSB0`, `/dev/ttyACM0`).
- Click **Connect**.

#### TCP / WiFi

- Enter the hostname or IP address of the node and the port (default 4403).
- Click **Connect**.

#### Bluetooth (BLE)

- Click **Scan for BLE Devices** to perform a 5-second scan.
- Click a row or enter a MAC address manually.
- Click **Connect**.

### Remember this device

The **Remember this device** switch (on by default) saves connection details
so the same transport and address are pre-filled on the next launch.

### Auto-connect

If a device was remembered from a previous session, the connection screen
starts a 5-second countdown and connects automatically.  The status line
shows "Connecting in Ns… (press any key to cancel)".  Press any key, switch
tabs, or click a button to cancel and configure manually.

### Status messages

- A status line shows progress: "Connecting…", "Connected — downloading
  nodes: …", "Download complete (N nodes) — waiting for radio confirmation…",
  "Connected! (N nodes loaded)".
- A red error line shows the failure reason if a connection attempt fails.

> **Note:** On busy networks (many nodes), the app transitions to the Main
> Screen as soon as the initial radio handshake completes.  Remaining node
> records continue to arrive in the background and appear in the Nodes tab
> as they come in.

### Keyboard shortcuts (Connection Screen)

| Key    | Action |
|--------|--------|
| Ctrl+Q | Quit   |

---

## 5. Main Screen

After a successful connection the app switches to the Main Screen, which has
four tabs.

The header bar has been intentionally removed to maximise usable display area.

---

### 5.1 Messages Tab

A unified, scrollable message history for all channels and direct messages,
plus a compose bar at the bottom.

#### Message display

Messages are displayed in a fixed-80-column terminal style:

```
HH:MM prefix: message text
```

- **Incoming broadcasts** — displayed flush with the left margin, labelled
  with the channel name (e.g. `Primary`, `LongFast`).
- **Incoming direct messages** — labelled with the sender's short name.
- **Outgoing messages** — indented by two spaces.
- Lines longer than 80 characters wrap to the next line, aligned under the
  message text.

#### Compose bar

The input field is pre-filled with the last active prefix (e.g. `Primary: `).
You can type and send as-is, or edit the prefix to target a different channel
or a specific node's short name.  Format:

```
prefix: your message text
```

- If the prefix matches a configured channel name → sent as a broadcast on
  that channel.
- If the prefix matches a node short name → sent as a direct message to that
  node.
- Press **Enter** or click **Send** to transmit.

#### Scrolling

- **Up / Down arrows** scroll the message history one line at a time.
- **PageUp / PageDown** scroll a full screen at a time.
- Scrolling works regardless of whether focus is on the message area or the
  compose input.

#### History

The 200 most recent messages (across all channels and DMs) are loaded from
the local database on startup.

---

### 5.2 Channels Tab

Lists all channels configured on the connected radio.

- Click a channel name to set it as the compose prefix in the Messages tab.
  The app switches back to Messages automatically.
- The list is refreshed each time the tab is shown.

---

### 5.3 Nodes Tab

A live table of all mesh nodes known to the radio.  Updates in real time as
position, telemetry, and node-info packets are received.

| Column     | Description                                      |
|------------|--------------------------------------------------|
| Short      | Node short name (4-character callsign).          |
| Long Name  | Node long name.                                  |
| SNR        | Last received signal-to-noise ratio (dB).        |
| Last Heard | Time of the last packet heard (HH:MM:SS, local). |
| Battery    | Reported battery level (%).                      |
| Position   | GPS coordinates (lat, lon) to 4 decimal places.  |
| HW Model   | Hardware model string.                           |

Press **Ctrl+R** to force a refresh from the radio.

Click any row to open the **Node Detail Modal**.

---

### 5.4 Node Detail Modal

Overlay shown when you click a node row.  Displays:

- Node ID, short name, long name, hardware model
- Last SNR, last heard timestamp
- Battery level
- Latitude, longitude, altitude

Fields show `—` when no value has been received.  Close with **Close**,
**Escape**, or **Q**.

---

### 5.5 Settings Tab

#### Connection section (top)

Shows the current connection state and provides a **Disconnect** button that
returns to the Connection Screen.  The status line includes the transport
description, the number of known nodes, and the local node's battery level
(when available).

#### Transport section

| Field                  | Description                                                   |
|------------------------|---------------------------------------------------------------|
| Default transport      | Tab pre-selected on the Connection Screen.                    |
| Serial port            | Last-used serial device path.                                 |
| TCP hostname           | Last-used TCP hostname or IP.                                 |
| TCP port               | Last-used TCP port (default 4403).                            |
| BLE address            | Last-used BLE MAC address.                                    |
| Auto-connect on launch | Saved but not yet active in the connection flow.              |

#### Display section

| Field                  | Description                                                   |
|------------------------|---------------------------------------------------------------|
| Show short node names  | Use 4-character short names as the primary identifier in the Nodes table. |
| Theme                  | UI colour theme — applied immediately on Save.                |

#### Messaging section

| Field           | Description                                              |
|-----------------|----------------------------------------------------------|
| Default channel | Channel index shown in Settings reference (0–7).         |

Click **Save** to apply.  The **Theme** setting takes effect immediately;
other settings apply on the next connection.

---

### 5.6 DM Slash Commands

The slash-command bot is **disabled by default**.  Start MeshEliza with the
`--bot` flag to enable it:

```
mesheliza --bot
```

When enabled, any incoming **direct message** (not a channel broadcast) whose
text begins with `/` is checked against the command list.

- Valid commands are displayed in the message history and an automatic reply
  is sent back to the sender.
- Unrecognised `/` commands are silently dropped and not displayed.
- When `--bot` is not set, DMs starting with `/` are displayed as normal
  messages and no automatic reply is sent.

#### Available commands

| Command    | Response                                                          |
|------------|-------------------------------------------------------------------|
| `/HELP`    | Lists all available commands.                                     |
| `/INFO`    | Returns the URL of the MeshEliza git repository.                    |
| `/JOKE`    | Returns the next joke from the joke file (sequential, wraps).     |
| `/GPIO`    | Returns the state of exported GPIO pins read via sysfs.           |
| `/WEATHER` | Returns a placeholder string (feature not implemented).           |
| `/NEWS`    | Returns a placeholder string.                                     |
| `/NULL`    | Returns "All is nothingness".                                     |

Commands are case-insensitive (`/joke`, `/JOKE`, and `/Joke` all work).

#### Joke file setup

`/JOKE` reads from a CSV file that is **not included in the repository**.
Place the file at:

```
meshtty/data/shortjokes.csv
```

The file must be a CSV with a `Joke` column header on the first row and one
joke per subsequent row.  A compatible file is available from
[Kaggle — Short Jokes dataset](https://www.kaggle.com/datasets/abhinavmoudgil95/short-jokes).

If the file is absent, `/JOKE` responds with:

> No joke for you.  It's a dull day.

The file is loaded once in the background at startup.  The joke counter
position is saved to `~/.config/mesheliza/joke_index` after each `/JOKE`
command and restored on the next run, so the sequence continues where it
left off.

---

## 6. Keyboard Shortcuts

### Connection Screen

| Key    | Action |
|--------|--------|
| Ctrl+Q | Quit   |

### Main Screen

| Key       | Action                                        |
|-----------|-----------------------------------------------|
| F1        | Help — show keyboard shortcut reference       |
| Ctrl+T    | Switch to Messages tab                        |
| Ctrl+L    | Switch to Channels tab                        |
| Ctrl+N    | Switch to Nodes tab                           |
| Ctrl+S    | Switch to Settings tab                        |
| ↑ / ↓    | Scroll message history up / down one line     |
| PgUp/PgDn | Scroll message history up / down one screen   |
| Ctrl+G    | Send ASCII BEL (0x07) to the current destination |
| Ctrl+R    | Refresh node table from radio                 |
| Ctrl+D    | Disconnect and return to Connection Screen    |
| Ctrl+Q    | Quit                                          |

### Node Detail Modal

| Key    | Action      |
|--------|-------------|
| Escape | Close modal |
| Q      | Close modal |

---

## 7. Configuration File

**Location:** `~/.config/mesheliza/config.json`

Created automatically on first run.  Edit with any text editor while MeshEliza
is not running.

```json
{
  "default_transport": "serial",
  "last_serial_port": "/dev/ttyUSB0",
  "last_tcp_host": "",
  "last_tcp_port": 4403,
  "last_ble_address": "",
  "auto_connect": true,
  "log_level": "WARNING",
  "db_path": "/home/<user>/.config/mesheliza/messages.db",
  "default_channel": 0,
  "node_short_name_display": true,
  "theme": "mesheliza-multicolor"
}
```

| Key                     | Type    | Default                         | Description                         |
|-------------------------|---------|---------------------------------|-------------------------------------|
| `default_transport`     | string  | `"serial"`                      | `"serial"`, `"tcp"`, or `"ble"`.   |
| `last_serial_port`      | string  | `""`                            | Serial device path.                 |
| `last_tcp_host`         | string  | `""`                            | TCP hostname or IP.                 |
| `last_tcp_port`         | integer | `4403`                          | TCP port number.                    |
| `last_ble_address`      | string  | `""`                            | BLE MAC address.                    |
| `auto_connect`          | boolean | `true`                          | Saved but not yet used at startup.  |
| `log_level`             | string  | `"WARNING"`                     | `"DEBUG"`, `"INFO"`, `"WARNING"`, or `"ERROR"`. |
| `db_path`               | string  | `~/.config/mesheliza/messages.db` | Path to the SQLite database.        |
| `default_channel`       | integer | `0`                             | Messaging default channel (0–7).   |
| `node_short_name_display` | boolean | `true`                        | Use short names in the Nodes table. |
| `theme`                 | string  | `"mesheliza-multicolor"`          | UI theme (see section 9).           |

---

## 8. Message & Node Database

**Location:** `~/.config/mesheliza/messages.db`

SQLite database created automatically.  Query with any SQLite tool.

### `messages` table

| Column           | Type    | Description                                        |
|------------------|---------|----------------------------------------------------|
| `id`             | INTEGER | Auto-increment primary key.                        |
| `packet_id`      | TEXT    | Meshtastic packet ID (NULL for sent messages).     |
| `from_id`        | TEXT    | Sender node ID string (e.g. `!abcd1234`).          |
| `to_id`          | TEXT    | Recipient node ID or `^all` for broadcast.         |
| `channel`        | INTEGER | Channel index (0–7).                               |
| `text`           | TEXT    | Message text.                                      |
| `rx_time`        | INTEGER | Unix timestamp (seconds).                          |
| `is_mine`        | INTEGER | `1` if sent by this device, `0` if received.       |
| `display_prefix` | TEXT    | Human-readable prefix stored at send/receive time. |

The history view loads the 200 most recent messages (all channels combined)
from this table on startup.

### `nodes` table

| Column       | Type    | Description                                   |
|--------------|---------|-----------------------------------------------|
| `node_id`    | TEXT    | Primary key.  Node ID string.                 |
| `short_name` | TEXT    | 4-character callsign.                         |
| `long_name`  | TEXT    | Full node name.                               |
| `hw_model`   | TEXT    | Hardware model string.                        |
| `last_snr`   | REAL    | Last signal-to-noise ratio (dB).              |
| `last_lat`   | REAL    | Last latitude.                                |
| `last_lon`   | REAL    | Last longitude.                               |
| `last_alt`   | INTEGER | Last altitude (metres).                       |
| `battery`    | INTEGER | Battery level (%).                            |
| `last_heard` | INTEGER | Unix timestamp of last received packet.       |
| `updated_at` | INTEGER | Unix timestamp of last database write.        |

Useful queries:

```sql
-- All messages, newest first
SELECT datetime(rx_time,'unixepoch','localtime') AS time,
       display_prefix, text
FROM messages ORDER BY rx_time DESC LIMIT 50;

-- All known nodes
SELECT node_id, short_name, long_name, battery, last_snr FROM nodes;
```

---

## 9. Themes

Three built-in themes, selectable from Settings → Theme.  Applied immediately
on Save; persisted in config.

| Config value         | Label           | Appearance                                        |
|----------------------|-----------------|---------------------------------------------------|
| `mesheliza-multicolor` | Multicolor      | Dark navy/purple background, blue/purple/pink accents. Default. |
| `mesheliza-phosphor`   | Green Phosphor  | Black background, green-on-black CRT look.        |
| `mesheliza-bw`         | Black & White   | Black background, white/grey monochrome.          |

---

## 10. Debug Logging

```
mesheliza --debug
tail -f /tmp/mesheliza.log
```

In normal operation the log level is controlled by `log_level` in config
(default `"WARNING"`).  Only warnings and errors are written to the log file.

### Common errors in the log

| Error                                                           | Likely cause                                      |
|-----------------------------------------------------------------|---------------------------------------------------|
| `PermissionError: [Errno 13] ... '/dev/ttyUSB0'`               | User not in the `dialout` group — see section 11. |
| `serial.serialutil.SerialException: could not open port`       | Port path wrong or device not plugged in.         |
| `ConnectionRefusedError`                                        | TCP host/port wrong or node unreachable.          |
| `_waitConnected timed out but N nodes present`                 | Noisy serial stream; the transport forces connection and proceeds. |
| `waitForConfig timed out but myInfo and N nodes present`       | Radio config incomplete; channels/localConfig may be missing. |

---

## 11. Serial Port Permissions (Linux)

```
sudo usermod -aG dialout $USER
```

Log out and back in.  Verify:

```
groups   # output should include "dialout"
```

---

## 12. Known Issues & Missing Features

This is a pre-alpha release.  The following are known to be broken or absent:

### Confirmed bugs

- **`display_prefix` missing from old database rows** — Messages stored before
  this version have an empty `display_prefix` column; they fall back to
  displaying the raw `from_id` node string.

### Not yet implemented

- **Channel switching confirmation** — Clicking a channel in the Channels tab
  switches the compose prefix but does not visually confirm which channel is
  active.
- **Message acknowledgement display** — Sent messages appear immediately in
  the history but there is no indication of whether the radio acknowledged
  delivery.
- **Persistent compose prefix** — The compose bar prefix resets to the first
  channel on each session start and on each received message.
- **BLE transport** — Largely untested.
- **Node position on map** — No map view.
- **Channel creation / management** — Read-only channel display only.
- **Firmware version / radio config display** — Not shown anywhere.
- **Notification / alert on new message** — No audio or visual alert when a
  new message arrives on a non-active tab.

---

## 13. Troubleshooting

### Slow connection or hangs during node download

The app transitions to the Main Screen as soon as the initial radio handshake
completes (`connection.established`).  On very busy networks the meshtastic
library may still time out waiting for the full radio config.  Run with
`--debug` and watch the log.  If you see:

```
_waitConnected timed out but N nodes present — forcing connected state
```

or

```
waitForConfig timed out but myInfo and N nodes present — proceeding without full config
```

the transport forced a connection after a timeout.  This is usually harmless —
node records continue arriving after the transition.  If the app appears
completely stuck, quit (Ctrl+Q) and reconnect.

### Serial device detected but connection fails

1. Run with `--debug` and check `/tmp/mesheliza.log` for the full traceback.
2. Confirm permissions (section 11).
3. Try unplugging and re-plugging the USB cable.
4. Test with the meshtastic CLI: `meshtastic --port /dev/ttyUSB0 --info`

### No serial devices in the auto-scan list

The scanner filters by USB vendor ID.  Supported chips:

| Chip                | USB VID |
|---------------------|---------|
| Silicon Labs CP210x | 10C4    |
| WCH CH340 / CH341   | 1A86    |
| FTDI                | 0403    |
| Espressif USB-JTAG  | 303A    |

If your adapter uses a different chip, enter the port path manually.

### BLE scan finds no devices

- Ensure the node has BLE enabled in its firmware settings.
- Ensure the host has a working Bluetooth adapter (`hciconfig`).

### Config file ignored or reset

Verify it is valid JSON:

```
python3 -m json.tool ~/.config/mesheliza/config.json
```

If `"theme"` contains an unrecognised value, the app silently resets it to
`mesheliza-multicolor`.

---

## 14. Headless / Kiosk Operation (Raspberry Pi)

MeshEliza is designed to run as a full-screen kiosk app on a headless Pi
connected to a physical display — no desktop environment required.

### Setup

1. Configure the Pi for **console auto-login** (e.g. `raspi-config` →
   System Options → Boot / Auto Login → Console Autologin).
2. Run `install.sh` on the Pi and answer **Y** when asked about auto-launch.

The installer adds a block to `~/.bash_profile` that:

- Activates only on `tty1` (the physical console) — SSH sessions are
  unaffected.
- Sets `TERM=xterm-256color` for full colour rendering.
- Runs MeshEliza in a restart loop so it comes back automatically after an
  exit or crash.

```bash
# MeshEliza auto-launch on tty1 (physical Pi screen)
if [[ "$(tty)" == "/dev/tty1" ]]; then
    export TERM=xterm-256color
    while true; do
        /home/pi/Vibe/MeshEliza/mesheliza.sh
        sleep 2
    done
fi
```

### What happens at boot

| Step | What MeshEliza does |
|------|-------------------|
| Login shell starts | `~/.bash_profile` runs the restart loop |
| `mesheliza.sh` starts | Checks stdin/stdout are a TTY; exits with an error if not |
| Serial transport configured | Waits up to 10 s for the USB device to enumerate (handles boot timing race) |
| App launches | Connection screen appears |
| Saved device present | 5-second countdown begins; connects automatically |
| App exits for any reason | `sleep 2`, then `mesheliza.sh` restarts |

### Troubleshooting a headless Pi

If the app is not starting or behaving unexpectedly, SSH in from another
machine to investigate without disturbing the console:

```
ssh pi@<pi-hostname>
tail -f /tmp/mesheliza.log          # live log output
```

Common issues on first boot:

| Symptom | Likely cause | Fix |
|---------|-------------|-----|
| Black screen / app not starting | User not in `dialout` group | Re-run `install.sh` or `sudo usermod -aG dialout pi` then reboot |
| "Waiting for USB serial device…" then connection fails | Radio not plugged in or wrong port | Plug in radio before booting; check `dmesg \| grep tty` |
| App starts but auto-connect does not fire | No saved device in config | Connect once manually; check **Remember this device** |
| App crashes immediately | `TERM` not set or `dumb` | Ensure the `~/.bash_profile` block sets `TERM=xterm-256color` |
