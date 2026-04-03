"""Compatibility-only legacy performance/cache utilities.

This top-level module is a stable compatibility shim. The implementation
now lives in `compat.legacy_performance`.
"""

import sys

from compat import legacy_performance as _impl

_impl.__doc__ = __doc__
sys.modules[__name__] = _impl
