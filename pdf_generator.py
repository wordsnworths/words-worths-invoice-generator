from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from pathlib import Path

def get_col_widths(columns, max_width=535):
    widths = []
    for col in columns:
        if col == 'S.No': widths.append(max_width * 0.06)
        elif col in ['Title', 'Item', 'Book Name']: widths.append(max_width * 0.35)
        elif col in ['Qty']: widths.append(max_width * 0.06)
        elif col in ['Rate', 'Amount']: widths.append(max_width * 0.10)
        else: widths.append(max_width * 0.12)
    
    total = sum(widths)
    return [w * (max_width / total) for w in widths]

def generate_pdf(doc_data, df, totals, template="Modern", filename="export.pdf"):
    Path("exports").mkdir(exist_ok=True)
    filepath = f"exports/{filename}"
    
    doc = SimpleDocTemplate(filepath, pagesize=A4, rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=30)
    elements = []
    styles = getSampleStyleSheet()
    
    # 1. Header & Company Info
    try:
        # Increased Logo Size
        logo = Image("assets/logo.png", width=180, height=75)
    except:
        logo = Paragraph("<b>Words & Worths Books Pvt Ltd</b>", styles['Heading2'])
    
    # Formatted Company Details placed beneath the logo
    company_details = Paragraph(
        "<font size=9>"
        "E-28, 2nd Avenue, Besant Nagar, Chennai - 600 090<br/>"
        "<b>GSTIN NO :</b> 33AAACW4666P1ZS | <b>Email:</b> wordsnworths@gmail.com<br/>"
        "<b>Ph No -</b> +91 9566 250 578 | <b>Tel:</b> 044 24468659"
        "</font>", 
        styles['Normal']
    )
    
    left_header = [logo, Spacer(1, 8), company_details]
    right_header = Paragraph(f"<b>{doc_data['type'].upper()}</b><br/>No: {doc_data['id']}<br/>Date: {doc_data['date']}", styles['Normal'])
    
    header_data = [[left_header, right_header]]
    header_table = Table(header_data, colWidths=[380, 155])
    header_table.setStyle(TableStyle([
        ('ALIGN', (1,0), (1,0), 'RIGHT'), 
        ('VALIGN', (0,0), (-1,-1), 'TOP')
    ]))
    
    elements.append(header_table)
    elements.append(Spacer(1, 25))
    
    # 2. Customer Info (with explicitly labeled GSTIN)
    cust_info = f"<b>Billed To:</b><br/><b>{doc_data['customer']}</b><br/>{doc_data['address']}<br/><br/><b>GSTIN:</b> {doc_data['gst']}"
    elements.append(Paragraph(cust_info, styles['Normal']))
    elements.append(Spacer(1, 20))
    
    # 3. Items Table
    cell_style = ParagraphStyle(name='CellStyle', parent=styles['Normal'], fontSize=9, alignment=1)
    
    table_data = [list(df.columns)] 
    for index, row in df.iterrows():
        row_data = [Paragraph(str(item), cell_style) for item in row.values]
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
    
    # 4. Totals Breakdown
    totals_data = [
        ["Gross Amount:", f"Rs. {totals['gross_total']:.2f}"]
    ]
    
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
    elements.append(totals_table)
    elements.append(Spacer(1, 10))
    
    # 5. Amount in Words
    elements.append(Paragraph(f"<b>Amount in Words:</b> {totals['amount_words']}", styles['Normal']))
    elements.append(Spacer(1, 25))
    
    # 6. Bank Details
    bank_text = (
        "<b>Bank Details:</b><br/>"
        "Bank Name: HDFC Bank<br/>"
        "Account No: 50200016569383<br/>"
        "IFSC Code: HDFC0000847<br/>"
        "Branch: Thiruvanmiyur, Chennai - 600 041<br/><br/>"
        "<b>Gpay:</b> 9566250578"
    )
    elements.append(Paragraph(bank_text, styles['Normal']))
    elements.append(Spacer(1, 15))
    
    # 7. Payment Terms
    elements.append(Paragraph("<b>Payment Terms & Conditions:</b><br/>" + doc_data['payment_terms'].replace('\n', '<br/>'), styles['Normal']))
    elements.append(Spacer(1, 10))
    
    # 8. Supply Guidelines / Terms
    elements.append(Paragraph("<b>Supply Guidelines / Terms:</b><br/>" + doc_data['terms'].replace('\n', '<br/>'), styles['Normal']))
    
    doc.build(elements)
    return filepath
