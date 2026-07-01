import pandas as pd
from num2words import num2words

def calculate_totals(df, include_gst=False, auto_round=True, overall_discount_percent=0.0):
    if df.empty or 'Qty' not in df.columns or 'Rate' not in df.columns:
        return {
            'total_qty': 0, 'gross_total': 0, 'discount_total': 0,
            'net_total': 0, 'gst_total': 0, 'round_off': 0,
            'final_amount': 0, 'amount_words': "Zero Only"
        }

    df['Qty'] = pd.to_numeric(df['Qty'], errors='coerce').fillna(0)
    df['Rate'] = pd.to_numeric(df['Rate'], errors='coerce').fillna(0)
    df['Discount %'] = pd.to_numeric(df.get('Discount %', 0), errors='coerce').fillna(0)

    # Base amount calculations
    df['Gross Amount'] = df['Qty'] * df['Rate']
    df['Row Discount'] = df['Gross Amount'] * (df['Discount %'] / 100)

    total_qty = df['Qty'].sum()
    gross_total = df['Gross Amount'].sum()
    row_discount_total = df['Row Discount'].sum()

    # Calculate Subtotal (Gross minus individual row discounts)
    subtotal = gross_total - row_discount_total

    # Calculate the Overall Discount Amount based on the user's percentage
    overall_discount_amount = subtotal * (overall_discount_percent / 100)

    # Combine row discounts and overall invoice discount
    total_discount = row_discount_total + overall_discount_amount
    net_total = subtotal - overall_discount_amount

    # Ensure net_total doesn't go below zero
    net_total = max(0, net_total)

    gst_total = 0
    if include_gst:
        # Calculate flat 18% GST on the final discounted net amount
        gst_total = net_total * 0.18

    final_amount = net_total + gst_total
    round_off = 0

    if auto_round:
        rounded_amount = round(final_amount)
        round_off = rounded_amount - final_amount
        final_amount = rounded_amount

    if final_amount == 0:
        words = "Zero Only"
    else:
        words = num2words(final_amount, lang='en_IN').title() + " Only"
    
    return {
        'total_qty': total_qty,
        'gross_total': gross_total,
        'discount_total': total_discount,
        'net_total': net_total,
        'gst_total': gst_total,
        'round_off': round_off,
        'final_amount': final_amount,
        'amount_words': words
    }