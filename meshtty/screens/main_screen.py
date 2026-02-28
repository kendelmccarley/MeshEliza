"""MainScreen — primary hub screen with TabbedContent."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.binding import Binding
from textual.screen import Screen
from textual.widgets import TabbedContent, TabPane

from meshtty.messages.app_messages import (
    ConnectionEstablished,
    ConnectionLost,
    NodeUpdated,
    TextMessageReceived,
)
from meshtty.screens.messages import MessagesView
from meshtty.screens.node_detail import NodeDetailModal
from meshtty.screens.nodes import NodeListView
from meshtty.screens.settings import SettingsView


class MainScreen(Screen):
    """Primary application screen."""

    BINDINGS = [
        Binding("ctrl+q", "app.quit", "Quit"),
        Binding("ctrl+d", "app.disconnect", "Disconnect"),
        Binding("ctrl+r", "refresh_nodes", "Refresh"),
        Binding("ctrl+t", "switch_tab('tab-messages')", "Messages", priority=True),
        Binding("ctrl+n", "switch_tab('tab-nodes')", "Nodes", priority=True),
        Binding("ctrl+s", "switch_tab('tab-settings')", "Settings", priority=True),
    ]

    def compose(self) -> ComposeResult:
        with TabbedContent(id="main-tabs", initial="tab-messages"):
            with TabPane("Messages", id="tab-messages"):
                yield MessagesView(id="messages-view")
            with TabPane("Nodes", id="tab-nodes"):
                yield NodeListView(id="nodes-view")
            with TabPane("Settings", id="tab-settings"):
                yield SettingsView(id="settings-view")

    def on_mount(self) -> None:
        pass

    # ------------------------------------------------------------------
    # App message handlers (routed from MeshElizaApp)
    # ------------------------------------------------------------------

    def on_connection_established(self, event: ConnectionEstablished) -> None:
        try:
            self.query_one("#settings-view", SettingsView).post_message(event)
        except Exception:
            pass

    def on_connection_lost(self, event: ConnectionLost) -> None:
        try:
            self.query_one("#settings-view", SettingsView).post_message(event)
        except Exception:
            pass

    def on_text_message_received(self, event: TextMessageReceived) -> None:
        try:
            self.query_one("#messages-view", MessagesView).post_message(event)
        except Exception:
            pass

    def on_node_updated(self, event: NodeUpdated) -> None:
        try:
            self.query_one("#settings-view", SettingsView).post_message(event)
        except Exception:
            pass
        try:
            self.query_one("#nodes-view", NodeListView).post_message(event)
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Row selection on the node table → push detail modal
    # ------------------------------------------------------------------

    def on_data_table_row_selected(self, event) -> None:
        try:
            node_id = str(event.row_key.value) if event.row_key else None
            if not node_id:
                return
            transport = self.app.transport
            if transport is None:
                return
            nodes = transport.get_nodes()
            node = nodes.get(node_id, {})
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
            self.app.push_screen(NodeDetailModal(node_id, info))
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    def action_switch_tab(self, tab_id: str) -> None:
        tc = self.query_one("#main-tabs", TabbedContent)
        tc.active = tab_id
        try:
            if tab_id == "tab-messages":
                self.query_one("#compose-input").focus()
            elif tab_id == "tab-nodes":
                self.query_one("DataTable").focus()
            elif tab_id == "tab-settings":
                self.query_one("#settings-view").focus()
        except Exception:
            pass

    def action_refresh_nodes(self) -> None:
        try:
            nodes_view = self.query_one("#nodes-view", NodeListView)
            nodes_view._load_nodes()
        except Exception:
            pass
