from __future__ import annotations

from .sheet import Sheet
from .renderers.html import HTMLRenderer
from .renderers.excel import ExcelRenderer


def render_sheet(sheet: Sheet, height: int = 800) -> None:
    """Render a Sheet as an interactive HTML grid in Streamlit.

    Uses ``streamlit.components.v1.html`` under the hood.
    The rendered component includes freeze panes, hidden row/column
    controls, and dynamic span recalculation via the embedded JS engine.

    Parameters
    ----------
    sheet  : Sheet to render.
    height : Component height in pixels.
    """
    import streamlit.components.v1 as _components
    html = HTMLRenderer(sheet).render()
    _components.html(html, height=height, scrolling=False)


def excel_download_button(
    sheet: Sheet,
    file_name: str = "export.xlsx",
    label: str = "📥 Download Excel",
) -> None:
    """Render a Streamlit download button that exports the Sheet as .xlsx.

    The workbook is generated in-memory via ``ExcelRenderer`` and streamed
    directly to the browser — no temporary files are written to disk.

    Parameters
    ----------
    sheet     : Sheet to export.
    file_name : Name of the downloaded file.
    label     : Button label text.
    """
    import streamlit as _st
    data = ExcelRenderer(sheet).render()
    _st.download_button(
        label=label,
        data=data,
        file_name=file_name,
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        type="primary",
        use_container_width=True,
    )
