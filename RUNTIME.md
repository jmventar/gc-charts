# Runtime Metadata

Target runtime for local validation:

- Python version observed: `3.11.9`
- Version detail: `3.11.9 (tags/v3.11.9:de54cf5, Apr  2 2024, 10:12:12) [MSC v.1938 64 bit (AMD64)]`

Use the Python runtime configured in your GoldenCheetah install for syntax checks before publishing chart scripts:

```console
<goldencheetah-python> -m py_compile cumulative_distance/cumulative_distance.py
```

After changing `cumulative_distance/cumulative_distance.py`, re-export `cumulative_distance/Cumulative Distance.gchart` from GoldenCheetah and verify that the exported chart imports cleanly in the Trends view.
