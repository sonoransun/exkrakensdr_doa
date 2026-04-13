import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from _viz.settings_reader import SettingsReader


def _make_settings_file(tmp_dir, settings_dict):
    path = os.path.join(tmp_dir, "settings.json")
    with open(path, "w") as f:
        json.dump(settings_dict, f)
    return path


class TestSettingsReader:
    def test_loads_existing_file(self, qtbot):
        with tempfile.TemporaryDirectory() as tmp:
            path = _make_settings_file(
                tmp,
                {
                    "center_freq": 394317376,
                    "compass_offset": 15,
                    "ant_arrangement": "UCA",
                    "ant_spacing_meters": 0.1,
                    "active_vfos": 3,
                    "station_id": "TEST01",
                    "latitude": 50.8,
                    "longitude": 6.9,
                },
            )
            reader = SettingsReader(settings_path=path)

            assert reader.center_freq == 394317376
            assert reader.compass_offset == 15
            assert reader.antenna_arrangement == "UCA"
            assert reader.antenna_spacing == 0.1
            assert reader.active_vfos == 3
            assert reader.station_id == "TEST01"
            assert reader.latitude == 50.8
            assert reader.longitude == 6.9

    def test_missing_file_returns_defaults(self, qtbot):
        reader = SettingsReader(settings_path="/nonexistent/settings.json")
        assert reader.center_freq == 0
        assert reader.compass_offset == 0
        assert reader.antenna_arrangement == "UCA"
        assert reader.station_id == ""
        assert reader.settings == {}

    def test_get_with_default(self, qtbot):
        with tempfile.TemporaryDirectory() as tmp:
            path = _make_settings_file(tmp, {"foo": "bar"})
            reader = SettingsReader(settings_path=path)
            assert reader.get("foo") == "bar"
            assert reader.get("missing_key", 42) == 42

    def test_settings_changed_signal(self, qtbot):
        with tempfile.TemporaryDirectory() as tmp:
            path = _make_settings_file(tmp, {"center_freq": 100e6})
            reader = SettingsReader(settings_path=path)

            received = []
            reader.settings_changed.connect(lambda d: received.append(d))

            # Write new settings to trigger reload
            with open(path, "w") as f:
                json.dump({"center_freq": 200e6}, f)
            reader._reload()

            assert len(received) == 1
            assert received[0]["center_freq"] == 200e6

    def test_malformed_json_does_not_crash(self, qtbot):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "settings.json")
            with open(path, "w") as f:
                f.write("{bad json")
            reader = SettingsReader(settings_path=path)
            assert reader.settings == {}
