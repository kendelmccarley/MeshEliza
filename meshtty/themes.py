from textual.theme import Theme

THEME_MULTICOLOR = Theme(
    name="mesheliza-multicolor",
    dark=True,
    background="#0D0D12",
    surface="#16161F",
    panel="#1E1E2E",
    primary="#7AA2F7",
    secondary="#BB9AF7",
    accent="#FF79C6",
    success="#9ECE6A",
    warning="#E0AF68",
    error="#F7768E",
    variables={"text-muted": "#565F89"},
)

THEME_PHOSPHOR = Theme(
    name="mesheliza-phosphor",
    dark=True,
    background="#000000",
    surface="#050F05",
    panel="#071007",
    primary="#33FF33",
    secondary="#00CC00",
    accent="#66FF66",
    success="#00FF00",
    warning="#AAFF00",
    error="#FF2200",
    variables={"text-muted": "#1A6B1A"},
)

THEME_BW = Theme(
    name="mesheliza-bw",
    dark=True,
    background="#000000",
    surface="#0F0F0F",
    panel="#1A1A1A",
    primary="#FFFFFF",
    secondary="#BBBBBB",
    accent="#FFFFFF",
    success="#DDDDDD",
    warning="#999999",
    error="#666666",
    variables={"text-muted": "#555555"},
)

ALL_THEMES = [THEME_MULTICOLOR, THEME_PHOSPHOR, THEME_BW]
