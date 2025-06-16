import subprocess
import os
from urllib.parse import urlparse
from flask import Flask, request, jsonify

app = Flask(__name__)

def extract_domain(domain_input):
    """
    Extract clean domain from various input formats:
    - example.com -> example.com  
    - https://example.com -> example.com
    - https://example.com/path -> example.com
    - http://subdomain.example.com/path?query=1 -> subdomain.example.com
    """
    if not domain_input:
        return None
    
    # Remove whitespace
    domain_input = domain_input.strip()
    
    # If it doesn't have a protocol, add one for parsing
    if not domain_input.startswith(('http://', 'https://')):
        domain_input = 'http://' + domain_input
    
    try:
        parsed = urlparse(domain_input)
        domain = parsed.netloc or parsed.path.split('/')[0]
        
        # Remove port if present
        if ':' in domain:
            domain = domain.split(':')[0]
            
        return domain if domain else None
    except Exception:
        return None

@app.route('/')
def index():
    return jsonify({"status": "success", "message": "Amass API is running"}), 200

@app.route('/amass', methods=['POST'])
def amass_enum():
    try:
        data = request.json
        domain_input = data.get("domain")
        brute = data.get("brute", False)
        min_for_recursive = data.get("min_for_recursive", 2)

        if not domain_input:
            return jsonify({"status": "error", "message": "Domain is required"}), 400

        # Extract clean domain from input
        domain = extract_domain(domain_input)
        if not domain:
            return jsonify({"status": "error", "message": "Invalid domain format"}), 400

        # Define output file path
        output_file = f"/results/amass_output_{domain}.txt"

        # Build the command
        command = [
            "amass", "enum",
            "-d", domain,
            "-min-for-recursive", str(min_for_recursive),
            "-o", output_file
        ]
        if brute:
            command.append("-brute")

        # Execute the command
        result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

        if result.returncode != 0:
            return jsonify({
                "status": "error",
                "message": f"Command '{' '.join(command)}' failed.",
                "stderr": result.stderr.strip()
            }), 500

        # Read the output file
        output_list = []
        if os.path.exists(output_file):
            with open(output_file, "r") as f:
                output_list = f.read().strip().split("\n")

        return jsonify({
            "status": "success",
            "message": "Amass enumeration completed.",
            "domain_used": domain,  # Include the cleaned domain in response
            "output": output_list
        }), 200

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == '__main__':
    # Ensure the /results directory exists
    os.makedirs("/results", exist_ok=True)
    app.run(host='0.0.0.0', port=8002)
