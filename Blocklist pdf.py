import streamlit as st
import pandas as pd
from datetime import datetime
from io import BytesIO

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle,
    Paragraph, Spacer, KeepTogether
)

# -------- SECURITY --------
def check_password():
    st.title("🔐 Login Required")

    username = st.text_input("Username")
    password = st.text_input("Password", type="password")

    if st.button("Login"):
        if username == "admin" and password == "matrix@123":
            st.session_state["authenticated"] = True
        else:
            st.error("Invalid username or password")

    return st.session_state.get("authenticated", False)


if not check_password():
    st.stop()
# --------------------------
# =========================================================
# CORE LOGIC — YOUR ORIGINAL CODE (I/O ONLY ADAPTED)
# =========================================================
def generate_blocklist_pdf(uploaded_file):

    file_name = uploaded_file.name
    current_date = datetime.now().strftime("%d-%m-%Y")

    # === LOAD EXCEL ===
    df = pd.read_excel(uploaded_file, header=8)

    # === DROP 'Due on' COLUMN ===
    if "Due on" in df.columns:
        df.drop(columns=["Due on"], inplace=True)

    # === DELETE OLD 'Age of Bill' COLUMN IF EXISTS ===
    if "Age of Bill" in df.columns:
        df.drop(columns=["Age of Bill"], inplace=True)

    # === RENAME COLUMNS FOR CLARITY ===
    rename_map = {
        "Opening": "Opening Amount",
        "Pending": "Pending Amount",
        "Post-Dated": "Post-Dated Amount",
        "Final": "Final Amount"
    }
    df.rename(columns=rename_map, inplace=True)

    # === FORMAT DATE COLUMN AND RECREATE 'Age of Bill in Days' ===
    if "Date" in df.columns:
        df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
        today = datetime.now()
        df["Age of Bill in Days"] = (today - df["Date"]).dt.days
        df["Date"] = df["Date"].dt.strftime("%d-%m-%Y")

    # === FILTER ONLY BILLS 90 DAYS AND ABOVE ===
    if "Age of Bill in Days" in df.columns:
        df = df[df["Age of Bill in Days"] >= 90]

    if df.empty:
        raise ValueError("No 90+ day records found")

    # === SORT DATA ===
    df.sort_values(
        by=["Party's Name", "Age of Bill in Days"],
        ascending=[True, False],
        inplace=True
    )

    # =================================================
    # PDF SETUP (MEMORY, NOT DISK)
    # =================================================
    buffer = BytesIO()

    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        topMargin=25,
        bottomMargin=25,
        leftMargin=25,
        rightMargin=25
    )

    elements = []

    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="CenterBold", alignment=1, fontSize=16, leading=20, spaceAfter=10))
    styles.add(ParagraphStyle(name="TableHeader", alignment=1, fontSize=11, leading=13, fontName="Helvetica-Bold"))
    styles.add(ParagraphStyle(name="LeftCell", alignment=0, fontSize=10, leading=13))
    styles.add(ParagraphStyle(name="RightCell", alignment=2, fontSize=10, leading=13))
    styles.add(ParagraphStyle(name="BoldCenter", alignment=1, fontSize=13, fontName="Helvetica-Bold", spaceBefore=15, spaceAfter=8))

    # === PDF HEADER ===
    elements.append(Paragraph("<b>MATRIX ELECTRICALS, COIMBATORE 641 012</b>", styles["CenterBold"]))
    elements.append(Paragraph(
        f"{file_name.split('.')[0].upper()} BLOCKLIST UPTO {current_date}",
        styles["CenterBold"]
    ))
    elements.append(Spacer(1, 10))

    # === CHOOSE COLUMNS ===
    preferred_cols = [
        "Date", "Ref. No.", "Party's Name", "Due days",
        "Opening Amount", "Pending Amount", "Post-Dated Amount",
        "Final Amount", "Age of Bill in Days"
    ]
    columns = [c for c in preferred_cols if c in df.columns]
    df = df[columns]

    # === GENERATE TABLE PER PARTY ===
    for party, group in df.groupby("Party's Name", sort=False):
        party_elements = []

        party_elements.append(Spacer(1, 12))
        party_elements.append(Paragraph(f"<b>{party}</b>", styles["BoldCenter"]))
        party_elements.append(Spacer(1, 6))

        # Headers
        wrapped_headers = []
        for c in columns:
            if c == "Age of Bill in Days":
                wrapped_headers.append(Paragraph("Age of Bill<br/>in Days", styles["TableHeader"]))
            elif c == "Post-Dated Amount":
                wrapped_headers.append(Paragraph("Post-Dated<br/>Amount", styles["TableHeader"]))
            else:
                wrapped_headers.append(Paragraph(c, styles["TableHeader"]))

        data = [wrapped_headers]

        # Rows
        for _, row in group.iterrows():
            row_data = []
            for col in columns:
                val = "" if pd.isna(row[col]) else row[col]
                if isinstance(val, (int, float)):
                    cell = Paragraph(f"{val:,.0f}", styles["RightCell"])
                else:
                    cell = Paragraph(str(val), styles["LeftCell"])
                row_data.append(cell)
            data.append(row_data)

        # Total row
        total_row = ["TOTAL" if c == "Date" else "" for c in columns]
        if "Pending Amount" in columns:
            total_row[columns.index("Pending Amount")] = Paragraph(
                f"{group['Pending Amount'].sum():,.0f}", styles["RightCell"]
            )
        if "Final Amount" in columns:
            total_row[columns.index("Final Amount")] = Paragraph(
                f"{group['Final Amount'].sum():,.0f}", styles["RightCell"]
            )
        data.append(total_row)

        col_widths = [64, 70, 100, 38, 61, 61, 72, 61, 65][:len(columns)]
        row_heights = [40] + [35] * (len(data) - 1)

        table = Table(data, colWidths=col_widths, rowHeights=row_heights, repeatRows=1)

        table.setStyle(TableStyle([
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("ALIGN", (0, 0), (-1, 0), "CENTER"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("ALIGN", (0, 1), (2, -1), "LEFT"),
            ("ALIGN", (3, 1), (-1, -1), "RIGHT"),
            ("SPAN", (0, -1), (columns.index("Pending Amount") - 1, -1)),
            ("LINEABOVE", (0, -1), (-1, -1), 1, colors.black),
            ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
            ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
            ("GRID", (0, 0), (-1, -1), 0.3, colors.grey),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
        ]))

        party_elements.append(table)
        party_elements.append(Spacer(1, 12))
        elements.append(KeepTogether(party_elements))

    # === FINAL SUMMARY TABLE ===
    elements.append(Spacer(1, 18))
    elements.append(Paragraph("<b>SUMMARY OF PENDING AMOUNTS</b>", styles["BoldCenter"]))
    elements.append(Spacer(1, 8))

    party_totals = (
        df.groupby("Party's Name", as_index=False)["Pending Amount"]
        .sum()
        .sort_values("Party's Name")
    )

    summary_data = [[
        Paragraph("<b>Party's Name</b>", styles["TableHeader"]),
        Paragraph("<b>Block List Amount</b>", styles["TableHeader"])
    ]]

    for _, row in party_totals.iterrows():
        summary_data.append([
            Paragraph(str(row["Party's Name"]), styles["LeftCell"]),
            Paragraph(f"{row['Pending Amount']:,.0f}", styles["RightCell"])
        ])

    total_pending = party_totals["Pending Amount"].sum()
    summary_data.append([
        Paragraph("<b>TOTAL</b>", styles["TableHeader"]),
        Paragraph(f"<b>{total_pending:,.0f}</b>", styles["RightCell"])
    ])

    summary_table = Table(summary_data, colWidths=[250, 100])
    summary_table.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
        ("ALIGN", (1, 1), (1, -1), "RIGHT"),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))

    elements.append(summary_table)

    doc.build(elements)
    buffer.seek(0)
    return buffer


# =========================================================
# STREAMLIT UI (SEPARATE FROM LOGIC)
# =========================================================
st.set_page_config(page_title="Blocklist PDF Generator", layout="centered")

st.title("📄 Blocklist PDF Generator")

uploaded_files = st.file_uploader(
    "Upload Excel file(s)",
    type=["xls", "xlsx"],
    accept_multiple_files=True
)

if uploaded_files:
    for uf in uploaded_files:
        try:
            pdf_buffer = generate_blocklist_pdf(uf)

            st.success(f"PDF generated for {uf.name}")

            st.download_button(
                label=f"⬇ Download {uf.name.split('.')[0]}_BLOCKLIST.pdf",
                data=pdf_buffer,
                file_name=f"{uf.name.split('.')[0]}_BLOCKLIST.pdf",
                mime="application/pdf"
            )

        except Exception as e:
            st.error(f"Error processing {uf.name}: {e}")
