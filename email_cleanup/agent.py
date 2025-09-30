import win32com.client
import re
import json
import logging
import configparser
from datetime import datetime
from difflib import SequenceMatcher
import os
from tabulate import tabulate
import ast
import sys

# --- Configuration ---
CONFIG_FILE = os.path.expanduser("C:\\Users\\psharmak\\OneDrive\\psharmak_agents\\email_cleanup\\config.ini")
config = configparser.ConfigParser()
config.read(CONFIG_FILE)

# --- Logging ---
LOG_FILE = os.path.expanduser(config.get('Logging', 'log_file'))
logging.basicConfig(filename=LOG_FILE, level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')

# --- Constants ---
LEARNED_PATTERNS_FILE = os.path.expanduser(config.get('Files', 'learned_patterns_file'))
BODY_SIMILARITY_THRESHOLD = config.getfloat('Thresholds', 'body_similarity')
FIRST_300_CHARS_SIMILARITY_THRESHOLD = config.getfloat('Thresholds', 'first_300_chars_similarity')
BODY_FILTERS = [filter.strip() for filter in config.get('Filters', 'body_filters').split('\n') if filter.strip()]

def connect_to_outlook():
    """Connects to Outlook and returns the inbox folder."""
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

def normalize_body(body):
    """Normalizes the email body for better comparison."""
    print("Normalizing body...")
    if not body:
        return ""
    try:
        body = re.sub(r'\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}', '', body)  # Remove timestamps
        body = re.sub(r'\s+', ' ', body)  # Normalize whitespace
        body = re.sub(r'http\S+', '', body)  # Remove URLs
        body = re.sub(r'[^a-zA-Z0-9\s]', '', body)  # Remove special characters
        body = body.lower() # Convert to lowercase
        body = re.sub(r'\b\w{1,2}\b', '', body) # Remove words that are 1 or 2 characters long
        return body.strip()
    except Exception as e:
        logging.error(f"Error normalizing body: {e}")
        return ""

def are_bodies_similar(body1, body2, threshold=BODY_SIMILARITY_THRESHOLD):
    """Checks if two email bodies are similar based on a threshold."""
    print("Comparing bodies...")    
    if not body1 or not body2:
        return False, 0.0
    try:
        similarity_ratio = SequenceMatcher(None, body1, body2).ratio()
        return similarity_ratio > threshold, similarity_ratio
    except Exception as e:
        logging.error(f"Error comparing bodies: {e}")
        return False, 0.0

def load_learned_patterns():
    """Loads learned patterns from the JSON file."""
    print("Loading learned patterns...")
    try:
        if os.path.exists(LEARNED_PATTERNS_FILE):
            with open(LEARNED_PATTERNS_FILE, 'r') as file:
                patterns = json.load(file)
                return {
                    'duplicates': {ast.literal_eval(key): value for key, value in patterns.get('duplicates', {}).items()},
                    'non_duplicates': {ast.literal_eval(key): value for key, value in patterns.get('non_duplicates', {}).items()}
                }
        else:
            logging.warning(f"Learned patterns file not found: {LEARNED_PATTERNS_FILE}. Starting with empty patterns.")
            return {'duplicates': {}, 'non_duplicates': {}}
    except (json.JSONDecodeError, ValueError, SyntaxError) as e:
        logging.error(f"Error decoding JSON file: {e}. Starting with empty patterns.")
        return {'duplicates': {}, 'non_duplicates': {}}
    except Exception as e:
        logging.error(f"Unexpected error loading learned patterns: {e}")
        return {'duplicates': {}, 'non_duplicates': {}}

def save_learned_patterns(patterns):
    """Saves learned patterns to the JSON file."""
    print("Saving learned patterns...")
    try:
        with open(LEARNED_PATTERNS_FILE, 'w') as file:
            patterns_str_keys = {
                'duplicates': {str(key): value for key, value in patterns['duplicates'].items()},
                'non_duplicates': {str(key): value for key, value in patterns['non_duplicates'].items()}
            }
            json.dump(patterns_str_keys, file, indent=4)
        logging.info("Learned patterns saved successfully.")
    except Exception as e:
        logging.error(f"Error saving learned patterns: {e}")

def find_and_remove_duplicates(folder, learned_patterns):
    """Finds and removes duplicate emails in a given folder."""
    print(f"Finding and removing duplicates in folder: {folder.Name}")
    try:
        messages = folder.Items
        seen = {}
        duplicates = []
        compared_pairs = set()

        message = messages.GetFirst()
        while message:
            key = (message.Subject, message.SenderName, message.ReceivedTime.date())
            normalized_body = normalize_body(message.Body)
            
            if key in seen:
                if (key, seen[key]['key']) in compared_pairs or (seen[key]['key'], key) in compared_pairs:
                    message = messages.GetNext()
                    continue

                if (key, seen[key]['key']) in learned_patterns['non_duplicates'] or (seen[key]['key'], key) in learned_patterns['non_duplicates']:
                    message = messages.GetNext()
                    continue

                similarity_ratio = SequenceMatcher(None, seen[key]['body'], normalized_body).ratio()
                compared_pairs.add((key, seen[key]['key']))

                if similarity_ratio == 1.0:
                    duplicates.append(message)
                    learned_patterns['duplicates'][key] = normalized_body
                elif BODY_SIMILARITY_THRESHOLD <= similarity_ratio < 1.0:
                    first_300_chars_similar, _ = are_bodies_similar(seen[key]['body'][:300], normalized_body[:300], threshold=FIRST_300_CHARS_SIMILARITY_THRESHOLD)
                    if first_300_chars_similar:
                        table_data = [
                            ["", "Original Email", "Duplicate Email"],
                            ["Folder", seen[key]['folder'], folder.Name],
                            ["Subject", seen[key]['subject'], message.Subject],
                            ["Sender", seen[key]['sender'], message.SenderName],
                            ["Received Time", seen[key]['received_time'], message.ReceivedTime],
                            ["Similarity", f"{similarity_ratio:.2f}", f"{similarity_ratio:.2f}"],
                            ["First 300 characters", seen[key]['body'][:300], normalized_body[:300]]
                        ]
                        print(tabulate(table_data, headers="firstrow", tablefmt="grid"))
                        user_input = input("Delete duplicate email? (y/n): ")
                        if user_input.lower() == 'y':
                            duplicates.append(message)
                            learned_patterns['duplicates'][key] = normalized_body
                        else:
                            learned_patterns['non_duplicates'][(key, seen[key]['key'])] = True
                            seen[key] = {
                                'folder': folder.Name,
                                'subject': message.Subject,
                                'sender': message.SenderName,
                                'received_time': message.ReceivedTime,
                                'body': normalized_body,
                                'key': key
                            }
                    else:
                        learned_patterns['non_duplicates'][(key, seen[key]['key'])] = True
                        seen[key] = {
                            'folder': folder.Name,
                            'subject': message.Subject,
                            'sender': message.SenderName,
                            'received_time': message.ReceivedTime,
                            'body': normalized_body,
                            'key': key
                        }
                else:
                    learned_patterns['non_duplicates'][(key, seen[key]['key'])] = True
                    seen[key] = {
                        'folder': folder.Name,
                        'subject': message.Subject,
                        'sender': message.SenderName,
                        'received_time': message.ReceivedTime,
                        'body': normalized_body,
                        'key': key
                    }
            else:
                seen[key] = {
                    'folder': folder.Name,
                    'subject': message.Subject,
                    'sender': message.SenderName,
                    'received_time': message.ReceivedTime,
                    'body': normalized_body,
                    'key': key
                }
            
            message = messages.GetNext()

        for duplicate in duplicates:
            logging.info(f"Deleting duplicate found in folder '{folder.Name}': Subject='{duplicate.Subject}', Sender='{duplicate.SenderName}', ReceivedTime='{duplicate.ReceivedTime}'")
            print(f"Deleting duplicate found in folder '{folder.Name}': Subject='{duplicate.Subject}', Sender='{duplicate.SenderName}', ReceivedTime='{duplicate.ReceivedTime}'")
            duplicate.Delete()
    except Exception as e:
        logging.error(f"Error in find_and_remove_duplicates: {e}")

def retain_most_recent_emails(folder):
    """Retains only the most recent emails with specific body content."""
    print(f"Retaining most recent emails in folder: {folder.Name}")
    try:
        messages = folder.Items
        most_recent_messages = {}
        messages_to_delete = []
        
        message = messages.GetFirst()
        while message:
            message_body = message.Body
            # Check if the email body contains any of the filter strings
            body_matches_filter = False
            for body_filter in BODY_FILTERS:
                if body_filter.lower() in message_body.lower():
                    body_matches_filter = True
                    break  # Exit the loop if a match is found
            
            # Only process if the body matches a filter
            if body_matches_filter:
                for body_filter in BODY_FILTERS:
                    if body_filter.lower() in message_body.lower():
                        if body_filter not in most_recent_messages or message.ReceivedTime > most_recent_messages[body_filter].ReceivedTime:
                            if body_filter in most_recent_messages:
                                messages_to_delete.append(most_recent_messages[body_filter])
                            most_recent_messages[body_filter] = message
                        else:
                            messages_to_delete.append(message)
                        break  # Only one filter should match per email
            message = messages.GetNext()

        for message in messages_to_delete:
            for body_filter in BODY_FILTERS:
                if body_filter.lower() in message.Body.lower():
                    logging.info(f"Deleting older message with body containing '{body_filter}' received on '{message.ReceivedTime}'")
                    print(f"Deleting older message with body containing '{body_filter}' received on '{message.ReceivedTime}'")
                    message.Delete()
                    break

        # Process subfolders
        subfolders = folder.Folders
        for subfolder in subfolders:
            retain_most_recent_emails(subfolder)
    except Exception as e:
        logging.error(f"Error in retain_most_recent_emails: {e}")

def process_folder(folder, learned_patterns):
    """Processes a folder and its subfolders."""
    print(f"Processing folder: {folder.Name}")
    try:
        find_and_remove_duplicates(folder, learned_patterns)
        retain_most_recent_emails(folder)
        subfolders = folder.Folders
        for subfolder in subfolders:
            process_folder(subfolder, learned_patterns)
    except Exception as e:
        logging.error(f"Error processing folder '{folder.Name}': {e}")

def main():
    """Main function to run the email cleanup process."""
    print("Starting email cleanup process...")
    try:
        inbox = connect_to_outlook()
        if inbox is None:
            logging.error("Could not connect to Outlook, exiting.")
            sys.exit(1)
        
        learned_patterns = load_learned_patterns()
        process_folder(inbox, learned_patterns)
        save_learned_patterns(learned_patterns)
        print("Duplicates removed from all folders and retained most recent emails with specified body content.")
        logging.info("Email cleanup process completed successfully.")
    except Exception as e:
        logging.error(f"An unexpected error occurred: {e}")

if __name__ == "__main__":
    main()
