import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pingMonitor import MonitorApp


class TestGetStatusInfo:
    """Tests for _get_status_info static method."""

    def test_online_true(self):
        """Test when device is online."""
        text, color = MonitorApp._get_status_info(True)
        assert text == "Online"
        assert color == "green"

    def test_online_false(self):
        """Test when device is offline."""
        text, color = MonitorApp._get_status_info(False)
        assert text == "Offline"
        assert color == "red"

    def test_online_none(self):
        """Test when device status is unknown."""
        text, color = MonitorApp._get_status_info(None)
        assert text == "Unknown"
        assert color == "gray"


class TestFormatLatency:
    """Tests for _format_latency static method."""

    def test_with_value(self):
        """Test formatting latency with a value."""
        assert MonitorApp._format_latency(100.0) == "100 ms"
        assert MonitorApp._format_latency(0.0) == "0 ms"
        assert MonitorApp._format_latency(50.5) == "50 ms"

    def test_with_none(self):
        """Test formatting latency with None."""
        assert MonitorApp._format_latency(None) == ""

    def test_with_negative(self):
        """Test formatting negative latency (edge case)."""
        assert MonitorApp._format_latency(-1.0) == "-1 ms"
