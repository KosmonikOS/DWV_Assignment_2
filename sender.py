# sender.py
import csv
import requests
import time
import os

# Configuration
CSV_FILE = 'ip_addresses.csv'
# Use environment variable for backend URL, defaulting for local testing
BACKEND_URL = os.getenv('BACKEND_URL', 'http://127.0.0.1:5000') + '/data'
INITIAL_DELAY_SECONDS = 2  # Wait a bit for the server to start

def send_data():
    """Reads the CSV file and sends data row by row to the backend,
    respecting the time intervals from the timestamps."""
    print(f"Sender started. Waiting {INITIAL_DELAY_SECONDS}s for backend...")
    time.sleep(INITIAL_DELAY_SECONDS)
    print(f"Sending data to: {BACKEND_URL}")

    last_timestamp = None

    try:
        with open(CSV_FILE, mode='r', newline='') as file:
            reader = csv.DictReader(file)
            # Clean up field names (remove leading/trailing spaces)
            reader.fieldnames = [name.strip() for name in reader.fieldnames]

            for i, row in enumerate(reader):
                try:
                    # Ensure keys match the cleaned fieldnames
                    current_timestamp = int(row['Timestamp'])
                    latitude = float(row['Latitude'])
                    longitude = float(row['Longitude'])
                    ip_address = row['ip address'].strip()
                    suspicious = float(row['suspicious'])

                    # Calculate delay based on timestamp difference
                    if last_timestamp is not None:
                        delay = current_timestamp - last_timestamp
                        # Ensure non-negative delay, max out unreasonable delays
                        delay = max(0, min(delay, 5)) # Cap delay at 5 seconds
                        if delay > 0:
                            # print(f"Sleeping for {delay} seconds...")
                            time.sleep(delay)

                    packet_data = {
                        'ip_address': ip_address,
                        'latitude': latitude,
                        'longitude': longitude,
                        'timestamp': current_timestamp,
                        'suspicious': suspicious
                    }

                    # Send data to Flask backend
                    response = requests.post(BACKEND_URL, json=packet_data)
                    response.raise_for_status() # Raise an exception for bad status codes
                    # Optional: Print progress
                    if (i + 1) % 100 == 0:
                         print(f"Sent {i + 1} packets...")

                    last_timestamp = current_timestamp

                except KeyError as e:
                    print(f"Error processing row {i+1}: Missing key {e}. Row: {row}")
                    continue # Skip rows with missing keys
                except ValueError as e:
                    print(f"Error processing row {i+1}: Invalid data type {e}. Row: {row}")
                    continue # Skip rows with invalid data types
                except requests.exceptions.RequestException as e:
                    print(f"Error sending data for row {i+1}: {e}")
                    # Decide whether to retry, wait, or stop
                    print("Attempting to resend in 5 seconds...")
                    time.sleep(5)
                    try:
                         response = requests.post(BACKEND_URL, json=packet_data)
                         response.raise_for_status()
                         print("Resend successful.")
                    except requests.exceptions.RequestException as re:
                         print(f"Resend failed: {re}. Stopping sender.")
                         break # Stop if resend fails
                except Exception as e:
                    print(f"An unexpected error occurred processing row {i+1}: {e}")
                    continue # Log and continue with the next row

            print("Finished sending all data.")

    except FileNotFoundError:
        print(f"Error: CSV file '{CSV_FILE}' not found.")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

if __name__ == '__main__':
    send_data() 