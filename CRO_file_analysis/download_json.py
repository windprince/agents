import jaydebeapi
import os
import requests

# JDBC connection details
jdbc_url = "jdbc:sftp:RemoteHost=sftp.amgen.com;"
jdbc_driver = "cdata.jdbc.sftp.SFTPDriver"
driver_jar = "C:/Program Files/CData/CData JDBC Driver for SFTP 2024/lib/cdata.jdbc.sftp.jar"  # Path to the JDBC driver JAR file
username = os.getenv('DATABRICKS_USERNAME')  # Use environment variable for security
password = os.getenv('DATABRICKS_PASSWORD')  # Use environment variable for security

# Define the folder to save the downloaded JSON files
output_folder = "C:\\Users\\psharmak\\OneDrive - Amgen\\psharmak\\agents\\CRO_file_analysis\\json_files"
os.makedirs(output_folder, exist_ok=True)

def run_query_and_get_file_paths():
    """
    Runs the SQL query via JDBC and returns the list of file paths.
    """
    try:
        # Connect to the SFTP server via JDBC
        conn = jaydebeapi.connect(
            jdbc_driver,
            jdbc_url,
            [username, password],
            driver_jar
        )
        cursor = conn.cursor()

        # Define the query
        query = """
        WITH CleanedFiles AS (
            SELECT
                r.FilePath,
                r.Filename,
                r.LastModified,
                REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(
                    r.Filename, '1', ''), '2', ''), '3', ''), '4', ''), '5', ''), '6', ''), '7', ''), '8', ''), '9', ''), '0', '') AS CleanedFilename
            FROM
                "CData.SFTP.Root" r
            WHERE
                UPPER(r.Filename) LIKE '%.JSON'
                AND UPPER(r.Filename) NOT LIKE '%TRANSFER%'
        ),
        LatestFiles AS (
            SELECT
                CleanedFilename,
                MAX(LastModified) AS LastModified
            FROM
                CleanedFiles
            GROUP BY
                CleanedFilename
        )
        SELECT
            r.FilePath
        FROM
            "CData.SFTP.Root" r
        JOIN
            LatestFiles lf
        ON
            REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(
                r.Filename, '1', ''), '2', ''), '3', ''), '4', ''), '5', ''), '6', ''), '7', ''), '8', ''), '9', ''), '0', '') = lf.CleanedFilename
        AND r.LastModified = lf.LastModified
        WHERE
            UPPER(r.Filename) LIKE 'FTA_CTMS%JSON'
            OR UPPER(r.Filename) LIKE 'FTA_STUDY%JSON'
            OR UPPER(r.Filename) LIKE 'ICN_CTMS%JSON'
            OR UPPER(r.Filename) LIKE 'ICN_STUDY%JSON'
            OR UPPER(r.Filename) LIKE 'PPD_CTMS%JSON'
            OR UPPER(r.Filename) LIKE 'PPD_STUDY%JSON'
            OR UPPER(r.Filename) LIKE 'PXL_CTMS%JSON'
            OR UPPER(r.Filename) LIKE 'PXL_STUDY%JSON'
            OR UPPER(r.Filename) LIKE 'PXL_STUDY_SITE%JSON'
            OR UPPER(r.Filename) LIKE 'PXL_STUDY_SITE_ADDRESS%JSON'
            OR UPPER(r.Filename) LIKE 'PXL_STUDY_SITE_PERSON%JSON'
            OR UPPER(r.Filename) LIKE 'PXL_STUDY_SITE_WORKFORCE%JSON';
        """

        # Execute the query
        cursor.execute(query)
        file_paths = [row[0] for row in cursor.fetchall()]

        # Close the connection
        conn.close()

        return file_paths
    except Exception as e:
        print(f"Error running query: {e}")
        return []

def download_json_files(file_paths):
    """
    Downloads JSON files from the given file paths and saves them to the output folder.
    """
    for file_path in file_paths:
        try:
            # Simulate downloading the file (replace this with actual logic if needed)
            response = requests.get(file_path)
            if response.status_code == 200:
                # Extract the file name from the file path
                file_name = os.path.basename(file_path)

                # Save the file to the output folder
                output_file_path = os.path.join(output_folder, file_name)
                with open(output_file_path, "wb") as output_file:
                    output_file.write(response.content)

                print(f"Downloaded and saved: {file_name}")
            else:
                print(f"Failed to download {file_path}: HTTP {response.status_code}")
        except Exception as e:
            print(f"Error downloading {file_path}: {e}")

if __name__ == "__main__":
    # Run the query and get the file paths
    file_paths = run_query_and_get_file_paths()

    if file_paths:
        print(f"Found {len(file_paths)} files to download.")
        # Download the JSON files
        download_json_files(file_paths)
    else:
        print("No files found to download.")