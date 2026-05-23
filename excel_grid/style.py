from __future__ import annotations
from dataclasses import dataclass
from typing import Optional


@dataclass
class CellStyle:
    """Visual properties for a single cell.

    Used by both renderers: ``to_css()`` drives the HTML output,
    ``to_excel_format()`` drives xlsxwriter.
    All color values accept standard hex strings (#RGB or #RRGGBB).
    """

    # ── Colour ────────────────────────────────────────────────────────────────
    bg_color:   Optional[str] = None
    text_color: Optional[str] = None

    # ── Font ─────────────────────────────────────────────────────────────────
    bold:      bool = False
    italic:    bool = False
    font_size: int  = 13   # points; used as-is for both HTML px and xlsxwriter pt

    # ── Layout ───────────────────────────────────────────────────────────────
    align:     str  = "center"   # "left" | "center" | "right"
    wrap_text: bool = False
    padding:   str  = "6px 8px"

    # ── Border ───────────────────────────────────────────────────────────────
    border: bool = True

    # ── Number formatting (Excel-style format string) ─────────────────────────
    num_format: Optional[str] = None

    # When True the cell is emitted as <th> rather than <td> in HTML output.
    is_header: bool = False

    # ─────────────────────────────────────────────────────────────────────────

    def _hex6(self, color: Optional[str]) -> Optional[str]:
        """Expand 3-digit #RGB shorthand to 6-digit #RRGGBB.
        xlsxwriter rejects the short form; HTML handles both."""
        if color and color.startswith("#") and len(color) == 4:
            return "#" + color[1] * 2 + color[2] * 2 + color[3] * 2
        return color

    def to_css(self) -> str:
        """Return an inline CSS string for this style."""
        parts = [
            f"padding: {self.padding};",
            f"font-size: {self.font_size}px;",
            f"text-align: {self.align};",
            "vertical-align: middle;",
            "background-clip: padding-box;",
            f"background-color: {self.bg_color or '#FFFFFF'};",
            f"color: {self.text_color or '#000000'};",
        ]
        if self.bold:
            parts.append("font-weight: bold;")
        if self.italic:
            parts.append("font-style: italic;")
        if self.wrap_text:
            parts.append("white-space: normal; word-wrap: break-word;")
        if self.border:
            parts.append("border: 1px solid #d0d7de;")
        return " ".join(parts)

    def to_excel_format(self) -> dict:
        """Return a format dict compatible with ``xlsxwriter.Workbook.add_format``."""
        fmt: dict = {
            "align":     self.align,
            "valign":    "vcenter",
            "font_size": self.font_size,
        }
        if self.bg_color:
            fmt["bg_color"]   = self._hex6(self.bg_color)
        if self.text_color:
            fmt["font_color"] = self._hex6(self.text_color)
        if self.bold:
            fmt["bold"]       = True
        if self.italic:
            fmt["italic"]     = True
        if self.num_format:
            fmt["num_format"] = self.num_format
        if self.border:
            fmt["border"]     = 1
        if self.wrap_text:
            fmt["text_wrap"]  = True
        return fmt
