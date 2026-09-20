"""Tests for the BitwigOSCClient class"""

import unittest
from unittest.mock import MagicMock, call

import pytest

from bitwig_mcp_server.osc.client import BitwigOSCClient
from bitwig_mcp_server.osc.exceptions import InvalidParameterError


class TestBitwigOSCClient(unittest.TestCase):
    """Test cases for BitwigOSCClient"""

    def setUp(self):
        """Set up test environment"""
        self.client = BitwigOSCClient()
        self.client.client = MagicMock()  # Mock the underlying UDP client

    def test_send(self):
        """Test sending OSC messages"""
        self.client.send("/test/address", 42)
        self.client.client.send_message.assert_called_once_with("/test/address", 42)
        self.assertEqual(self.client.addr_log, ["/test/address"])

    def test_transport_controls(self):
        """Test transport control methods"""
        # Test play with different states
        self.client.play(True)
        self.client.client.send_message.assert_called_with("/play", 1)

        self.client.play(False)
        self.client.client.send_message.assert_called_with("/play", 0)

    def test_device_controls(self):
        """Test device control methods"""
        # Test toggle device bypass
        self.client.toggle_device_bypass()
        self.client.client.send_message.assert_called_with("/device/bypass", None)

        # Test select device sibling
        self.client.select_device_sibling(3)
        self.client.client.send_message.assert_called_with(
            "/device/sibling/3/select", 1
        )

        # Test select device by index
        self.client.select_device_by_index(2)
        self.client.client.send_message.assert_called_with("/device/select/2", 1)

        # Test select invalid device index
        with pytest.raises(InvalidParameterError):
            self.client.select_device_by_index(0)  # Below range

        # Test select invalid sibling
        with pytest.raises(InvalidParameterError):
            self.client.select_device_sibling(0)  # Below range
        with pytest.raises(InvalidParameterError):
            self.client.select_device_sibling(9)  # Above range

        # Test navigate device next
        self.client.navigate_device("next")
        self.client.client.send_message.assert_called_with("/device/+", None)

        # Test navigate device previous
        self.client.navigate_device("previous")
        self.client.client.send_message.assert_called_with("/device/-", None)

        # Test invalid navigation direction
        with pytest.raises(InvalidParameterError):
            self.client.navigate_device("invalid")

        # Test enter device layer
        self.client.enter_device_layer(2)
        self.client.client.send_message.assert_called_with(
            "/device/layer/2/enter", None
        )

        # Test exit device layer
        self.client.exit_device_layer()
        self.client.client.send_message.assert_called_with("/device/layer/parent", None)

        # Test toggle device window
        self.client.toggle_device_window()
        self.client.client.send_message.assert_called_with("/device/window", None)

        self.client.play()
        self.client.client.send_message.assert_called_with("/play", None)

        # Test stop
        self.client.stop()
        self.client.client.send_message.assert_called_with("/stop", 1)

        # Test tempo
        self.client.set_tempo(120.5)
        self.client.client.send_message.assert_called_with("/tempo/raw", 120.5)

        # Test tempo clamping
        self.client.set_tempo(1200)
        self.client.client.send_message.assert_called_with("/tempo/raw", 999)

    def test_track_controls(self):
        """Test track control methods"""
        # Test volume
        self.client.set_track_volume(1, 64)
        self.client.client.send_message.assert_called_with("/track/1/volume", 64)

        # Test pan
        self.client.set_track_pan(2, 32)
        self.client.client.send_message.assert_called_with("/track/2/pan", 32)

        # Test mute
        self.client.set_track_mute(3, True)
        self.client.client.send_message.assert_called_with("/track/3/mute", 1)

        self.client.toggle_track_mute(4)
        self.client.client.send_message.assert_called_with("/track/4/mute", None)

    def test_numeric_values_are_sent_as_floats(self):
        """Regression test: ranged OSC values must be sent as floats.

        Bitwig's OSC "Value Resolution" handling can silently ignore
        updates sent as ints, so tempo/volume/pan/param values must be
        coerced to float before being sent.
        """
        self.client.set_tempo(120)
        args, _ = self.client.client.send_message.call_args
        self.assertEqual(args, ("/tempo/raw", 120.0))
        self.assertIsInstance(args[1], float)

        self.client.set_track_volume(1, 64)
        args, _ = self.client.client.send_message.call_args
        self.assertEqual(args, ("/track/1/volume", 64.0))
        self.assertIsInstance(args[1], float)

        self.client.set_track_pan(1, 32)
        args, _ = self.client.client.send_message.call_args
        self.assertEqual(args, ("/track/1/pan", 32.0))
        self.assertIsInstance(args[1], float)

        self.client.set_device_parameter(1, 100)
        args, _ = self.client.client.send_message.call_args
        self.assertEqual(args, ("/device/param/1/value", 100.0))
        self.assertIsInstance(args[1], float)

    def test_transport_record_and_repeat(self):
        """Test record and repeat transport methods"""
        self.client.record()
        self.client.client.send_message.assert_called_with("/record", 1)

        self.client.repeat(True)
        self.client.client.send_message.assert_called_with("/repeat", 1)

        self.client.repeat(False)
        self.client.client.send_message.assert_called_with("/repeat", 0)

        self.client.repeat()
        self.client.client.send_message.assert_called_with("/repeat", None)

    def test_track_send_controls(self):
        """Test track send volume/enable methods"""
        self.client.set_track_send_volume(1, 2, 100)
        self.client.client.send_message.assert_called_with(
            "/track/1/send/2/volume", 100.0
        )

        # Clamping
        self.client.set_track_send_volume(1, 2, -10)
        self.client.client.send_message.assert_called_with(
            "/track/1/send/2/volume", 0.0
        )
        self.client.set_track_send_volume(1, 2, 200)
        self.client.client.send_message.assert_called_with(
            "/track/1/send/2/volume", 128.0
        )

        with pytest.raises(InvalidParameterError):
            self.client.set_track_send_volume(0, 1, 64)  # Invalid track_index
        with pytest.raises(InvalidParameterError):
            self.client.set_track_send_volume(1, 0, 64)  # Invalid send_index
        with pytest.raises(InvalidParameterError):
            self.client.set_track_send_volume(1, 1, "not-a-number")

        self.client.set_track_send_enabled(1, 2, True)
        self.client.client.send_message.assert_called_with(
            "/track/1/send/2/activated", 1
        )
        self.client.set_track_send_enabled(1, 2, False)
        self.client.client.send_message.assert_called_with(
            "/track/1/send/2/activated", 0
        )

        with pytest.raises(InvalidParameterError):
            self.client.set_track_send_enabled(0, 1, True)  # Invalid track_index
        with pytest.raises(InvalidParameterError):
            self.client.set_track_send_enabled(1, 0, True)  # Invalid send_index
        with pytest.raises(InvalidParameterError):
            self.client.set_track_send_enabled(1, 1, "not-a-bool")

    def test_track_record_arm_and_solo(self):
        """Test track record arm and solo methods"""
        self.client.set_track_record_arm(1, True)
        self.client.client.send_message.assert_called_with("/track/1/recarm", 1)

        self.client.set_track_record_arm(1, False)
        self.client.client.send_message.assert_called_with("/track/1/recarm", 0)

        with pytest.raises(InvalidParameterError):
            self.client.set_track_record_arm(0, True)  # Invalid track_index
        with pytest.raises(InvalidParameterError):
            self.client.set_track_record_arm(1, "not-a-bool")

        self.client.set_track_solo(1, True)
        self.client.client.send_message.assert_called_with("/track/1/solo", 1)

        self.client.set_track_solo(1, False)
        self.client.client.send_message.assert_called_with("/track/1/solo", 0)

        with pytest.raises(InvalidParameterError):
            self.client.set_track_solo(0, True)  # Invalid track_index
        with pytest.raises(InvalidParameterError):
            self.client.set_track_solo(1, "not-a-bool")

    def test_track_management(self):
        """Test track add/select/delete/duplicate/rename methods"""
        self.client.add_track("instrument")
        self.client.client.send_message.assert_called_with("/track/add/instrument", 1)

        # Track type is case-insensitive
        self.client.add_track("AUDIO")
        self.client.client.send_message.assert_called_with("/track/add/audio", 1)

        self.client.add_track("effect")
        self.client.client.send_message.assert_called_with("/track/add/effect", 1)

        with pytest.raises(InvalidParameterError):
            self.client.add_track("invalid")

        self.client.select_track(3)
        self.client.client.send_message.assert_called_with("/track/3/select", 1)

        with pytest.raises(InvalidParameterError):
            self.client.select_track(0)

        self.client.delete_track(2)
        self.client.client.send_message.assert_called_with("/track/2/remove", 1)

        with pytest.raises(InvalidParameterError):
            self.client.delete_track(0)

        self.client.duplicate_track(4)
        self.client.client.send_message.assert_called_with("/track/4/duplicate", 1)

        with pytest.raises(InvalidParameterError):
            self.client.duplicate_track(0)

        self.client.rename_track(1, "Bass")
        self.client.client.send_message.assert_called_with("/track/1/name", "Bass")

        with pytest.raises(InvalidParameterError):
            self.client.rename_track(0, "Bass")  # Invalid track_index
        with pytest.raises(InvalidParameterError):
            self.client.rename_track(1, "")  # Empty name
        with pytest.raises(InvalidParameterError):
            self.client.rename_track(1, "   ")  # Whitespace-only name

    def test_clip_launcher_controls(self):
        """Test record quantization and launcher settings methods"""
        self.client.set_track_record_quantization(1, "off")
        self.client.client.send_message.assert_called_with(
            "/track/1/recordQuantization", "OFF"
        )

        self.client.set_track_record_quantization(1, "1/16")
        self.client.client.send_message.assert_called_with(
            "/track/1/recordQuantization", "1/16"
        )

        # Case-insensitive "off"
        self.client.set_track_record_quantization(1, "OFF")
        self.client.client.send_message.assert_called_with(
            "/track/1/recordQuantization", "OFF"
        )

        with pytest.raises(InvalidParameterError):
            self.client.set_track_record_quantization(0, "off")  # Invalid track_index
        with pytest.raises(InvalidParameterError):
            self.client.set_track_record_quantization(1, "1/3")  # Invalid value

        self.client.set_launcher_post_recording_action("play_recorded")
        self.client.client.send_message.assert_called_with(
            "/launcher/postRecordingAction", "play_recorded"
        )

        with pytest.raises(InvalidParameterError):
            self.client.set_launcher_post_recording_action("invalid")

        self.client.set_launcher_default_quantization("none")
        self.client.client.send_message.assert_called_with(
            "/launcher/defaultQuantization", "none"
        )

        self.client.set_launcher_default_quantization("1/4")
        self.client.client.send_message.assert_called_with(
            "/launcher/defaultQuantization", "1/4"
        )

        with pytest.raises(InvalidParameterError):
            self.client.set_launcher_default_quantization("invalid")

    def test_browser_basic_controls(self):
        """Test basic browser control methods"""
        # Test browse for device
        self.client.browse_for_device("after")
        self.client.client.send_message.assert_called_with("/browser/device", None)

        self.client.browse_for_device("before")
        self.client.client.send_message.assert_called_with(
            "/browser/device/before", None
        )

        # Test invalid position
        with pytest.raises(InvalidParameterError):
            self.client.browse_for_device("invalid")

        # Test browse for preset
        self.client.browse_for_preset()
        self.client.client.send_message.assert_called_with("/browser/preset", None)

        # Test commit browser selection
        self.client.commit_browser_selection()
        self.client.client.send_message.assert_called_with("/browser/commit", None)

        # Test cancel browser
        self.client.cancel_browser()
        self.client.client.send_message.assert_called_with("/browser/cancel", None)

    def test_browser_navigation(self):
        """Test browser navigation methods"""
        # Test navigate browser tab
        self.client.navigate_browser_tab("+")
        self.client.client.send_message.assert_called_with("/browser/tab/+", None)

        self.client.navigate_browser_tab("-")
        self.client.client.send_message.assert_called_with("/browser/tab/-", None)

        # Test invalid direction
        with pytest.raises(InvalidParameterError):
            self.client.navigate_browser_tab("invalid")

        # Test navigate browser filter
        self.client.navigate_browser_filter(1, "+")
        self.client.client.send_message.assert_called_with("/browser/filter/1/+", None)

        self.client.navigate_browser_filter(2, "-")
        self.client.client.send_message.assert_called_with("/browser/filter/2/-", None)

        # Test invalid filter index
        with pytest.raises(InvalidParameterError):
            self.client.navigate_browser_filter(0, "+")  # Below range
        with pytest.raises(InvalidParameterError):
            self.client.navigate_browser_filter(7, "+")  # Above range

        # Test invalid direction
        with pytest.raises(InvalidParameterError):
            self.client.navigate_browser_filter(1, "invalid")

        # Test reset browser filter
        self.client.reset_browser_filter(1)
        self.client.client.send_message.assert_called_with(
            "/browser/filter/1/reset", None
        )

        # Test invalid filter index
        with pytest.raises(InvalidParameterError):
            self.client.reset_browser_filter(0)  # Below range
        with pytest.raises(InvalidParameterError):
            self.client.reset_browser_filter(7)  # Above range

        # Test navigate browser result
        self.client.navigate_browser_result("+")
        self.client.client.send_message.assert_called_with("/browser/result/+", None)

        self.client.navigate_browser_result("-")
        self.client.client.send_message.assert_called_with("/browser/result/-", None)

        # Test invalid direction
        with pytest.raises(InvalidParameterError):
            self.client.navigate_browser_result("invalid")

        # Test navigate browser result page
        self.client.navigate_browser_result_page("+")
        self.client.client.send_message.assert_called_with(
            "/browser/result/page/+", None
        )

        self.client.navigate_browser_result_page("-")
        self.client.client.send_message.assert_called_with(
            "/browser/result/page/-", None
        )

        # Test invalid direction
        with pytest.raises(InvalidParameterError):
            self.client.navigate_browser_result_page("invalid")

    def test_browser_convenience_methods(self):
        """Test browser convenience methods"""
        # Test insert device after selected
        self.client.insert_device_after_selected()
        self.client.client.send_message.assert_called_with("/browser/device", None)

        # Test insert device before selected
        self.client.insert_device_before_selected()
        self.client.client.send_message.assert_called_with(
            "/browser/device/before", None
        )

        # Test browse device presets
        self.client.browse_device_presets()
        self.client.client.send_message.assert_called_with("/browser/preset", None)

        # Test select next browser tab
        self.client.select_next_browser_tab()
        self.client.client.send_message.assert_called_with("/browser/tab/+", None)

        # Test select previous browser tab
        self.client.select_previous_browser_tab()
        self.client.client.send_message.assert_called_with("/browser/tab/-", None)

        # Test select next filter option
        self.client.select_next_filter_option(1)
        self.client.client.send_message.assert_called_with("/browser/filter/1/+", None)

        # Test select previous filter option
        self.client.select_previous_filter_option(2)
        self.client.client.send_message.assert_called_with("/browser/filter/2/-", None)

        # Test select next browser result
        self.client.select_next_browser_result()
        self.client.client.send_message.assert_called_with("/browser/result/+", None)

        # Test select previous browser result
        self.client.select_previous_browser_result()
        self.client.client.send_message.assert_called_with("/browser/result/-", None)

        # Test select next browser result page
        self.client.select_next_browser_result_page()
        self.client.client.send_message.assert_called_with(
            "/browser/result/page/+", None
        )

        # Test select previous browser result page
        self.client.select_previous_browser_result_page()
        self.client.client.send_message.assert_called_with(
            "/browser/result/page/-", None
        )

    def test_browser_workflow_methods(self):
        """Test browser workflow methods"""
        # Test browse and insert device
        self.client.browse_and_insert_device(
            num_tabs=2, num_filters=[(1, 3), (2, -1)], num_results=4
        )

        expected_calls = [
            call("/browser/device", None),  # Open browser
            call("/browser/tab/+", None),  # Tab navigation 1
            call("/browser/tab/+", None),  # Tab navigation 2
            call("/browser/filter/1/+", None),  # Filter 1, nav 1
            call("/browser/filter/1/+", None),  # Filter 1, nav 2
            call("/browser/filter/1/+", None),  # Filter 1, nav 3
            call("/browser/filter/2/-", None),  # Filter 2, nav 1
            call("/browser/result/+", None),  # Result nav 1
            call("/browser/result/+", None),  # Result nav 2
            call("/browser/result/+", None),  # Result nav 3
            call("/browser/result/+", None),  # Result nav 4
            call("/browser/commit", None),  # Commit selection
        ]

        # Check that the calls were made in the right order
        self.client.client.send_message.assert_has_calls(
            expected_calls, any_order=False
        )

        # Reset the mock
        self.client.client.send_message.reset_mock()

        # Test browse and load preset
        self.client.browse_and_load_preset(num_filters=[(1, 2)], num_results=3)

        expected_calls = [
            call("/browser/preset", None),  # Open preset browser
            call("/browser/filter/1/+", None),  # Filter 1, nav 1
            call("/browser/filter/1/+", None),  # Filter 1, nav 2
            call("/browser/result/+", None),  # Result nav 1
            call("/browser/result/+", None),  # Result nav 2
            call("/browser/result/+", None),  # Result nav 3
            call("/browser/commit", None),  # Commit selection
        ]

        # Check that the calls were made in the right order
        self.client.client.send_message.assert_has_calls(
            expected_calls, any_order=False
        )


if __name__ == "__main__":
    unittest.main()
