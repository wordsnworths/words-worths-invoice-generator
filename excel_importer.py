import pandas as pd
from pathlib import Path
import openpyxl
from openpyxl.styles import Font, Alignment, Border, Side, PatternFill
from openpyxl.drawing.image import Image as XLImage
from openpyxl.utils import get_column_letter

def generate_excel(doc_data, df, totals, template="Modern", filename="export.xlsx"):
    Path("exports").mkdir(exist_ok=True)
    filepath = Path("exports") / filename
    
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = doc_data['type']
    
    # 1. Page Setup for Professional A4 Printing
    ws.page_setup.paperSize = ws.PAPERSIZE_A4
    ws.page_margins.left = 0.5
    ws.page_margins.right = 0.5
    ws.page_margins.top = 0.5
    ws.page_margins.bottom = 0.5
    ws.print_options.horizontalCentered = True
    
    # Reusable Styles
    bold_font = Font(bold=True)
    header_font = Font(bold=True, size=16)
    white_bold_font = Font(bold=True, color="FFFFFF")
    center_align = Alignment(horizontal="center", vertical="center", wrap_text=True)
    left_align = Alignment(horizontal="left", vertical="center", wrap_text=True)
    right_align = Alignment(horizontal="right", vertical="center")
    header_fill = PatternFill(start_color="2C3E50", end_color="2C3E50", fill_type="solid")
    thin_border = Border(
        left=Side(style='thin'), 
        right=Side(style='thin'), 
        top=Side(style='thin'), 
        bottom=Side(style='thin')
    )
    
    current_row = 1
    total_cols = len(df.columns) if len(df.columns) > 3 else 4
    
    # 2. Document Heading
    ws.merge_cells(start_row=current_row, start_column=1, end_row=current_row, end_column=total_cols)
    title_cell = ws.cell(row=current_row, column=1, value=doc_data['type'].upper())
    title_cell.font = header_font
    title_cell.alignment = center_align
    current_row += 2
    
    # 3. Logo & Header Details
    try:
        img = XLImage("assets/logo.png")
        img.width = 180
        img.height = 70
        ws.add_image(img, f"A{current_row}")
    except Exception:
        ws.cell(row=current_row, column=1, value="Words & Worths Books Pvt Ltd").font = bold_font
        
    # Document No and Date mapped to the far right columns
    ws.cell(row=current_row, column=total_cols-1, value="No:").font = bold_font
    ws.cell(row=current_row, column=total_cols, value=str(doc_data['id'])).alignment = right_align
    ws.cell(row=current_row+1, column=total_cols-1, value="Date:").font = bold_font
    ws.cell(row=current_row+1, column=total_cols, value=str(doc_data['date'])).alignment = right_align
    current_row += 4
    
    # Company Info
    company_info = (
        "E-28, 2nd Avenue, Besant Nagar, Chennai - 600 090\n"
        "GSTIN NO : 33AAACW4666P1ZS | Email: wordsnworths@gmail.com\n"
        "Ph No - +91 9566 250 578 | Tel: 044 24468659"
    )
    ws.merge_cells(start_row=current_row, start_column=1, end_row=current_row, end_column=total_cols)
    comp_cell = ws.cell(row=current_row, column=1, value=company_info)
    comp_cell.alignment = center_align
    ws.row_dimensions[current_row].height = 45
    current_row += 2
    
    # 4. Customer Info
    ws.cell(row=current_row, column=1, value="Billed To:").font = bold_font
    current_row += 1
    ws.cell(row=current_row, column=1, value=doc_data['customer']).font = bold_font
    current_row += 1
    ws.cell(row=current_row, column=1, value=doc_data['address']).alignment = left_align
    ws.row_dimensions[current_row].height = 30
    current_row += 1
    
    gst_val = str(doc_data.get('gst', '')).strip()
    if gst_val:
        ws.cell(row=current_row, column=1, value=f"GSTIN: {gst_val}").font = bold_font
        current_row += 1
    current_row += 1
    
    # 5. Items Table Header
    ws.print_title_rows = f'{current_row}:{current_row}' 
    
    for c_idx, col_name in enumerate(df.columns, 1):
        cell = ws.cell(row=current_row, column=c_idx, value=col_name)
        cell.font = white_bold_font
        cell.fill = header_fill
        cell.alignment = center_align
        cell.border = thin_border
        
        col_lower = col_name.lower().strip()
        col_letter = get_column_letter(c_idx)
        
        if 's.no' in col_lower: 
            ws.column_dimensions[col_letter].width = 6
        elif col_lower in ['title', 'item', 'book name']: 
            ws.column_dimensions[col_letter].width = 45
        elif col_lower in ['qty', 'quantity']: 
            ws.column_dimensions[col_letter].width = 10
        elif col_lower in ['rate', 'mrp']: 
            ws.column_dimensions[col_letter].width = 12
        elif col_lower in ['amount']: 
            ws.column_dimensions[col_letter].width = 15
        elif col_lower in ['discount %', 'discount']: 
            ws.column_dimensions[col_letter].width = 12
        elif col_lower in ['publication', 'publisher']: 
            ws.column_dimensions[col_letter].width = 20
        else: 
            ws.column_dimensions[col_letter].width = 15
            
    current_row += 1
    
    # 6. Items Table Data
    for index, row in df.iterrows():
        ws.row_dimensions[current_row].height = 20 
        for c_idx, col_name in enumerate(df.columns, 1):
            cell = ws.cell(row=current_row, column=c_idx)
            cell.border = thin_border
            
            item = row[col_name]
            if pd.isna(item):
                cell.value = ""
                continue
                
            val_str = str(item).strip()
            if not val_str:
                cell.value = ""
                continue
                
            col_lower = str(col_name).lower().strip()
            
            if col_lower == 'amount':
                try:
                    cell.value = float(val_str)
                    cell.number_format = '#,##0.00'
                    cell.alignment = right_align
                except Exception:
                    cell.value = val_str
                    cell.alignment = right_align
                    
            elif col_lower == 's.no':
                try:
                    cell.value = int(float(val_str))
                    cell.alignment = center_align
                except Exception:
                    cell.value = val_str
                    cell.alignment = center_align
                    
            elif col_lower in ['qty', 'quantity', 'rate', 'mrp']:
                try:
                    val = float(val_str)
                    if val.is_integer():
                        cell.value = int(val)
                        cell.number_format = '0'
                    else:
                        cell.value = val
                        cell.number_format = '0.0#'
                    
                    if col_lower in ['rate', 'mrp']:
                        cell.alignment = right_align
                    else:
                        cell.alignment = center_align
                except Exception:
                    cell.value = val_str
                    cell.alignment = center_align
                    
            elif col_lower in ['discount %', 'discount']:
                try:
                    clean_val = val_str.replace('%', '')
                    val = float(clean_val)
                    if val.is_integer():
                        cell.value = f"{int(val)}%"
                    else:
                        cell.value = f"{val}%"
                    cell.alignment = center_align
                except Exception:
                    cell.value = val_str
                    cell.alignment = center_align
                    
            else:
                if val_str.endswith(".0"):
                    try:
                        float(val_str)
                        val_str = val_str[:-2]
                    except Exception:
                        pass
                cell.value = val_str
                cell.alignment = left_align
                
        current_row += 1
        
    current_row += 1
    
    # 7. Totals Section
    totals_map = [("Gross Amount:", totals['gross_total'])]
    if totals['discount_total'] > 0: 
        totals_map.append(("Total Discount:", -totals['discount_total']))
    totals_map.append(("Net Amount:", totals['net_total']))
    if totals['gst_total'] > 0: 
        totals_map.append(("GST (18%):", totals['gst_total']))
    if totals['round_off'] != 0: 
        totals_map.append(("Round Off:", totals['round_off']))
    totals_map.append(("Final Amount:", totals['final_amount']))
    
    for label, val in totals_map:
        ws.cell(row=current_row, column=total_cols-1, value=label).font = bold_font
        ws.cell(row=current_row, column=total_cols-1).alignment = right_align
        
        v_cell = ws.cell(row=current_row, column=total_cols, value=val)
        if label == "Final Amount:":
            v_cell.font = bold_font
        else:
            v_cell.font = Font(bold=False)
            
        v_cell.number_format = '#,##0.00'
        v_cell.alignment = right_align
        current_row += 1
        
    current_row += 1
    
    # Amount in Words
    ws.merge_cells(start_row=current_row, start_column=1, end_row=current_row, end_column=total_cols)
    ws.cell(row=current_row, column=1, value=f"Amount in Words: {totals['amount_words']}").font = bold_font
    current_row += 2
    
    # 8. Conditional Output Sections
    if doc_data.get('inc_bank', True):
        ws.cell(row=current_row, column=1, value="Bank Details:").font = bold_font
        current_row += 1
        bank_info = (
            "Bank Name: HDFC Bank\n"
            "Account No: 50200016569383\n"
            "IFSC Code: HDFC0000847\n"
            "Branch: Thiruvanmiyur, Chennai - 600 041\n"
            "Gpay: 9566250578"
        )
        ws.merge_cells(start_row=current_row, start_column=1, end_row=current_row, end_column=3)
        bc = ws.cell(row=current_row, column=1, value=bank_info)
        bc.alignment = left_align
        ws.row_dimensions[current_row].height = 75
        current_row += 2
        
    if doc_data.get('inc_payment', True) and str(doc_data.get('payment_terms', '')).strip():
        ws.cell(row=current_row, column=1, value="Payment Terms & Conditions:").font = bold_font
        current_row += 1
        ws.merge_cells(start_row=current_row, start_column=1, end_row=current_row, end_column=total_cols)
        ptc = ws.cell(row=current_row, column=1, value=doc_data['payment_terms'])
        ptc.alignment = left_align
        ws.row_dimensions[current_row].height = 40
        current_row += 2
        
    if doc_data.get('inc_supply', True) and str(doc_data.get('terms', '')).strip():
        ws.cell(row=current_row, column=1, value="Supply Guidelines / Terms:").font = bold_font
        current_row += 1
        ws.merge_cells(start_row=current_row, start_column=1, end_row=current_row, end_column=total_cols)
        stc = ws.cell(row=current_row, column=1, value=doc_data['terms'])
        stc.alignment = left_align
        ws.row_dimensions[current_row].height = 90
        
    wb.save(filepath)
    return str(filepath)
