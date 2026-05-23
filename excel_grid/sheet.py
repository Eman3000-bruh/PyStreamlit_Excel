from __future__ import annotations
from typing import Any, Iterator

from .cell import Cell
from .style import CellStyle


class Sheet:
    """The core data model for a grid.

    Stores cells by their (row, col) origin, tracks which positions are
    covered by a merge, and holds display hints (freeze panes, hidden
    rows/columns, column widths) that both renderers consume.

    All coordinates are 0-indexed.

    Example
    -------
    >>> sheet = Sheet("Revenue")
    >>> sheet.write(0, 0, "Partner", style=CellStyle(bold=True))
    >>> sheet.write(0, 1, "Q1–Q4", colspan=4, style=CellStyle(bold=True))
    >>> sheet.set_column_width(0, 160)
    >>> sheet.set_freeze_panes(row=1, col=1)
    """

    def __init__(self, name: str = "Sheet1") -> None:
        self.name = name

        # Origin cell for each written position.
        self._grid: dict[tuple[int, int], Cell] = {}

        # Positions covered by a merge but not the origin of any cell.
        # The renderers skip these when building table output.
        self._merged: set[tuple[int, int]] = set()

        self.col_widths:  dict[int, int] = {}
        self.hidden_rows: set[int]       = set()
        self.hidden_cols: set[int]       = set()
        self.freeze_row:  int            = 0
        self.freeze_col:  int            = 0

        self._max_row: int = 0
        self._max_col: int = 0

    # ── Dimensions ────────────────────────────────────────────────────────────

    @property
    def max_row(self) -> int:
        """Highest occupied row index (inclusive)."""
        return self._max_row

    @property
    def max_col(self) -> int:
        """Highest occupied column index (inclusive)."""
        return self._max_col

    # ── Display configuration ─────────────────────────────────────────────────

    def set_column_width(self, col: int, width_px: int) -> None:
        """Set the pixel width of a column."""
        self.col_widths[col] = width_px

    def set_freeze_panes(self, row: int = 0, col: int = 0) -> None:
        """Freeze the first ``row`` rows and first ``col`` columns.

        Mirrors Excel freeze-panes semantics: ``set_freeze_panes(row=2, col=1)``
        keeps rows 0–1 and column 0 visible while scrolling.
        """
        self.freeze_row = max(0, row)
        self.freeze_col = max(0, col)

    def hide_row(self, row: int) -> None:
        """Mark a row as hidden. Hidden rows are skipped by both renderers."""
        self.hidden_rows.add(row)

    def hide_column(self, col: int) -> None:
        """Mark a column as hidden. Hidden columns are skipped by both renderers."""
        self.hidden_cols.add(col)

    # ── Writing ───────────────────────────────────────────────────────────────

    def write(
        self,
        row: int,
        col: int,
        value: Any = "",
        rowspan: int = 1,
        colspan: int = 1,
        style: CellStyle | None = None,
    ) -> None:
        """Write a value to the grid at (``row``, ``col``).

        If ``rowspan`` or ``colspan`` are greater than 1, all positions covered
        by the merge are recorded in ``_merged`` so renderers know to skip them.
        Writing to a position that is already covered by an existing merge is
        silently allowed — the new cell will overwrite the coverage record.

        Parameters
        ----------
        row, col : 0-based grid coordinates.
        value    : Any scalar value; strings, ints, floats all work.
        rowspan  : Rows spanned by this cell (default 1).
        colspan  : Columns spanned by this cell (default 1).
        style    : Cell style; a default ``CellStyle`` is used if omitted.
        """
        cell = Cell(value, rowspan, colspan, style)
        self._grid[(row, col)] = cell

        for r in range(row, row + cell.rowspan):
            for c in range(col, col + cell.colspan):
                if (r, c) != (row, col):
                    self._merged.add((r, c))

        self._max_row = max(self._max_row, row + cell.rowspan - 1)
        self._max_col = max(self._max_col, col + cell.colspan - 1)

    # ── Read access ───────────────────────────────────────────────────────────

    def get_cell(self, row: int, col: int) -> Cell | None:
        """Return the Cell at (row, col), or None if the position is empty."""
        return self._grid.get((row, col))

    def is_merged(self, row: int, col: int) -> bool:
        """True if (row, col) is covered by a merge and is not its origin."""
        return (row, col) in self._merged

    def iter_cells(self) -> Iterator[tuple[int, int, Cell]]:
        """Yield (row, col, Cell) for every origin cell in the grid."""
        yield from (
            (r, c, cell) for (r, c), cell in self._grid.items()
        )

    def __repr__(self) -> str:
        return (
            f"Sheet(name={self.name!r}, "
            f"rows={self._max_row + 1}, cols={self._max_col + 1}, "
            f"cells={len(self._grid)})"
        )
