"""NodeDetailModal — full telemetry display for a single node."""

from __future__ import annotations

from datetime import datetime

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import ScrollableContainer, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Label, Static


def _fmt(val, suffix: str = "", na: str = "—") -> str:
    return f"{val}{suffix}" if val is not None else na


def _fmt_ts(ts) -> str:
    if not ts:
        return "—"
    try:
        return datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S")
    except (OSError, ValueError, OverflowError):
        return "—"


class NodeDetailModal(ModalScreen):
    """Shows all available info for a single mesh node."""

    BINDINGS = [
        Binding("escape", "dismiss", "Close"),
        Binding("q", "dismiss", "Close"),
    ]

    DEFAULT_CSS = """
    NodeDetailModal {
        align: center middle;
    }
    #modal-container {
        width: 60;
        height: auto;
        max-height: 80vh;
        border: round $primary;
        background: $surface;
        padding: 1 2;
    }
    #modal-container Label {
        padding: 0 0 1 0;
    }
    .field-label {
        color: $text-muted;
    }
    .field-value {
        padding: 0 0 0 2;
    }
    #close-btn {
        margin-top: 1;
        min-height: 3;
        width: 100%;
    }
    """

    def __init__(self, node_id: str, node_info: dict) -> None:
        super().__init__()
        self._node_id = node_id
        self._info = node_info

    def compose(self) -> ComposeResult:
        info = self._info
        with Vertical(id="modal-container"):
            yield Label(
                f"Node: {info.get('short_name') or self._node_id}",
                id="modal-title",
            )
            with ScrollableContainer():
                yield Label("Identity", classes="field-label")
                yield Static(
                    f"  ID:         {self._node_id}\n"
                    f"  Short name: {_fmt(info.get('short_name'))}\n"
                    f"  Long name:  {_fmt(info.get('long_name'))}\n"
                    f"  HW model:   {_fmt(info.get('hw_model'))}",
                    classes="field-value",
                )
                yield Label("Signal", classes="field-label")
                yield Static(
                    f"  SNR:        {_fmt(info.get('last_snr'), ' dB')}\n"
                    f"  Last heard: {_fmt_ts(info.get('last_heard'))}",
                    classes="field-value",
                )
                yield Label("Power", classes="field-label")
                yield Static(
                    f"  Battery:    {_fmt(info.get('battery'), '%')}",
                    classes="field-value",
                )
                yield Label("Position", classes="field-label")
                lat = info.get("last_lat")
                lon = info.get("last_lon")
                alt = info.get("last_alt")
                pos_str = (
                    f"  Lat:        {_fmt(lat, '°')}\n"
                    f"  Lon:        {_fmt(lon, '°')}\n"
                    f"  Alt:        {_fmt(alt, ' m')}"
                )
                yield Static(pos_str, classes="field-value")
            yield Button("Close", id="close-btn", variant="default")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "close-btn":
            self.dismiss()
