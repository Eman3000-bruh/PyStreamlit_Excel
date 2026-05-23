from __future__ import annotations
import json
import uuid

from ..sheet import Sheet


# ── Column label helper ───────────────────────────────────────────────────────

_COL_NAME_CACHE: dict[int, str] = {}


def _col_name(n: int) -> str:
    """Convert a 0-based column index to an Excel column label.
    0 → 'A', 25 → 'Z', 26 → 'AA', etc. Results are cached.
    """
    if n in _COL_NAME_CACHE:
        return _COL_NAME_CACHE[n]
    result, i = "", n
    while i >= 0:
        result = chr(i % 26 + 65) + result
        i = i // 26 - 1
    _COL_NAME_CACHE[n] = result
    return result


# ── Stylesheet ────────────────────────────────────────────────────────────────
# Static string — never interpolated with Python values.

_CSS = """\
html, body {
    height: 100%; margin: 0; padding: 0;
    overflow: hidden; font-family: Calibri, sans-serif;
}
.eg-hidden-col, .eg-hidden-row, .eg-hidden-cell { display: none !important; }

.eg-col-hdr, .eg-row-hdr, .eg-origin {
    background: #f3f2f1; color: #323130; font-size: 13px;
    border-right: 1px solid #c8c6c4; border-bottom: 1px solid #c8c6c4;
    user-select: none; box-sizing: border-box;
}
.eg-col-hdr { height: 28px; line-height: 28px; padding: 0; }
.eg-row-hdr { width: 40px; }
.eg-origin  { cursor: pointer; text-align: center; }
.eg-origin:hover, .eg-col-hdr:hover, .eg-row-hdr:hover { background: #e1dfdd; }

.eg-hide-btn {
    opacity: 0; cursor: pointer;
    color: #a19f9d; font-size: 11px;
    transition: opacity 0.1s;
}
.eg-hide-btn:hover { color: #d13438; font-weight: bold; }
.eg-col-hdr:hover .eg-hide-btn,
.eg-row-hdr:hover .eg-hide-btn { opacity: 1; }

::-webkit-scrollbar { width: 10px; height: 10px; }
::-webkit-scrollbar-track { background: #f1f1f1; }
::-webkit-scrollbar-thumb { background: #c1c1c1; border-radius: 5px; }
::-webkit-scrollbar-thumb:hover { background: #a8a8a8; }
"""


# ── JS grid engine ────────────────────────────────────────────────────────────
# Pure JavaScript — no Python string formatting in this block.
# Dynamic values (hidden cols/rows, freeze counts) are passed via the
# table._state object bootstrapped by _js_init().

_JS_ENGINE = r"""
function egRender(table) {
    const s = table._state;

    // Apply column visibility to <col> elements and header <th> cells.
    table.querySelectorAll('colgroup col[data-c]').forEach(el => {
        const c = el.dataset.c;
        if (c !== 'origin') el.classList.toggle('eg-hidden-col', s.hiddenCols.has(+c));
    });
    table.querySelectorAll('th.eg-col-hdr[data-c]').forEach(th => {
        th.classList.toggle('eg-hidden-col', s.hiddenCols.has(+th.dataset.c));
    });

    // Apply row visibility to <tr> elements.
    table.querySelectorAll('tr[data-r]').forEach(tr => {
        const r = tr.dataset.r;
        if (r !== 'origin') tr.classList.toggle('eg-hidden-row', s.hiddenRows.has(+r));
    });

    // Recalculate colspan/rowspan values accounting for hidden rows and columns.
    // Each cell stores its original start/end coordinates in data attributes so
    // we can recompute the effective visible span on every render.
    table.querySelectorAll('td[data-cs], th[data-cs]').forEach(cell => {
        if (cell.classList.contains('eg-row-hdr')) return;

        const cs = +cell.dataset.cs, ce = +cell.dataset.ce;
        const rs = +cell.dataset.rs, re = +cell.dataset.re;

        let firstVisC = -1, visC = 0;
        for (let i = cs; i <= ce; i++) {
            if (!s.hiddenCols.has(i)) { visC++; if (firstVisC === -1) firstVisC = i; }
        }
        let firstVisR = -1, visR = 0;
        for (let i = rs; i <= re; i++) {
            if (!s.hiddenRows.has(i)) { visR++; if (firstVisR === -1) firstVisR = i; }
        }

        if (visC === 0 || visR === 0) {
            cell.classList.add('eg-hidden-cell');
        } else {
            cell.classList.remove('eg-hidden-cell');
            if (visC > 1) cell.setAttribute('colspan', visC); else cell.removeAttribute('colspan');
            if (visR > 1) cell.setAttribute('rowspan', visR); else cell.removeAttribute('rowspan');
        }
        cell.dataset.fvc = firstVisC;
        cell.dataset.fvr = firstVisR;
    });

    // Build cumulative left offsets per column for sticky positioning.
    const colLefts = { origin: 0 };
    let left = 40;
    for (let i = 0; i <= s.maxCol; i++) {
        colLefts[i] = left;
        if (!s.hiddenCols.has(i)) {
            const el = table.querySelector(`col[data-c="${i}"]`);
            if (el) left += parseFloat(el.style.width) || 0;
        }
    }

    // Build cumulative top offsets per row for sticky positioning.
    const rowTops = { origin: 0 };
    let top = 28;
    for (let i = 0; i <= s.maxRow; i++) {
        rowTops[i] = top;
        if (!s.hiddenRows.has(i)) {
            const el = table.querySelector(`tr[data-r="${i}"]`);
            if (el) top += el.offsetHeight;
        }
    }

    // Apply sticky positioning and z-index for freeze panes.
    // Merged cells use their first-visible row/col coordinate for positioning.
    table.querySelectorAll('th, td').forEach(cell => {
        const rAttr = cell.dataset.r;
        const cAttr = cell.dataset.c;

        let logR = (rAttr === 'origin') ? -1
                 : (cell.dataset.fvr !== undefined ? +cell.dataset.fvr : +rAttr);
        let logC = (cAttr === 'origin') ? -1
                 : (cell.dataset.fvc !== undefined ? +cell.dataset.fvc : +cAttr);

        if (rAttr === 'origin' && cAttr === 'origin') { logR = -1; logC = -1; }
        else if (rAttr === 'origin') { logR = -1; logC = +cAttr; }
        else if (cAttr === 'origin') { logC = -1; logR = +rAttr; }

        const frozenR = logR < s.freezeRows;
        const frozenC = logC < s.freezeCols;

        cell.style.position = '';
        cell.style.top      = '';
        cell.style.left     = '';
        cell.style.zIndex   = '';
        cell.style.boxShadow = '';

        if (!frozenR && !frozenC) return;

        cell.style.position = 'sticky';
        if (frozenR) cell.style.top  = (rowTops[rAttr === 'origin' ? 'origin' : logR] ?? 0) + 'px';
        if (frozenC) cell.style.left = (colLefts[cAttr === 'origin' ? 'origin' : logC] ?? 0) + 'px';

        // z-index stacking: corner origin > header row/col > data freeze intersection > single-axis frozen
        cell.style.zIndex =
            (logR === -1 && logC === -1) ? 1000 :
            (logR === -1 && frozenC)     ?  900 :
            (logC === -1 && frozenR)     ?  900 :
            (frozenR && frozenC)         ?  800 :
            (logR === -1 || logC === -1) ?  700 : 600;

        // Draw freeze boundary shadows on the last frozen row and column.
        const shadows = [];
        if (frozenR && logR === s.freezeRows - 1 && rAttr !== 'origin')
            shadows.push('inset 0 -2px 0 0 rgba(0,0,0,0.1)');
        if (frozenC && logC === s.freezeCols - 1 && cAttr !== 'origin')
            shadows.push('inset -2px 0 0 0 rgba(0,0,0,0.1)');
        if (shadows.length) cell.style.boxShadow = shadows.join(', ');
    });
}
"""


def _js_init(table_id: str, sheet: Sheet) -> str:
    """Return the JS bootstrap block for a specific table instance.

    This is the only place Python values are interpolated into JavaScript.
    Everything else lives in the static _JS_ENGINE string above.
    """
    config = json.dumps({
        "hiddenCols": list(sheet.hidden_cols),
        "hiddenRows": list(sheet.hidden_rows),
        "freezeRows": sheet.freeze_row,
        "freezeCols": sheet.freeze_col,
        "maxRow":     sheet.max_row,
        "maxCol":     sheet.max_col,
    })

    return f"""
(function() {{
    const table = document.getElementById('{table_id}');
    if (!table) return;

    const cfg = {config};
    table._state = {{
        hiddenCols: new Set(cfg.hiddenCols),
        hiddenRows: new Set(cfg.hiddenRows),
        freezeRows: cfg.freezeRows,
        freezeCols: cfg.freezeCols,
        maxRow:     cfg.maxRow,
        maxCol:     cfg.maxCol,
    }};

    // Public API — called by onclick handlers in the generated HTML.
    window['{table_id}'] = {{
        hideCol:   (c) => {{ table._state.hiddenCols.add(c);                                   egRender(table); }},
        hideRow:   (r) => {{ table._state.hiddenRows.add(r);                                   egRender(table); }},
        unhideAll: ()  => {{ table._state.hiddenCols.clear(); table._state.hiddenRows.clear(); egRender(table); }},
    }};

    // Defer first render until layout is settled so row heights are accurate.
    setTimeout(() => egRender(table), 0);
}})();
"""


# ── Renderer ──────────────────────────────────────────────────────────────────

class HTMLRenderer:
    """Converts a Sheet to a self-contained HTML/JS string.

    The output is a single string with an embedded ``<style>``, ``<table>``,
    and ``<script>`` block — no external dependencies or network requests.
    Each render call generates a unique table ID so multiple grids can
    coexist on the same Streamlit page without state collisions.
    """

    def __init__(self, sheet: Sheet) -> None:
        self._sheet = sheet

    def render(self) -> str:
        s   = self._sheet
        tid = f"eg_{uuid.uuid4().hex[:8]}"

        parts = [
            f"<style>{_CSS}</style>",
            f'<div id="container_{tid}" style="'
            f'width:100%;height:100%;overflow:auto;position:relative;background:#fff;">',
            f'<table id="{tid}" style="'
            f'border-collapse:collapse;table-layout:fixed;width:max-content;">',
            self._colgroup(s),
            self._thead(s, tid),
            self._tbody(s, tid),
            "</table></div>",
            f"<script>{_JS_ENGINE}\n{_js_init(tid, s)}</script>",
        ]
        return "".join(parts)

    # ─────────────────────────────────────────────────────────────────────────

    def _colgroup(self, s: Sheet) -> str:
        out = ["<colgroup>"]
        out.append('<col data-c="origin" style="width:40px;min-width:40px;max-width:40px;">')
        for c in range(s.max_col + 1):
            w = s.col_widths.get(c, 130)
            out.append(f'<col data-c="{c}" style="width:{w}px;min-width:{w}px;max-width:{w}px;">')
        out.append("</colgroup>")
        return "".join(out)

    def _thead(self, s: Sheet, tid: str) -> str:
        out = ['<thead><tr data-r="origin">']

        # Origin corner cell — clicking it restores all hidden rows and columns.
        out.append(
            f'<th class="eg-origin" data-r="origin" data-c="origin" '
            f"onclick=\"window['{tid}'].unhideAll()\" "
            f'title="Click to unhide all">◢</th>'
        )

        for c in range(s.max_col + 1):
            out.append(
                f'<th class="eg-col-hdr" data-r="origin" data-c="{c}">'
                f'<div style="display:flex;justify-content:space-between;align-items:center;'
                f'width:100%;padding:0 4px;box-sizing:border-box;">'
                f'<span style="flex-grow:1;text-align:center;">{_col_name(c)}</span>'
                f'<span class="eg-hide-btn" '
                f"onclick=\"window['{tid}'].hideCol({c})\" "
                f'title="Hide column">✖</span>'
                f"</div></th>"
            )

        out.append("</tr></thead>")
        return "".join(out)

    def _tbody(self, s: Sheet, tid: str) -> str:
        out = ["<tbody>"]
        for r in range(s.max_row + 1):
            out.append(f'<tr data-r="{r}">')

            out.append(
                f'<th class="eg-row-hdr" data-r="{r}" data-c="origin">'
                f'<div style="display:flex;justify-content:space-between;align-items:center;'
                f'width:100%;padding:0 4px;box-sizing:border-box;">'
                f'<span style="flex-grow:1;text-align:center;">{r + 1}</span>'
                f'<span class="eg-hide-btn" '
                f"onclick=\"window['{tid}'].hideRow({r})\" "
                f'title="Hide row">✖</span>'
                f"</div></th>"
            )

            for c in range(s.max_col + 1):
                out.append(self._cell_html(s, r, c))

            out.append("</tr>")
        out.append("</tbody>")
        return "".join(out)

    def _cell_html(self, s: Sheet, r: int, c: int) -> str:
        # Cells covered by a merge don't emit their own <td> — the origin
        # cell carries the rowspan/colspan attributes instead.
        if s.is_merged(r, c):
            return ""

        cell = s.get_cell(r, c)

        # data-cs/ce/rs/re store the original span boundaries so the JS engine
        # can recalculate effective spans when rows or columns are hidden.
        span = f'data-cs="{c}" data-ce="{c}" data-rs="{r}" data-re="{r}"'

        if cell is None:
            return f'<td style="border:1px solid #d0d7de;padding:6px 8px;" {span}></td>'

        ce   = c + cell.colspan - 1
        re   = r + cell.rowspan - 1
        span = f'data-cs="{c}" data-ce="{ce}" data-rs="{r}" data-re="{re}"'
        tag  = "th" if cell.style.is_header else "td"
        css  = cell.style.to_css()
        val  = cell.display_value()

        return f'<{tag} style="{css}" {span}>{val}</{tag}>'
