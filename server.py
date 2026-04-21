from flask import Flask, request, jsonify
import os, datetime

app = Flask(__name__)
SAVE_DIR = "server_snaps"
os.makedirs(SAVE_DIR, exist_ok=True)

@app.route('/alert', methods=['POST'])
def alert():
    img = request.files.get("image")
    if img:
        filename = datetime.datetime.now().strftime("%Y%m%d_%H%M%S.jpg")
        path = os.path.join(SAVE_DIR, filename)
        img.save(path)
        print(f"[SERVER] Snapshot saved: {path}")
        return jsonify({"status": "ok", "file": filename})
    return jsonify({"status": "failed"})

if __name__ == '__main__':
    app.run(port=5000)
