# vbolib

Lightweight library to parse, edit and write Racelogic/VBox `.vbo` telemetry files while preserving original text formatting.

## Features

- `.vbo` file content parsing.
- Computed channels (e.g. GPS heading, rotation speed, oversteer) addition via helper methods or user-supplied compute functions.
- Existing colmun removal.
- Link `.vbo` file and related video linking.
- New `.vbo` writing (preserving original formatting).

## Requirements

- Python 3.12

## Quick usage

```python
from vbolib import VboFile

vbo_file = VboFile(r'C:\path\to\session.vbo')
vbo_file.add_rotation_speed_from_heading_column()   # compute rotation speed from heading
vbo_file.add_oversteer_column()                     # compute oversteer from rotation & gyro z
vbo_file.write(r'C:\path\to\session_modified.vbo')
```

## Contract for compute functions
On top of the provided methods, you can add your own computed channels in the `.vbo` file content using a `compute_function`:
- Signature: `def compute_function(data: OrderedDict[str, List[str]]) -> OrderedDict[str, List[str]]`
- Expectations:
    + New computed channel must have the same number of values (matching existing timestamps).
    + Must add exactly one new key -> list[str] pair in the `OrderedDict`.
    + Values must be strings formatted for .vbo output.
    + Check that the name of the new channel doesn't already exist in the `OrderedDict` keys.

Example:

```python
from vbolib import VboFile
from collections import OrderedDict
from typing import List

def compute_function(data: OrderedDict[str, List[str]]) -> OrderedDict[str, List[str]]:

    new_column = 'new_channel'

    if new_column in data]:
            raise KeyError(f"New column '{new_column}' already exists in data.")

    # nval = number of rows
    nval = len(next(iter(data.values()))) if data else 0
    new_col: List[str] = []
    for i in range(nval):
        # read string values; convert to numeric if needed
        v_str = float(data['velocity'][i])
        # compute numeric result, then format
        new_col.append(f"{0.00:.2f}")
    data[new_column] = new_col
    return data

vbo_file = VboFile(r'C:\path\to\session.vbo')
vbo_file.add_computed_column('new_channel_header', compute_function)   # compute custom channel
vbo_file.write(r'C:\path\to\session_modified.vbo')
```