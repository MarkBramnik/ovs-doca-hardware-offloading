from http.server import HTTPServer, BaseHTTPRequestHandler
from datetime import datetime
import json
import os

class TestServer(BaseHTTPRequestHandler):
    def do_GET(self):
        # Prepare the JSON data
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        response_data = {
            "status": "Ok",
            "time": current_time
        }
        
        # Convert dictionary to JSON string and encode to bytes
        json_bytes = json.dumps(response_data).encode('utf-8')
        
        # Send headers
        self.send_response(200)
        self.send_header("Content-type", "application/json")
        self.send_header("Content-Length", str(len(json_bytes)))
        self.end_headers()
        
        # Write JSON response
        self.wfile.write(json_bytes)

def run(server_class=HTTPServer, handler_class=TestServer):
    # Read PORT from environment variable, falling back to 8000 if not set
    port_env = os.environ.get("PORT", "8000")
    
    try:
        port = int(port_env)
    except ValueError:
        print(f"Invalid PORT environment variable '{port_env}'. Defaulting to 8000.")
        port = 8000

    server_address = ('0.0.0.0', port)
    httpd = server_class(server_address, handler_class)
    print(f"Starting JSON server on http://0.0.0.0:{port}...")
    httpd.serve_forever()

if __name__ == "__main__":
    run()