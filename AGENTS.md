# Repository Guidelines

## Project Structure & Module Organization

This repository contains GoldenCheetah Python chart scripts.

- `cumulative_distance/cumulative_distance.py` is the main chart script. It is intended to be pasted into a GoldenCheetah Trends Python chart and rendered through `GC.webpage()`.
- `cumulative_distance/cumulative distance.gchart` is the exported GoldenCheetah chart file users can import directly into the Trends view.
- `README.md` documents installation and end-user configuration.
- Generated files such as `__pycache__/` are local artifacts and should not be committed.

Keep each chart's source script and exported `.gchart` file together in a dedicated chart folder unless the project grows enough to justify folders such as `charts/`, `tests/`, or `docs/`.

## Build, Test, and Development Commands

Use GoldenCheetah's bundled Python when possible because that is the target runtime:

```console
<goldencheetah-python> -m py_compile cumulative_distance/cumulative_distance.py
```

This checks Python syntax without requiring a live GoldenCheetah athlete database.

For a lightweight smoke test, import the `.gchart` file into GoldenCheetah Trends, or run the script inside GoldenCheetah after pasting it into a Trends Python chart. Select different sidebar seasons or date ranges and confirm the Plotly buttons switch between `All years` and `Selection`.

## Coding Style & Naming Conventions

Write Python using 4-space indentation and clear snake_case names for functions, variables, and constants. Keep user-editable settings near the top of each script, as with `SPORT_FILTER`, `DISTANCE_FIELDS`, and `DISTANCE_UNIT`.

Prefer small helper functions over long inline chart logic. Keep GoldenCheetah API calls in `main()` or similarly obvious entry points so fake `GC` objects can be used for smoke testing.

## Testing Guidelines

There is no formal test suite yet. Before submitting changes:

- Run `py_compile` with GoldenCheetah's Python.
- Smoke test in GoldenCheetah Trends view.
- Verify empty data, selected date ranges, and multi-year data do not crash the chart.

If tests are added later, place them under `tests/` and name files `test_<feature>.py`.

## Commit & Pull Request Guidelines

This folder currently has no git history, so use conventional, concise commit messages such as `Add cumulative distance chart` or `Fix selected range handling`.

Pull requests should include a short description, the GoldenCheetah version tested, screenshots or notes for chart rendering changes, and the commands or manual checks performed.

## Agent-Specific Instructions

Do not introduce external services or network dependencies. Keep scripts paste-ready for GoldenCheetah and avoid changes that require users to restructure their local GoldenCheetah setup.
