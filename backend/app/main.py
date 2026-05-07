"""
Flask 应用入口
"""
from flask import Flask, jsonify
from flask_sock import Sock
from flask_cors import CORS

from app.config import config
from app.database import init_db
from app.ws_handler import handle_websocket

app = Flask(__name__)
app.config.from_object(config)
CORS(app)
sock = Sock(app)


@app.route("/")
def index():
    return jsonify({
        "name": "vx版Agent集合体",
        "version": "0.5.0",
        "status": "running"
    })


@app.route("/health")
def health():
    return jsonify({"status": "healthy"})


@sock.route("/ws")
def websocket(ws):
    """WebSocket 处理 — 消息路由"""
    handle_websocket(ws)


if __name__ == "__main__":
    print("Starting vx版Agent集合体 Backend...")
    init_db()
    app.run(host="localhost", port=7890, debug=True)
