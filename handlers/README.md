# Handlers Module

This module contains specialized request handlers for the MultiChain Explorer application.

## Overview

The handlers module implements the **Handler Pattern** to decompose the monolithic `MCEDataHandler` class into manageable, focused components. Each handler is responsible for a specific entity type or functionality.

## Architecture

```
handlers/
├── __init__.py              # Package exports
├── base.py                  # BaseHandler with common functionality
├── block_handler.py         # Block-related operations
├── transaction_handler.py   # Transaction operations
├── address_handler.py       # Address operations
├── asset_handler.py         # Asset operations
├── stream_handler.py        # Stream operations
├── chain_handler.py         # Chain information
└── permission_handler.py    # Permission operations
```

## Handler Classes

### BaseHandler
**File:** `base.py` (275 lines)

Common functionality for all handlers:
- Template rendering with fallback
- Error response generation
- JSON API responses
- Pagination logic
- URL building utilities
- Hash and amount formatting

### BlockHandler
**File:** `block_handler.py` (86 lines, 4 methods)

Handles block-related operations:
- `handle_block()` - Block detail page
- `handle_blocks()` - Block list page
- `handle_blocktransactions()` - Transactions in a block
- `handle_blocksummary()` - Block summary page

### TransactionHandler
**File:** `transaction_handler.py` (70 lines, 3 methods)

Handles transaction operations:
- `handle_tx()` - Transaction detail page
- `handle_transactions()` - Transaction list page
- `handle_rawtransaction()` - Raw transaction data

### AddressHandler
**File:** `address_handler.py` (112 lines, 5 methods)

Handles address operations:
- `handle_address()` - Address detail page
- `handle_addresses()` - Address list page
- `handle_addressstreams()` - Streams for an address
- `handle_addressassets()` - Assets owned by address
- `handle_addresstransactions()` - Address transactions

### AssetHandler
**File:** `asset_handler.py` (149 lines, 7 methods)

Handles asset operations:
- `handle_asset()` - Asset detail page
- `handle_assets()` - Asset list page
- `handle_assetissues()` - Asset issuance history
- `handle_assettransactions()` - Asset transactions
- `handle_assetholders()` - Asset holders
- `handle_assetholdertransactions()` - Holder transactions
- `handle_assetpermissions()` - Asset permissions

### StreamHandler
**File:** `stream_handler.py` (167 lines, 8 methods)

Handles stream operations:
- `handle_stream()` - Stream detail page
- `handle_streams()` - Stream list page
- `handle_streamitems()` - Items in a stream
- `handle_streamkeys()` - Keys in a stream
- `handle_streampublishers()` - Stream publishers
- `handle_keyitems()` - Items for a key
- `handle_publisheritems()` - Items from a publisher
- `handle_streampermissions()` - Stream permissions

### ChainHandler
**File:** `chain_handler.py` (90 lines, 4 methods)

Handles chain information:
- `handle_chains()` - Chain list page
- `handle_chainsummary()` - Chain summary/home page
- `handle_peers()` - Network peers
- `handle_miners()` - Miner statistics

### PermissionHandler
**File:** `permission_handler.py` (30 lines, 1 method)

Handles permission operations:
- `handle_globalpermissions()` - Global permissions page

## Usage

### Importing Handlers

```python
from handlers import (
    BlockHandler,
    TransactionHandler,
    AddressHandler,
    AssetHandler,
    StreamHandler,
    ChainHandler,
    PermissionHandler,
)
```

### Creating a Handler

```python
from handlers import BlockHandler

# Pass the MCEDataHandler instance
handler = BlockHandler(data_handler)

# Call handler methods
response = handler.handle_block(chain, params, nparams)
```

### Handler Registry Pattern

```python
from handlers import *

# Create a registry of handlers
handler_registry = {
    'block': BlockHandler(data_handler),
    'transaction': TransactionHandler(data_handler),
    'address': AddressHandler(data_handler),
    'asset': AssetHandler(data_handler),
    'stream': StreamHandler(data_handler),
    'chain': ChainHandler(data_handler),
    'permission': PermissionHandler(data_handler),
}

# Route to appropriate handler
handler_type = 'block'
handler = handler_registry[handler_type]
response = handler.handle_block(chain, params, nparams)
```

## Design Principles

### Single Responsibility
Each handler focuses on one entity type or functionality, making the code easier to understand and maintain.

### Delegation Pattern
Currently, handlers delegate to `MCEDataHandler` methods. This allows for gradual migration without breaking changes.

### Small Files
All handler files are under 200 lines, making them easy to read and navigate.

### Testability
Each handler can be independently tested with mocked dependencies.

### Backward Compatibility
Handlers maintain full backward compatibility with existing code through delegation.

## Testing

All handlers are comprehensively tested:

```bash
# Run handler tests
pytest tests/test_handlers.py -v
pytest tests/test_specialized_handlers.py -v

# Run all tests
pytest tests/ -v
```

**Test Coverage:**
- BaseHandler: 18 tests
- Specialized handlers: 28 tests
- Total: 46 tests (100% passing)

## Future Improvements

### Phase 3.2: Service Layer
Extract business logic from `MCEDataHandler` into service classes:
- `BlockchainService` - RPC abstraction
- `PaginationService` - Pagination logic
- `FormattingService` - Data transformation

### Phase 3.3: Routing
Implement declarative routing with decorators:
```python
@route('/block/<height>')
def handle_block(height: int):
    pass
```

### Phase 3.4: Domain Models
Create typed domain models for all entities:
```python
@dataclass
class Block:
    height: int
    hash: str
    timestamp: int
    transactions: List[str]
```

## Contributing

When adding new handlers:

1. Follow the existing pattern (see `block_handler.py`)
2. Keep files under 200 lines
3. Add comprehensive tests
4. Update `__init__.py` exports
5. Document methods with docstrings
6. Maintain backward compatibility

## License

Copyright (c) Coin Sciences Ltd
All rights reserved under BSD 3-clause license

## See Also

- [PHASE3.1_COMPLETE.md](../PHASE3.1_COMPLETE.md) - Phase 3.1 documentation
- [ARCHITECTURE_ROADMAP.md](../ARCHITECTURE_ROADMAP.md) - Project roadmap
- [tests/test_specialized_handlers.py](../tests/test_specialized_handlers.py) - Handler tests
