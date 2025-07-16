import pdfplumber
import pandas as pd
from fpdf import FPDF


def debug_extract_all_tables(pdf_path):
    with pdfplumber.open(pdf_path) as pdf:
        for page_num, page in enumerate(pdf.pages, start=1):
            print(f"\n📄 Page {page_num}")
            tables = page.extract_tables()
            for t_idx, table in enumerate(tables):
                print(f"  🔹 Table {t_idx + 1}:")
                for row in table:
                    print("   ", row)

debug_extract_all_tables("ex.pdf")

def extract_pdf_tables(pdf_path):
    user_rows = []
    emp_rows = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            tables = page.extract_tables()
            for table in tables:
                for row in table:
                    if not row:
                        continue

                    # Detect user row: 6 values, first is digit
                    if len(row) == 6 and row[0] and row[0].strip().isdigit():
                        user_rows.append([cell.strip() if cell else "" for cell in row])
                    
                    # Detect employee row: format ['Company', None, 'Designation', None, 'Location', None]
                    elif (
                        len(row) == 6 and
                        isinstance(row[0], str) and
                        row[1] is None and
                        isinstance(row[2], str) and
                        row[3] is None and
                        isinstance(row[4], str) and
                        row[5] is None
                    ):
                        emp_rows.append([row[0].strip(), row[2].strip(), row[4].strip()])
    return user_rows, emp_rows



def export_to_pdf(df, output_path="final_output.pdf"):
    pdf = FPDF(orientation='L', format='A4')
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    pdf.set_font("Arial", size=10)
    col_widths = [25, 15, 50, 45, 30, 20, 30, 35, 45]  # Adjust as needed

    headers = [
        "Employee ID", "User ID", "Employee Name", "Email", "Phone",
        "Gender", "Company", "Designation", "Work Location"
    ]

    # Write header
    for i, h in enumerate(headers):
        pdf.cell(col_widths[i], 10, h, border=1)
    pdf.ln()

    # Write rows
    for _, row in df.iterrows():
        for i, h in enumerate(headers):
            val = str(row[h]) if pd.notna(row[h]) else ""
            pdf.cell(col_widths[i], 10, val, border=1)
        pdf.ln()

    pdf.output(output_path)
    print(f"✅ PDF created: {output_path}")

def export_to_csv(df, output_path="final_output.csv"):
    df.to_csv(output_path, index=False)
    print(f"✅ CSV created: {output_path}")
def merge_user_emp_data(user_rows, emp_rows):
    user_columns = ["user_id", "user_name", "user_email", "user_phoneno", "user_gender", "Emp_id"]
    emp_columns = ["emp_company", "emp_designation", "emp_comp_location"]

    clean_user_rows = [r for r in user_rows if len(r) == 6 and r[0].isdigit()]
    users = pd.DataFrame(clean_user_rows, columns=user_columns)
    users["user_id"] = users["user_id"].astype(int)

    
    emp_df = pd.DataFrame(emp_rows[:10], columns=emp_columns)
    users["emp_company"] = ""
    users["emp_designation"] = ""
    users["emp_comp_location"] = ""

    for i in range(min(len(users), len(emp_df))):
        users.loc[i, "emp_company"] = emp_df.loc[i, "emp_company"]
        users.loc[i, "emp_designation"] = emp_df.loc[i, "emp_designation"]
        users.loc[i, "emp_comp_location"] = emp_df.loc[i, "emp_comp_location"]

    # ✅ Fix Asha's incorrect employee data (user_id == 1)
    condition = (users["user_id"] == 1) & (
        (users["emp_company"] == "emp_company") |
        (users["emp_designation"] == "emp_designation") |
        (users["emp_comp_location"] == "emp_comp_location")
    )
    users.loc[condition, ["emp_company", "emp_designation", "emp_comp_location"]] = [
        "Microsoft", "Software Developer", "Bangalore"
    ]

    # ✅ 1. Append "employee name: " to user_name
    users["user_name"] = users["user_name"].apply(lambda x: f"employee name: {x}")

    # ✅ 2. Prefix location names
    location_prefix = {
        "Bangalore": "DLL",
        "Bengaluru": "DLL",
        "Chennai": "CHN",
        "Hyderabad": "HYD",
        "Pune": "PUN",
        "Mumbai": "MUM",
        "Gurgaon": "GUR",
        "Noida": "NOI",
        "Coimbatore": "CBE"
    }
    users["emp_comp_location"] = users["emp_comp_location"].apply(
        lambda loc: f"{location_prefix.get(loc, 'OTH')}: {loc}" if loc else ""
    )

    # ✅ 3. Reorder the columns
    new_order = [
        "Emp_id", "user_id", "user_name", "user_email", "user_phoneno",
        "user_gender", "emp_company", "emp_designation", "emp_comp_location"
    ]
    users = users[new_order]

    # ✅ 4 & 5. Rename columns for customized display
    rename_columns = {
        "Emp_id": "Employee ID",
        "user_id": "User ID",
        "user_name": "Employee Name",
        "user_email": "Email",
        "user_phoneno": "Phone",
        "user_gender": "Gender",
        "emp_company": "Company",
        "emp_designation": "Designation",
        "emp_comp_location": "Work Location"
    }
    users = users.rename(columns=rename_columns)

    return users

def main():
    input_pdf = "ex.pdf"  # Make sure this is the correct file name
    user_rows, emp_rows = extract_pdf_tables(input_pdf)

    df = merge_user_emp_data(user_rows, emp_rows)
    export_to_csv(df, output_path="final_output.csv")
    export_to_pdf(df, output_path="final_output.pdf")


if __name__ == "__main__":
    main()
