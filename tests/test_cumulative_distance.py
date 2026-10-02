"""Offline checks using GoldenCheetah's bundled pandas and Plotly."""

import ast
import datetime as dt
import json
from pathlib import Path
import tempfile
import types
import unittest
from unittest.mock import Mock, patch


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "cumulative_distance" / "cumulative_distance.py"


def load_chart():
    # Load helpers without executing the paste-ready GoldenCheetah entry point.
    tree = ast.parse(SOURCE.read_text(encoding="utf-8"))
    tree.body.pop()
    chart = types.ModuleType("chart")
    exec(compile(tree, str(SOURCE), "exec"), chart.__dict__)
    if chart.IMPORT_ERROR:
        raise chart.IMPORT_ERROR
    return chart


class ChartTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.chart = load_chart()

    def test_daily_totals_and_leap_day(self):
        chart = self.chart
        metrics = {
            "date": [dt.datetime(2024, 2, 29, 18), dt.datetime(2024, 2, 29, 9),
                     dt.date(2024, 3, 2), dt.date(2024, 3, 1)],
            "Distance": [10, 5, 7, -4],
        }
        frame = chart.metrics_to_frame(metrics)
        dates, daily, cumulative = chart.date_range_frame(
            frame, dt.date(2024, 2, 28), dt.date(2024, 3, 2)
        )
        self.assertEqual(daily, [0, 15, 0, 7])
        self.assertEqual(cumulative, [0, 15, 15, 22])
        trace = chart.build_year_traces(metrics)[0]
        leap_index = list(trace.x).index("2000-02-29")
        self.assertEqual(trace.customdata[leap_index], ["2024-02-29", 15])
        self.assertEqual(trace.y[-1], 22)
        self.assertEqual(dates[-1], dt.date(2024, 3, 2))

    def test_current_selection_does_not_fetch_comparison_metrics(self):
        season = {"start": [dt.date(2024, 1, 1)], "end": [dt.date(2024, 12, 31)]}
        gc = Mock()
        gc.season.return_value = season
        gc.seasonMetrics.return_value = {"date": [], "Distance": []}
        with patch.object(self.chart, "GC", gc, create=True):
            metrics, seasons = self.chart.selected_metrics_and_seasons()
        gc.seasonMetrics.assert_called_once_with()
        self.assertEqual(seasons, season)
        self.assertEqual(len(metrics), 1)

    def test_comparison_does_not_fetch_unused_current_metrics(self):
        for seasons in (
            {"start": [dt.date(2023, 1, 1), dt.date(2024, 1, 1)]},
            [{"start": dt.date(2023, 1, 1)}, {"start": dt.date(2024, 1, 1)}],
        ):
            gc = Mock()
            gc.season.return_value = seasons
            gc.seasonMetrics.return_value = [{"Distance": []}, {"Distance": []}]
            with patch.object(self.chart, "GC", gc, create=True):
                metrics, result_seasons = self.chart.selected_metrics_and_seasons()
            gc.seasonMetrics.assert_called_once_with(compare=True)
            self.assertEqual(result_seasons, seasons)
            self.assertEqual(len(metrics), 2)

    def test_script_filter_is_preserved(self):
        gc = Mock()
        with patch.object(self.chart, "GC", gc, create=True), patch.object(
            self.chart, "SPORT_FILTER", 'Sport="Bike"'
        ):
            self.chart.season_metrics(all_dates=True)
            self.chart.season_metrics(compare=True)
        self.assertEqual(gc.seasonMetrics.call_args_list[0].kwargs,
                         {"all": True, "filter": 'Sport="Bike"'})
        self.assertEqual(gc.seasonMetrics.call_args_list[1].kwargs,
                         {"compare": True, "filter": 'Sport="Bike"'})

    def test_selection_bounds_and_button_ranges(self):
        chart = self.chart
        metrics = {"date": [dt.date(2023, 1, 2), dt.date(2024, 1, 2)],
                   "Distance": [10, 20], "Sport": ["Bike", "Bike"]}
        seasons = {"start": dt.date(2023, 1, 1), "end": dt.date(2024, 1, 3)}
        selected = chart.build_selected_traces([metrics], seasons)
        self.assertEqual(selected[0].x[0], "2023-01-01")
        self.assertEqual(selected[0].x[-1], "2024-01-03")
        self.assertEqual(selected[0].y[-1], 30)
        years = chart.build_year_traces(metrics)
        fig = chart.build_figure(years, selected, False)
        buttons = fig.layout.updatemenus[0].buttons
        self.assertEqual(list(buttons[0].args[0]["visible"]), [True, True, False])
        self.assertEqual(list(buttons[1].args[0]["visible"]), [False, False, True])
        self.assertEqual(list(buttons[1].args[1]["xaxis.range"]),
                         ["2023-01-01", "2024-01-03"])
        self.assertEqual(chart.trace_y_range(selected), [0, 31.5])

    def test_empty_invalid_and_single_day(self):
        chart = self.chart
        self.assertEqual(chart.build_year_traces({}), [])
        self.assertEqual(chart.build_selected_traces([{}], {}), [])
        self.assertTrue(chart.metrics_to_frame(
            {"date": ["invalid"], "Distance": ["invalid"]}
        ).empty)
        metrics = {"date": [dt.date(2024, 1, 2)], "Distance": [5]}
        traces = chart.build_selected_traces([metrics], {})
        self.assertEqual(chart.trace_x_range(traces), ["2024-01-01", "2024-01-03"])
        self.assertEqual(chart.trace_y_range([]), [0, 1])

    def test_local_bundle_reused_and_html_written(self):
        chart = self.chart
        with tempfile.TemporaryDirectory() as directory, patch.object(
            chart.tempfile, "gettempdir", return_value=directory
        ), patch.object(chart.plotly.offline, "get_plotlyjs", return_value="/* bundle */") as bundle:
            gc = Mock()
            with patch.object(chart, "GC", gc, create=True):
                fig = chart.build_figure([], [], False)
                chart.write_plot(fig)
                chart.write_plot(fig)
            bundle.assert_called_once_with()
            page = Path(directory, "GC_cumulative_distance.html").read_text(encoding="utf-8")
            self.assertIn(f'src="GC_cumulative_distance_plotly-{chart.plotly.__version__}.min.js"', page)
            self.assertIn('index !== menu.active', page)
            self.assertEqual(gc.webpage.call_count, 2)
            self.assertLess(len(page), 50000)

    def test_bundle_write_failure_uses_inline_fallback(self):
        with patch.object(Path, "is_file", return_value=False), patch.object(
            Path, "write_text", side_effect=OSError("read only")
        ), patch.object(self.chart.plotly.offline, "get_plotlyjs", return_value="bundle"):
            self.assertIs(self.chart.local_plotly_bundle(), True)

    def test_export_contains_current_script(self):
        exported = json.loads((SOURCE.parent / "Cumulative Distance.gchart").read_text(encoding="utf-8"))
        self.assertEqual(exported["CHART"]["PROPERTIES"]["script"], SOURCE.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
