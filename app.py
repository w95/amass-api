import subprocess
import os
from flask import Flask, request, jsonify

app = Flask(__name__)

@app.route('/api/amass/enum', methods=['POST'])
def amass_enum():
    try:
        data = request.json
        domain = data.get("domain")
        brute = data.get("brute", False)
        min_for_recursive = data.get("min_for_recursive", 2)

        if not domain:
            return jsonify({"status": "error", "message": "Domain is required"}), 400

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
            "output": output_list
        }), 200

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == '__main__':
    # Ensure the /results directory exists
    os.makedirs("/results", exist_ok=True)
    app.run(host='0.0.0.0', port=5000)

