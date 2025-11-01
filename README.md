# MultiChain Explorer 2

**Version:** 2.0.0  
**License:** BSD-3-Clause  
**Python:** 3.8+

A modern, web-based explorer for MultiChain blockchains with a clean architecture, comprehensive testing, and professional UI.

---

## 📋 Table of Contents

- [Features](#features)
- [Quick Start](#quick-start)
- [Installation](#installation)
- [Configuration](#configuration)
- [Running the Server](#running-the-server)
- [Development](#development)
- [Architecture](#architecture)
- [Testing](#testing)
- [Project Structure](#project-structure)
- [Contributing](#contributing)
- [License](#license)

---

## ✨ Features

- **Multi-Chain Support** - Browse multiple MultiChain blockchains from a single interface
- **Comprehensive Explorer** - View blocks, transactions, addresses, assets, streams, and permissions
- **Modern UI** - Clean, responsive interface built with TailwindCSS and AlpineJS
- **Real-time Search** - Live search and filtering across all entity types
- **Clean Architecture** - Modular handler system with separated concerns
- **Type-Safe** - Input validation with Pydantic
- **Well-Tested** - 283+ tests with 100% pass rate
- **Production-Ready** - Security hardening, error handling, and performance optimizations

---

## 🚀 Quick Start

### Prerequisites

- Python 3.8 or higher
- Access to one or more MultiChain nodes (local or remote)
- MultiChain RPC credentials

### Basic Installation

```bash
# 1. Clone the repository
git clone https://github.com/MultiChain/multichain-explorer-2.git
cd multichain-explorer-2

# 2. Install dependencies
pip install -r requirements.txt

# 3. Copy and configure the example config file
cp example.ini multichain.ini
# Edit multichain.ini with your MultiChain node details

# 4. Start the explorer
python main.py multichain.ini
```

The explorer will be available at `http://localhost:4444` (or the port specified in your config).

---

## 📦 Installation

### Option 1: Standard Installation

```bash
# Install production dependencies
pip install -r requirements.txt
```

### Option 2: Development Installation

```bash
# Install both production and development dependencies
pip install -r requirements-dev.txt

# Set up pre-commit hooks (recommended for contributors)
pre-commit install
```

### Option 3: Using pip (from source)

```bash
# Install in editable mode
pip install -e .

# Or with development dependencies
pip install -e ".[dev]"
```

---

## ⚙️ Configuration

### Configuration File

Create a configuration file (e.g., `multichain.ini`) based on `example.ini`:

```ini
[main]
# Network settings
host=localhost        # Use 0.0.0.0 to accept connections from anywhere
port=4444            # Web server port

# Optional: URL prefix for all links (default: /)
# base=/explorer/

[chains]
# Enable/disable chains
chain1=on
chain2=off

[chain1]
# Chain display name
name=My MultiChain

# RPC connection settings
# For remote nodes, specify all RPC settings:
# rpchost=http://123.45.67.89
# rpcport=8000
# rpcuser=multichainrpc
# rpcpassword=your-secure-password

# For local nodes, specify datadir (credentials auto-detected):
datadir=~/.multichain/chain1

[chain2]
name=Another Chain
# ... additional chain configuration
```

### Configuration Parameters

#### Main Section

| Parameter | Description | Default | Required |
|-----------|-------------|---------|----------|
| `host` | Server bind address | `localhost` | No |
| `port` | Server port | `4444` | No |
| `base` | URL prefix for links | `/` | No |
| `debug` | Enable debug mode | `false` | No |

#### Chain Section

| Parameter | Description | Default | Required |
|-----------|-------------|---------|----------|
| `name` | Display name for the chain | - | Yes |
| `rpchost` | RPC server URL (with scheme) | `http://127.0.0.1` | No* |
| `rpcport` | RPC server port | Auto-detected | No* |
| `rpcuser` | RPC username | Auto-detected | No* |
| `rpcpassword` | RPC password | Auto-detected | No* |
| `datadir` | MultiChain data directory | `~/.multichain` | No* |

\* For **local nodes**, only `datadir` is needed (RPC credentials auto-detected).  
\* For **remote nodes**, all RPC parameters (`rpchost`, `rpcport`, `rpcuser`, `rpcpassword`) are required.

---

## 🏃 Running the Server

### Standard Mode

Start the server in the foreground:

```bash
python main.py multichain.ini
```

Access the explorer at `http://localhost:4444` (or your configured host/port).

Press `Ctrl+C` to stop the server.

### Daemon Mode

Start the server as a background daemon:

```bash
# Start in background
python main.py multichain.ini daemon

# Check status
python main.py multichain.ini status

# Stop the daemon
python main.py multichain.ini stop
```

### Alternative Entry Points

You can also run the server directly using:

```bash
# Using http_server.py (recommended for development)
python http_server.py

# This requires the configuration to be loaded first
```

### Server Options

```bash
# Show usage information
python main.py

# Start with a specific config file
python main.py /path/to/config.ini

# Start as daemon
python main.py multichain.ini daemon

# Check if running
python main.py multichain.ini status

# Stop daemon
python main.py multichain.ini stop
```

### Logs

Server logs are written to:
- Console output (stdout)
- `explorer.log` file in the working directory

---

## 🛠️ Development

### Setting Up Development Environment

```bash
# 1. Install development dependencies
pip install -r requirements-dev.txt

# 2. Set up pre-commit hooks
pre-commit install

# 3. Run tests to verify setup
pytest

# 4. Check code formatting
black --check .
isort --check .
flake8 .
```

### Development Workflow

1. **Make changes** to code
2. **Run tests** to ensure nothing breaks:
   ```bash
   pytest
   ```
3. **Format code** (auto-formatted by pre-commit):
   ```bash
   black .
   isort .
   ```
4. **Check types** (optional):
   ```bash
   mypy .
   ```
5. **Commit** - pre-commit hooks will run automatically

### Code Quality Tools

| Tool | Purpose | Command |
|------|---------|---------|
| **pytest** | Run tests | `pytest` |
| **black** | Code formatting | `black .` |
| **isort** | Import sorting | `isort .` |
| **flake8** | Linting | `flake8 .` |
| **mypy** | Type checking | `mypy .` |
| **pre-commit** | Git hooks | `pre-commit run --all-files` |

### Running Development Server

For development, you can run the server with debug mode enabled:

```ini
# In your config file
[main]
debug=true
```

This will:
- Show detailed error messages
- Log more verbose output
- Disable some caching

---

## 🏗️ Architecture

MultiChain Explorer 2 follows a clean, modular architecture:

```
┌─────────────────┐
│  HTTP Server    │  ← http_server.py (Modern HTTPServer)
└────────┬────────┘
         │
┌────────▼────────┐
│   Routing       │  ← routing.py (URL routing & dispatch)
└────────┬────────┘
         │
┌────────▼────────┐
│   Handlers      │  ← handlers/ (Specialized request handlers)
├─────────────────┤
│ • BlockHandler  │  ← Block operations
│ • TxHandler     │  ← Transaction operations
│ • AddrHandler   │  ← Address operations
│ • AssetHandler  │  ← Asset operations
│ • StreamHandler │  ← Stream operations
│ • ChainHandler  │  ← Chain info
│ • PermHandler   │  ← Permissions
└────────┬────────┘
         │
┌────────▼────────┐
│   Services      │  ← services/ (Business logic)
├─────────────────┤
│ • Blockchain    │  ← RPC abstraction
│ • Cache         │  ← Response caching
│ • Formatting    │  ← Data transformation
│ • Pagination    │  ← List pagination
└────────┬────────┘
         │
┌────────▼────────┐
│   Templates     │  ← templates/ (Jinja2 + TailwindCSS)
└─────────────────┘
```

### Key Components

- **`http_server.py`** - Modern HTTP server with static file serving
- **`routing.py`** - URL routing and request dispatching
- **`handlers/`** - Specialized request handlers (7 handlers)
- **`services/`** - Business logic and data services (4 services)
- **`templates/`** - Jinja2 templates with TailwindCSS
- **`validators.py`** - Input validation with Pydantic
- **`config.py`** - Type-safe configuration management
- **`exceptions.py`** - Centralized error handling

See [handlers/README.md](handlers/README.md) for detailed handler documentation.

---

## 🧪 Testing

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage report
pytest --cov=. --cov-report=html

# Run specific test file
pytest tests/test_handlers.py

# Run specific test
pytest tests/test_handlers.py::test_block_handler

# Run with verbose output
pytest -v

# Run tests matching a pattern
pytest -k "handler"
```

### Test Structure

```
tests/
├── test_config.py              # Configuration tests
├── test_validators.py          # Input validation tests
├── test_exceptions.py          # Error handling tests
├── test_handlers.py            # BaseHandler tests
├── test_specialized_handlers.py # Handler-specific tests
├── test_services.py            # Service layer tests
├── test_routing.py             # Routing tests
├── test_template_engine.py     # Template tests
├── test_integration.py         # End-to-end tests
└── mocks/                      # Test fixtures & mocks
```

### Test Coverage

- **283+ tests** with **100% pass rate**
- Comprehensive coverage of:
  - Input validation and security
  - Configuration management
  - Error handling
  - Handler operations
  - Service layer
  - Template rendering
  - Integration scenarios

### Running Specific Test Categories

```bash
# Run unit tests only
pytest -m unit

# Run integration tests only
pytest -m integration

# Run security tests only
pytest -m security
```

---

## 📁 Project Structure

```
multichain-explorer-2/
├── main.py                  # Main entry point
├── http_server.py           # HTTP server implementation
├── routing.py               # URL routing
├── app.py                   # Application setup
├── app_state.py             # Global state management
├── config.py                # Configuration management
├── validators.py            # Input validation
├── exceptions.py            # Error handling
├── template_engine.py       # Template rendering
├── multichain.py            # MultiChain RPC client
├── utils.py                 # Utility functions
│
├── handlers/                # Request handlers
│   ├── __init__.py
│   ├── README.md           # Handler documentation
│   ├── base.py             # BaseHandler (common functionality)
│   ├── block_handler.py    # Block operations
│   ├── transaction_handler.py
│   ├── address_handler.py
│   ├── asset_handler.py
│   ├── stream_handler.py
│   ├── chain_handler.py
│   └── permission_handler.py
│
├── services/                # Business logic services
│   ├── __init__.py
│   ├── blockchain_service.py   # RPC abstraction
│   ├── cache_service.py        # Caching
│   ├── formatting_service.py   # Data formatting
│   └── pagination_service.py   # Pagination
│
├── templates/               # Jinja2 templates
│   ├── base.html
│   ├── components/         # Reusable components
│   │   ├── header.html
│   │   ├── footer.html
│   │   ├── pagination.html
│   │   └── search.html
│   └── pages/              # Page templates
│       ├── chain_home.html
│       ├── blocks.html
│       ├── block.html
│       ├── transactions.html
│       └── ...
│
├── static/                  # Static assets
│   ├── css/
│   ├── js/
│   └── images/
│
├── tests/                   # Test suite
│   ├── conftest.py
│   ├── test_*.py
│   └── mocks/
│
├── requirements.txt         # Production dependencies
├── requirements-dev.txt     # Development dependencies
├── pyproject.toml          # Project configuration
├── pytest.ini              # Pytest configuration
├── example.ini             # Example configuration
├── LICENSE.txt             # BSD-3-Clause license
├── ARCHITECTURE_ROADMAP.md # Development roadmap
└── README.md               # This file
```

---

## 🤝 Contributing

We welcome contributions! Here's how to get started:

### 1. Fork & Clone

```bash
git clone https://github.com/YOUR_USERNAME/multichain-explorer-2.git
cd multichain-explorer-2
```

### 2. Set Up Development Environment

```bash
pip install -r requirements-dev.txt
pre-commit install
```

### 3. Create a Branch

```bash
git checkout -b feature/my-new-feature
```

### 4. Make Changes

- Follow the existing code style
- Add tests for new features
- Update documentation as needed

### 5. Run Tests

```bash
# Run all tests
pytest

# Check code formatting
black --check .
isort --check .
flake8 .
```

### 6. Commit & Push

```bash
git add .
git commit -m "Add my new feature"
git push origin feature/my-new-feature
```

### 7. Create Pull Request

Open a pull request on GitHub with a clear description of your changes.

### Code Style Guidelines

- **Python**: Follow PEP 8 (enforced by Black and flake8)
- **Line length**: 100 characters (Black default)
- **Imports**: Sorted with isort
- **Type hints**: Encouraged but not required
- **Docstrings**: Use Google-style docstrings
- **Tests**: Required for all new features

---

## 📊 Current Status

**Phase 3 COMPLETE** ✅

- ✅ **283 tests** (100% passing)
- ✅ **Handler decomposition** complete (7 specialized handlers)
- ✅ **Service layer** implemented (4 services)
- ✅ **Modern routing** system
- ✅ **Template integration** for all core pages
- ✅ **Clean architecture** with separated concerns
- ✅ **Production-grade security** with input validation
- ✅ **Type-safe configuration** management

See [ARCHITECTURE_ROADMAP.md](ARCHITECTURE_ROADMAP.md) for detailed progress and future plans.

---

## 📖 Additional Documentation

- **[Handler Documentation](handlers/README.md)** - Detailed handler architecture and usage
- **[Architecture Roadmap](ARCHITECTURE_ROADMAP.md)** - Development phases and progress
- **[Example Configuration](example.ini)** - Sample configuration file with comments

---

## 🐛 Troubleshooting

### Common Issues

#### Server won't start

```bash
# Check if another instance is running
python main.py multichain.ini status

# Stop existing instance
python main.py multichain.ini stop

# Check port availability
# Windows PowerShell:
netstat -ano | findstr :4444
```

#### Can't connect to MultiChain node

1. Verify MultiChain node is running
2. Check RPC credentials in config file
3. For local nodes, verify `datadir` path
4. For remote nodes, check firewall settings

#### Import errors

```bash
# Reinstall dependencies
pip install -r requirements.txt --force-reinstall
```

#### Tests failing

```bash
# Clear pytest cache
pytest --cache-clear

# Run with verbose output
pytest -v -s
```

---

## 📄 License

Copyright (c) Coin Sciences Ltd

All rights reserved under the **BSD-3-Clause** license.

See [LICENSE.txt](LICENSE.txt) for the full license text.

---

## 🔗 Links

- **MultiChain**: https://www.multichain.com/
- **Documentation**: https://www.multichain.com/developers/
- **GitHub**: https://github.com/MultiChain/multichain-explorer-2
- **Support**: https://www.multichain.com/contact/

---

## 👥 Authors

**Coin Sciences Ltd** - MultiChain creators and maintainers

---

## 🙏 Acknowledgments

- Built with Python 3.8+
- Powered by MultiChain blockchain platform
- UI styled with TailwindCSS
- Interactive components with AlpineJS
- Template engine using Jinja2
- Validation with Pydantic
- Testing with pytest

---

**Happy Exploring! 🚀**
