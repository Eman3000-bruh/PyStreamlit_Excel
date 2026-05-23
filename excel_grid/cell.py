from __future__ import annotations
import html as _html
from typing import Any, Callable

from .style import CellStyle


# Excel-style format string → Python formatter.
# Dict lookup avoids the substring-collision bugs that come with if/elif chains
# (e.g. "#,##0" matching before "#,##0.0").
_NUM_FORMATTERS: dict[str, Callable[[float], str]] = {
    "$#,##0":    lambda v: f"${int(v):,}",
    "#,##0":     lambda v: f"{int(v):,}",
    "#,##0.0":   lambda v: f"{v:,.1f}",
    "#,##0.00":  lambda v: f"{v:,.2f}",
    "#,##0.000": lambda v: f"{v:,.3f}",
    "0.0%":      lambda v: f"{v * 100:.1f}%",
}


class Cell:
    """A single grid cell: value + span geometry + style.

    Attributes
    ----------
    value   : Raw value written to the cell.
    rowspan : Row span (≥ 1).
    colspan : Column span (≥ 1).
    style   : Visual properties for this cell.
    """

    __slots__ = ("value", "rowspan", "colspan", "style")

    def __init__(
        self,
        value: Any = "",
        rowspan: int = 1,
        colspan: int = 1,
        style: CellStyle | None = None,
    ) -> None:
        self.value   = value
        self.rowspan = max(1, rowspan)
        self.colspan = max(1, colspan)
        self.style   = style or CellStyle()

    def display_value(self) -> str:
        """HTML-safe display string, with num_format applied if applicable.

        Newlines become ``<br>`` tags so multi-line cell content renders
        correctly inside the HTML table.
        """
        val = self.value
        fmt = self.style.num_format
        if isinstance(val, (int, float)) and fmt and fmt in _NUM_FORMATTERS:
            val = _NUM_FORMATTERS[fmt](val)
        return _html.escape(str(val)).replace("\n", "<br>")

    def __repr__(self) -> str:
        return (
            f"Cell(value={self.value!r}, "
            f"rowspan={self.rowspan}, colspan={self.colspan})"
        )
