# excel_grid

A Streamlit-native grid component that renders Excel-like tables in the browser — with freeze panes, merged cells, per-cell conditional formatting, and one-click `.xlsx` export.

Built for dashboards and data-heavy apps where `st.dataframe` isn't enough control.

---

## Features

- **Freeze panes** — freeze any number of header rows and label columns, sticky through scroll
- **Merged cells** — `rowspan` and `colspan` on any cell, recalculated correctly when rows/columns are hidden
- **Per-cell styling** — background colour, text colour, font size, bold/italic, alignment, borders, number formats
- **Hide/unhide** — hover any column or row header to reveal a hide button; click the corner to restore all
- **XLSX export** — one-click download that mirrors the exact layout rendered in the browser
- **No external dependencies in browser** — fully self-contained HTML/JS output, no CDN requests

---

## Installation

```bash
pip install streamlit xlsxwriter
```

Then drop the `excel_grid/` folder into your project:

```
your_app/
├── excel_grid/
│   ├── __init__.py
│   ├── style.py
│   ├── cell.py
│   ├── sheet.py
│   ├── components.py
│   └── renderers/
│       ├── html.py
│       └── excel.py
└── app.py
```

---

## Quick start

```python
import streamlit as st
from excel_grid import Sheet, CellStyle, render_sheet, excel_download_button

sheet = Sheet("Q4 Revenue")

# Header row
sheet.write(0, 0, "Region",  style=CellStyle(bold=True, bg_color="#4472C4", text_color="#FFF"))
sheet.write(0, 1, "Revenue", style=CellStyle(bold=True, bg_color="#4472C4", text_color="#FFF"))
sheet.write(0, 2, "Growth",  style=CellStyle(bold=True, bg_color="#4472C4", text_color="#FFF"))

# Data rows
data = [("North", 1_240_000, 0.12), ("South", 980_000, -0.04), ("West", 1_560_000, 0.23)]
for r, (region, revenue, growth) in enumerate(data, start=1):
    sheet.write(r, 0, region)
    sheet.write(r, 1, revenue, style=CellStyle(num_format="#,##0", align="right"))
    sheet.write(r, 2, growth,  style=CellStyle(num_format="0.0%",  align="right",
                                                text_color="#C00000" if growth < 0 else "#375623"))

sheet.set_freeze_panes(row=1, col=1)
sheet.set_column_width(0, 120)
sheet.set_column_width(1, 140)

excel_download_button(sheet, file_name="q4_revenue.xlsx")
render_sheet(sheet, height=300)
```

---

## API reference

### `Sheet`

```python
sheet = Sheet(name="Sheet1")
```

| Method | Description |
|---|---|
| `sheet.write(row, col, value, rowspan=1, colspan=1, style=None)` | Write a value to the grid |
| `sheet.set_freeze_panes(row=0, col=0)` | Freeze the first N rows and M columns |
| `sheet.set_column_width(col, width_px)` | Set column width in pixels |
| `sheet.hide_row(row)` | Mark a row as hidden |
| `sheet.hide_column(col)` | Mark a column as hidden |
| `sheet.get_cell(row, col)` | Return the `Cell` at a position, or `None` |

All coordinates are 0-indexed.

---

### `CellStyle`

```python
CellStyle(
    bg_color   = "#4472C4",   # hex colour, #RGB or #RRGGBB
    text_color = "#FFFFFF",
    bold       = True,
    italic     = False,
    font_size  = 13,          # points
    align      = "center",    # "left" | "center" | "right"
    wrap_text  = False,
    border     = True,
    num_format = "#,##0.00",  # Excel-style format string
    is_header  = False,       # renders as <th> instead of <td>
)
```

**Supported `num_format` values:**

| Format string | Example output |
|---|---|
| `#,##0` | `1,234` |
| `#,##0.0` | `1,234.5` |
| `#,##0.00` | `1,234.56` |
| `#,##0.000` | `1,234.567` |
| `$#,##0` | `$1,234` |
| `0.0%` | `12.3%` |

---

### `render_sheet`

```python
render_sheet(sheet, height=800)
```

Renders the grid inside a Streamlit `components.v1.html` block. The component handles scrolling internally — set `height` to match your layout.

---

### `excel_download_button`

```python
excel_download_button(sheet, file_name="export.xlsx", label="📥 Download Excel")
```

Adds a Streamlit download button. The workbook is generated in-memory; nothing is written to disk.

---

## Recipes

### Multi-level headers with colspan

```python
sheet.write(0, 0, "Property Specs", colspan=3,
            style=CellStyle(bold=True, bg_color="#333", text_color="#FFF", align="center"))
sheet.write(1, 0, "Rooms",   style=CellStyle(bold=True))
sheet.write(1, 1, "Bedrooms",style=CellStyle(bold=True))
sheet.write(1, 2, "Baths",   style=CellStyle(bold=True))
sheet.set_freeze_panes(row=2)
```

### Grouped row labels with rowspan

```python
# Group rows by category
sheet.write(1, 0, "Category A", rowspan=3,
            style=CellStyle(bold=True, align="center", bg_color="#F0F0F0"))
sheet.write(1, 1, "Row 1 value")
sheet.write(2, 1, "Row 2 value")
sheet.write(3, 1, "Row 3 value")
```

### Heatmap conditional formatting

```python
import numpy as np

values = np.random.rand(10, 5)
vmin, vmax = values.min(), values.max()

for r, row in enumerate(values):
    for c, val in enumerate(row):
        norm = (val - vmin) / (vmax - vmin)
        r_ch = int(255 * (1 - norm))
        g_ch = int(255 * norm)
        bg   = f"#{r_ch:02X}{g_ch:02X}00"
        lum  = (0.299 * r_ch + 0.587 * g_ch) / 255
        fg   = "#FFF" if lum < 0.5 else "#000"
        sheet.write(r, c, round(val, 3),
                    style=CellStyle(bg_color=bg, text_color=fg, align="center"))
```

### Hiding rows based on a filter

```python
for i, row in df.iterrows():
    if row["value"] > threshold:
        sheet.hide_row(i + HEADER_ROWS)
    sheet.write(i + HEADER_ROWS, 0, row["label"])
    sheet.write(i + HEADER_ROWS, 1, row["value"])
```

---

## Architecture

```
excel_grid/
├── style.py          CellStyle dataclass — no rendering logic
├── cell.py           Cell — value, span geometry, display_value()
├── sheet.py          Sheet — grid state, merge tracking, display hints
├── renderers/
│   ├── html.py       HTMLRenderer — Sheet → self-contained HTML/JS string
│   └── excel.py      ExcelRenderer — Sheet → .xlsx bytes via xlsxwriter
└── components.py     render_sheet(), excel_download_button() — Streamlit wrappers
```

The data layer (`style`, `cell`, `sheet`) has no knowledge of any rendering target. `streamlit` is imported lazily inside `components.py` so the rest of the package works in plain Python scripts and tests without Streamlit installed.

---

## Demo app

The included `example_app.py` is a stress test using the California Housing dataset (requires `scikit-learn`):

```bash
pip install scikit-learn
streamlit run example_app.py
```

It demonstrates:
- 3-level header rows with colspan grouping
- `rowspan` grouping by `HouseAge`
- Per-cell heatmap colouring with automatic contrast text
- Dynamic row hiding via the outlier slider
- Dynamic column hiding via the multiselect
- Freeze panes on header rows and the grouping column
- One-click XLSX export
