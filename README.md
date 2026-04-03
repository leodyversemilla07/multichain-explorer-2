# MultiChain Explorer 2

**Version:** 2.1.0  
**License:** BSD-3-Clause  
**Python:** 3.9+  
**Framework:** FastAPI + Uvicorn

A modern, web-based explorer for MultiChain blockchains with a clean architecture, comprehensive testing, and professional UI. **Now powered by FastAPI** for async performance and modern API design.

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
- **FastAPI Powered** - Async performance with modern Python web framework
- **Auto-Generated API Docs** - Interactive Swagger UI at `/docs`
- **Clean Architecture** - Modular HTML/API routers with shared services and dependencies
- **Type-Safe** - Input validation with Pydantic and FastAPI
- **Well-Tested** - 375 automated tests passing locally
- **Production-Ready** - Security hardening, error handling, and performance optimizations

---

## 🚀 Quick Start

### Prerequisites

- Python 3.8 or higher
- Access to a MultiChain node (local or remote)
- MultiChain RPC credentials

### Basic Installation

```bash
# 1. Clone the repository
git clone https://github.com/MultiChain/multichain-explorer-2.git
cd multichain-explorer-2

# 2. Install dependencies
pip install -r requirements.txt

# 3. Copy and configure the .env file
cp .env.example .env
# Edit .env with your MultiChain node details

# 4. Start the explorer
python main.py

# Or using uvicorn directly (recommended for production)
uvicorn main:app --host 0.0.0.0 --port 8080
```

The explorer will be available at `http://localhost:8080`.

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

### Environment Variables

Configuration is managed through a `.env` file. Copy `.env.example` to `.env` and customize:

```bash
cp .env.example .env
```

### Configuration File (.env)

```env
# MultiChain Node Connection
MULTICHAIN_CHAIN_NAME=mychain
MULTICHAIN_RPC_HOST=127.0.0.1
MULTICHAIN_RPC_PORT=8000
MULTICHAIN_RPC_USERNAME=multichainrpc
MULTICHAIN_RPC_PASSWORD=your_rpc_password_here

# Explorer Settings
EXPLORER_HOST=127.0.0.1
EXPLORER_PORT=8080
DEBUG=false
```

### Configuration Parameters

| Variable | Description | Default |
|----------|-------------|---------|
| `MULTICHAIN_CHAIN_NAME` | Name of the blockchain | `chain1` |
| `MULTICHAIN_RPC_HOST` | MultiChain RPC host | `127.0.0.1` |
| `MULTICHAIN_RPC_PORT` | MultiChain RPC port | `8000` |
| `MULTICHAIN_RPC_USERNAME` | RPC username | `multichainrpc` |
| `MULTICHAIN_RPC_PASSWORD` | RPC password | (required) |
| `EXPLORER_HOST` | Explorer bind address | `127.0.0.1` |
| `EXPLORER_PORT` | Explorer web port | `8080` |
| `DEBUG` | Enable debug/reload | `false` |
| `BASE_URL` | URL prefix for reverse proxy | `/` |

---

## 🏃 Running the Server

### Starting the Server

Start the server using Uvicorn:

```bash
# Development mode with auto-reload
uvicorn main:app --reload --port 8080

# Production mode
uvicorn main:app --host 0.0.0.0 --port 8080 --workers 4

# Using the built-in CLI
python main.py --port 8080 --reload
python main.py --host 0.0.0.0 --port 8080
```

Access the explorer at `http://localhost:8080`

Press `Ctrl+C` to stop the server.

**Additional endpoints:**
- **API Documentation:** `http://localhost:8080/docs` (Swagger UI)
- **Alternative Docs:** `http://localhost:8080/redoc` (ReDoc)

### CLI Options

The `main.py` supports the following command-line options:

```bash
python main.py [OPTIONS]

Options:
  --host HOST       Host to bind to (default: 127.0.0.1)
  --port PORT       Port to bind to (default: 8080)
  --reload          Enable auto-reload for development
  --config FILE     Reserved for compatibility; `.env` is the supported configuration source
```

### Production Deployment

For production environments, use Uvicorn with multiple workers:

```bash
uvicorn main:app --host 0.0.0.0 --port 8080 --workers 4
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

```env
# In your .env file
DEBUG=true
```

This will:
- Show detailed error messages
- Log more verbose output
- Disable some caching

---

## 🏗️ Architecture

MultiChain Explorer 2 follows a clean, modular architecture powered by **FastAPI**:

```
┌─────────────────┐
│   Uvicorn       │  ← ASGI server
└────────┬────────┘
         │
┌────────▼────────┐
│   FastAPI App   │  ← main.py
└────────┬────────┘
         │
┌────────▼────────┐
│  HTML Routers   │  ← routers/*.py
├─────────────────┤
│  API Routers    │  ← routers/api/*.py
└────────┬────────┘
         │
┌────────▼────────┐
│ Shared Services │  ← blockchain, cache, pagination, search
└────────┬────────┘
         │
┌────────▼────────┐
│ MultiChain RPC  │
└─────────────────┘
```

### Key Components

- **`main.py`** - FastAPI application with routers, middleware, startup, and exception handlers
- **`routers/`** - Server-rendered HTML routes and dependency injection helpers
- **`routers/api/`** - JSON API endpoints under `/api/v1`
- **`services/`** - Shared RPC, cache, pagination, formatting, and search services
- **Legacy `/chain/...` routes** - Supported compatibility URLs with dedicated regression coverage
- **`ACTIVE_ARCHITECTURE.md`** - Current runtime architecture and active-path notes
- **`COMPATIBILITY_BOUNDARY.md`** - Compatibility surface and compatibility-only module policy
- **`templates/`** - Jinja2 templates with TailwindCSS
- **`validators.py`** - Input validation with Pydantic
- **`config.py`** - Type-safe configuration management
- **`exceptions.py`** - Centralized error handling

---

## 🧪 Testing

### Running Tests

```bash
# Run all tests
pytest

# Run a single test module
pytest tests/test_api_routers.py

# Run a single test
pytest tests/test_main.py::TestHealthEndpoint::test_health_check_returns_200

# Run tests matching a pattern
pytest -k "search"
```

### Test Structure

```
tests/
├── test_api_routers.py         # JSON API route coverage
├── test_routers.py             # HTML route coverage
├── test_main.py                # App factory and system routes
├── test_services.py            # Service layer tests
├── test_cache_service.py       # Cache providers and decorator behavior
├── test_config.py              # Dataclass config tests
├── test_env_config.py          # Environment settings tests
├── test_dependencies.py        # FastAPI dependency tests
├── test_exceptions.py          # Error handling tests
├── test_models.py              # Domain model tests
├── test_multichain.py          # Legacy RPC client tests
├── test_utils.py               # Utility tests
└── test_validators.py          # Input validation tests
```

### Test Coverage

- The repo includes targeted coverage for the active FastAPI runtime path and separate regression coverage for compatibility surfaces.
- Comprehensive coverage of:
  - Input validation and security
  - Configuration management
  - Error handling
  - Router behavior
  - Service layer
  - Startup and dependency injection
  - Template-backed HTML views
  - Legacy `/chain/...` compatibility routes
  - Architecture boundary enforcement for compatibility-only modules

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
├── main.py                  # FastAPI application (single entry point)
├── app_state.py             # Global state management
├── config.py                # Configuration dataclasses
├── env_config.py            # Environment-backed settings loader
├── validators.py            # Input validation helpers
├── exceptions.py            # Error handling
├── multichain.py            # Compatibility-only legacy RPC client
├── performance.py           # Compatibility-only utility surface
├── utils.py                 # Utility functions
├── ACTIVE_ARCHITECTURE.md   # Current active runtime path
├── COMPATIBILITY_BOUNDARY.md # Compatibility policy and boundaries
│
├── routers/                 # FastAPI routers
│   ├── __init__.py
│   ├── dependencies.py      # Dependency injection
│   ├── chains.py            # Chain routes
│   ├── blocks.py            # Block routes
│   ├── transactions.py      # Transaction routes
│   ├── addresses.py         # Address routes
│   ├── assets.py            # Asset routes
│   ├── streams.py           # Stream routes
│   ├── permissions.py       # Permission routes
│   ├── search.py            # Search routes
│   └── api/                 # JSON API routes
│
├── services/                # Business logic services
│   ├── __init__.py
│   ├── blockchain_service.py   # RPC abstraction
│   ├── cache_service.py        # Caching
│   ├── formatting_service.py   # Data formatting
│   ├── pagination_service.py   # Pagination helpers
│   └── search_service.py       # Shared search logic
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
├── pyproject.toml           # Packaging / tool configuration
├── pytest.ini              # Pytest configuration
├── .env.example            # Example environment configuration
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

**Current snapshot**

- ✅ **375 tests** passing locally
- ✅ **Server-rendered HTML routes** and **JSON API routes**
- ✅ **Shared service layer** for RPC, cache, pagination, and search
- ✅ **Template integration** for core explorer pages
- ✅ **Production-focused middleware** for rate limiting, CORS, and trusted hosts
- ✅ **Type-safe configuration** management

See [ARCHITECTURE_ROADMAP.md](ARCHITECTURE_ROADMAP.md) for detailed progress and future plans.

---

## 📖 Additional Documentation

- **[Architecture Roadmap](ARCHITECTURE_ROADMAP.md)** - Development phases and progress
- **[.env.example](.env.example)** - Sample environment configuration

---

## 🐛 Troubleshooting

### Common Issues

#### Server won't start

```bash
# Check if port is in use
# Windows PowerShell:
netstat -ano | findstr :8080

# Kill process using the port (replace PID)
taskkill /PID <pid> /F

# Linux/Mac:
lsof -i :8080
kill -9 <pid>
```

#### Can't connect to MultiChain node

1. Verify MultiChain node is running
2. Check RPC credentials in `.env`
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
