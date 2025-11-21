import streamlit as st
import pandas as pd
from difflib import get_close_matches
from io import BytesIO

# ==============================
# CONFIGURATION
# ==============================
CLINQURE_LOGO = "https://clinqure.com/images/logo.png"
PRIMARY_COLOR = "#008080"
ACCENT_COLOR = "#ff9000"
SECONDARY_ACCENT = "#ffa800"
NEUTRAL_COLOR = "#686767"

# ==============================
# CUSTOM CSS FOR BRANDING
# ==============================
st.markdown(f"""
<style>
    .stButton>button {{
        background-color: {PRIMARY_COLOR};
        color: white;
        font-size: 16px;
        border-radius: 8px;
        padding: 10px 20px;
    }}
    .stButton>button:hover {{
        background-color: {ACCENT_COLOR};
        color: white;
    }}
    .footer {{
        text-align: center;
        font-size: 14px;
        color: {NEUTRAL_COLOR};
        margin-top: 50px;
    }}
</style>
""", unsafe_allow_html=True)

# ==============================
# HEADER WITH BRANDING
# ==============================
st.markdown(
    f"""
    <div style="text-align:center;">
        <CLINQURE_LOGO}
        <h2 style="color:{PRIMARY_COLOR};">ClinQure Data Consolidation Tool</h2>
        <p style="font-size:18px;color:{NEUTRAL_COLOR};">
            Upload, Map, and Consolidate Your Clinical Data Seamlessly
        </p>
    </div>
    """,
    unsafe_allow_html=True
)

# ==============================
# STEP 1: UPLOAD MULTIPLE FILES
# ==============================
st.markdown(f"<h3 style='color:{PRIMARY_COLOR};'>Step 1: Upload Your Files</h3>", unsafe_allow_html=True)
uploaded_files = st.file_uploader("Upload CSV or Excel files", type=["csv", "xlsx"], accept_multiple_files=True)

# ==============================
# FUNCTIONS
# ==============================
def create_draft_mapping_excel(files, cutoff):
    all_headers = []
    for file in files:
        if file.name.endswith(".csv"):
            df = pd.read_csv(file)
        else:
            df = pd.read_excel(file)
        all_headers.extend(df.columns.tolist())

    normalized_headers = [h.strip().lower().replace(" ", "_") for h in all_headers]
    unique_headers = list(set(normalized_headers))

    mapping_dict = {}
    visited = set()
    for header in unique_headers:
        if header not in visited:
            matches = get_close_matches(header, unique_headers, n=10, cutoff=cutoff)
            mapping_dict[header] = matches
            visited.update(matches)

    rows = [{"Standard_Name": k, "Variations": ", ".join(v)} for k, v in mapping_dict.items()]
    draft_df = pd.DataFrame(rows)
    output = BytesIO()
    draft_df.to_excel(output, index=False)
    output.seek(0)
    return output

def convert_excel_to_json(file):
    df = pd.read_excel(file)
    mapping_dict = {}
    for _, row in df.iterrows():
        standard = str(row["Standard_Name"]).strip().lower().replace(" ", "_")
        variations = [v.strip().lower().replace(" ", "_") for v in str(row["Variations"]).split(",") if v.strip()]
        mapping_dict[standard] = variations
    return mapping_dict

def consolidate_files(files, mapping_dict):
    reverse_map = {variation: standard for standard, variations in mapping_dict.items() for variation in variations}
    dfs = []

    st.info("Starting file consolidation...")
    progress = st.progress(0)
    total_files = len(files)

    for idx, file in enumerate(files):
        progress.progress((idx + 1) / total_files)

        if not (file.name.endswith(".csv") or file.name.endswith(".xlsx")):
            st.error(f"File {file.name} is not a supported format.")
            continue

        if file.size == 0:
            st.error(f"File {file.name} is empty. Skipping...")
            continue

        file.seek(0)

        try:
            df = pd.read_csv(file) if file.name.endswith(".csv") else pd.read_excel(file, engine="openpyxl")
            new_cols = []
            for col in df.columns:
                normalized = col.strip().lower().replace(" ", "_")
                new_cols.append(reverse_map.get(normalized, normalized))
            df.columns = new_cols
            dfs.append(df)

        except pd.errors.EmptyDataError:
            st.error(f"File {file.name} has no readable data.")
            continue
        except Exception as e:
            st.error(f"Error reading {file.name}: {e}")
            continue

    if not dfs:
        st.warning("No valid files were processed.")
        return None, None, None

    consolidated_df = pd.concat(dfs, ignore_index=True)

    excel_buffer = BytesIO()
    consolidated_df.to_excel(excel_buffer, index=False)
    excel_buffer.seek(0)

    csv_buffer = BytesIO()
    consolidated_df.to_csv(csv_buffer, index=False)
    csv_buffer.seek(0)

    st.success("Files consolidated successfully!")
    return consolidated_df, excel_buffer, csv_buffer

# ==============================
# STEP 2: GENERATE DRAFT MAPPING
# ==============================
if uploaded_files:
    st.markdown(f"<h3 style='color:{PRIMARY_COLOR};'>Step 2: Generate Draft Mapping</h3>", unsafe_allow_html=True)
    cutoff = st.slider("Fuzzy Matching Threshold", 0.6, 0.9, 0.8, 0.05)

    with st.spinner("Generating draft mapping, please wait..."):
        draft_excel = create_draft_mapping_excel(uploaded_files, cutoff)

    st.download_button("Download Draft Mapping Excel", data=draft_excel, file_name="draft_mapping.xlsx")

# ==============================
# STEP 3: UPLOAD EDITED MAPPING
# ==============================
st.markdown(f"<h3 style='color:{PRIMARY_COLOR};'>Step 3: Upload Edited Mapping File</h3>", unsafe_allow_html=True)
edited_mapping_file = st.file_uploader("Upload your edited mapping Excel file", type=["xlsx"])

if edited_mapping_file:
    mapping_dict = convert_excel_to_json(edited_mapping_file)
    st.markdown('Preview your mappings before consolidation:')
    preview_rows = [{"Standard Name": k, "Mapped Variations": ", ".join(v)} for k, v in mapping_dict.items()]
    st.dataframe(pd.DataFrame(preview_rows))

# ==============================
# STEP 4: CONSOLIDATE FILES
# ==============================
if edited_mapping_file and uploaded_files:
    st.markdown(f"<h3 style='color:{PRIMARY_COLOR};'>Step 4: Consolidate Files</h3>", unsafe_allow_html=True)
    st.markdown('Preview the consolidated data below, then download the final files.')

    with st.spinner("Consolidating files, please wait..."):
        consolidated_df, excel_output, csv_output = consolidate_files(uploaded_files, mapping_dict)

    if consolidated_df is not None:
        st.dataframe(consolidated_df.head(10))
        st.download_button("Download Consolidated Excel", data=excel_output, file_name="consolidated.xlsx")
        st.download_button("Download Consolidated CSV", data=csv_output, file_name="consolidated.csv")

# ==============================
# FOOTER
# ==============================
st.markdown(f"<div class='footer'>© 2025 ClinQure | All Rights Reserved</div>", unsafe_allow_html=True)
