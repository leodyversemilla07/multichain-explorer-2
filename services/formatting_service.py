"""
Formatting service - Data transformation and formatting utilities.

Provides consistent formatting for common data types (hashes, amounts,
timestamps, etc.) used throughout the application.
"""

import hashlib
from datetime import datetime
from typing import Any, Optional, Union


class FormattingService:
    """Service for formatting and transforming data for display."""

    @staticmethod
    def format_hash(hash_value: str, length: int = 16) -> str:
        """
        Format a hash for display (truncate with ellipsis).

        Args:
            hash_value: Full hash string
            length: Number of characters to show (default: 16)

        Returns:
            Formatted hash string (e.g., "abc123...def789")
        """
        if not hash_value or len(hash_value) <= length:
            return hash_value

        half = length // 2
        return f"{hash_value[:half]}...{hash_value[-half:]}"

    @staticmethod
    def format_amount(amount: Union[int, float], decimals: int = 8, symbol: str = "") -> str:
        """
        Format an amount with proper decimal places.

        Args:
            amount: Numeric amount
            decimals: Number of decimal places
            symbol: Optional currency symbol

        Returns:
            Formatted amount string
        """
        if isinstance(amount, (int, float)):
            formatted = f"{amount:.{decimals}f}".rstrip("0").rstrip(".")
            return f"{formatted} {symbol}".strip()
        return str(amount)

    @staticmethod
    def format_timestamp(timestamp: Union[int, float], fmt: str = "%Y-%m-%d %H:%M:%S") -> str:
        """
        Format a Unix timestamp.

        Args:
            timestamp: Unix timestamp
            fmt: strftime format string

        Returns:
            Formatted datetime string
        """
        try:
            dt = datetime.fromtimestamp(timestamp)
            return dt.strftime(fmt)
        except (ValueError, OSError, TypeError):
            return str(timestamp)

    @staticmethod
    def format_relative_time(timestamp: Union[int, float]) -> str:
        """
        Format timestamp as relative time (e.g., "5 minutes ago").

        Args:
            timestamp: Unix timestamp

        Returns:
            Human-readable relative time string
        """
        try:
            dt = datetime.fromtimestamp(timestamp)
            now = datetime.now()
            diff = now - dt

            seconds = diff.total_seconds()

            if seconds < 60:
                return f"{int(seconds)} seconds ago"
            elif seconds < 3600:
                return f"{int(seconds / 60)} minutes ago"
            elif seconds < 86400:
                return f"{int(seconds / 3600)} hours ago"
            elif seconds < 2592000:  # 30 days
                return f"{int(seconds / 86400)} days ago"
            elif seconds < 31536000:  # 365 days
                return f"{int(seconds / 2592000)} months ago"
            else:
                return f"{int(seconds / 31536000)} years ago"
        except (ValueError, OSError, TypeError):
            return str(timestamp)

    @staticmethod
    def format_bytes(size: int, binary: bool = True) -> str:
        """
        Format byte size in human-readable format.

        Args:
            size: Size in bytes
            binary: Use binary (1024) or decimal (1000) units

        Returns:
            Formatted size string (e.g., "1.5 MB")
        """
        base = 1024 if binary else 1000
        units = (
            ["B", "KB", "MB", "GB", "TB", "PB"]
            if not binary
            else ["B", "KiB", "MiB", "GiB", "TiB", "PiB"]
        )

        if size < base:
            return f"{size} {units[0]}"

        for unit in units[1:]:
            size /= base
            if size < base:
                return f"{size:.2f} {unit}"

        return f"{size:.2f} {units[-1]}"

    @staticmethod
    def format_number(number: Union[int, float], separator: str = ",") -> str:
        """
        Format a number with thousand separators.

        Args:
            number: Number to format
            separator: Separator character (default: comma)

        Returns:
            Formatted number string
        """
        if isinstance(number, float):
            return f"{number:,.2f}".replace(",", separator)
        return f"{number:,}".replace(",", separator)

    @staticmethod
    def format_address(address: str, length: int = 20) -> str:
        """
        Format an address for display.

        Args:
            address: Full address string
            length: Number of characters to show

        Returns:
            Formatted address string
        """
        if not address or len(address) <= length:
            return address

        half = length // 2
        return f"{address[:half]}...{address[-half:]}"

    @staticmethod
    def format_percentage(value: float, decimals: int = 2) -> str:
        """
        Format a percentage value.

        Args:
            value: Percentage value (0-100)
            decimals: Number of decimal places

        Returns:
            Formatted percentage string
        """
        return f"{value:.{decimals}f}%"

    @staticmethod
    def truncate_string(text: str, max_length: int = 100, suffix: str = "...") -> str:
        """
        Truncate a string to a maximum length.

        Args:
            text: Text to truncate
            max_length: Maximum length
            suffix: Suffix to add when truncated

        Returns:
            Truncated string
        """
        if len(text) <= max_length:
            return text
        return text[: max_length - len(suffix)] + suffix

    @staticmethod
    def sanitize_html(text: str) -> str:
        """
        Basic HTML sanitization (for display purposes).

        Args:
            text: Text that may contain HTML

        Returns:
            Sanitized text with HTML entities escaped
        """
        return (
            str(text)
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
            .replace("'", "&#x27;")
        )

    @staticmethod
    def calculate_hash(data: str, algorithm: str = "sha256") -> str:
        """
        Calculate hash of data.

        Args:
            data: Data to hash
            algorithm: Hash algorithm (sha256, md5, etc.)

        Returns:
            Hex digest of hash
        """
        hash_obj = hashlib.new(algorithm)
        hash_obj.update(data.encode("utf-8"))
        return hash_obj.hexdigest()

    @staticmethod
    def format_confirmations(confirmations: int) -> str:
        """
        Format confirmation count with appropriate context.

        Args:
            confirmations: Number of confirmations

        Returns:
            Formatted string
        """
        if confirmations == 0:
            return "Unconfirmed"
        elif confirmations == 1:
            return "1 confirmation"
        else:
            return f"{confirmations:,} confirmations"
