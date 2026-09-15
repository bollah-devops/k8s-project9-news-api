from flask import Flask, jsonify, request
import os
import datetime

app = Flask(__name__)

APP_VERSION = os.environ.get("APP_VERSION", "1.0.0")
ENVIRONMENT = os.environ.get("ENVIRONMENT", "development")

posts = []
post_counter = 0

@app.route("/")
def home():
    return jsonify({
        "service": "news-api",
        "version": APP_VERSION,
        "environment": ENVIRONMENT,
        "pod": os.environ.get("HOSTNAME", "unknown"),
        "timestamp": datetime.datetime.utcnow().isoformat()
    })

@app.route("/news")
def get_news():
    return jsonify({
        "version": APP_VERSION,
        "count": len(posts),
        "news": posts,
        "served_by": os.environ.get("HOSTNAME", "unknown")
    })

@app.route("/news/publish", methods=["POST"])
def publish_news():
    global post_counter
    data = request.get_json()
    if not data or "title" not in data:
        return jsonify({"error": "title required"}), 400
    post_counter += 1
    post = {
        "id": post_counter,
        "title": data["title"],
        "content": data.get("content", ""),
        "version": APP_VERSION,
        "published_at": datetime.datetime.utcnow().isoformat()
    }
    posts.append(post)
    return jsonify({"message": "Published", "post": post}), 201

@app.route("/health")
def health():
    return jsonify({
        "status": "healthy",
        "version": APP_VERSION,
        "environment": ENVIRONMENT
    }), 200

@app.route("/ready")
def ready():
    return jsonify({"status": "ready"}), 200

@app.route("/version")
def version():
    return jsonify({
        "version": APP_VERSION,
        "environment": ENVIRONMENT,
        "deployed_at": os.environ.get("DEPLOY_TIME", "unknown")
    })

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
