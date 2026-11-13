import streamlit as st
import pandas as pd
from datetime import datetime
import database as db
import calculations as calc
import excel_importer as xl
import pdf_generator as pdf
import excel_generator as excel
import base64
import os

# UI Configuration
st.set_page_config(page_title="Words & Worths ERP", layout="wide", initial_sidebar_state="expanded")
st.markdown("""
    <style>
    .stApp { background-color: #FAFAFA; }
    .css-1d391kg { padding-top: 1rem; }
    </style>
""", unsafe_allow_html=True)

db.init_db()

# Initialize critical session workflow variables
if 'step' not in st.session_state: st.session_state.step = 1
if 'doc_type' not in st.session_state: st.session_state.doc_type = "Invoice"
if 'overall_discount' not in st.session_state: st.session_state.overall_discount = 0.0
if 'include_gst' not in st.session_state: st.session_state.include_gst = False
if 'auto_round' not in st.session_state: st.session_state.auto_round = True
if 'inc_payment' not in st.session_state: st.session_state.inc_payment = True
if 'inc_supply' not in st.session_state: st.session_state.inc_supply = True
if 'inc_bank' not in st.session_state: st.session_state.inc_bank = True

default_payment = "- 50% advance payment upon confirmation of order\n- Balance payment on delivery."
default_supply = """1. 50% advance against order confirmation / P.O
2. Delivery Supply is subject to availability with publishers at the time of procurement.
3. Delivery schedules and prices quoted are indicative only and are subject to publisher stock availability and MRP market revisions.
4. Partial supply may be effected where required.
5. Unavailable titles (cost) will be refunded / credited or adjusted with alternative titles as mutually agreed.
6. Books supplied against confirmed order are not returnable / cancellable, except due to damage / supply discrepancy."""

if 'payment_terms' not in st.session_state: st.session_state.payment_terms = default_payment
if 'supply_terms' not in st.session_state: st.session_state.supply_terms = default_supply

def main():
    st.sidebar.image("assets/logo.png", use_container_width=True)
    menu = st.sidebar.radio("Navigation", ["New Document", "History", "Customers", "Products", "Settings"])

    if menu == "New Document":
        render_new_document_workflow()
    elif menu == "History":
        render_history()
    elif menu == "Customers":
        render_customers()

def render_new_document_workflow():
    if st.session_state.step == 1: step_1_data_entry()
    elif st.session_state.step == 2: step_2_column_selection()
    elif st.session_state.step == 3: step_3_additional_sections()
    elif st.session_state.step == 4: step_4_preview_and_confirm()

def step_1_data_entry():
    st.title("Create New Document (Step 1 of 4)")
    col1, col2, col3 = st.columns(3)
    
    doc_type = col1.selectbox("Document Type", ["Invoice", "Proforma", "Quotation"], 
                              index=["Invoice", "Proforma", "Quotation"].index(st.session_state.doc_type))
    
    if doc_type != st.session_state.doc_type:
        st.session_state.doc_type = doc_type
        st.rerun()

    doc_num = col2.text_input("Document Number", value=str(db.get_next_sequence(st.session_state.doc_type)))
    doc_date = col3.date_input("Date", datetime.today())

    cust_df = db.load_table('customers')
    cust_names = ["Select Customer..."] + cust_df['name'].tolist() if not cust_df.empty else ["No Customers Found"]
    customer = st.selectbox("Customer", cust_names)
    
    cust_address, cust_gst = "", ""
    if customer not in ["Select Customer...", "No Customers Found"]:
        selected_cust = cust_df[cust_df['name'] == customer].iloc[0]
        
        street = str(selected_cust['address']).strip() if pd.notna(selected_cust['address']) else ""
        city_state_pin = [str(p).strip() for p in [selected_cust['city'], selected_cust['state'], selected_cust['pincode']] if pd.notna(p) and str(p).strip()]
        city_line = ", ".join(city_state_pin)
        
        if street and city_line: cust_address = f"{street}\n{city_line}"
        elif street: cust_address = street
        elif city_line: cust_address = city_line
        cust_gst = selected_cust['gst'] if pd.notna(selected_cust['gst']) else ""

    st.markdown("### Item Details")
    uploaded_file = st.file_uploader("Upload Excel/CSV", type=["xlsx", "csv"])
    
    if "invoice_data" not in st.session_state:
        st.session_state.invoice_data = pd.DataFrame(columns=['S.No', 'Title', 'Publication', 'Qty', 'Rate', 'Discount %'])

    if uploaded_file:
        st.session_state.invoice_data = xl.process_upload(uploaded_file)

    edited_df = st.data_editor(
        st.session_state.invoice_data, 
        num_rows="dynamic", 
        use_container_width=True,
        hide_index=True
    )

    temp_qty = pd.to_numeric(edited_df['Qty'], errors='coerce').fillna(0)
    temp_rate = pd.to_numeric(edited_df['Rate'], errors='coerce').fillna(0)
    temp_disc = pd.to_numeric(edited_df.get('Discount %', 0), errors='coerce').fillna(0)
    edited_df['Amount'] = ((temp_qty * temp_rate) * (1 - temp_disc / 100)).round(2)

    st.divider()

    col_set, col_tot = st.columns([1.5, 1.2])
    with col_set:
        st.markdown("**Tax, Discounts & Terms**")
        overall_discount = st.number_input("Overall Additional Discount (%)", min_value=0.0, max_value=100.0, value=st.session_state.overall_discount, step=1.0)
        include_gst = st.checkbox("Include GST (18%)", value=st.session_state.include_gst)
        auto_round = st.checkbox("Auto Round Off", value=st.session_state.auto_round)
        payment_terms = st.text_area("Payment Terms & Conditions", st.session_state.payment_terms, height=80)
        supply_terms = st.text_area("Supply Guidelines / Terms", st.session_state.supply_terms, height=180)

    with col_tot:
        st.markdown("**Calculation Summary**")
        totals = calc.calculate_totals(edited_df, include_gst, auto_round, overall_discount)
        st.metric("Net Amount", f"₹ {totals['net_total']:.2f}")
        if include_gst: st.metric("GST Amount", f"₹ {totals['gst_total']:.2f}")
        st.metric("Final Amount", f"₹ {totals['final_amount']:.2f}", delta=f"Round off: {totals['round_off']:.2f}", delta_color="off")
        st.caption(f"**In Words:** {totals['amount_words']}")

    st.divider()
    if st.button("Next: Select Columns", type="primary"):
        if customer in ["Select Customer...", "No Customers Found"]:
            st.error("Please select a valid customer before proceeding.")
        else:
            st.session_state.doc_num = doc_num
            st.session_state.doc_date = doc_date
            st.session_state.customer = customer
            st.session_state.cust_address = cust_address
            st.session_state.cust_gst = cust_gst
            st.session_state.working_df = edited_df
            st.session_state.totals = totals
            st.session_state.overall_discount = overall_discount
            st.session_state.include_gst = include_gst
            st.session_state.auto_round = auto_round
            st.session_state.payment_terms = payment_terms
            st.session_state.supply_terms = supply_terms
            st.session_state.step = 2
            st.rerun()

def step_2_column_selection():
    st.title("Select Table Columns (Step 2 of 4)")
    st.write("Check the columns you want to display on the generated PDF/Excel document.")
    
    available_cols = st.session_state.working_df.columns.tolist()
    col_a, col_b = st.columns([1, 10])
    
    if col_a.button("Select All"):
        for c in available_cols: st.session_state[f"col_chk_{c}"] = True
        st.rerun()
    if col_b.button("Deselect All"):
        for c in available_cols: st.session_state[f"col_chk_{c}"] = False
        st.rerun()

    st.write("")
    grid = st.columns(4)
    selected_cols = []
    
    for i, col_name in enumerate(available_cols):
        if col_name in ['Gross Amount', 'Row Discount']: continue
        with grid[i % 4]:
            is_checked = st.checkbox(col_name, value=st.session_state.get(f"col_chk_{col_name}", True), key=f"col_chk_{col_name}")
            if is_checked: selected_cols.append(col_name)

    st.divider()
    b1, b2, _ = st.columns([2, 2, 8])
    with b1:
        if st.button("← Back"):
            st.session_state.step = 1
            st.rerun()
    with b2:
        if st.button("Next: Additional Sections →", type="primary"):
            if not selected_cols:
                st.error("Please select at least one column to proceed.")
            else:
                st.session_state.selected_cols = selected_cols
                st.session_state.step = 3
                st.rerun()

def step_3_additional_sections():
    st.title("Additional Document Sections (Step 3 of 4)")
    st.write("Choose the independent sections to include at the bottom of your document.")
    
    st.session_state.inc_payment = st.checkbox("Include Payment Terms & Conditions", value=st.session_state.inc_payment)
    st.session_state.inc_supply = st.checkbox("Include Supply Guidelines / Terms", value=st.session_state.inc_supply)
    st.session_state.inc_bank = st.checkbox("Include Bank Details", value=st.session_state.inc_bank)

    st.divider()
    b1, b2, _ = st.columns([2, 2, 8])
    with b1:
        if st.button("← Back"):
            st.session_state.step = 2
            st.rerun()
    with b2:
        if st.button("Generate Preview →", type="primary"):
            st.session_state.step = 4
            st.rerun()

def step_4_preview_and_confirm():
    st.title("Document Preview & Download (Step 4 of 4)")
    st.info("Review the document. Select your preferred output format below. The system sequence updates only upon explicit download.")
    
    doc_data = {
        'type': st.session_state.doc_type, 'id': st.session_state.doc_num, 
        'date': st.session_state.doc_date.strftime("%d-%m-%Y"),
        'customer': st.session_state.customer, 'address': st.session_state.cust_address, 
        'gst': st.session_state.cust_gst, 'terms': st.session_state.supply_terms, 
        'payment_terms': st.session_state.payment_terms,
        'inc_payment': st.session_state.inc_payment,
        'inc_supply': st.session_state.inc_supply,
        'inc_bank': st.session_state.inc_bank
    }
    filtered_df = st.session_state.working_df[st.session_state.selected_cols]
    
    # Render Preview Stream (Always generated as PDF visually for ease of review)
    pdf_path = pdf.generate_pdf(doc_data, filtered_df, st.session_state.totals, filename="preview.pdf")
    with open(pdf_path, "rb") as f:
        pdf_bytes = f.read()
        
    base64_pdf = base64.b64encode(pdf_bytes).decode('utf-8')
    pdf_display = f'<iframe src="data:application/pdf;base64,{base64_pdf}#toolbar=0" width="100%" height="700" type="application/pdf"></iframe>'
    st.markdown(pdf_display, unsafe_allow_html=True)
    st.divider()

    # Pre-Generate Excel Bytes for Instant Download Access
    excel_path = excel.generate_excel(doc_data, filtered_df, st.session_state.totals, filename="preview.xlsx")
    with open(excel_path, "rb") as ef:
        excel_bytes = ef.read()

    # Form Submission Handler - Preserves Database Integrity against Double/Split-Clicking 
    def handle_download_callback(fmt):
        final_path = pdf_path if fmt == "PDF" else excel_path
        db.save_document(st.session_state.doc_num, st.session_state.doc_type, st.session_state.doc_date, 
                         st.session_state.customer, st.session_state.totals['final_amount'], final_path)
        if str(st.session_state.doc_num) == str(db.get_next_sequence(st.session_state.doc_type)):
            db.increment_sequence(st.session_state.doc_type)
        st.session_state.step = 1

    b1, b2, b3 = st.columns([3, 3, 4])
    with b1:
        if st.button("← Edit Selections"):
            st.session_state.step = 3
            st.rerun()
    with b2:
        st.download_button(
            label="📄 Download as PDF", data=pdf_bytes, 
            file_name=f"{st.session_state.doc_type}_{st.session_state.doc_num}.pdf", 
            mime="application/pdf", on_click=handle_download_callback, args=("PDF",), type="primary"
        )
    with b3:
        st.download_button(
            label="📊 Download as Excel", data=excel_bytes, 
            file_name=f"{st.session_state.doc_type}_{st.session_state.doc_num}.xlsx", 
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", 
            on_click=handle_download_callback, args=("Excel",), type="primary"
        )

# --- Standard Modules ---
def render_history():
    st.title("Document History")
    df = db.load_table('documents')
    st.dataframe(df, use_container_width=True)

def render_customers():
    st.title("Customer Master")
    tab1, tab2 = st.tabs(["Add New Customer", "Manage Existing Customers"])
    with tab1:
        with st.form("new_customer"):
            col1, col2 = st.columns(2)
            with col1:
                name = st.text_input("Company Name *")
                contact = st.text_input("Contact Person")
                phone = st.text_input("Phone Number")
                email = st.text_input("Email Address")
                gst = st.text_input("GST Number")
            with col2:
                address = st.text_area("Street Address")
                city = st.text_input("City")
                state = st.text_input("State")
                pincode = st.text_input("Pincode")

            if st.form_submit_button("Save Customer"):
                if not name: st.error("Company Name is required.")
                else:
                    db.get_connection().execute('''INSERT INTO customers 
                                  (name, contact, address, city, state, pincode, phone, email, gst) 
                                  VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''', 
                                 (name, contact, address, city, state, pincode, phone, email, gst)).connection.commit()
                    st.success(f"Customer {name} saved successfully!")
    with tab2:
        cust_df = db.load_table('customers')
        if not cust_df.empty:
            cust_to_edit = st.selectbox("Select Customer to Manage", cust_df['name'].tolist())
            if cust_to_edit:
                cust_data = cust_df[cust_df['name'] == cust_to_edit].iloc[0]
                with st.form("edit_customer"):
                    col1, col2 = st.columns(2)
                    with col1:
                        e_name = st.text_input("Company Name *", value=cust_data['name'])
                        e_contact = st.text_input("Contact Person", value=cust_data['contact'] if pd.notna(cust_data['contact']) else "")
                        e_phone = st.text_input("Phone Number", value=cust_data['phone'] if pd.notna(cust_data['phone']) else "")
                        e_email = st.text_input("Email Address", value=cust_data['email'] if pd.notna(cust_data['email']) else "")
                        e_gst = st.text_input("GST Number", value=cust_data['gst'] if pd.notna(cust_data['gst']) else "")
                    with col2:
                        e_address = st.text_area("Street Address", value=cust_data['address'] if pd.notna(cust_data['address']) else "")
                        e_city = st.text_input("City", value=cust_data['city'] if pd.notna(cust_data['city']) else "")
                        e_state = st.text_input("State", value=cust_data['state'] if pd.notna(cust_data['state']) else "")
                        e_pincode = st.text_input("Pincode", value=cust_data['pincode'] if pd.notna(cust_data['pincode']) else "")
                    
                    col_a, col_b = st.columns([1, 5])
                    with col_a: update_btn = st.form_submit_button("Update Customer", type="primary")
                    with col_b: delete_btn = st.form_submit_button("Delete Customer")
                        
                    if update_btn:
                        if not e_name: st.error("Company Name is required.")
                        else:
                            db.update_customer(int(cust_data['id']), e_name, e_contact, e_address, e_city, e_state, e_pincode, e_phone, e_email, e_gst)
                            st.success(f"Customer {e_name} updated successfully!")
                            st.rerun()
                    if delete_btn:
                        db.delete_customer(int(cust_data['id']))
                        st.warning(f"Customer {e_name} has been deleted.")
                        st.rerun()
        else: st.info("No customers found in the database.")
    st.divider()
    st.markdown("### Customer Directory")
    st.dataframe(db.load_table('customers'), use_container_width=True)

if __name__ == "__main__":
    main()
