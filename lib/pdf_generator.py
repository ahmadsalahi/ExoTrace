"""
lib/pdf_generator.py — High-Fidelity Scientific PDF Generator for ExoTrace.

Uses headless Chromium / Edge to convert structured HTML reports into pristine,
publication-grade A4 PDF documents with native Arabic RTL and English LTR support,
embedded high-res lightcurve plots, and complete astrophysical tables.
"""

import os
import base64
import tempfile
import subprocess
import pandas as pd
import streamlit as st


def get_browser_executable() -> str:
    """Find Microsoft Edge or Google Chrome executable on Windows/Linux."""
    import shutil
    # 1. Check PATH first (this works perfectly for Streamlit Cloud Linux containers)
    for exe in ["chromium", "chromium-browser", "google-chrome", "chrome", "msedge"]:
        path = shutil.which(exe)
        if path:
            return path
            
    # 2. Fallback to static Windows paths
    candidates = [
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    ]
    for c in candidates:
        if os.path.exists(c):
            return c
    return ""


@st.cache_data(ttl=120)
def generate_star_report_pdf(
    sel_tic: str,
    star_name: str,
    scan_time: str,
    status: str,
    sectors: int,
    dips: int,
    comets: int,
    summary: str,
    star_df_records: list[dict],
    plot_path: str = None,
    lang: str = None,
) -> bytes:
    """
    Generate high-resolution A4 PDF document bytes for a scanned star.
    Supports Arabic (RTL) and English (LTR).
    """
    browser_exe = get_browser_executable()
    if not browser_exe:
        raise RuntimeError("No headless browser (Edge or Chrome) found on the system.")

    if lang is None:
        try:
            from lib.i18n import get_lang
            lang = get_lang()
        except Exception:
            lang = "ar"

    is_en = (lang == "en")
    dir_val = "ltr" if is_en else "rtl"
    lang_code = "en" if is_en else "ar"
    align_val = "left" if is_en else "right"

    star_df = pd.DataFrame(star_df_records) if star_df_records else pd.DataFrame()

    # Prepare table HTML with highlighted comet candidate rows
    table_html = ""
    if not star_df.empty:
        if is_en:
            disp_cols = {
                "sector": "Sector",
                "classification_en": "Classification",
                "depth_display": "Dip Depth %",
                "asym_display": "A_time",
                "asym_shape_display": "A_shape",
                "asym_area_display": "A_area",
                "duration_display_en": "Duration",
            }
            # Fallbacks if _en columns missing
            for col, fallback in [("duration_display_en", "duration_display"), ("classification_en", "classification_ar")]:
                if col not in star_df.columns and fallback in star_df.columns:
                    disp_cols[fallback] = disp_cols.pop(col)
        else:
            disp_cols = {
                "sector": "القطاع",
                "classification_ar": "التصنيف الرصدي",
                "depth_display": "عمق الهبوط %",
                "asym_display": "A_time",
                "asym_shape_display": "A_shape",
                "asym_area_display": "A_area",
                "duration_display": "مدة العبور",
            }

        valid_keys = [c for c in disp_cols.keys() if c in star_df.columns]
        headers_html = "".join(f"<th>{disp_cols[k]}</th>" for k in valid_keys)

        rows_html = []
        sort_col = "sector" if "sector" in star_df.columns else valid_keys[0]
        for _, row in star_df.sort_values(by=sort_col).iterrows():
            cls_txt = str(row.get("classification_en" if is_en else "classification_ar", row.get("classification_ar", "")))
            cat_code = str(row.get("category_code", ""))
            is_comet = (cat_code == "strong") or ("مذنّب" in cls_txt) or ("Comet" in cls_txt)

            if is_comet:
                row_style = "background-color: #fef3c7; color: #92400e; font-weight: bold;"
            else:
                row_style = ""

            cells_html = []
            for k in valid_keys:
                val = str(row.get(k, "—"))
                if val in ["nan", "None"]:
                    val = "—"
                if "classification" in k and is_comet and not val.startswith("☄️"):
                    val = f"☄️ {val}"
                cells_html.append(f"<td>{val}</td>")

            tr_attr = f' style="{row_style}"' if row_style else ""
            rows_html.append(f"<tr{tr_attr}>" + "".join(cells_html) + "</tr>")

        table_heading = "<h3>☄️ Detected Exocomets and Transit Dips:</h3>" if is_en else "<h3>☄️ جدول المذنبات وإشارات انخفاض السطوع المرصودة:</h3>"
        table_html = f"""
        {table_heading}
        <table class="report-table">
            <thead>
                <tr>{headers_html}</tr>
            </thead>
            <tbody>
                {''.join(rows_html)}
            </tbody>
        </table>
        """

    # Embed plot image as base64
    img_tag = ""
    if plot_path and os.path.exists(plot_path):
        try:
            with open(plot_path, "rb") as f:
                b64_data = base64.b64encode(f.read()).decode("utf-8")
            plot_heading = "📈 Photometric Transit Light Curve Plot" if is_en else "📈 المنحنى الضوئي الرصدي (Light Curve Plot)"
            img_tag = f"""
            <div class="plot-container">
                <h3>{plot_heading}</h3>
                <img src="data:image/png;base64,{b64_data}" style="max-width: 100%; height: auto; border: 1px solid #cbd5e1; border-radius: 6px; box-shadow: 0 1px 3px rgba(0,0,0,0.05);" />
            </div>
            """
        except Exception:
            img_tag = ""

    doc_title = f"ExoTrace Survey Dossier — TIC {sel_tic}" if is_en else f"تقرير فحص النجم {sel_tic}"
    header_h1 = f"Observation Dossier: {star_name}" if is_en else f"تقرير الفحص الفلكي: {star_name}"
    meta_sub = f"Target TIC ID: <b>{sel_tic}</b> • Observation Timestamp: <b>{scan_time}</b>" if is_en else f"معرف النجم (TIC ID): <b>{sel_tic}</b> • تاريخ الرصد: <b>{scan_time}</b>"
    
    kpi_date_lbl = "Survey Date" if is_en else "تاريخ الفحص"
    kpi_sec_lbl = "Surveyed Sectors" if is_en else "القطاعات المفحوصة"
    kpi_sec_val = f"{sectors} Sectors" if is_en else f"{sectors} قطاع"
    kpi_dips_lbl = "Flux Dips" if is_en else "إشارات الهبوط"
    kpi_dips_val = f"{dips} Signals" if is_en else f"{dips} إشارة"
    kpi_comets_lbl = "Comet Candidates" if is_en else "المذنبات المرشحة"
    kpi_comets_val = f"{comets} Comets" if is_en else f"{comets} مذنّب"

    summary_label = "📌 Scientific Observation Summary:" if is_en else "📌 ملخص نتائج الفحص:"
    footer_text = "Generated by ExoTrace Spectroscopic Observatory • NASA TESS Mission Cadence Analysis" if is_en else "صادر عن منظومة ExoTrace للأرصاد الفلكية وتحليل بيانات NASA TESS"

    html = f"""<!DOCTYPE html>
<html dir="{dir_val}" lang="{lang_code}">
<head>
<meta charset="utf-8">
<title>{doc_title}</title>
<style>
    @page {{
        size: A4;
        margin: 14mm 16mm;
    }}
    body {{
        font-family: 'Segoe UI', -apple-system, BlinkMacSystemFont, Tahoma, Arial, sans-serif;
        color: #1e293b;
        background: #ffffff;
        margin: 0;
        padding: 0;
        line-height: 1.5;
        direction: {dir_val};
        text-align: {align_val};
    }}
    .header {{
        border-bottom: 2px solid #0284c7;
        padding-bottom: 12px;
        margin-bottom: 16px;
        display: flex;
        justify-content: space-between;
        align-items: center;
    }}
    .header h1 {{
        margin: 0;
        font-size: 19pt;
        font-weight: 800;
        color: #0369a1;
    }}
    .header .meta {{
        font-size: 9.5pt;
        color: #64748b;
        margin-top: 4px;
    }}
    .badge {{
        background: #dcfce7;
        color: #15803d;
        border: 1px solid #86efac;
        padding: 6px 14px;
        border-radius: 6px;
        font-weight: 700;
        font-size: 9.5pt;
    }}
    .kpi-grid {{
        display: grid;
        grid-template-columns: repeat(4, 1fr);
        gap: 12px;
        margin-bottom: 16px;
    }}
    .kpi-card {{
        background: #f8fafc;
        border: 1px solid #e2e8f0;
        border-radius: 8px;
        padding: 10px 12px;
        text-align: center;
    }}
    .kpi-label {{
        font-size: 8pt;
        color: #64748b;
        font-weight: 600;
        margin-bottom: 4px;
    }}
    .kpi-value {{
        font-size: 13pt;
        font-weight: 800;
        color: #0284c7;
    }}
    .summary-box {{
        background: #f0f9ff;
        border: 1px solid #bae6fd;
        border-radius: 8px;
        padding: 12px 16px;
        font-size: 9.5pt;
        line-height: 1.6;
        color: #0c4a6e;
        margin-bottom: 16px;
    }}
    .report-table {{
        width: 100%;
        border-collapse: collapse;
        margin-top: 8px;
        margin-bottom: 16px;
        font-size: 8.5pt;
    }}
    .report-table th, .report-table td {{
        border: 1px solid #cbd5e1;
        padding: 6px 8px;
        text-align: center;
    }}
    .report-table th {{
        background: #0f172a;
        color: #ffffff;
        font-weight: bold;
    }}
    .plot-container {{
        margin-top: 14px;
        text-align: center;
        page-break-inside: avoid;
    }}
    .footer {{
        margin-top: 20px;
        border-top: 1px solid #e2e8f0;
        padding-top: 8px;
        font-size: 8pt;
        color: #94a3b8;
        display: flex;
        justify-content: space-between;
    }}
</style>
</head>
<body>
    <div class="header">
        <div>
            <h1>{header_h1}</h1>
            <div class="meta">{meta_sub}</div>
        </div>
        <div>
            <span class="badge">{status}</span>
        </div>
    </div>

    <div class="kpi-grid">
        <div class="kpi-card">
            <div class="kpi-label">{kpi_date_lbl}</div>
            <div class="kpi-value">{str(scan_time).split(' ')[0]}</div>
        </div>
        <div class="kpi-card">
            <div class="kpi-label">{kpi_sec_lbl}</div>
            <div class="kpi-value">{kpi_sec_val}</div>
        </div>
        <div class="kpi-card">
            <div class="kpi-label">{kpi_dips_lbl}</div>
            <div class="kpi-value">{kpi_dips_val}</div>
        </div>
        <div class="kpi-card">
            <div class="kpi-label">{kpi_comets_lbl}</div>
            <div class="kpi-value">{kpi_comets_val}</div>
        </div>
    </div>

    <div class="summary-box">
        <b>{summary_label}</b> {summary}
    </div>

    {table_html}

    {img_tag}

    <div class="footer">
        <span>{footer_text}</span>
    </div>
</body>
</html>"""

    temp_dir = tempfile.gettempdir()
    temp_html = os.path.join(temp_dir, f"report_{sel_tic}_{os.getpid()}.html")
    temp_pdf = os.path.join(temp_dir, f"report_{sel_tic}_{os.getpid()}.pdf")

    with open(temp_html, "w", encoding="utf-8") as f:
        f.write(html)

    cmd = [
        browser_exe,
        "--headless",
        "--disable-gpu",
        "--run-all-compositor-stages-before-draw",
        "--no-pdf-header-footer",
        f"--print-to-pdf={temp_pdf}",
        temp_html,
    ]
    subprocess.run(cmd, capture_output=True, check=True, timeout=25)

    with open(temp_pdf, "rb") as f:
        pdf_bytes = f.read()

    try:
        os.remove(temp_html)
        os.remove(temp_pdf)
    except Exception:
        pass

    return pdf_bytes


@st.cache_data(ttl=120)
def generate_table_report_pdf(
    report_title: str,
    scope_description: str,
    records: list[dict],
    lang: str = None,
) -> bytes:
    """
    Generate an A4 landscape PDF document containing a styled table of candidates/dips.
    Supports English (LTR) and Arabic (RTL).
    """
    browser_exe = get_browser_executable()
    if not browser_exe:
        raise RuntimeError("No headless browser (Edge or Chrome) found on the system.")

    if not records:
        raise ValueError("No records provided to generate PDF table.")

    if lang is None:
        try:
            from lib.i18n import get_lang
            lang = get_lang()
        except Exception:
            lang = "ar"

    is_en = (lang == "en")
    dir_val = "ltr" if is_en else "rtl"
    lang_code = "en" if is_en else "ar"
    align_val = "left" if is_en else "right"

    df = pd.DataFrame(records)

    if is_en:
        col_order = [
            ("tic_id", "Star (TIC)"),
            ("star_name", "Star Name"),
            ("sector", "Sector"),
            ("classification_en", "Classification"),
            ("depth_display", "Dip Depth %"),
            ("asym_display", "Asymmetry (A)"),
            ("ingress_display_en", "Ingress Time"),
            ("egress_display_en", "Egress Time"),
            ("duration_display_en", "Duration"),
        ]
        # Map fallback if _en keys absent
        for idx, (k, lbl) in enumerate(col_order):
            if k not in df.columns:
                fb = k.replace("_en", "_ar").replace("_display_ar", "_display")
                if fb in df.columns:
                    col_order[idx] = (fb, lbl)
    else:
        col_order = [
            ("tic_id", "رقم النجم (TIC)"),
            ("star_name", "اسم النجم"),
            ("sector", "القطاع"),
            ("classification_ar", "التصنيف الرصدي"),
            ("depth_display", "عمق الهبوط %"),
            ("asym_display", "اللاتماثل (A)"),
            ("ingress_display", "زمن الدخول"),
            ("egress_display", "زمن الخروج"),
            ("duration_display", "مدة العبور"),
        ]

    valid_cols = [(k, label) for k, label in col_order if k in df.columns]
    if not valid_cols:
        valid_cols = [(c, c) for c in df.columns]

    headers_html = "".join(f"<th>{label}</th>" for _, label in valid_cols)

    rows_html = []
    for _, row in df.iterrows():
        cls_txt = str(row.get("classification_en" if is_en else "classification_ar", row.get("classification_ar", "")))
        cat_code = str(row.get("category_code", ""))
        is_comet = (cat_code == "strong") or ("مذنّب" in cls_txt) or ("Comet" in cls_txt)

        if is_comet:
            row_style = "background-color: #fef3c7; color: #78350f; font-weight: bold;"
        else:
            row_style = ""

        cells = []
        for k, _ in valid_cols:
            val = str(row.get(k, "—"))
            if val in ["nan", "None"]:
                val = "—"
            if "classification" in k and is_comet and not val.startswith("☄️"):
                val = f"☄️ {val}"
            cells.append(f"<td>{val}</td>")

        tr_attr = f' style="{row_style}"' if row_style else ""
        rows_html.append(f"<tr{tr_attr}>" + "".join(cells) + "</tr>")

    meta_line = f"Scope: <b>{scope_description}</b> • Total Records: <b>{len(df)} signals</b>" if is_en else f"نطاق التقرير: <b>{scope_description}</b> • إجمالي السجلات: <b>{len(df)} سجل</b>"
    footer_text = "Generated by ExoTrace Spectroscopic Observatory • NASA TESS Mission Cadence Analysis" if is_en else "صادر عن منظومة ExoTrace للأرصاد الفلكية وتحليل بيانات NASA TESS"

    html = f"""<!DOCTYPE html>
<html dir="{dir_val}" lang="{lang_code}">
<head>
<meta charset="utf-8">
<title>{report_title}</title>
<style>
    @page {{
        size: A4 landscape;
        margin: 12mm 15mm;
    }}
    body {{
        font-family: 'Segoe UI', -apple-system, BlinkMacSystemFont, Tahoma, Arial, sans-serif;
        color: #1e293b;
        background: #ffffff;
        margin: 0;
        padding: 0;
        direction: {dir_val};
        text-align: {align_val};
        line-height: 1.4;
    }}
    .header {{
        border-bottom: 2px solid #0284c7;
        padding-bottom: 10px;
        margin-bottom: 14px;
        display: flex;
        justify-content: space-between;
        align-items: center;
    }}
    .header h1 {{
        margin: 0;
        font-size: 17pt;
        font-weight: 800;
        color: #0369a1;
    }}
    .meta {{
        font-size: 9pt;
        color: #64748b;
        margin-top: 4px;
    }}
    table {{
        width: 100%;
        border-collapse: collapse;
        margin-top: 10px;
        font-size: 8.5pt;
    }}
    th, td {{
        border: 1px solid #cbd5e1;
        padding: 7px 9px;
        text-align: center;
    }}
    th {{
        background: #0f172a;
        color: #ffffff;
        font-weight: bold;
    }}
    tr:nth-child(even) {{
        background: #f8fafc;
    }}
    .footer {{
        margin-top: 20px;
        border-top: 1px solid #e2e8f0;
        padding-top: 8px;
        font-size: 8pt;
        color: #94a3b8;
        display: flex;
        justify-content: space-between;
    }}
</style>
</head>
<body>
    <div class="header">
        <div>
            <h1>{report_title}</h1>
            <div class="meta">{meta_line}</div>
        </div>
    </div>
    <table>
        <thead><tr>{headers_html}</tr></thead>
        <tbody>{''.join(rows_html)}</tbody>
    </table>
    <div class="footer">
        <span>{footer_text}</span>
    </div>
</body>
</html>"""

    temp_dir = tempfile.gettempdir()
    temp_html = os.path.join(temp_dir, f"table_report_{os.getpid()}.html")
    temp_pdf = os.path.join(temp_dir, f"table_report_{os.getpid()}.pdf")

    with open(temp_html, "w", encoding="utf-8") as f:
        f.write(html)

    cmd = [
        browser_exe,
        "--headless",
        "--disable-gpu",
        "--run-all-compositor-stages-before-draw",
        "--no-pdf-header-footer",
        f"--print-to-pdf={temp_pdf}",
        temp_html,
    ]
    subprocess.run(cmd, capture_output=True, check=True, timeout=25)

    with open(temp_pdf, "rb") as f:
        pdf_bytes = f.read()

    try:
        os.remove(temp_html)
        os.remove(temp_pdf)
    except Exception:
        pass

    return pdf_bytes
