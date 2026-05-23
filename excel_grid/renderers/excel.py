from __future__ import annotations
import io

import xlsxwriter

from ..sheet import Sheet


class ExcelRenderer:
    """Converts a Sheet to .xlsx bytes via xlsxwriter.

    Format objects are cached by their dict representation to avoid
    xlsxwriter's hard limit of 65,536 unique formats per workbook.
    In practice this matters for heatmap-heavy sheets where every cell
    carries a unique background colour.
    """

    # xlsxwriter column widths are in character units, not pixels.
    # 7 px ≈ 1 character width for Calibri 11pt.
    _PX_TO_CHAR = 7.0

    def __init__(self, sheet: Sheet) -> None:
        self._sheet = sheet

    def render(self) -> bytes:
        """Return the workbook as raw bytes suitable for a download response."""
        s      = self._sheet
        output = io.BytesIO()

        workbook  = xlsxwriter.Workbook(output, {"in_memory": True})
        worksheet = workbook.add_worksheet(s.name)

        fmt_cache: dict[str, xlsxwriter.format.Format] = {}

        self._apply_columns(s, worksheet, workbook, fmt_cache)
        self._apply_rows(s, worksheet)
        self._write_cells(s, worksheet, workbook, fmt_cache)
        self._apply_freeze(s, worksheet)

        workbook.close()
        return output.getvalue()

    # ─────────────────────────────────────────────────────────────────────────

    def _get_format(
        self,
        fmt_dict: dict,
        workbook: xlsxwriter.Workbook,
        cache: dict,
    ) -> xlsxwriter.format.Format:
        key = str(fmt_dict)
        if key not in cache:
            cache[key] = workbook.add_format(fmt_dict)
        return cache[key]

    def _apply_columns(self, s: Sheet, ws, wb, cache: dict) -> None:
        for c in range(s.max_col + 1):
            width_chars = s.col_widths.get(c, 130) / self._PX_TO_CHAR
            options     = {"hidden": True} if c in s.hidden_cols else {}
            ws.set_column(c, c, width_chars, None, options)

    def _apply_rows(self, s: Sheet, ws) -> None:
        for r in s.hidden_rows:
            ws.set_row(r, None, None, {"hidden": True})

    def _write_cells(self, s: Sheet, ws, wb, cache: dict) -> None:
        for r in range(s.max_row + 1):
            for c in range(s.max_col + 1):
                if s.is_merged(r, c):
                    continue

                cell = s.get_cell(r, c)
                if cell is None:
                    continue

                fmt = self._get_format(cell.style.to_excel_format(), wb, cache)

                if cell.rowspan > 1 or cell.colspan > 1:
                    ws.merge_range(
                        r, c,
                        r + cell.rowspan - 1,
                        c + cell.colspan - 1,
                        cell.value,
                        fmt,
                    )
                else:
                    ws.write(r, c, cell.value, fmt)

    def _apply_freeze(self, s: Sheet, ws) -> None:
        if s.freeze_row or s.freeze_col:
            ws.freeze_panes(s.freeze_row, s.freeze_col)
