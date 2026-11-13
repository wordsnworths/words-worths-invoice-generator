from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image, KeepTogether
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from pathlib import Path
import html
import pandas as pd

def get_col_widths(columns, max_width=535):
    """Dynamically sizes columns to utilize 100% of the A4 width cleanly."""
    widths = []
    for col in columns:
        col_lower = col.lower()
        if 's.no' in col_lower: widths.append(0.06)
        elif col_lower in ['title', 'item', 'book name']: widths.append(0.40)
        elif col_lower in ['qty', 'quantity']: widths.append(0.08)
        elif col_lower in ['rate', 'amount', 'mrp']: widths.append(0.12)
        elif col_lower in ['discount %', 'discount']: widths.append(0.09)
        elif col_lower in ['publication', 'publisher']: widths.append(0.15)
        else: widths.append(0.12)
    
    total = sum(widths)
    return [w * (max_width / total) for w in widths]

def add_page_number(canvas, doc):
    """Draws a footer page number on every generated page."""
    page_num = canvas.getPageNumber()
    text = f"Page {page_num}"
    canvas.saveState()
    canvas.setFont('Helvetica', 9)
    canvas.drawRightString(A4[0] - 30, 20, text)
    canvas.restoreState()

def generate_pdf(doc_data, df, totals, template="Modern", filename="export.pdf"):
    Path("exports").mkdir(exist_ok=True)
    filepath = f"exports/{filename}"
    
    doc = SimpleDocTemplate(filepath, pagesize=A4, rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=40)
    elements = []
    styles = getSampleStyleSheet()
    
    # 1. Centered Document Heading (Top of Page)
    title_style = ParagraphStyle(
        name='CenteredTitle', 
        parent=styles['Heading1'], 
        alignment=1, 
        fontSize=16,
        spaceAfter=15
    )
    elements.append(Paragraph(f"<b>{html.escape(doc_data['type']).upper()}</b>", title_style))
    
    # 2. Header & Company Info
    try:
        # Enforced strict aspect ratio scaling
        logo = Image("assets/logo.png", width=220, height=90, preserveAspectRatio=True)
    except:
        logo = Paragraph("<b>Words & Worths Books Pvt Ltd</b>", styles['Heading2'])
    
    company_details = Paragraph(
        "<font size=9>"
        "E-28, 2nd Avenue, Besant Nagar, Chennai - 600 090<br/>"
        "<b>GSTIN NO :</b> 33AAACW4666P1ZS | <b>Email:</b> wordsnworths@gmail.com<br/>"
        "<b>Ph No -</b> +91 9566 250 578 | <b>Tel:</b> 044 24468659"
        "</font>", 
        styles['Normal']
    )
    
    left_header = [logo, Spacer(1, 8), company_details]
    right_header = Paragraph(f"<b>No:</b> {html.escape(str(doc_data['id']))}<br/><b>Date:</b> {html.escape(str(doc_data['date']))}", styles['Normal'])
    
    header_table = Table([[left_header, right_header]], colWidths=[380, 155])
    header_table.setStyle(TableStyle([
        ('ALIGN', (1,0), (1,0), 'RIGHT'), 
        ('VALIGN', (0,0), (-1,-1), 'TOP')
    ]))
    
    elements.append(header_table)
    elements.append(Spacer(1, 25))
    
    # 3. Customer Info (With Conditional GSTIN formatting)
    safe_address = html.escape(doc_data['address']).replace('\n', '<br/>')
    cust_info = f"<b>Billed To:</b><br/><b>{html.escape(doc_data['customer'])}</b><br/>{safe_address}"
    
    gst_val = str(doc_data.get('gst', '')).strip()
    if gst_val:
        cust_info += f"<br/><br/><b>GSTIN:</b> {html.escape(gst_val)}"
        
    elements.append(Paragraph(cust_info, styles['Normal']))
    elements.append(Spacer(1, 20))
    
    # 4. Items Table (With dynamic decimal formatting)
    cell_style = ParagraphStyle(name='CellStyle', parent=styles['Normal'], fontSize=9, alignment=1)
    
    table_data = [list(df.columns)] 
    for index, row in df.iterrows():
        row_data = []
        for col_name in df.columns:
            item = row[col_name]
            
            # Handle NaN / Blank cells cleanly
            if pd.isna(item):
                val_str = ""
            else:
                val_str = str(item).strip()
                if val_str != "":
                    col_lower = str(col_name).lower()
                    
                    # FORMAT 1: Force exactly 2 decimals for the Amount column
                    if col_lower == 'amount':
                        try:
                            val_str = f"{float(val_str):.2f}"
                        except (ValueError, TypeError):
                            pass
                            
                    # FORMAT 2: Completely drop decimals for S.No, Qty, Rate, Discount
                    elif col_lower in ['s.no', 'qty', 'rate', 'discount %', 'discount', 'quantity', 'mrp']:
                        try:
                            val_str = str(int(float(val_str)))
                        except (ValueError, TypeError, OverflowError):
                            pass
                            
                    # FORMAT 3: Safe fallback for strings (ISBNs) that pandas incorrectly appended '.0' to
                    else:
                        if val_str.endswith(".0"):
                            try:
                                float(val_str) 
                                val_str = val_str[:-2]
                            except ValueError:
                                pass
            
            row_data.append(Paragraph(html.escape(val_str), cell_style))
            
        table_data.append(row_data)
        
    colWidths = get_col_widths(df.columns)
    item_table = Table(table_data, repeatRows=1, colWidths=colWidths)
    
    bg_color = colors.HexColor("#2C3E50") if template == "Modern" else colors.grey
    item_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), bg_color),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
    ]))
    elements.append(item_table)
    elements.append(Spacer(1, 20))
    
    # 5. Bottom Sections (Bound in KeepTogether to prevent visual fracturing across pages)
    footer_elements = []
    
    # Financial Totals Breakdown
    totals_data = [["Gross Amount:", f"Rs. {totals['gross_total']:.2f}"]]
    if totals['discount_total'] > 0:
        totals_data.append(["Total Discount:", f"- Rs. {totals['discount_total']:.2f}"])
    totals_data.append(["Net Amount:", f"Rs. {totals['net_total']:.2f}"])
    if totals['gst_total'] > 0:
        totals_data.append(["GST (18%):", f"Rs. {totals['gst_total']:.2f}"])
    if totals['round_off'] != 0:
        totals_data.append(["Round Off:", f"Rs. {totals['round_off']:.2f}"])
    totals_data.append(["Final Amount:", f"Rs. {totals['final_amount']:.2f}"])

    totals_table = Table(totals_data, colWidths=[400, 100])
    totals_table.setStyle(TableStyle([
        ('ALIGN', (0,0), (-1,-1), 'RIGHT'), 
        ('FONTNAME', (0,-1), (-1,-1), 'Helvetica-Bold')
    ]))
    footer_elements.append(totals_table)
    footer_elements.append(Spacer(1, 10))
    
    # Amount in Words
    footer_elements.append(Paragraph(f"<b>Amount in Words:</b> {totals['amount_words']}", styles['Normal']))
    footer_elements.append(Spacer(1, 25))
    
    # Optional Appendages Based on User Selection
    if doc_data.get('inc_bank', True):
        bank_text = (
            "<b>Bank Details:</b><br/>"
            "Bank Name: HDFC Bank<br/>"
            "Account No: 50200016569383<br/>"
            "IFSC Code: HDFC0000847<br/>"
            "Branch: Thiruvanmiyur, Chennai - 600 041<br/><br/>"
            "<b>Gpay:</b> 9566250578"
        )
        footer_elements.append(Paragraph(bank_text, styles['Normal']))
        footer_elements.append(Spacer(1, 15))
        
    if doc_data.get('inc_payment', True) and str(doc_data.get('payment_terms', '')).strip():
        safe_pt = html.escape(doc_data['payment_terms']).replace('\n', '<br/>')
        footer_elements.append(Paragraph(f"<b>Payment Terms & Conditions:</b><br/>{safe_pt}", styles['Normal']))
        footer_elements.append(Spacer(1, 10))
        
    if doc_data.get('inc_supply', True) and str(doc_data.get('terms', '')).strip():
        safe_st = html.escape(doc_data['terms']).replace('\n', '<br/>')
        footer_elements.append(Paragraph(f"<b>Supply Guidelines / Terms:</b><br/>{safe_st}", styles['Normal']))
    
    elements.append(KeepTogether(footer_elements))
    
    # Bind page numbering handler to document compilation
    doc.build(elements, onFirstPage=add_page_number, onLaterPages=add_page_number)
    return filepath
