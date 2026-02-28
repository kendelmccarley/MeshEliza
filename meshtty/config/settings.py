import json
from dataclasses import asdict, dataclass, field
from pathlib import Path

CONFIG_DIR = Path.home() / ".config" / "mesheliza"
CONFIG_FILE = CONFIG_DIR / "config.json"


@dataclass
class AppConfig:
    default_transport: str = "serial"       # "serial" | "tcp" | "ble"
    last_serial_port: str = ""
    last_tcp_host: str = ""
    last_tcp_port: int = 4403
    last_ble_address: str = ""
    auto_connect: bool = True
    log_level: str = "WARNING"
    db_path: str = field(
        default_factory=lambda: str(Path.home() / ".config" / "mesheliza" / "messages.db")
    )
    node_short_name_display: bool = True
    theme: str = "mesheliza-multicolor"


def load_config() -> AppConfig:
    if not CONFIG_FILE.exists():
        return AppConfig()
    try:
        with CONFIG_FILE.open() as f:
            data = json.load(f)
        valid_keys = AppConfig.__dataclass_fields__.keys()
        return AppConfig(**{k: v for k, v in data.items() if k in valid_keys})
    except (json.JSONDecodeError, TypeError):
        return AppConfig()


def save_config(cfg: AppConfig) -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    with CONFIG_FILE.open("w") as f:
        json.dump(asdict(cfg), f, indent=2)
