import pandas as pd

COLUMN_MAPPINGS = {
    'Title': ['title', 'book', 'book name', 'item', 'description'],
    'Publication': ['publication', 'publisher', 'imprint'],
    'Qty': ['qty', 'quantity', 'copies', 'nos'],
    'Rate': ['rate', 'price', 'mrp', 'unit price'],
    'Discount %': ['discount', 'disc %', 'discount %'],
    'ISBN': ['isbn'],
    'Author': ['author']
}

def auto_map_columns(df):
    mapped_df = pd.DataFrame()
    lower_cols = [str(c).lower().strip() for c in df.columns]
    
    for std_col, aliases in COLUMN_MAPPINGS.items():
        found = False
        for idx, col in enumerate(lower_cols):
            if any(alias == col for alias in aliases):
                mapped_df[std_col] = df.iloc[:, idx]
                found = True
                break
        if not found:
            mapped_df[std_col] = 0 if std_col in ['Qty', 'Rate', 'Discount %'] else ''
            
    # Add S.No automatically
    mapped_df.insert(0, 'S.No', range(1, len(mapped_df) + 1))
    return mapped_df

def process_upload(file):
    if file.name.endswith('.csv'):
        df = pd.read_csv(file)
    else:
        df = pd.read_excel(file)
    return auto_map_columns(df)