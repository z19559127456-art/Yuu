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
        "name": "Yu",
        "version": "0.1.13",
        "status": "running"
    })


@app.route("/health")
def health():
    return jsonify({"status": "healthy"})


@sock.route("/ws")
def websocket(ws):
    """WebSocket 处理 — 消息路由"""
    handle_websocket(ws)


import os

if __name__ == "__main__":
    print("Starting Yu Backend...")
    init_db()
    # 生产模式：彻底禁用 debug 和 reloader，防止僵尸进程
    app.run(host="localhost", port=7890, debug=False, use_reloader=False)
