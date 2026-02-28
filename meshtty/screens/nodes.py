"""NodeListView — live DataTable of all mesh nodes."""

from __future__ import annotations

from textual import work
from textual.app import ComposeResult
from textual.widget import Widget

from meshtty.messages.app_messages import NodeUpdated
from meshtty.widgets.node_table import NodeTable


class NodeListView(Widget):
    """Displays all mesh nodes in a live-updating table."""

    DEFAULT_CSS = """
    NodeListView {
        height: 1fr;
        layout: vertical;
    }
    """

    def compose(self) -> ComposeResult:
        yield NodeTable(id="node-table")

    def on_mount(self) -> None:
        self._load_nodes()

    def on_node_updated(self, event: NodeUpdated) -> None:
        try:
            table = self.query_one("#node-table", NodeTable)
            table.upsert_node(event.node_id, event.node_info)
            self._save_node(event.node_id, event.node_info)
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Workers
    # ------------------------------------------------------------------

    @work(thread=True, name="load-nodes", exit_on_error=False)
    def _load_nodes(self) -> None:
        transport = self.app.transport
        if transport is None:
            return
        nodes = transport.get_nodes()
        self.app.call_from_thread(self._apply_nodes, nodes)

    def _apply_nodes(self, nodes: dict) -> None:
        self.query_one("#node-table", NodeTable).populate(nodes)

    @work(thread=True, name="save-node", exit_on_error=False)
    def _save_node(self, node_id: str, info: dict) -> None:
        self.app.db.upsert_node(node_id, info)
