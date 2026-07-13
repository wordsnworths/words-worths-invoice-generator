import streamlit as st
import pandas as pd
from datetime import datetime
import database as db
import calculations as calc
import excel_importer as xl
import pdf_generator as pdf

# UI Configuration
st.set_page_config(page_title="Words & Worths ERP", layout="wide", initial_sidebar_state="expanded")
st.markdown("""
    <style>
    .stApp { background-color: #FAFAFA; }
    .css-1d391kg { padding-top: 1rem; }
    </style>
""", unsafe_allow_html=True)

# Initialize System
db.init_db()

def main():
    st.sidebar.image("assets/logo.png", use_container_width=True)
    menu = st.sidebar.radio("Navigation", ["New Document", "History", "Customers", "Products", "Settings"])

    if menu == "New Document":
        render_new_document()
    elif menu == "History":
        render_history()
    elif menu == "Customers":
        render_customers()

def render_new_document():
    st.title("Create New Document")
    
    col1, col2, col3 = st.columns(3)
    doc_type = col1.selectbox("Document Type", ["Invoice", "Proforma", "Quotation"])
    doc_num = col2.text_input("Document Number", value=str(db.get_next_sequence(doc_type)))
    doc_date = col3.date_input("Date", datetime.today())

    cust_df = db.load_table('customers')
    cust_names = ["Select Customer..."] + cust_df['name'].tolist() if not cust_df.empty else ["No Customers Found"]
    customer = st.selectbox("Customer", cust_names)
    
    cust_address = ""
    cust_gst = ""
    if customer not in ["Select Customer...", "No Customers Found"]:
        selected_cust = cust_df[cust_df['name'] == customer].iloc[0]
        
        # FIX: Cleanly format the street address and convert newlines to PDF breaks
        street = str(selected_cust['address']).strip().replace('\n', '<br/>') if pd.notna(selected_cust['address']) else ""
        city_state_pin = [str(p).strip() for p in [selected_cust['city'], selected_cust['state'], selected_cust['pincode']] if pd.notna(p) and str(p).strip()]
        city_line = ", ".join(city_state_pin)
        
        # Combine them safely
        if street and city_line:
            cust_address = f"{street}<br/>{city_line}"
        elif street:
            cust_address = street
        elif city_line:
            cust_address = city_line
            
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
    
    edited_df['Amount'] = (temp_qty * temp_rate) * (1 - temp_disc / 100)
    edited_df['Amount'] = edited_df['Amount'].round(2)

    st.divider()

    col_cols, col_set, col_tot = st.columns([1.5, 1.5, 1.2])
    
    with col_cols:
        st.markdown("**Print Layout Options**")
        available_cols = edited_df.columns.tolist()
        selected_cols = st.multiselect("Columns to include in PDF", available_cols, default=available_cols)

    with col_set:
        st.markdown("**Tax, Discounts & Terms**")
        overall_discount_percent = st.number_input("Overall Additional Discount (%)", min_value=0.0, max_value=100.0, value=0.0, step=1.0)
        include_gst = st.checkbox("Include GST (18%)", value=False)
        auto_round = st.checkbox("Auto Round Off", value=True)
        
        default_payment_terms = "- 50% advance payment upon confirmation of order\n- Balance payment on delivery."
        payment_terms = st.text_area("Payment Terms & Conditions", default_payment_terms, height=80)
        
        default_terms = """1. 50% advance against order confirmation / P.O
2. Delivery Supply is subject to availability with publishers at the time of procurement.
3. Delivery schedules and prices quoted are indicative only and are subject to publisher stock availability and MRP market revisions.
4. Partial supply may be effected where required.
5. Unavailable titles (cost) will be refunded / credited or adjusted with alternative titles as mutually agreed.
6. Books supplied against confirmed order are not returnable / cancellable, except due to damage / supply discrepancy."""
        terms = st.text_area("Supply Guidelines / Terms", default_terms, height=180)

    with col_tot:
        st.markdown("**Calculation Summary**")
        totals = calc.calculate_totals(edited_df, include_gst, auto_round, overall_discount_percent)
        st.metric("Net Amount", f"₹ {totals['net_total']:.2f}")
        if include_gst: st.metric("GST Amount", f"₹ {totals['gst_total']:.2f}")
        st.metric("Final Amount", f"₹ {totals['final_amount']:.2f}", delta=f"Round off: {totals['round_off']:.2f}", delta_color="off")
        st.caption(f"**In Words:** {totals['amount_words']}")

    st.divider()
    if st.button("Generate Document", type="primary"):
        if customer in ["Select Customer...", "No Customers Found"]:
            st.error("Please select a valid customer.")
            return
        if not selected_cols:
            st.error("Please select at least one column for the PDF.")
            return
            
        doc_data = {
            'type': doc_type, 'id': doc_num, 'date': doc_date.strftime("%d-%m-%Y"),
            'customer': customer, 'address': cust_address, 'gst': cust_gst, 
            'terms': terms, 'payment_terms': payment_terms
        }
        
        pdf_df = edited_df[selected_cols]
        pdf_path = pdf.generate_pdf(doc_data, pdf_df, totals)
        
        db.save_document(doc_num, doc_type, doc_date, customer, totals['final_amount'], pdf_path)
        if str(doc_num) == str(db.get_next_sequence(doc_type)):
            db.increment_sequence(doc_type)
            
        st.success(f"{doc_type} {doc_num} generated successfully!")
        with open(pdf_path, "rb") as f:
            st.download_button("Download PDF", f, file_name=f"{doc_type}_{doc_num}.pdf", mime="application/pdf")

def render_history():
    st.title("Document History")
    df = db.load_table('documents')
    st.dataframe(df, use_container_width=True)

def render_customers():
    st.title("Customer Master")
    
    # --- NEW: Added Tabs for Add and Manage features ---
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
                if not name:
                    st.error("Company Name is required.")
                else:
                    conn = db.get_connection()
                    conn.execute('''INSERT INTO customers 
                                  (name, contact, address, city, state, pincode, phone, email, gst) 
                                  VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''', 
                                 (name, contact, address, city, state, pincode, phone, email, gst))
                    conn.commit()
                    st.success(f"Customer {name} saved successfully!")
                    
    with tab2:
        cust_df = db.load_table('customers')
        if not cust_df.empty:
            cust_to_edit = st.selectbox("Select Customer to Manage", cust_df['name'].tolist())
            if cust_to_edit:
                # Get the selected customer's existing data
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
                    with col_a:
                        update_btn = st.form_submit_button("Update Customer", type="primary")
                    with col_b:
                        delete_btn = st.form_submit_button("Delete Customer")
                        
                    if update_btn:
                        if not e_name:
                            st.error("Company Name is required.")
                        else:
                            db.update_customer(int(cust_data['id']), e_name, e_contact, e_address, e_city, e_state, e_pincode, e_phone, e_email, e_gst)
                            st.success(f"Customer {e_name} updated successfully!")
                            st.rerun() # Refresh the page to reflect changes instantly
                            
                    if delete_btn:
                        db.delete_customer(int(cust_data['id']))
                        st.warning(f"Customer {e_name} has been deleted.")
                        st.rerun()
        else:
            st.info("No customers found in the database.")
            
    st.divider()
    st.markdown("### Customer Directory")
    # Refresh the table display from the database
    st.dataframe(db.load_table('customers'), use_container_width=True)

if __name__ == "__main__":
    main()
