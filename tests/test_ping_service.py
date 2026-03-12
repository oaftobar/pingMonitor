import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ping_service import is_valid_ip


class TestIsValidIP:
    """Tests for is_valid_ip function."""

    def test_valid_ipv4_addresses(self):
        """Test valid IPv4 addresses."""
        assert is_valid_ip("192.168.1.1") is True
        assert is_valid_ip("10.0.0.1") is True
        assert is_valid_ip("255.255.255.255") is True
        assert is_valid_ip("0.0.0.0") is True

    def test_invalid_ipv4_addresses(self):
        """Test invalid IPv4 addresses."""
        # Out of range
        assert is_valid_ip("256.1.1.1") is False
        assert is_valid_ip("192.168.1.256") is False
        assert is_valid_ip("300.0.0.1") is False

        # Invalid format
        assert is_valid_ip("192.168.1") is False
        assert is_valid_ip("192.168.1.1.1") is False
        assert is_valid_ip("192.168.1.") is False
        assert is_valid_ip(".192.168.1.1") is False

    def test_non_ip_strings(self):
        """Test non-IP strings."""
        assert is_valid_ip("not-an-ip") is False
        assert is_valid_ip("example.com") is False
        assert is_valid_ip("") is False

    def test_whitespace(self):
        """Test whitespace handling."""
        assert is_valid_ip(" 192.168.1.1") is False
        assert is_valid_ip("192.168.1.1 ") is False
