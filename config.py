"""
MultiChain Explorer 2 - Type-Safe Configuration
Replaces global state with proper configuration management
"""

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class ChainConfig:
    """Configuration for a single MultiChain blockchain"""

    name: str
    display_name: str
    path_name: str
    ini_name: str

    # RPC Configuration
    rpc_host: str = "127.0.0.1"
    rpc_port: int = 0
    rpc_user: str = ""
    rpc_password: str = ""

    # Optional
    datadir: Optional[str] = None
    native_flag: bool = False

    # Generated fields (populated during initialization)
    multichain_url: str = field(default="", init=False)
    multichain_headers: Dict[str, str] = field(default_factory=dict, init=False)
    config: Dict[str, Any] = field(default_factory=dict, init=False)

    def __post_init__(self) -> None:
        """Initialize derived fields"""
        if not self.multichain_url:
            self.multichain_url = f"http://{self.rpc_host}:{self.rpc_port}"

        if not self.multichain_headers:
            import base64

            auth_string = f"{self.rpc_user}:{self.rpc_password}"
            auth_bytes = auth_string.encode("utf-8")
            auth_b64 = base64.b64encode(auth_bytes).decode("utf-8")

            self.multichain_headers = {
                "Content-Type": "application/json",
                "Connection": "close",
                "Authorization": f"Basic {auth_b64}",
            }

        # Build config dict for backward compatibility
        if not self.config:
            self.config = {
                "name": self.name,
                "display-name": self.display_name,
                "path-name": self.path_name,
                "ini-name": self.ini_name,
                "path-ini-name": self.ini_name,
                "multichain-url": self.multichain_url,
                "multichain-headers": self.multichain_headers,
                "native-flag": self.native_flag,
            }


@dataclass
class ServerConfig:
    """HTTP server configuration"""

    host: str = "127.0.0.1"
    port: int = 4444
    base_url: str = "/"

    # Environment overrides
    @classmethod
    def from_env(cls, config_dict: Optional[Dict] = None) -> "ServerConfig":
        """Create from environment variables with optional base config"""
        config_dict = config_dict or {}

        return cls(
            host=os.getenv("MCE_HOST", config_dict.get("host", cls.host)),
            port=int(os.getenv("MCE_PORT", config_dict.get("port", cls.port))),
            base_url=os.getenv("MCE_BASE_URL", config_dict.get("base", cls.base_url)),
        )


