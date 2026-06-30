import os
import time
import urllib.request
import urllib.error
import json
import logging

# Configure logging format to include timestamps and severity levels
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

def get_env_vars():
    """Reads and validates properties from environment variables."""
    # Read environment variables with default fallbacks
    host = os.environ.get("SERVER_HOST", "0.0.0.0")
    port_str = os.environ.get("SERVER_PORT", "8000")
    calls_str = os.environ.get("CALLS", "5")
    freq_str = os.environ.get("CALL_FREQUENCY_SECONDS", "2")
    
    # Safely cast string inputs to integers
    try:
        port = int(port_str)
        calls = int(calls_str)
        freq = int(freq_str)
    except ValueError as e:
        logging.error("Error parsing environment variables to integer: %s", e)
        logging.warning("Falling back to default integer values.")
        port, calls, freq = 8000, 5, 2

    return host, port, calls, freq

def main():
    host, port, calls, freq = get_env_vars()
    url = f"http://{host}:{port}/"
    
    logging.info("Configuration Loaded:")
    logging.info("  Target URL: %s", url)
    logging.info("  Total Calls: %d", calls)
    logging.info("  Frequency: Every %d second(s)", freq)

    for attempt in range(1, calls + 1):
        try:
            # Send HTTP GET request using Python's built-in urllib
            with urllib.request.urlopen(url, timeout=5) as response:
                # Read bytes and decode to string
                raw_data = response.read().decode('utf-8')
                # Parse string into a Python dictionary/JSON object
                json_data = json.loads(raw_data)
                
                logging.info("Attempt [%d/%d]: Fetching %s...: Success Response: %s", attempt, calls, url, json_data)
                
        except urllib.error.URLError as e:
            logging.error("Network Connection Error: %s", e.reason)
        except json.JSONDecodeError:
            logging.error("Failed to decode response as JSON.")
        except Exception as e:
            logging.critical("An unexpected error occurred: %s", e, exc_info=True)

        # Sleep on all iterations except the very last one
        if attempt < calls:
            logging.info("Sleeping for %d seconds...", freq)
            time.sleep(freq)

if __name__ == "__main__":
    main()
