import sqlite3
import csv
import os

root_folder = "C:\\Users\\psharmak\\OneDrive - Amgen\\psharmak\\agents\\CRO_file_analysis\\"
files_folder = os.path.join(root_folder, "files")

# Specify the CSV files to be imported
csv_files = {
    "CTMS_REPORT": "ctms_report.csv",
    "CTMS_DEVODS_SAP_CMP_REPORT": "ctms_devods_sap_cmp_report.csv"
}

def insert_data_from_csv():
    conn = sqlite3.connect(root_folder + "db\\cro_analysis.db")
    cursor = conn.cursor()

    for table_name, csv_file in csv_files.items():
        csv_path = os.path.join(files_folder, csv_file)
        if not os.path.exists(csv_path):
            print(f"{csv_file} not found. Skipping insertion into {table_name}.")
            continue

        # Truncate the table
        cursor.execute(f"DELETE FROM {table_name}")

        # Insert data into the table
        record_count = 0
        try:
            with open(csv_path, 'r', encoding='utf-8') as file:
                reader = csv.DictReader(file)
                for row in reader:
                    values = [row[column] for column in reader.fieldnames]
                    placeholders = ', '.join(['?'] * len(values))
                    cursor.execute(f"INSERT INTO {table_name} VALUES ({placeholders})", values)
                    record_count += 1
        except FileNotFoundError:
            print(f"{csv_file} not found. Skipping insertion into {table_name}.")

        # Print the number of records inserted into the table
        print(f"Number of records inserted into {table_name}: {record_count}")

    conn.commit()
    conn.close()

if __name__ == "__main__":
    insert_data_from_csv()
