# GoldenCheetah Cumulative Distance Chart

Current chart version: **1.1**, a performance update to the original **1.0**. The version is recorded in the header of the Python script and its exported `.gchart`.

This repository contains a GoldenCheetah Trends chart for cumulative distance. It plots cumulative distance and can switch between:

- all calendar years overlaid by month/day
- the date range or compared ranges selected in GoldenCheetah's Trends sidebar

Use `cumulative_distance/Cumulative Distance.gchart` to import the chart directly into GoldenCheetah. The matching source script is kept in `cumulative_distance/cumulative_distance.py` for review and customization.

The chart upload description is in [cumulative_distance/upload_description.md](cumulative_distance/upload_description.md).

## Install

### Import The Chart

1. Open GoldenCheetah and go to `Trends`.
2. Import `cumulative_distance/Cumulative Distance.gchart` into the Trends view.
3. Select a season or date range in the left Trends sidebar. The chart refreshes from that selection.

### Paste The Source Script

If you prefer to inspect or customize the chart before installing it:

1. Open GoldenCheetah and go to `Trends`.
2. Click the `+` button on the top-right chart bar to add a new chart and choose `Python Chart`.
3. When the `Python Chart` editor opens, paste the full contents of `cumulative_distance/cumulative_distance.py` directly into the chart code field.
4. Set the chart title to `Cumulative Distance` and save it. When exporting from GoldenCheetah, save it as `cumulative_distance/Cumulative Distance.gchart`.

The `.gchart` file already contains the chart script exported from GoldenCheetah. Only use `cumulative_distance/cumulative_distance.py` if you are manually creating or modifying a Python Chart. Do not use `import cumulative_distance` inside GoldenCheetah; the script expects GoldenCheetah to run it directly and provide the `GC` chart API.

GoldenCheetah 3.6+ normally includes the needed Python modules. If the chart reports missing packages, install `pandas` and `plotly` into the Python runtime configured in GoldenCheetah.

The current local GoldenCheetah bundled Python version is documented in `RUNTIME.md`. Use that executable for syntax checks when changing `cumulative_distance/cumulative_distance.py` to avoid issues caused by validating with a different Python runtime.

After changing the Python source, re-export the chart from GoldenCheetah so `cumulative_distance/Cumulative Distance.gchart` contains the same script. Before publishing, smoke test by importing the `.gchart` file into the Trends view.

## Selection And Filters

The `Selection` view uses GoldenCheetah's active Trends sidebar date range and any active sidebar search/data filters. Leave `SPORT_FILTER` empty to let GoldenCheetah apply the active filter itself; for example, an active `Sport="Bike"` filter limits both chart views to bike activities. In the `Selection` view, the selected date range is shown under the chart title. A second line shows the applied filter value when the filtered activities have a single visible workout `Code` value, otherwise a single visible `Sport` value. If `SPORT_FILTER` has a value, the filter line shows that exact expression instead.

The chart remembers the last selected view button, so changing the Trends date range or filters keeps the chart on `All years` or `Selection` instead of resetting the view.

By default the script does not add an extra sport filter:

```python
SPORT_FILTER = ""
```

To add a chart script sport filter, edit this line near the top of `cumulative_distance/cumulative_distance.py`:

```python
SPORT_FILTER = 'Sport="Bike"'
```

GoldenCheetah still applies active sidebar filters to chart API calls, so clear those filters in GoldenCheetah when you want the script sport filter alone.

## Performance And Validation

The chart avoids fetching unused comparison metrics, aggregates activities by day before creating Python dates, and uses trace endpoints to calculate axis ranges. It preserves every daily point and hover value.

Plotly's installed JavaScript bundle is saved once in the system temporary directory, beside the generated HTML, and reused on refresh. Its filename includes the Plotly version so upgrades get a separate bundle. No network connection or extra packages are needed. If the bundle cannot be written, the chart falls back to embedding it in the HTML.

An offline benchmark with 40,000 synthetic activities over 30 years, using GoldenCheetah's Python 3.11.9, measured median chart generation at 0.272 seconds versus 0.387 seconds before optimization (five refreshes after warm-up). Generated HTML decreased from 5.8 MB to 0.95 MB. These measurements exclude real GoldenCheetah database access and browser rendering; actual loading times depend on the athlete database and web view.

Run the offline checks with the Python executable configured in GoldenCheetah:

```console
<goldencheetah-python> -m py_compile cumulative_distance/cumulative_distance.py
<goldencheetah-python> -m unittest discover -s tests -v
```

The checks cover daily totals, leap days, empty data, selection and comparison ranges, filter forwarding, local bundle reuse, and matching source in the exported chart. Import the `.gchart` into GoldenCheetah Trends to verify rendering and both view buttons with your athlete database.

## License

This repository's chart scripts are distributed under the GNU General Public License version 3. See `LICENSE`.

GoldenCheetah itself is distributed under GPL-2.0.
