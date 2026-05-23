"""
excel_grid — Streamlit-native Excel-like data grid.

Quick start
-----------
    from excel_grid import Sheet, CellStyle, render_sheet, excel_download_button

    sheet = Sheet("Report")
    sheet.write(0, 0, "Header", style=CellStyle(bold=True, bg_color="#4472C4", text_color="#FFF"))
    sheet.write(1, 0, 1234.5,   style=CellStyle(num_format="#,##0.00", align="right"))
    sheet.set_freeze_panes(row=1, col=1)
    render_sheet(sheet)

Package layout
--------------
    excel_grid/
    ├── style.py          CellStyle
    ├── cell.py           Cell
    ├── sheet.py          Sheet
    ├── renderers/
    │   ├── html.py       HTMLRenderer   (Sheet → self-contained HTML/JS)
    │   └── excel.py      ExcelRenderer  (Sheet → .xlsx bytes)
    └── components.py     render_sheet(), excel_download_button()
"""

from .style import CellStyle
from .cell import Cell
from .sheet import Sheet
from .components import render_sheet, excel_download_button

__all__ = [
    "CellStyle",
    "Cell",
    "Sheet",
    "render_sheet",
    "excel_download_button",
]
