"""
complex_sklearn_app.py
----------------------
End-to-end stress test for excel_grid.
Features: 
- Dynamic data updates via Streamlit widgets.
- Heavy per-cell conditional formatting (Custom Heatmap interpolation).
- Complex multi-level headers (colspan) & grouped categorical columns (rowspan).
- Real-time hiding of rows (outliers) and columns.
"""

import streamlit as st
import pandas as pd
import numpy as np

# Ensure scikit-learn is installed for the dataset
try:
    from sklearn.datasets import fetch_california_housing
except ImportError:
    st.error("Please install scikit-learn to run this test: `pip install scikit-learn`")
    st.stop()

from excel_grid import Sheet, CellStyle, render_sheet, excel_download_button

# ─── 1. Core Utilities & Data Loading ─────────────────────────────────────────

@st.cache_data
def load_data(max_rows: int = 500) -> pd.DataFrame:
    """Loads California Housing data, sorts by HouseAge to test rowspans."""
    data = fetch_california_housing(as_frame=True)
    df = data.frame
    # Sort by HouseAge so we can group consecutive values with rowspans
    df = df.sort_values("HouseAge").reset_index(drop=True)
    return df.head(max_rows)

def interpolate_color(val: float, min_val: float, max_val: float, theme: str) -> tuple[str, str]:
    """
    Interpolates a value into an HTML hex background color, and returns an 
    appropriate contrasting text color (white/black).
    """
    if pd.isna(val) or max_val == min_val:
        return "#FFFFFF", "#000000"
        
    # Normalize value between 0 and 1
    norm = max(0.0, min(1.0, (val - min_val) / (max_val - min_val)))
    
    if theme == "Red-Yellow-Green":
        # Multi-stop gradient: Red(0) -> Yellow(0.5) -> Green(1)
        if norm < 0.5:
            r, g, b = 255, int(255 * (norm * 2)), 0
        else:
            r, g, b = int(255 * (1 - (norm - 0.5) * 2)), 255, 0
    elif theme == "Blues":
        # White(0) -> Dark Blue(1)
        r, g, b = int(255 * (1 - norm)), int(255 * (1 - norm)), 255
    else: # "Magma" approximation
        r, g, b = int(255 * norm), 0, int(150 * norm)

    bg_hex = f"#{r:02X}{g:02X}{b:02X}"
    
    # Calculate luminance to decide text color (black vs white)
    luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255
    text_hex = "#FFFFFF" if luminance < 0.5 else "#000000"
    
    return bg_hex, text_hex


# ─── 2. Application UI & Controls ─────────────────────────────────────────────

st.set_page_config(page_title="Sklearn Grid Stress Test", layout="wide")

with st.sidebar:
    st.header("⚙️ Grid Constraints")
    
    # Dynamic Updates: Changing these sliders triggers a full re-render
    n_rows = st.slider("Dataset Rows", min_value=50, max_value=2000, value=250, step=50,
                       help="Warning: High values will heavily stress the browser DOM rendering.")
    
    theme = st.selectbox("Heatmap Theme",["Red-Yellow-Green", "Blues", "Magma"])
    
    st.divider()
    st.header("🔍 Filters & Visibility")
    
    # Test hiding rows dynamically
    outlier_limit = st.slider("Hide Population Outliers >", min_value=1000, max_value=10000, value=5000)
    
    # Test hiding columns dynamically
    all_cols =["MedInc", "AveRooms", "AveBedrms", "Population", "AveOccup", "Latitude", "Longitude"]
    show_cols = st.multiselect("Visible Features", all_cols, default=all_cols)

# Load data dynamically based on slider
df = load_data(n_rows)

# Precalculate min/max for color gradients
col_stats = {col: (df[col].min(), df[col].max()) for col in df.columns if col != "HouseAge"}

# ─── 3. Grid Generation ───────────────────────────────────────────────────────

sheet = Sheet(f"CA_Housing_{n_rows}")

# ---- A. Complex Headers (Colspans)
TOP_HDR = CellStyle(bold=True, bg_color="#1E1E1E", text_color="#FFFFFF", align="center", border=True, is_header=True)
SUB_HDR = CellStyle(bold=True, bg_color="#333333", text_color="#DDDDDD", align="center", border=True, is_header=True)

sheet.write(0, 0, "California Housing Dynamics (SciKit-Learn)", colspan=9, style=TOP_HDR)

# Level 2 Headers spanning categorical groupings
sheet.write(1, 0, "Demographics", colspan=1, style=SUB_HDR)  # Age grouping
sheet.write(1, 1, "Economics", colspan=1, style=SUB_HDR)     # Income
sheet.write(1, 2, "Property Specs", colspan=4, style=SUB_HDR) # Rooms/Occupants
sheet.write(1, 6, "Geo Location", colspan=2, style=SUB_HDR)  # Lat/Lon
sheet.write(1, 8, "Target Variable", colspan=1, style=SUB_HDR) # Price

# Level 3 Headers (Actual column names)
grid_columns =[
    ("HouseAge", "center", None),
    ("MedInc", "right", "#,##0.000"),
    ("AveRooms", "right", "#,##0.0"),
    ("AveBedrms", "right", "#,##0.0"),
    ("Population", "right", "#,##0"),
    ("AveOccup", "right", "#,##0.0"),
    ("Latitude", "right", "0.000"),
    ("Longitude", "right", "0.000"),
    ("MedHouseVal", "right", "$#,##0.00"),
]

for col_idx, (col_name, _, _) in enumerate(grid_columns):
    # We dynamically apply hide_column via the sheet's API
    if col_name not in show_cols and col_name not in["HouseAge", "MedHouseVal"]:
        sheet.hide_column(col_idx)
        
    sheet.write(2, col_idx, col_name, style=CellStyle(
        bold=True, bg_color="#E0E0E0", border=True, align="center", is_header=True
    ))

# ---- B. Data Rendering & Rowspan Logic
current_row = 3
age_start_row = 3
current_age = df.iloc[0]["HouseAge"]
age_count = 0

for i, row in df.iterrows():
    # 1. Dynamic Row Hiding: Hide rows where Population > Outlier Limit
    if row["Population"] > outlier_limit:
        sheet.hide_row(current_row)

    # 2. Rowspan Tracking logic for "HouseAge"
    # We group by HouseAge to test the complex dynamic span calculation engine
    if row["HouseAge"] == current_age:
        age_count += 1
    else:
        # Write the spanning cell for the previous age group
        sheet.write(age_start_row, 0, f"{int(current_age)} yrs", rowspan=age_count, 
                    style=CellStyle(bg_color="#F8F9FA", bold=True, align="center", border=True, font_size=15))
        
        # Reset for new age group
        current_age = row["HouseAge"]
        age_start_row = current_row
        age_count = 1

    # 3. Heavy Per-Cell Styling Loop
    for col_idx, (col_name, align, num_fmt) in enumerate(grid_columns):
        if col_idx == 0:
            continue # Handled by rowspan logic above
            
        val = row[col_name]
        
        # Scale Target Variable up for visual '$' formatting realism
        if col_name == "MedHouseVal":
            val = val * 100000 
            
        # Calculate dynamic heatmap colors
        min_v, max_v = col_stats[col_name]
        if col_name == "MedHouseVal": max_v *= 100000 # adjust max for the *100k scaling
        
        bg_hex, txt_hex = interpolate_color(val, min_v, max_v, theme)
        
        # Outlier flag formatting (bold & red border simulation via text)
        is_outlier = row["Population"] > outlier_limit
        if is_outlier:
            txt_hex = "#FF0000" # Force red text for hidden outlier rows (visible only if unhidden)
            
        # Construct the unique style
        cell_style = CellStyle(
            bg_color=bg_hex,
            text_color=txt_hex,
            align=align,
            num_format=num_fmt,
            border=True,
            bold=is_outlier
        )
        
        sheet.write(current_row, col_idx, val, style=cell_style)
        
    current_row += 1

# Write the final rowspan block
sheet.write(age_start_row, 0, f"{int(current_age)} yrs", rowspan=age_count, 
            style=CellStyle(bg_color="#F8F9FA", bold=True, align="center", border=True, font_size=15))

# ---- C. Sheet Configuration & Displays
# Freeze Top 3 header rows and the HouseAge grouping column
sheet.set_freeze_panes(row=3, col=1)

# Set custom widths
sheet.set_column_width(0, 100) # HouseAge
for i in range(1, 8):
    sheet.set_column_width(i, 110)
sheet.set_column_width(8, 140) # MedHouseVal

# ─── 4. Streamlit Render ──────────────────────────────────────────────────────

st.title("🏡 Scikit-Learn Grid Heatmap")
st.markdown("""
This grid dynamically groups identical `HouseAge` rows using `rowspan`, applies heavy O(N*M) heatmap conditional formatting to every cell, and calculates custom contrast text colors. 

Try dragging the **Dataset Rows** slider or changing the **Visible Features** to test the grid's render speed and `hide_column` HTML engine!
""")

col1, col2 = st.columns([5, 1])
with col2:
    excel_download_button(sheet, file_name=f"california_housing_{n_rows}.xlsx", label="📥 Export XLSX")

with st.container(border=True):
    # Render the heavy HTML representation
    render_sheet(sheet, height=700)