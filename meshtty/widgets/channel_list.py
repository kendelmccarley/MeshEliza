"""ChannelList — sidebar list of mesh channels."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.message import Message
from textual.widget import Widget
from textual.widgets import Label, ListView, ListItem


class ChannelList(Widget):
    """Displays configured channels and fires ChannelSelected on click."""

    class ChannelSelected(Message, bubble=False):
        def __init__(self, channel_index: int) -> None:
            self.channel_index = channel_index
            super().__init__()

    DEFAULT_CSS = """
    ChannelList {
        width: 18;
        height: 1fr;
        border-right: solid $primary;
        background: $panel;
    }
    ChannelList Label {
        padding: 0 1;
        color: $text-muted;
    }
    ChannelList ListView {
        height: 1fr;
    }
    """

    def compose(self) -> ComposeResult:
        yield Label("Channels")
        yield ListView(id="channel-listview")

    def on_mount(self) -> None:
        """Populate with channels actually configured on the radio."""
        transport = self.app.transport
        channels = transport.get_channels() if transport else [(0, "Primary")]
        lv = self.query_one("#channel-listview", ListView)
        for idx, name in channels:
            lv.append(ListItem(Label(f"  {name}"), id=f"ch-{idx}"))

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        item_id = event.item.id or ""
        if item_id.startswith("ch-"):
            try:
                ch = int(item_id.split("-")[1])
                self.post_message(self.ChannelSelected(ch))
            except (IndexError, ValueError):
                pass
