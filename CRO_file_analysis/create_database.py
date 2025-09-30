import sqlite3

root_folder = "C:/Users/psharmak/OneDrive/psharmak_agents/CRO_file_analysis/"
db_folder = root_folder + "db/"

def drop_tables():
    conn = sqlite3.connect(db_folder + "cro_analysis.db")
    cursor = conn.cursor()

    # Drop ctms_report table
    cursor.execute(
        """
        DROP TABLE IF EXISTS ctms_report
    """
    )
    # Drop ctms_devods_sap_cmp_report table
    cursor.execute(
        """
        DROP TABLE IF EXISTS ctms_devods_sap_cmp_report
    """
    )


def create_database():
    conn = sqlite3.connect(db_folder + "cro_analysis.db")
    cursor = conn.cursor()

    # Create ctms_report table
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS ctms_report (
        VENDOR_NAME TEXT,
        STUDY_NUMBER TEXT,
        STUDY_SITE_ID TEXT,
        SITE_NUMBER_WITHIN_STUDY TEXT,
        COUNTRY_NAME TEXT,
        PI_FNAME TEXT,
        PI_LNAME TEXT,
        SIV_PLANNED_DATE TEXT,
        SIP_PLANNED_DATE TEXT,
        DEVODS_SITE_EXISTS TEXT,
        DEVODS_DATA_COMPLETE TEXT,
        SAP_SITE_CREATED TEXT,
        SAP_REGULATORY_BLOCK TEXT,
        ADDITIONAL_DETAILS TEXT,
        HZN_STUDY_NUMBER TEXT
    )
    """
    )

    # Create ctms_devods_sap_cmp_report table
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS ctms_devods_sap_cmp_report (
        Sales_Organization TEXT,
        ABP_PRA TEXT,
        ShipTo TEXT,
        STUDY_SITE_ID TEXT,
        STUDY_NUMBER TEXT,
        ZZSTUDY_STAT TEXT,
        Study_Branch TEXT,
        SITE_NUMBER TEXT,
        SAP_Name TEXT,
        ODS_Site_Name TEXT,
        SAP_Name_3 TEXT,
        ODS_ShipToName TEXT,
        SAP_Street TEXT,
        ODS_Street TEXT,
        SAP_STREET_4 TEXT,
        ODS_LINE_2 TEXT,
        SAP_POSTAL_CODE TEXT,
        ODS_POSTAL_CODE TEXT,
        SAP_CITY TEXT,
        ODS_CITY TEXT,
        SAP_COUNTRY TEXT,
        ODS_ISO_COUNTRY_2_CHAR TEXT,
        SAP_STATE TEXT,
        ODS_STATE TEXT,
        SAP_Telephone TEXT,
        ODS_Telephone TEXT,
        SAP_Fax TEXT,
        ODS_Fax TEXT,
        SAP_Email TEXT,
        ODS_Email TEXT,
        SAP_CRA_First_Name TEXT,
        ODS_Primary_CRA_Primary_Study_Team_Member_First_Name TEXT,
        ODS_ISS_Primary_CRA_Primary_Study_Team_Member_First_Name TEXT,
        SAP_CRA_Last_Name TEXT,
        ODS_Primary_CRA_Primary_Study_Team_Member_Last_Name TEXT,
        ODS_ISS_Primary_CRA_Primary_Study_Team_Member_Last_Name TEXT,
        SAP_CRA_Phone TEXT,
        ODS_Primary_CRA_Primary_Study_Team_Member_Telephone TEXT,
        SAP_CRA_Email TEXT,
        ODS_Primary_CRA_Primary_Study_Team_Member_Email TEXT,
        ODS_ISS_Primary_CRA_Primary_Study_Team_Member_Email TEXT,
        SAP_PI_Title TEXT,
        SAP_PI_First_Name TEXT,
        ODS_PI_First_Name TEXT,
        SAP_PI_Last_Name TEXT,
        ODS_PI_Last_Name TEXT,
        SAP_PI_Site_Name TEXT,
        ODS_Short_Site_Name TEXT,
        SAP_PI_Street_House TEXT,
        ODS_PI_Street_House TEXT,
        SAP_PI_Street4 TEXT,
        ODS_PI_Street4 TEXT,
        SAP_PI_Postal TEXT,
        ODS_PI_Postal TEXT,
        SAP_PI_City TEXT,
        ODS_PI_City TEXT,
        SAP_PI_Country TEXT,
        ODS_PI_Country TEXT,
        SAP_PI_Region TEXT,
        ODS_PI_Region TEXT,
        SAP_PI_Phone TEXT,
        ODS_PI_Phone TEXT,
        SAP_PI_Fax TEXT,
        ODS_PI_Fax TEXT,
        SAP_PI_Email TEXT,
        ODS_PI_Email TEXT,
        Created_by TEXT,
        Entered_on TEXT,
        Central_delivery_block TEXT,
        Central_order_block TEXT,
        SITE_STATUS TEXT,
        Comment TEXT,
        SITE_NAME_STATUS_CHANGE_DT TEXT,
        Address_UPDATED_DATE TEXT,
        Account_group TEXT,
        ODS_ShipTo_Missing TEXT,
        ODS_STREET_Missing TEXT,
        ODS_PHONE_Missing TEXT,
        ODS_Primary_CRA_Primary_Study_Team_Member_Missing TEXT,
        ODS_PI_Missing TEXT
    )
    """
    )

    conn.commit()
    conn.close()


if __name__ == "__main__":
    drop_tables()
    create_database()
