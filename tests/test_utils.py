"""
Tests for utils.py - Utility functions.
"""

import os
import tempfile
from unittest.mock import patch, Mock

import pytest

import app_state


class TestFileOperations:
    """Test file operation utilities."""

    def test_file_write_and_read(self):
        """Test file_write and file_read functions."""
        from utils import file_write, file_read

        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt") as f:
            temp_path = f.name

        try:
            # Write to file
            result = file_write(temp_path, "test content")
            assert result is True

            # Read from file
            content = file_read(temp_path)
            assert content == "test content"
        finally:
            os.unlink(temp_path)

    def test_file_write_append(self):
        """Test file_write with append mode."""
        from utils import file_write, file_read

        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt") as f:
            temp_path = f.name

        try:
            file_write(temp_path, "first\n")
            file_write(temp_path, "second\n", append=True)

            content = file_read(temp_path)
            assert "first" in content
            assert "second" in content
        finally:
            os.unlink(temp_path)

    def test_file_read_nonexistent(self):
        """Test file_read with nonexistent file."""
        from utils import file_read

        result = file_read("/nonexistent/path/file.txt")
        assert result is None

    def test_file_exists(self):
        """Test file_exists function."""
        from utils import file_exists

        with tempfile.NamedTemporaryFile(delete=False) as f:
            temp_path = f.name

        try:
            assert file_exists(temp_path) is True
            assert file_exists("/nonexistent/file.txt") is False
        finally:
            os.unlink(temp_path)

    def test_remove_file(self):
        """Test remove_file function."""
        from utils import remove_file, file_exists

        with tempfile.NamedTemporaryFile(delete=False) as f:
            temp_path = f.name

        assert file_exists(temp_path) is True
        remove_file(temp_path)
        assert file_exists(temp_path) is False

    def test_remove_file_nonexistent(self):
        """Test remove_file with nonexistent file (should not raise)."""
        from utils import remove_file

        # Should not raise an exception
        remove_file("/nonexistent/path/file.txt")


class TestDirectoryOperations:
    """Test directory operation utilities."""

    def test_check_directory_creates_dir(self):
        """Test check_directory creates directory if not exists."""
        from utils import check_directory, directory_exists

        with tempfile.TemporaryDirectory() as temp_dir:
            new_dir = os.path.join(temp_dir, "new_subdir")

            assert directory_exists(new_dir) is False
            result = check_directory(new_dir)
            assert result is True
            assert directory_exists(new_dir) is True

    def test_check_directory_existing(self):
        """Test check_directory with existing directory."""
        from utils import check_directory

        with tempfile.TemporaryDirectory() as temp_dir:
            result = check_directory(temp_dir)
            assert result is True

    def test_directory_exists(self):
        """Test directory_exists function."""
        from utils import directory_exists

        with tempfile.TemporaryDirectory() as temp_dir:
            assert directory_exists(temp_dir) is True
            assert directory_exists("/nonexistent/directory") is False

    def test_full_dir_name(self):
        """Test full_dir_name function."""
        from utils import full_dir_name

        # Test trailing slash handling
        result = full_dir_name("/path/to/dir")
        assert result.endswith("/")

        result = full_dir_name("/path/to/dir/")
        assert result.endswith("/")
        assert not result.endswith("//")

    def test_full_dir_name_expands_tilde(self):
        """Test full_dir_name expands ~."""
        from utils import full_dir_name

        result = full_dir_name("~/mydir")
        assert "~" not in result
        assert result.endswith("/")

    def test_file_dir_name(self):
        """Test file_dir_name function."""
        from utils import file_dir_name
        import os

        # Use a real path that works on the current OS
        if os.name == "nt":  # Windows
            result = file_dir_name("C:\\path\\to\\file.txt")
            assert result.endswith("\\to/") or result.endswith("/to/")
        else:
            result = file_dir_name("/path/to/file.txt")
            assert result == "/path/to/"

    def test_file_file_name(self):
        """Test file_file_name function."""
        from utils import file_file_name

        result = file_file_name("/path/to/file.txt")
        assert result == "file.txt"


class TestBinaryOperations:
    """Test binary data utilities."""

    def test_bytes_to_hex(self):
        """Test bytes_to_hex conversion."""
        from utils import bytes_to_hex

        result = bytes_to_hex(b"\xde\xad\xbe\xef")
        assert result == "deadbeef"

        result = bytes_to_hex(b"\x00\x01\x02\x03")
        assert result == "00010203"

    def test_bytes_to_int32(self):
        """Test bytes_to_int32 conversion."""
        from utils import bytes_to_int32
        import struct

        # Create bytes for integer 12345
        data = struct.pack("i", 12345)
        result = bytes_to_int32(data)
        assert result == 12345

    def test_bytes_to_int64(self):
        """Test bytes_to_int64 conversion."""
        from utils import bytes_to_int64
        import struct

        # Create bytes for large integer
        large_num = 9876543210
        data = struct.pack("q", large_num)
        result = bytes_to_int64(data)
        assert result == large_num

    def test_str_to_int8(self):
        """Test str_to_int8 conversion."""
        from utils import str_to_int8

        result = str_to_int8("A")
        assert result == 65  # ASCII code for 'A'


class TestHelperFunctions:
    """Test miscellaneous helper functions."""

    def test_is_true_positive_cases(self):
        """Test is_true with positive cases."""
        from utils import is_true

        assert is_true("on") is True
        assert is_true("ON") is True
        assert is_true("yes") is True
        assert is_true("YES") is True
        assert is_true("true") is True
        assert is_true("TRUE") is True
        assert is_true("True") is True

    def test_is_true_negative_cases(self):
        """Test is_true with negative cases."""
        from utils import is_true

        assert is_true("off") is False
        assert is_true("no") is False
        assert is_true("false") is False
        assert is_true("0") is False
        assert is_true("") is False
        assert is_true("random") is False

    def test_is_printable_ascii(self):
        """Test is_printable with printable ASCII."""
        from utils import is_printable

        assert is_printable("Hello World!") is True
        assert is_printable("123 abc") is True
        assert is_printable("test@example.com") is True

    def test_is_printable_non_ascii(self):
        """Test is_printable with non-printable characters."""
        from utils import is_printable

        assert is_printable("Hello\x00World") is False  # Null byte
        assert is_printable("Test\x1b[31m") is False  # ANSI escape

    def test_print_error(self, capsys):
        """Test print_error outputs to stderr."""
        from utils import print_error

        print_error("test error message")
        captured = capsys.readouterr()
        assert "test error message" in captured.err

    def test_get_pid(self):
        """Test get_pid returns current process ID."""
        from utils import get_pid

        pid = get_pid()
        assert pid == os.getpid()
        assert isinstance(pid, int)
        assert pid > 0


class TestProcessOperations:
    """Test process-related utilities."""

    def test_is_process_running_current(self):
        """Test is_process_running with current process."""
        from utils import is_process_running

        current_pid = os.getpid()
        assert is_process_running(current_pid) is True

    def test_is_process_running_nonexistent(self):
        """Test is_process_running with nonexistent process."""
        from utils import is_process_running

        # Use a very high PID that likely doesn't exist
        assert is_process_running(999999999) is False

    def test_kill_process_nonexistent(self):
        """Test kill_process with nonexistent process."""
        from utils import kill_process

        # Should return False for nonexistent process
        result = kill_process(999999999)
        assert result is False


class TestLogging:
    """Test logging utilities."""

    def test_log_write(self):
        """Test log_write function."""
        from utils import log_write, file_read

        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".log") as f:
            temp_log = f.name

        try:
            # Set up app_state with log file
            app_state.get_state().log_file = temp_log

            log_write("test log message")

            content = file_read(temp_log)
            assert "test log message" in content
            # Should include timestamp
            assert "-" in content  # Date format includes dashes
        finally:
            os.unlink(temp_log)

    def test_log_error(self):
        """Test log_error function."""
        from utils import log_error, file_read

        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".log") as f:
            temp_log = f.name

        try:
            app_state.get_state().log_file = temp_log

            log_error("test error")

            content = file_read(temp_log)
            assert "ERROR:" in content
            assert "test error" in content
        finally:
            os.unlink(temp_log)


class TestFilePointerOperations:
    """Test file pointer read/write utilities."""

    def test_read_write_file_ptr(self):
        """Test read_file_ptr and write_file_ptr functions."""
        from utils import read_file_ptr, write_file_ptr, remove_file

        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".ptr") as f:
            temp_ptr = f.name

        try:
            config = {"ptr": temp_ptr}

            # Initial read should return (0, 0)
            ptr = read_file_ptr(config)
            assert ptr == (0, 0)

            # Write a pointer
            write_file_ptr(config, (10, 500))

            # Read it back
            ptr = read_file_ptr(config)
            assert ptr == (10, 500)
        finally:
            remove_file(temp_ptr)

    def test_read_file_ptr_nonexistent(self):
        """Test read_file_ptr with nonexistent file."""
        from utils import read_file_ptr

        config = {"ptr": "/nonexistent/file.ptr"}
        ptr = read_file_ptr(config)
        assert ptr == (0, 0)
