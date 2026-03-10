import numpy as np
import pytest

from kraken_web_multi_doa import MAX_VFOS, init_multi_doa_fig, init_multi_doa_history_fig, plot_multi_doa


class MockWebInterface:
    def __init__(self):
        self.compass_offset = 0
        self.multi_doa_all_results = {}
        self.multi_doa_history = []


class MockApp:
    def __init__(self):
        self.push_mods_calls = []

    def push_mods(self, mods):
        self.push_mods_calls.append(mods)


def _make_fig_layout():
    import plotly.graph_objects as go

    return go.Layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        template="plotly_dark",
        showlegend=True,
    )


class TestInitMultiDoaFig:
    def test_creates_correct_number_of_traces(self):
        wi = MockWebInterface()
        fig = init_multi_doa_fig(wi, _make_fig_layout())
        assert len(fig.data) == 2 * MAX_VFOS

    def test_all_traces_initially_invisible(self):
        wi = MockWebInterface()
        fig = init_multi_doa_fig(wi, _make_fig_layout())
        for trace in fig.data:
            assert trace.visible is False


class TestInitMultiDoaHistoryFig:
    def test_creates_correct_number_of_traces(self):
        fig = init_multi_doa_history_fig(_make_fig_layout())
        assert len(fig.data) == MAX_VFOS


class TestPlotMultiDoa:
    def test_empty_results_no_crash(self):
        app = MockApp()
        wi = MockWebInterface()
        wi.multi_doa_all_results = {}
        fig = init_multi_doa_fig(wi, _make_fig_layout())
        hist_fig = init_multi_doa_history_fig(_make_fig_layout())
        # Should not raise
        plot_multi_doa(app, wi, fig, hist_fig)
        assert len(app.push_mods_calls) == 0

    def test_active_vfo_traces_visible(self):
        app = MockApp()
        wi = MockWebInterface()
        thetas = np.linspace(0, 360, 361)
        result0 = np.random.rand(361)
        wi.multi_doa_all_results = {
            "thetas": thetas,
            "results": [result0],
            "angles": [90.0],
            "freqs": [100e6],
            "powers": [-50.0],
            "confidences": [0.8],
            "squelch_active": [True],
        }
        fig = init_multi_doa_fig(wi, _make_fig_layout())
        hist_fig = init_multi_doa_history_fig(_make_fig_layout())
        plot_multi_doa(app, wi, fig, hist_fig)
        # First VFO traces (curve=0, peak=1) should be visible
        assert fig.data[0]["visible"] is True
        assert fig.data[1]["visible"] is True
        # Second VFO traces should be invisible
        assert fig.data[2]["visible"] is False

    def test_compass_offset(self):
        app = MockApp()
        wi = MockWebInterface()
        wi.compass_offset = 90
        thetas = np.array([0.0, 90.0, 180.0, 270.0])
        result0 = np.array([1.0, 2.0, 3.0, 4.0])
        wi.multi_doa_all_results = {
            "thetas": thetas,
            "results": [result0],
            "angles": [0.0],
            "freqs": [100e6],
            "powers": [-50.0],
            "confidences": [0.8],
            "squelch_active": [True],
        }
        fig = init_multi_doa_fig(wi, _make_fig_layout())
        hist_fig = init_multi_doa_history_fig(_make_fig_layout())
        plot_multi_doa(app, wi, fig, hist_fig)
        # The display angle should be offset
        peak_theta = fig.data[1]["theta"]
        expected_angle = (360 - 0.0 + 90) % 360
        assert peak_theta[0] == expected_angle
