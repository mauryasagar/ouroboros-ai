from flask import Flask, request, jsonify, render_template
import os
import json
import time
import logging
from dotenv import load_dotenv
from agent import SidekickAgent

load_dotenv()
logging.basicConfig(level=logging.INFO)

app = Flask(__name__)

# Create a single agent instance
agent = SidekickAgent()

@app.route("/")
def landing():
    return render_template("landing.html")

@app.route("/app")
def chat_app():
    return render_template("index.html")

@app.route("/ask", methods=["POST"])
def ask():
    data = request.get_json(force=True) or {}
    question = data.get("question", "").strip()
    if not question:
        return jsonify({"error": "No question provided"}), 400

    start = time.time()
    try:
        answer, tools_used = agent.ask(question)
        latency_ms = int((time.time() - start) * 1000)
        return jsonify({
            "answer": answer,
            "tools_used": tools_used,
            "tools": tools_used,
            "latency_ms": latency_ms,
            "elapsed_ms": latency_ms,
        })
    except Exception as e:
        logging.error(f"Error: {e}", exc_info=True)
        return jsonify({
            "answer": f"Error querying SigNoz: {str(e)}",
            "tools_used": [],
            "tools": [],
            "latency_ms": 0,
            "elapsed_ms": 0,
        }), 500

if __name__ == "__main__":
    print("🚀 Ouroboros Sidekick on http://localhost:3001")
    app.run(host="0.0.0.0", port=3001, debug=True)
