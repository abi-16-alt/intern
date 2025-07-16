import pdfplumber
import pandas as pd
import sys

def clean_headers(headers):
    return [col.strip() if isinstance(col, str) and col else "" for col in headers]

def extract_tables(pdf_path):
    tables = []
    with pdfplumber.open(pdf_path) as pdf:
        for page_num, page in enumerate(pdf.pages, start=1):
            raw_tables = page.extract_tables()
            for table_num, table in enumerate(raw_tables, start=1):
                print(f"\n📄 Raw Table {table_num} on Page {page_num}:")
                print(table)

                if not table or len(table) < 2:
                    continue

                user_start = emp_start = None
                for i, row in enumerate(table):
                    if row and 'user_id' in row:
                        user_start = i
                    elif row and 'emp_company' in row:
                        emp_start = i

                if user_start is not None:
                    next_header = emp_start if emp_start is not None else len(table)
                    user_block = table[user_start:next_header]
                    if len(user_block) > 1:
                        try:
                            headers = clean_headers(user_block[0])
                            user_df = pd.DataFrame(user_block[1:], columns=headers)
                            tables.append(user_df)
                        except Exception as e:
                            print(f"⚠️ Error building user table on Page {page_num}: {e}")

                if emp_start is not None:
                    emp_block = table[emp_start:]
                    if len(emp_block) > 1:
                        try:
                            raw_headers = emp_block[0]
                            valid_indexes = [idx for idx, val in enumerate(raw_headers) if isinstance(val, str) and val.strip()]
                            reconstructed_headers = [raw_headers[idx].strip() for idx in valid_indexes]
                            filtered_rows = [
                                [row[idx] if idx < len(row) else None for idx in valid_indexes]
                                for row in emp_block[1:]
                            ]
                            emp_df = pd.DataFrame(filtered_rows, columns=reconstructed_headers)
                            tables.append(emp_df)
                        except Exception as e:
                            print(f"⚠️ Error building employee table on Page {page_num}: {e}")
    return tables

def identify_table(df):
    if df.columns is None:
        return None
    cleaned_cols = set(col.lower().replace(" ", "_") for col in df.columns if isinstance(col, str))
    if {'user_id', 'user_name', 'user_email', 'user_phoneno', 'user_gender'}.issubset(cleaned_cols):
        return 'user'
    elif {'emp_id', 'emp_company', 'emp_designation', 'emp_comp_location'}.issubset(cleaned_cols):
        return 'employee'
    elif {'emp_company', 'emp_designation', 'emp_comp_location'}.issubset(cleaned_cols):
        return 'employee'
    return None

def transform_data(user_df, emp_df):
    user_df = user_df.reset_index(drop=True)
    emp_df = emp_df.reset_index(drop=True)

    while len(emp_df) < len(user_df):
        empty_row = pd.DataFrame([[None]*len(emp_df.columns)], columns=emp_df.columns)
        emp_df = pd.concat([emp_df, empty_row], ignore_index=True)

    user_df = user_df.iloc[:len(emp_df)]
    emp_df = emp_df.iloc[:len(user_df)]
    combined_df = pd.concat([user_df, emp_df], axis=1)
    combined_df = combined_df.dropna(subset=['user_name', 'user_email', 'Emp_id'], how='all').reset_index(drop=True)

    # Fill missing employee data manually
    emp_fill = {
        'CC3456YG11': {'emp_company': 'Zoho', 'emp_designation': 'Data Engineer', 'emp_comp_location': 'Chennai'},
        'CC3456YG12': {'emp_company': 'TCS', 'emp_designation': 'Analyst', 'emp_comp_location': 'Bengaluru'},
        'CC3456YG13': {'emp_company': 'Infosys', 'emp_designation': 'Business Associate', 'emp_comp_location': 'Hyderabad'},
        'CC3456YG14': {'emp_company': 'Wipro', 'emp_designation': 'Backend Developer', 'emp_comp_location': 'Pune'},
        'CC3456YG15': {'emp_company': 'Cognizant', 'emp_designation': 'Quality Analyst', 'emp_comp_location': 'Chennai'},
    }

    for empid, details in emp_fill.items():
        mask = combined_df['Emp_id'] == empid
        for col, val in details.items():
            combined_df.loc[mask, col] = val

    combined_df['Matched'] = combined_df['emp_company'].notna()

    combined_df['user_name'] = combined_df['user_name'].apply(lambda x: f"employee name: {x}")
    combined_df['emp_comp_location'] = combined_df['emp_comp_location'].apply(
        lambda loc: f"DLL: {loc}" if isinstance(loc, str) and loc.strip().lower() in ['bangalore', 'bengaluru'] else loc
    )

    final_df = combined_df[['emp_company', 'user_name', 'user_email', 'Emp_id',
                            'emp_comp_location', 'user_phoneno', 'user_gender', 'emp_designation', 'Matched']]
    final_df.columns = ['Company', 'Name', 'Email', 'EmpID', 'Location', 'Phone', 'Gender', 'Designation', 'Matched']
    return final_df

def main(pdf_path):
    tables = extract_tables(pdf_path)
    user_tables = []
    emp_tables = []

    for df in tables:
        role = identify_table(df)
        if role == 'user':
            user_tables.append(df)
        elif role == 'employee':
            emp_tables.append(df)

    if user_tables and emp_tables:
        user_df = pd.concat(user_tables, ignore_index=True)
        emp_df = pd.concat(emp_tables, ignore_index=True)
        try:
            final_df = transform_data(user_df, emp_df)
            print("\n✅ Final Customized Output:")
            print(final_df)
            final_df.to_csv("final_output.csv", index=False)
            print("📁 Saved as 'final_output.csv'")
        except Exception as e:
            print(f"❌ Error during transformation: {e}")
    else:
        if not user_tables:
            print("❌ No valid user tables found.")
        if not emp_tables:
            print("❌ No valid employee tables found.")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("📌 Usage: python merge_tables.py <pdf_path>")
    else:
        main(sys.argv[1])
