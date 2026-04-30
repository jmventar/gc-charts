"""
GoldenCheetah Trend chart: cumulative distance.

Paste this file into a GoldenCheetah Python chart in Trends view.
The chart has two views:
  - all calendar years overlaid by month/day
  - the currently selected GoldenCheetah date range(s)
"""

import datetime as dt
import html
import pathlib
import tempfile
import traceback


DISTANCE_FIELDS = ("Distance", "Workout_Distance")
DATE_FIELD = "date"
DISTANCE_UNIT = "km"
TODAY_LINE_COLOR = "#d62728"
CONTEXT_TEXT_COLOR = "#455a64"
PLOT_DIV_ID = "gc-cumulative-distance"
VIEW_STATE_KEY = "gc-cumulative-distance-view"
FILTER_VALUE_FIELD_GROUPS = (
    (("Workout_Code", "Workout Code", "Code", "code"), "Code"),
    (("Sport", "sport"), "Sport"),
)

# Leave empty to rely on GoldenCheetah's active sidebar filters.
# Example for bikes only: 'Sport="Bike"'
SPORT_FILTER = ""


IMPORT_ERROR = None
PALETTE_COLORS = ()
try:
    import pandas as pd
    import plotly
    import plotly.graph_objects as go
    from plotly.colors import qualitative
    PALETTE_COLORS = (
        qualitative.Dark24
        + qualitative.Set2
        + qualitative.Bold
        + qualitative.Plotly
    )
except Exception as exc:
    IMPORT_ERROR = exc


# Basic Value Helpers

def as_date(value):
    if value is None:
        return None
    if isinstance(value, dt.datetime):
        return value.date()
    if isinstance(value, dt.date):
        return value

    parsed = pd.to_datetime(value, errors="coerce")
    if pd.isna(parsed):
        return None
    return parsed.date()


def as_float(value):
    try:
        if value is None:
            return None
        result = float(value)
        if pd.isna(result):
            return None
        return result
    except (TypeError, ValueError):
        return None


def first_existing_key(mapping, candidates):
    if not mapping:
        return None
    for key in candidates:
        if key in mapping:
            return key
    return None


def as_list(value):
    if value is None:
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, tuple):
        return list(value)
    return [value]


# GoldenCheetah API Helpers

def metrics_filter():
    return SPORT_FILTER.strip()


def season_metrics(all_dates=False, compare=False):
    kwargs = {}
    filter_expression = metrics_filter()
    if all_dates:
        kwargs["all"] = True
    if compare:
        kwargs["compare"] = True
    if filter_expression:
        kwargs["filter"] = filter_expression

    return GC.seasonMetrics(**kwargs)


def season_value(seasons, index, key):
    if seasons is None:
        return None

    if isinstance(seasons, (list, tuple)):
        if index >= len(seasons):
            return None
        item = seasons[index]
        if isinstance(item, dict):
            return item.get(key)
        return None

    if isinstance(seasons, dict):
        value = seasons.get(key)
        if isinstance(value, (list, tuple)):
            if index < len(value):
                return value[index]
            return None
        return value

    return None


def selected_metrics_and_seasons():
    current_metrics = season_metrics()
    current_season = GC.season()
    compare_metrics = as_list(season_metrics(compare=True))
    compare_seasons = GC.season(compare=True)

    if len(compare_metrics) > 1:
        return compare_metrics, compare_seasons

    return [current_metrics], current_season


# Data Preparation

def metrics_to_frame(metrics):
    distance_field = first_existing_key(metrics, DISTANCE_FIELDS)
    if not metrics or DATE_FIELD not in metrics or distance_field is None:
        return pd.DataFrame(columns=["date", "distance"])

    frame = pd.DataFrame(
        zip(metrics[DATE_FIELD], metrics[distance_field]),
        columns=["date", "distance"],
    )
    if frame.empty:
        return pd.DataFrame(columns=["date", "distance"])

    frame["date"] = pd.to_datetime(frame["date"], errors="coerce")
    frame["distance"] = pd.to_numeric(frame["distance"], errors="coerce")
    frame = frame.dropna(subset=["date", "distance"])
    if frame.empty:
        return pd.DataFrame(columns=["date", "distance"])

    frame["date"] = frame["date"].dt.date
    frame["distance"] = frame["distance"].clip(lower=0.0)
    frame = frame.groupby("date", as_index=False)["distance"].sum()
    return frame.sort_values("date")


def capped_end_date(start, end, data_end):
    if start is None or end is None:
        return end

    today = dt.date.today()
    if start <= today <= end:
        end = today

    if data_end is not None and data_end > end:
        end = data_end

    return end


def date_range_frame(frame, start, end):
    if start is None or end is None or start > end:
        return [], [], []

    index = pd.date_range(start=start, end=end, freq="D").date
    if frame.empty:
        daily = pd.Series(0.0, index=index)
    else:
        daily = frame.set_index("date")["distance"].reindex(index, fill_value=0.0)

    cumulative = daily.cumsum()
    return list(index), daily.tolist(), cumulative.tolist()


def selected_bounds(index, seasons, frame):
    start = as_date(season_value(seasons, index, "start"))
    end = as_date(season_value(seasons, index, "end"))

    if frame.empty:
        return start, end

    data_start = frame["date"].min()
    data_end = frame["date"].max()
    start = start or data_start
    end = end or data_end
    end = capped_end_date(start, end, data_end)

    return start, end


def frame_at(metrics_sets, frames, index):
    if frames is not None and index < len(frames):
        return frames[index]
    return metrics_to_frame(metrics_sets[index])


def total_distance(values):
    if not values:
        return 0.0
    return float(values[-1])


# Label And Subtitle Helpers

def label_total(total):
    if total >= 100:
        return f"{total:.0f}"
    return f"{total:.1f}"


def selected_range_label(index, seasons, frame):
    name = season_value(seasons, index, "name")
    if name:
        return str(name)

    start = as_date(season_value(seasons, index, "start"))
    end = as_date(season_value(seasons, index, "end"))
    if start and end:
        return f"{start.isoformat()} to {end.isoformat()}"

    if not frame.empty:
        return f"{frame['date'].min().isoformat()} to {frame['date'].max().isoformat()}"

    return f"Selected range {index + 1}"


def selected_date_label(index, seasons, frame):
    start = as_date(season_value(seasons, index, "start"))
    end = as_date(season_value(seasons, index, "end"))

    if start and end:
        date_text = f"{start.isoformat()} to {end.isoformat()}"
    elif start:
        date_text = f"from {start.isoformat()}"
    elif end:
        date_text = f"to {end.isoformat()}"
    elif not frame.empty:
        date_text = f"{frame['date'].min().isoformat()} to {frame['date'].max().isoformat()}"
    else:
        date_text = f"range {index + 1}"

    return date_text


def truncated_join(items, separator="; ", limit=3):
    if len(items) <= limit:
        return separator.join(items)
    visible = separator.join(items[:limit])
    return f"{visible}{separator}+{len(items) - limit} more"


def selection_context_text(metrics_sets, seasons, frames=None):
    date_labels = []
    for index, _metrics in enumerate(metrics_sets):
        frame = frame_at(metrics_sets, frames, index)
        date_labels.append(selected_date_label(index, seasons, frame))

    dates = truncated_join(date_labels) if date_labels else "none"
    filter_value = selection_filter_label(metrics_sets)
    if filter_value:
        return (
            f"Date Range: {html.escape(dates)}"
            f"<br>Filter: {html.escape(filter_value)}"
        )

    return f"Date Range: {html.escape(dates)}"


def single_metric_value(metrics_sets, field_names):
    result = ""
    seen = set()
    for metrics in metrics_sets:
        field_name = first_existing_key(metrics, field_names)
        if not metrics or field_name is None:
            continue
        for raw_value in as_list(metrics[field_name]):
            value = normalized_filter_value(raw_value)
            if value and value not in seen:
                seen.add(value)
                result = value
                if len(seen) > 1:
                    return ""

    return result


def normalized_filter_value(value):
    if value is None:
        return ""
    text = str(value).strip()
    if not text:
        return ""
    if text.lower() in ("none", "nan", "all"):
        return ""
    return text


def selection_filter_label(metrics_sets):
    script_filter = metrics_filter().strip()
    if script_filter:
        return script_filter

    for field_names, label in FILTER_VALUE_FIELD_GROUPS:
        value = single_metric_value(metrics_sets, field_names)
        if value:
            return f"{label}: {value}"

    return ""


# Plot Layout Helpers

def palette_color(index):
    return PALETTE_COLORS[index % len(PALETTE_COLORS)]


def trace_x_range(traces):
    x_values = []
    for trace in traces:
        for value in trace.x if trace.x is not None else []:
            date_value = as_date(value)
            if date_value is not None:
                x_values.append(date_value)

    if not x_values:
        return None

    start = min(x_values)
    end = max(x_values)
    if start == end:
        start -= dt.timedelta(days=1)
        end += dt.timedelta(days=1)

    return [start.isoformat(), end.isoformat()]


def trace_y_range(traces):
    y_values = []
    for trace in traces:
        for value in trace.y if trace.y is not None else []:
            distance = as_float(value)
            if distance is not None:
                y_values.append(distance)

    if not y_values:
        return [0, 1]

    top = max(y_values)
    if top <= 0:
        return [0, 1]

    return [0, top * 1.05]


def is_in_x_range(x_range, date_value):
    if not x_range or date_value is None:
        return False
    iso_value = date_value.isoformat()
    return x_range[0] <= iso_value <= x_range[1]


def today_line_shape(date_value):
    iso_value = date_value.isoformat()
    return {
        "type": "line",
        "xref": "x",
        "yref": "paper",
        "x0": iso_value,
        "x1": iso_value,
        "y0": 0,
        "y1": 1,
        "line": {"color": TODAY_LINE_COLOR, "width": 2, "dash": "dash"},
    }


def view_layout(title, xaxis_title, tickformat, traces, today_x=None, context_text=""):
    x_range = trace_x_range(traces)
    shapes = []
    if is_in_x_range(x_range, today_x):
        shapes.append(today_line_shape(today_x))

    annotations = []
    if context_text:
        annotations.append(
            {
                "text": context_text,
                "xref": "paper",
                "yref": "paper",
                "x": 0,
                "y": 1.08,
                "xanchor": "left",
                "yanchor": "top",
                "align": "left",
                "showarrow": False,
                "font": {"size": 11, "color": CONTEXT_TEXT_COLOR},
            }
        )

    return {
        "title": title,
        "xaxis": {
            "title": xaxis_title,
            "tickformat": tickformat,
            "type": "date",
            "autorange": x_range is None,
            **({"range": x_range} if x_range else {}),
        },
        "yaxis": {
            "title": f"Cumulative distance ({DISTANCE_UNIT})",
            "range": trace_y_range(traces),
            "rangemode": "tozero",
        },
        "shapes": shapes,
        "annotations": annotations,
    }


def view_update(layout):
    update = {
        "title.text": layout["title"],
        "xaxis.title.text": layout["xaxis"]["title"],
        "xaxis.tickformat": layout["xaxis"]["tickformat"],
        "xaxis.type": layout["xaxis"]["type"],
        "xaxis.autorange": layout["xaxis"]["autorange"],
        "yaxis.title.text": layout["yaxis"]["title"],
        "yaxis.range": layout["yaxis"]["range"],
        "yaxis.rangemode": layout["yaxis"]["rangemode"],
        "shapes": layout["shapes"],
        "annotations": layout["annotations"],
    }

    if "range" in layout["xaxis"]:
        update["xaxis.range"] = layout["xaxis"]["range"]

    return update


# Trace Builders

def build_year_traces(metrics):
    frame = metrics_to_frame(metrics)
    if frame.empty:
        return []

    traces = []
    today = dt.date.today()
    frame = frame.assign(year=frame["date"].map(lambda ride_date: ride_date.year))

    for color_index, (year, year_frame) in enumerate(frame.groupby("year", sort=True)):
        year = int(year)
        start = dt.date(year, 1, 1)
        end = dt.date(year, 12, 31)
        if year == today.year:
            end = min(end, max(today, year_frame["date"].max()))

        actual_dates, daily, cumulative = date_range_frame(year_frame, start, end)
        if not actual_dates:
            continue

        x_values = [dt.date(2000, ride_date.month, ride_date.day) for ride_date in actual_dates]
        total = total_distance(cumulative)
        custom_data = [
            (ride_date.isoformat(), daily_distance)
            for ride_date, daily_distance in zip(actual_dates, daily)
        ]

        traces.append(
            go.Scatter(
                x=x_values,
                y=cumulative,
                customdata=custom_data,
                name=f"{year} ({label_total(total)} {DISTANCE_UNIT})",
                mode="lines",
                line={"color": palette_color(color_index), "width": 2.2},
                hovertemplate=(
                    "Date: %{customdata[0]}"
                    f"<br>Day distance: %{{customdata[1]:.1f}} {DISTANCE_UNIT}"
                    f"<br>Cumulative: %{{y:.1f}} {DISTANCE_UNIT}"
                    "<extra>%{fullData.name}</extra>"
                ),
            )
        )

    return traces


def build_selected_traces(metrics_sets, seasons, frames=None):
    traces = []

    for index, metrics in enumerate(metrics_sets):
        frame = frame_at(metrics_sets, frames, index)
        start, end = selected_bounds(index, seasons, frame)
        actual_dates, daily, cumulative = date_range_frame(frame, start, end)
        if not actual_dates:
            continue

        total = total_distance(cumulative)
        name = selected_range_label(index, seasons, frame)
        custom_data = [
            (ride_date.isoformat(), daily_distance)
            for ride_date, daily_distance in zip(actual_dates, daily)
        ]

        traces.append(
            go.Scatter(
                x=actual_dates,
                y=cumulative,
                customdata=custom_data,
                name=f"{name} ({label_total(total)} {DISTANCE_UNIT})",
                mode="lines",
                line={"color": palette_color(index), "width": 2.6},
                hovertemplate=(
                    "Date: %{customdata[0]}"
                    f"<br>Day distance: %{{customdata[1]:.1f}} {DISTANCE_UNIT}"
                    f"<br>Cumulative: %{{y:.1f}} {DISTANCE_UNIT}"
                    "<extra>%{fullData.name}</extra>"
                ),
            )
        )

    return traces


# Figure Assembly

def configure_visibility(traces, year_count, selected_count, default_selected):
    for index, trace in enumerate(traces):
        is_selected_trace = index >= year_count
        trace.visible = is_selected_trace if default_selected else not is_selected_trace

    year_visibility = [index < year_count for index in range(len(traces))]
    selected_visibility = [index >= year_count for index in range(len(traces))]
    return year_visibility, selected_visibility


def build_figure(year_traces, selected_traces, default_selected, selection_context=""):
    traces = year_traces + selected_traces
    year_count = len(year_traces)
    selected_count = len(selected_traces)
    year_visibility, selected_visibility = configure_visibility(
        traces, year_count, selected_count, default_selected
    )
    today = dt.date.today()
    all_year_today = dt.date(2000, today.month, today.day)
    year_layout = view_layout(
        "Cumulative distance by calendar year",
        "Month",
        "%b",
        year_traces,
        today_x=all_year_today,
    )
    selected_layout = view_layout(
        "Cumulative distance for selection",
        "Date",
        "%d %b %Y",
        selected_traces,
        today_x=today,
        context_text=selection_context,
    )

    fig = go.Figure(data=traces)
    buttons = []

    if year_count:
        buttons.append(
            {
                "label": "All years",
                "method": "update",
                "args": [
                    {"visible": year_visibility},
                    view_update(year_layout),
                ],
            }
        )

    if selected_count:
        buttons.append(
            {
                "label": "Selection",
                "method": "update",
                "args": [
                    {"visible": selected_visibility},
                    view_update(selected_layout),
                ],
            }
        )

    initial_layout = selected_layout if default_selected else year_layout

    fig.update_layout(
        title=initial_layout["title"],
        template="plotly_white",
        hovermode="x unified",
        margin={"l": 68, "r": 24, "t": 124, "b": 58},
        xaxis=initial_layout["xaxis"],
        yaxis=initial_layout["yaxis"],
        shapes=initial_layout["shapes"],
        annotations=initial_layout["annotations"],
        legend={
            "orientation": "h",
            "yanchor": "bottom",
            "y": 1.02,
            "xanchor": "left",
            "x": 0,
        },
        updatemenus=[
            {
                "type": "buttons",
                "direction": "right",
                "x": 1,
                "xanchor": "right",
                "y": 1.16,
                "yanchor": "top",
                "buttons": buttons,
                "active": 1 if default_selected and len(buttons) > 1 else 0,
            }
        ]
        if buttons
        else [],
    )

    return fig


# HTML Output

def render_message(title, message, detail=""):
    body = f"""
<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <style>
    body {{
      margin: 0;
      font-family: Arial, sans-serif;
      color: #263238;
      background: #ffffff;
    }}
    main {{
      padding: 28px;
      max-width: 900px;
    }}
    h1 {{
      margin: 0 0 12px;
      font-size: 22px;
      font-weight: 600;
    }}
    p {{
      margin: 0 0 16px;
      line-height: 1.45;
    }}
    pre {{
      white-space: pre-wrap;
      overflow-wrap: anywhere;
      background: #f5f7f8;
      border: 1px solid #d7dde1;
      border-radius: 6px;
      padding: 12px;
      font-size: 12px;
    }}
  </style>
</head>
<body>
  <main>
    <h1>{html.escape(title)}</h1>
    <p>{html.escape(message)}</p>
    {f"<pre>{html.escape(detail)}</pre>" if detail else ""}
  </main>
</body>
</html>
"""
    temp_file = tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8", prefix="GC_distance_", suffix=".html", delete=False
    )
    try:
        temp_file.write(body)
    finally:
        temp_file.close()

    GC.webpage(pathlib.Path(temp_file.name).as_uri())


def view_state_script():
    return f"""
(function() {{
  var plot = document.getElementById({PLOT_DIV_ID!r});
  var storageKey = {VIEW_STATE_KEY!r};
  var allowedViews = {{
    "All years": true,
    "Selection": true
  }};

  function storedView() {{
    try {{
      return window.localStorage.getItem(storageKey);
    }} catch (error) {{
      return null;
    }}
  }}

  function saveView(label) {{
    if (!allowedViews[label]) {{
      return;
    }}
    try {{
      window.localStorage.setItem(storageKey, label);
    }} catch (error) {{
      // GoldenCheetah's web view may disable storage in some environments.
    }}
  }}

  function buttonIndex(label) {{
    var menus = (plot.layout && plot.layout.updatemenus) || [];
    var buttons = menus.length ? (menus[0].buttons || []) : [];
    for (var index = 0; index < buttons.length; index += 1) {{
      if (buttons[index].label === label) {{
        return index;
      }}
    }}
    return -1;
  }}

  function applyButton(index) {{
    var menu = plot.layout.updatemenus && plot.layout.updatemenus[0];
    var button = menu && menu.buttons && menu.buttons[index];
    if (!button || !button.args) {{
      return;
    }}

    Plotly.update(plot, button.args[0] || {{}}, button.args[1] || {{}})
      .then(function() {{
        return Plotly.relayout(plot, {{"updatemenus[0].active": index}});
      }});
  }}

  if (!plot || !window.Plotly) {{
    return;
  }}

  plot.on("plotly_buttonclicked", function(eventData) {{
    if (eventData && eventData.button) {{
      saveView(eventData.button.label);
    }}
  }});

  var index = buttonIndex(storedView());
  if (index >= 0) {{
    applyButton(index);
  }}
}}());
"""


def write_plot(fig):
    plot_html = plotly.io.to_html(
        fig,
        include_plotlyjs=True,
        full_html=True,
        div_id=PLOT_DIV_ID,
        post_script=view_state_script(),
        config={"displayModeBar": False, "displaylogo": False, "responsive": True},
    )

    temp_file = pathlib.Path(tempfile.gettempdir()) / "GC_cumulative_distance.html"
    temp_file.write_text(plot_html, encoding="utf-8")
    GC.webpage(temp_file.as_uri())


# Entry Point

def main():
    if IMPORT_ERROR is not None:
        render_message(
            "Missing Python package",
            "This chart needs pandas and plotly in the Python runtime configured in GoldenCheetah.",
            str(IMPORT_ERROR),
        )
        return

    all_metrics = season_metrics(all_dates=True)
    selected_metrics, selected_seasons = selected_metrics_and_seasons()
    selected_frames = [metrics_to_frame(metrics) for metrics in selected_metrics]

    year_traces = build_year_traces(all_metrics)
    selected_traces = build_selected_traces(
        selected_metrics, selected_seasons, selected_frames
    )
    selection_context = selection_context_text(
        selected_metrics, selected_seasons, selected_frames
    )

    if not year_traces and not selected_traces:
        render_message(
            "No distance data",
            "GoldenCheetah did not return any activities with date and distance metrics for this chart.",
        )
        return

    default_selected = bool(selected_traces) and not bool(year_traces)

    fig = build_figure(
        year_traces, selected_traces, default_selected, selection_context
    )
    write_plot(fig)


try:
    main()
except Exception:
    render_message(
        "Cumulative distance chart error",
        "The chart failed while reading GoldenCheetah metrics or building the plot.",
        traceback.format_exc(),
    )
