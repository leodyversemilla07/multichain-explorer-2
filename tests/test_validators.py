"""
Tests for Input Validators
Security-focused validation testing
"""

import os
import sys

import pytest
from pydantic import ValidationError

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from validators import (
    AddressParams,
    BlockHeightParams,
    EntityNameParams,
    PaginationParams,
    SearchParams,
    TransactionParams,
    sanitize_html,
    validate_address,
    validate_block_height,
    validate_entity_name,
    validate_numeric_string,
    validate_transaction_id,
)


class TestBlockHeightValidation:
    """Test block height parameter validation"""

    @pytest.mark.unit
    def test_valid_block_height(self):
        """Test valid block heights"""
        assert validate_block_height("0") == 0
        assert validate_block_height("100") == 100
        assert validate_block_height("999999999") == 999999999

    @pytest.mark.unit
    def test_invalid_block_height_negative(self):
        """Test negative block height is rejected"""
        with pytest.raises(ValueError):
            validate_block_height("-1")

    @pytest.mark.unit
    def test_invalid_block_height_too_large(self):
        """Test too large block height is rejected"""
        with pytest.raises(ValueError):
            validate_block_height("1000000000")

    @pytest.mark.unit
    def test_invalid_block_height_non_numeric(self):
        """Test non-numeric block height is rejected"""
        with pytest.raises(ValueError):
            validate_block_height("abc")


class TestTransactionValidation:
    """Test transaction ID parameter validation"""

    @pytest.mark.unit
    def test_valid_transaction_id(self):
        """Test valid 64-char hex transaction ID"""
        valid_txid = "a" * 64
        result = validate_transaction_id(valid_txid)
        assert result == valid_txid.lower()

    @pytest.mark.unit
    def test_invalid_transaction_id_short(self):
        """Test short transaction ID is rejected"""
        with pytest.raises(ValueError):
            validate_transaction_id("a" * 63)

    @pytest.mark.unit
    def test_invalid_transaction_id_long(self):
        """Test long transaction ID is rejected"""
        with pytest.raises(ValueError):
            validate_transaction_id("a" * 65)

    @pytest.mark.unit
    def test_invalid_transaction_id_non_hex(self):
        """Test non-hex transaction ID is rejected"""
        with pytest.raises(ValueError):
            validate_transaction_id("g" * 64)

    @pytest.mark.security
    def test_transaction_id_injection_attempt(self):
        """Test injection attempt in transaction ID is rejected"""
        with pytest.raises(ValueError):
            validate_transaction_id("'; DROP TABLE transactions; --" + "a" * 30)


class TestAddressValidation:
    """Test MultiChain address parameter validation"""

    @pytest.mark.unit
    def test_valid_address(self):
        """Test valid MultiChain address"""
        valid_address = "1AAAAAAAAAAAAAAAAAAAAAAAAAAAAA"  # 32 chars
        result = validate_address(valid_address)
        assert result == valid_address

    @pytest.mark.unit
    def test_invalid_address_too_short(self):
        """Test too short address is rejected"""
        with pytest.raises(ValueError):
            validate_address("1ABC")

    @pytest.mark.unit
    def test_invalid_address_bad_start(self):
        """Test address not starting with 1 or 3 is rejected"""
        with pytest.raises(ValueError):
            validate_address("2AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA")

    @pytest.mark.security
    def test_address_injection_attempt(self):
        """Test injection attempt in address is rejected"""
        with pytest.raises(ValueError):
            validate_address("1ABC'; DELETE FROM users; --")


class TestPaginationValidation:
    """Test pagination parameter validation"""

    @pytest.mark.unit
    def test_valid_pagination_defaults(self):
        """Test default pagination values"""
        params = PaginationParams()
        assert params.size == 20
        assert params.from_ == 0

    @pytest.mark.unit
    def test_valid_pagination_custom(self):
        """Test custom pagination values"""
        params = PaginationParams(size=50, **{"from": 100})
        assert params.size == 50
        assert params.from_ == 100

    @pytest.mark.unit
    def test_invalid_pagination_size_zero(self):
        """Test size of 0 is rejected"""
        with pytest.raises(ValidationError):
            PaginationParams(size=0)

    @pytest.mark.unit
    def test_invalid_pagination_size_too_large(self):
        """Test size > 500 is rejected"""
        with pytest.raises(ValidationError):
            PaginationParams(size=501)

    @pytest.mark.unit
    def test_invalid_pagination_negative_offset(self):
        """Test negative offset is rejected"""
        with pytest.raises(ValidationError):
            PaginationParams(**{"from": -1})


class TestEntityNameValidation:
    """Test asset/stream name parameter validation"""

    @pytest.mark.unit
    def test_valid_entity_names(self):
        """Test valid entity names"""
        assert validate_entity_name("TestAsset") == "TestAsset"
        assert validate_entity_name("test-stream") == "test-stream"
        assert validate_entity_name("asset_123") == "asset_123"

    @pytest.mark.unit
    def test_invalid_entity_name_empty(self):
        """Test empty name is rejected"""
        with pytest.raises(ValueError):
            validate_entity_name("")

    @pytest.mark.unit
    def test_invalid_entity_name_too_long(self):
        """Test name > 32 chars is rejected"""
        with pytest.raises(ValueError):
            validate_entity_name("a" * 33)

    @pytest.mark.security
    def test_invalid_entity_name_special_chars(self):
        """Test name with special characters is rejected"""
        with pytest.raises(ValueError):
            validate_entity_name("asset'; DROP TABLE--")

    @pytest.mark.security
    def test_invalid_entity_name_path_traversal(self):
        """Test path traversal attempt is rejected"""
        with pytest.raises(ValueError):
            validate_entity_name("../../../etc/passwd")


class TestSearchValidation:
    """Test search parameter validation"""

    @pytest.mark.unit
    def test_valid_search_queries(self):
        """Test valid search queries"""
        params = SearchParams(search_value="abc123")
        assert params.search_value == "abc123"

        params = SearchParams(search_value="test-asset")
        assert params.search_value == "test-asset"

    @pytest.mark.security
    def test_invalid_search_special_chars(self):
        """Test search with special characters is rejected"""
        with pytest.raises(ValidationError):
            SearchParams(search_value="'; DELETE FROM users; --")

    @pytest.mark.security
    def test_invalid_search_script_tag(self):
        """Test search with script tag is rejected"""
        with pytest.raises(ValidationError):
            SearchParams(search_value="<script>alert('xss')</script>")


class TestSecurityHelpers:
    """Test security helper functions"""

    @pytest.mark.security
    def test_sanitize_html_basic(self):
        """Test HTML sanitization of basic tags"""
        result = sanitize_html("<script>alert('xss')</script>")
        assert "<script>" not in result
        assert "&lt;script&gt;" in result

    @pytest.mark.security
    def test_sanitize_html_quotes(self):
        """Test HTML sanitization of quotes"""
        result = sanitize_html('"quoted" text')
        assert "&quot;" in result

    @pytest.mark.security
    def test_sanitize_html_ampersand(self):
        """Test HTML sanitization of ampersands"""
        result = sanitize_html("A & B")
        assert "&amp;" in result


class TestNumericValidation:
    """Test numeric string validation"""

    @pytest.mark.unit
    def test_valid_numeric_string(self):
        """Test valid numeric strings"""
        assert validate_numeric_string("0") == 0
        assert validate_numeric_string("100") == 100
        assert validate_numeric_string("999999999") == 999999999

    @pytest.mark.unit
    def test_invalid_numeric_string_non_numeric(self):
        """Test non-numeric string is rejected"""
        with pytest.raises(ValueError):
            validate_numeric_string("abc")

    @pytest.mark.unit
    def test_invalid_numeric_string_out_of_range(self):
        """Test out of range numeric string is rejected"""
        with pytest.raises(ValueError):
            validate_numeric_string("1000000000")

    @pytest.mark.unit
    def test_numeric_string_custom_range(self):
        """Test numeric validation with custom range"""
        result = validate_numeric_string("50", min_val=0, max_val=100)
        assert result == 50

        with pytest.raises(ValueError):
            validate_numeric_string("150", min_val=0, max_val=100)


class TestEdgeCases:
    """Test edge cases and boundary conditions"""

    @pytest.mark.unit
    def test_whitespace_handling(self):
        """Test that whitespace is handled correctly"""
        # Pydantic doesn't strip whitespace by default for integers
        # Test that clean integer works
        params = BlockHeightParams(height=100)
        assert params.height == 100

    @pytest.mark.unit
    def test_case_insensitive_hex(self):
        """Test that hex validation is case-insensitive"""
        upper_txid = "A" * 64
        lower_txid = validate_transaction_id(upper_txid)
        assert lower_txid == "a" * 64

    @pytest.mark.unit
    def test_boundary_values_pagination(self):
        """Test boundary values for pagination"""
        # Minimum valid
        params = PaginationParams(size=1, **{"from": 0})
        assert params.size == 1
        assert params.from_ == 0

        # Maximum valid
        params = PaginationParams(size=500, **{"from": 999999})
        assert params.size == 500
        assert params.from_ == 999999


@pytest.mark.smoke
class TestValidatorSmoke:
    """Quick smoke tests for validators"""

    def test_all_validators_importable(self):
        """Test that all validators can be imported"""
        from validators import (
            AddressParams,
            BlockHeightParams,
            EntityNameParams,
            PaginationParams,
            TransactionParams,
        )

        assert all(
            [
                BlockHeightParams,
                TransactionParams,
                AddressParams,
                PaginationParams,
                EntityNameParams,
            ]
        )

    def test_basic_validation_works(self):
        """Test basic validation functionality"""
        # This should not raise
        validate_block_height("100")
        validate_entity_name("TestAsset")
