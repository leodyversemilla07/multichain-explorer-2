"""Tests for performance.py utilities."""

from unittest.mock import patch

import pytest


class TestCompressResponse:
    """Test gzip compression behavior."""

    def test_module_docstring_marks_compatibility_only(self):
        """The legacy utility module should describe itself as compatibility-only."""
        import performance

        assert performance.__doc__ is not None
        assert "Compatibility-only" in performance.__doc__

    def test_small_response_is_not_compressed(self):
        """Small payloads should bypass compression."""
        from performance import compress_response

        content = b"small payload"
        result, compressed = compress_response(content, min_size=1024)

        assert result == content
        assert compressed is False

    def test_large_response_is_compressed_when_smaller(self):
        """Large compressible payloads should return gzip output."""
        from performance import compress_response

        content = b"a" * 4096
        result, compressed = compress_response(content, min_size=32)

        assert compressed is True
        assert len(result) < len(content)

    def test_compression_failure_returns_original_content(self):
        """Compression fallback should return the original payload."""
        from performance import compress_response

        content = b"a" * 4096
        with patch("performance.gzip.compress", side_effect=OSError("gzip failed")):
            result, compressed = compress_response(content, min_size=32)

        assert result == content
        assert compressed is False


class TestRequestTimer:
    """Test request timing/logging behavior."""

    def test_request_timer_logs_slow_requests(self):
        """Slow requests should log at warning level."""
        from performance import RequestTimer

        with (
            patch("performance.time.time", side_effect=[0.0, 1.0]),
            patch("performance.logger.warning") as mock_warning,
        ):
            with RequestTimer("/test-path"):
                pass

        mock_warning.assert_called_once()
        assert "/test-path" in mock_warning.call_args[0][0]

    def test_request_timer_does_not_suppress_exceptions(self):
        """Timer context manager should not swallow exceptions from the body."""
        from performance import RequestTimer

        with pytest.raises(RuntimeError):
            with RequestTimer("/test-path"):
                raise RuntimeError("boom")


class TestPerformanceStats:
    """Test performance stats logging helpers."""

    def test_log_performance_stats_supports_fractional_hit_rate(self):
        """Fallback hit-rate formatting should support 0..1 provider values."""
        from performance import log_performance_stats

        fake_cache = type(
            "FakeCache",
            (),
            {
                "get_stats": lambda self: {
                    "hits": 2,
                    "misses": 1,
                    "hit_rate": 2 / 3,
                    "size": 5,
                }
            },
        )()

        with (
            patch("performance.get_cache", return_value=fake_cache),
            patch("performance.logger.info") as mock_info,
        ):
            log_performance_stats()

        logged_lines = [call.args[0] for call in mock_info.call_args_list]
        assert any("66.67%" in line for line in logged_lines)
