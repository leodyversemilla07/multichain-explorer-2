"""Compatibility-only legacy MultiChain RPC wrapper.

This top-level module is a stable compatibility shim. The implementation
now lives in `compat.legacy_multichain`.
"""

import sys

from compat import legacy_multichain as _impl

_impl.__doc__ = __doc__
sys.modules[__name__] = _impl
