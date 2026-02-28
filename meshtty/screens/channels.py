"""ChannelView — channels tab showing configured mesh channels."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.widget import Widget
from textual.widgets import Label, ListItem, ListView, TabbedContent

from meshtty.screens.messages import MessagesView
from meshtty.widgets.compose_bar import ComposeBar


class ChannelView(Widget):
    """Tab showing configured channels; click one to set compose target."""

    DEFAULT_CSS = """
    ChannelView {
        height: 1fr;
        padding: 1 2;
    }
    ChannelView #channel-list {
        height: 1fr;
        margin-top: 1;
    }
    ChannelView ListItem {
        height: 3;
        padding: 0 1;
    }
    """

    def compose(self) -> ComposeResult:
        yield Label("Channels", classes="section-header")
        yield ListView(id="channel-list")

    def on_mount(self) -> None:
        self._populate()

    def on_show(self) -> None:
        self._populate()

    def on_connection_established(self, event) -> None:
        try:
            self._populate()
        except Exception:
            pass

    def _populate(self) -> None:
        try:
            transport = self.app.transport
            channels = transport.get_channels() if transport else [(0, "Primary")]
            lv = self.query_one("#channel-list", ListView)
            lv.clear()
            for idx, name in channels:
                lv.append(ListItem(Label(f"{name}  (ch {idx})", markup=False), id=f"ch-{idx}"))
        except Exception:
            pass

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        try:
            item_id = event.item.id or ""
            if not item_id.startswith("ch-"):
                return
            ch_idx = int(item_id.split("-")[1])
            transport = self.app.transport
            channels = transport.get_channels() if transport else [(0, "Primary")]
            name = next((n for i, n in channels if i == ch_idx), f"Ch {ch_idx}")
            try:
                msgs = self.app.query_one("#messages-view", MessagesView)
                msgs.query_one(ComposeBar).set_prefix(name)
            except Exception:
                pass
            try:
                self.app.query_one("#main-tabs", TabbedContent).active = "tab-messages"
            except Exception:
                pass
        except (IndexError, ValueError, Exception):
            pass
