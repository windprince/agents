import win32com.client
import sqlite3
import gradio as gr
import logging
import os
import subprocess
import sys
import matplotlib.pyplot as plt

root_folder = "C:\\Users\\psharmak\\OneDrive - Amgen\\psharmak\\agents\\CRO_file_analysis\\"
files_folder = os.path.join(root_folder, "files")

ATTACHMENT_SUBJECTS = {
    "ExtCTMS: All CRO Partner - CTMS Report for study and site Information": "ctms_report.csv",
    "ExtCTMS: Fortrea / Covance CRO Partner - CTMS Report for study and site Information": "ctms_cvd_fta_report.csv",
    "ExtCTMS: ICON / PRA CRO Partner - CTMS Report for study and site Information": "ctms_pra_icn_report.csv",
    "ExtCTMS: Parexel CRO Partner - CTMS Report for study and site Information": "ctms_pxl_report.csv",
    "ExtCTMS: PPD CRO Partner - CTMS Report for study and site Information": "ctms_ppd_report.csv",
    "The SAP site report with ExtCTMS sites": "ctms_devods_sap_cmp_report.csv",
}

class OutlookConnector:
    def connect(self):
        print("Connecting to Outlook...")
        try:
            outlook = win32com.client.Dispatch("Outlook.Application").GetNamespace("MAPI")
            inbox = outlook.GetDefaultFolder(6)  # 6 refers to the inbox
            logging.info("Successfully connected to Outlook.")
            return inbox
        except Exception as e:
            logging.error(f"Failed to connect to Outlook: {e}")
            print(f"Failed to connect to Outlook: {e}")
            return None

class AttachmentExtractor:
    def __init__(self, connector, save_path, subjects):
        self.connector = connector
        self.save_path = save_path
        self.subjects = subjects

    def extract(self):
        print(f"Extracting attachments")
        try:
            inbox = self.connector.connect()
            if inbox is None:
                logging.error("Could not connect to Outlook, exiting.")
                sys.exit(1)
            extctms_folder = inbox.Folders["ExtCTMS"]
            if extctms_folder is None:
                logging.error("Could not find the ExtCTMS sub-folder, exiting.")
                sys.exit(1)
            else:
                messages = extctms_folder.Items
                message = messages.GetFirst()
                while message:
                    subject = message.Subject
                    if subject in self.subjects:
                        for attachment in message.Attachments:
                            save_path = os.path.join(self.save_path, attachment.FileName)
                            # Check if the file already exists and has the same size
                            if os.path.exists(save_path) and os.path.getsize(save_path) == attachment.Size:
                                logging.info(f"Attachment '{attachment.FileName}' already exists with the same size at '{save_path}', skipping.")
                                print(f"Attachment '{attachment.FileName}' already exists with the same size at '{save_path}', skipping.")
                            else:
                                action = "Overwriting" if os.path.exists(save_path) else "Saving"
                                logging.info(f"{action} attachment '{attachment.FileName}' from email with subject '{subject}' to '{save_path}'")
                                print(f"{action} attachment '{attachment.FileName}' from email with subject '{subject}' to '{save_path}'")
                                attachment.SaveAsFile(save_path)
                    message = messages.GetNext()
        except Exception as e:
            logging.error(f"Error in extract_attachments: {e}")

class DataInserter:
    def __init__(self, root_folder, files_folder):
        self.root_folder = root_folder
        self.files_folder = files_folder

    def check_and_execute(self):
        ctms_devods_sap_cmp_report_path = os.path.join(self.files_folder, "ctms_devods_sap_cmp_report.csv")
        ctms_report_path = os.path.join(self.files_folder, "ctms_report.csv")
        ctms_devods_sap_cmp_report_exists = os.path.exists(ctms_devods_sap_cmp_report_path)
        ctms_report_exists = os.path.exists(ctms_report_path)

        if ctms_devods_sap_cmp_report_exists and ctms_report_exists:
            print("Both files found. Inserting data from CSV files.")
            subprocess.run(["python", os.path.join(self.root_folder, "insert_data_from_csv.py")])
        else:
            print("One or both files are missing. Skipping insert_data_from_csv.py")
            return

class DatabaseAccessor:
    def __init__(self, db_path):
        self.db_path = db_path

    def get_vendor_names(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT DISTINCT VENDOR_NAME FROM CTMS_REPORT")
        vendor_names = [row[0] for row in cursor.fetchall()]
        conn.close()
        return vendor_names

    def get_study_numbers(self, vendor_name):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT DISTINCT STUDY_NUMBER FROM CTMS_REPORT WHERE VENDOR_NAME = ?", (vendor_name,))
        study_numbers = [row[0] for row in cursor.fetchall()]
        conn.close()
        return study_numbers

    def get_country_names(self, vendor_name, study_number):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT DISTINCT SITE_NUMBER_WITHIN_STUDY 
            FROM CTMS_REPORT 
            WHERE VENDOR_NAME = ? AND STUDY_NUMBER = ? AND SAP_REGULATORY_BLOCK != 'Block Removed'
        """, (vendor_name, study_number))
        site_numbers = [row[0] for row in cursor.fetchall()]
        conn.close()
        return site_numbers

    def get_site_details(self, vendor_name, study_number, site_number):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT SIP_PLANNED_DATE, DEVODS_SITE_EXISTS, DEVODS_DATA_COMPLETE, SAP_SITE_CREATED, SAP_REGULATORY_BLOCK, ADDITIONAL_DETAILS
            FROM CTMS_REPORT
            WHERE VENDOR_NAME = ? AND STUDY_NUMBER = ? AND SITE_NUMBER_WITHIN_STUDY = ?
        """, (vendor_name, study_number, site_number))
        result = cursor.fetchone()
        conn.close()
        if result:
            sip_planned_date, devods_site_exists, devods_data_complete, sap_site_created, sap_regulatory_block, additional_details = result
            devods_site_exists = 'Yes' if devods_site_exists == 'Yes' else 'No'
            devods_data_complete = 'Yes' if devods_data_complete == 'Yes' else 'No'
            sap_site_created = 'Yes' if sap_site_created == 'Yes' else 'No'
            return [sip_planned_date, devods_site_exists, devods_data_complete, sap_site_created, sap_regulatory_block, additional_details]
        else:
            return ["", "", "", "", "", ""]

    def get_dashboard_data(self, vendor_name=None, study_number=None, site_number=None, output_variable=None):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        query = f"""
            SELECT 
                SUM(CASE WHEN {output_variable} = 'Yes' THEN 1 ELSE 0 END) AS yes_count,
                SUM(CASE WHEN {output_variable} = 'No' THEN 1 ELSE 0 END) AS no_count,
                SUM(CASE WHEN {output_variable} IS NULL THEN 1 ELSE 0 END) AS absent_count
            FROM CTMS_REPORT
            WHERE 1=1
        """
        params = []
        if vendor_name:
            query += " AND VENDOR_NAME = ?"
            params.append(vendor_name)
        if study_number:
            query += " AND STUDY_NUMBER = ?"
            params.append(study_number)
        if site_number:
            query += " AND SITE_NUMBER_WITHIN_STUDY = ?"
            params.append(site_number)
        cursor.execute(query, params)
        result = cursor.fetchone()
        conn.close()
        return result

# Initialize components
connector = OutlookConnector()
extractor = AttachmentExtractor(connector, files_folder, ATTACHMENT_SUBJECTS)
inserter = DataInserter(root_folder, files_folder)
db_accessor = DatabaseAccessor(root_folder + "db\\cro_analysis.db")

# Call the functions once before launching the Gradio app
extractor.extract()
inserter.check_and_execute()

vendor_names = db_accessor.get_vendor_names()

OUTPUT_VARIABLE_MAP = {
    "Site in DevODS": "DEVODS_SITE_EXISTS",
    "Data in DevODS": "DEVODS_DATA_COMPLETE",
    "Site in SAP": "SAP_SITE_CREATED",
    "Reg. Block": "SAP_REGULATORY_BLOCK"
}

def generate_pie_charts(vendor_name=None, study_number=None, site_number=None, output_variables=None):
    figs = []
    if not output_variables:
        return []
    for output_variable in output_variables:
        db_column = OUTPUT_VARIABLE_MAP.get(output_variable)
        if not db_column:
            continue
        data = db_accessor.get_dashboard_data(vendor_name, study_number, site_number, db_column)
        labels = ['Yes', 'No', 'Absent']
        sizes = [data[0] or 0, data[1] or 0, data[2] or 0]
        fig, ax = plt.subplots()
        if sum(sizes) > 0:
            ax.pie(sizes, labels=labels, autopct='%1.1f%%', startangle=90)
            ax.axis('equal')  # Equal aspect ratio ensures that pie is drawn as a circle.
        else:
            ax.text(0.5, 0.5, "No data available", ha="center", va="center")
            ax.axis('off')
        ax.set_title(output_variable)
        fig_path = os.path.join(files_folder, f"{output_variable}.png")
        fig.savefig(fig_path)
        plt.close(fig)
        figs.append(fig_path)
    return figs

with gr.Blocks() as demo:
    with gr.Row():
        vendor_name_dropdown = gr.Dropdown(label="Select Vendor Name", choices=vendor_names, value=None)
        study_number_dropdown = gr.Dropdown(label="Select Study Number", choices=[])
        site_number_dropdown = gr.Dropdown(label="Select Site Number", choices=[])
    
    vendor_name_dropdown.change(fn=lambda vendor_name: gr.update(choices=db_accessor.get_study_numbers(vendor_name)), inputs=vendor_name_dropdown, outputs=study_number_dropdown)
    study_number_dropdown.change(fn=lambda vendor_name, study_number: gr.update(choices=db_accessor.get_site_numbers(vendor_name, study_number)), inputs=[vendor_name_dropdown, study_number_dropdown], outputs=site_number_dropdown)
    
    with gr.Row():
        sip_planned_date = gr.Textbox(label="SIP Planned Date", interactive=False)
        devods_site_exists = gr.Textbox(label="DevODS Site Exists", interactive=False)
        devods_data_complete = gr.Textbox(label="DevODS Data Complete", interactive=False)
        sap_site_created = gr.Textbox(label="SAP Site Created", interactive=False)
        sap_regulatory_block = gr.Textbox(label="SAP Regulatory Block", interactive=False)
        additional_details = gr.Textbox(label="Additional Details", interactive=False)
    
    site_number_dropdown.change(
        fn=lambda vendor_name, study_number, site_number: db_accessor.get_site_details(vendor_name, study_number, site_number), 
        inputs=[vendor_name_dropdown, study_number_dropdown, site_number_dropdown], 
        outputs=[sip_planned_date, devods_site_exists, devods_data_complete, sap_site_created, sap_regulatory_block, additional_details]
    )

    with gr.Row():
        with gr.Column():
            gr.Markdown("## Reports")
            report_vendor_name = gr.Dropdown(label="Vendor Name", choices=vendor_names, value=None)
            report_study_number = gr.Dropdown(label="Study Number", choices=[])
            report_site_number = gr.Dropdown(label="Site Number", choices=[])
            output_variables = gr.CheckboxGroup(label="Select Output Variables", choices=list(OUTPUT_VARIABLE_MAP.keys()))
            report_button = gr.Button("Generate Report")
        
        with gr.Column():
            gr.Markdown("## Dashboard")
            pie_charts = gr.Gallery()

    report_vendor_name.change(fn=lambda vendor_name: gr.update(choices=db_accessor.get_study_numbers(vendor_name)), inputs=report_vendor_name, outputs=report_study_number)
    report_study_number.change(fn=lambda vendor_name, study_number: gr.update(choices=db_accessor.get_site_numbers(vendor_name, study_number)), inputs=[report_vendor_name, report_study_number], outputs=report_site_number)
    report_button.click(fn=generate_pie_charts, inputs=[report_vendor_name, report_study_number, report_site_number, output_variables], outputs=pie_charts)

demo.launch()
