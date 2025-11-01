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


@dataclass
class AppConfig:
    """Main application configuration"""

    version: str = "2.1"

    # Chains
    chains: List[ChainConfig] = field(default_factory=list)

    # Server
    server: ServerConfig = field(default_factory=ServerConfig)

    # Paths
    ini_dir: Path = field(default_factory=lambda: Path.cwd())
    ini_file: str = ""
    log_file: str = ""
    pid_file: str = ""
    explorer_name: str = ""

    # Legacy settings (for backward compatibility)
    settings: Optional[Dict] = None

    # Action
    action: Optional[str] = None

    def __post_init__(self) -> None:
        """Initialize derived fields"""
        if isinstance(self.ini_dir, str):
            self.ini_dir = Path(self.ini_dir)

        if not self.log_file and self.explorer_name:
            self.log_file = str(self.ini_dir / f"{self.explorer_name}.log")

        if not self.pid_file and self.explorer_name:
            self.pid_file = str(self.ini_dir / f"{self.explorer_name}.pid")

    def get_chain(self, name: str) -> Optional[ChainConfig]:
        """Get chain configuration by name"""
        for chain in self.chains:
            if chain.name == name or chain.path_name == name:
                return chain
        return None

    def add_chain(self, chain: ChainConfig) -> None:
        """Add a chain configuration"""
        self.chains.append(chain)

    @property
    def chain_names(self) -> List[str]:
        """Get list of chain names"""
        return [chain.name for chain in self.chains]


def load_env_file(env_path: Optional[str] = None) -> bool:
    """Load environment variables from .env file"""
    try:
        from dotenv import load_dotenv

        if env_path:
            load_dotenv(env_path)
        else:
            # Try to find .env in current directory or parent
            load_dotenv()

        return True
    except ImportError:
        # python-dotenv not installed
        return False


def create_example_env() -> str:
    """Create an example .env file"""
    example_content = """# MultiChain Explorer 2 - Environment Configuration
# Copy this file to .env and customize

# Server Configuration
MCE_HOST=0.0.0.0
MCE_PORT=4444
MCE_BASE_URL=/

# Logging
MCE_LOG_LEVEL=INFO

# Development
MCE_DEBUG=False
MCE_RELOAD=False
"""
    return example_content


# Singleton instance (for backward compatibility)
_current_config: Optional[AppConfig] = None


def get_config() -> Optional[AppConfig]:
    """Get the current application configuration"""
    return _current_config


def set_config(config: AppConfig) -> None:
    """Set the current application configuration"""
    global _current_config
    _current_config = config


def reset_config() -> None:
    """Reset configuration (useful for testing)"""
    global _current_config
    _current_config = None
