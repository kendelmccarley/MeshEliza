"""NodeTable — DataTable wrapper showing all mesh nodes."""

from __future__ import annotations

from datetime import datetime

from textual.app import ComposeResult
from textual.widget import Widget
from textual.widgets import DataTable


def _fmt_snr(snr) -> str:
    return f"{snr:.1f} dB" if snr is not None else "—"


def _fmt_battery(bat) -> str:
    return f"{bat}%" if bat is not None else "—"


def _fmt_coords(lat, lon) -> str:
    if lat is None or lon is None:
        return "—"
    return f"{lat:.4f}, {lon:.4f}"


def _fmt_last_heard(ts) -> str:
    if not ts:
        return "—"
    try:
        return datetime.fromtimestamp(ts).strftime("%H:%M:%S")
    except (OSError, ValueError, OverflowError):
        return "—"


COLUMNS = [
    ("Short", "short"),
    ("Long Name", "long"),
    ("SNR", "snr"),
    ("Last Heard", "heard"),
    ("Battery", "bat"),
    ("Position", "pos"),
    ("HW Model", "hw"),
]


class NodeTable(Widget):
    """Displays all mesh nodes in a sortable DataTable."""

    DEFAULT_CSS = """
    NodeTable {
        height: 1fr;
    }
    NodeTable DataTable {
        height: 1fr;
    }
    """

    def compose(self) -> ComposeResult:
        table = DataTable(id="node-datatable", cursor_type="row")
        for label, key in COLUMNS:
            table.add_column(label, key=key)
        yield table

    def upsert_node(self, node_id: str, info: dict) -> None:
        table = self.query_one("#node-datatable", DataTable)
        use_short = self.app.config.node_short_name_display
        row_values = (
            info.get("short_name") or node_id,
            info.get("long_name") or "",
            _fmt_snr(info.get("last_snr")),
            _fmt_last_heard(info.get("last_heard")),
            _fmt_battery(info.get("battery")),
            _fmt_coords(info.get("last_lat"), info.get("last_lon")),
            info.get("hw_model") or "",
        )
        try:
            # Update existing row
            for col_idx, (_, col_key) in enumerate(COLUMNS):
                table.update_cell(node_id, col_key, row_values[col_idx])
        except Exception:
            try:
                # Row doesn't exist yet — add it
                table.add_row(*row_values, key=node_id)
            except Exception:
                # Row was added concurrently; ignore
                pass

    def populate(self, nodes: dict) -> None:
        """Bulk-populate from transport.get_nodes() dict."""
        for node_id, node in nodes.items():
            user = node.get("user", {})
            pos = node.get("position", {})
            metrics = node.get("deviceMetrics", {})
            info = {
                "short_name": user.get("shortName", ""),
                "long_name": user.get("longName", ""),
                "hw_model": user.get("hwModel", ""),
                "last_snr": node.get("snr"),
                "last_lat": pos.get("latitude"),
                "last_lon": pos.get("longitude"),
                "last_alt": pos.get("altitude"),
                "battery": metrics.get("batteryLevel"),
                "last_heard": node.get("lastHeard"),
            }
            self.upsert_node(str(node_id), info)
