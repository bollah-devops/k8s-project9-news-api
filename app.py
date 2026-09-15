from flask import Flask, jsonify, request
from prometheus_flask_exporter import PrometheusMetrics
import psycopg2
import redis
import os
import json
import datetime
import time

app = Flask(__name__)
metrics = PrometheusMetrics(app)

# Team name comes from environment variable
TEAM = os.environ.get("TEAM_NAME", "unknown")

def get_db():
    return psycopg2.connect(
        host=os.environ.get("DB_HOST", "postgres-service"),
        database=os.environ.get("DB_NAME", "tasksdb"),
        user=os.environ.get("DB_USER", "admin"),
        password=os.environ.get("DB_PASSWORD", "password123")
    )

def get_cache():
    return redis.Redis(
        host=os.environ.get("REDIS_HOST", "redis-service"),
        port=6379,
        decode_responses=True
    )

def init_db():
    for i in range(10):
        try:
            conn = get_db()
            cur = conn.cursor()
            cur.execute("""
                CREATE TABLE IF NOT EXISTS tasks (
                    id SERIAL PRIMARY KEY,
                    title VARCHAR(200) NOT NULL,
                    status VARCHAR(50) DEFAULT 'pending',
                    assignee VARCHAR(100),
                    created_at TIMESTAMP DEFAULT NOW()
                )
            """)
            cur.execute("SELECT COUNT(*) FROM tasks")
            count = cur.fetchone()[0]
            if count == 0:
                cur.execute("""
                    INSERT INTO tasks (title, status, assignee) VALUES
                    (%s, 'pending', %s),
                    (%s, 'in-progress', %s)
                """, (
                    f"Setup {TEAM} environment",
                    f"{TEAM}-lead",
                    f"Review {TEAM} documentation",
                    f"{TEAM}-member"
                ))
            conn.commit()
            cur.close()
            conn.close()
            return
        except Exception as e:
            print(f"DB not ready ({i+1}/10): {e}")
            time.sleep(3)

@app.route("/tasks")
def get_tasks():
    cache = get_cache()
    cached = cache.get(f"{TEAM}_tasks")
    if cached:
        return jsonify({"team": TEAM, "source": "cache", "tasks": json.loads(cached)})
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT id, title, status, assignee, created_at FROM tasks ORDER BY id")
    rows = cur.fetchall()
    cur.close()
    conn.close()
    tasks = [{"id": r[0], "title": r[1], "status": r[2],
              "assignee": r[3], "created_at": str(r[4])} for r in rows]
    cache.setex(f"{TEAM}_tasks", 60, json.dumps(tasks))
    return jsonify({"team": TEAM, "source": "database", "tasks": tasks})

@app.route("/tasks/create", methods=["POST"])
def create_task():
    data = request.get_json()
    if not data or "title" not in data:
        return jsonify({"error": "title required"}), 400
    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO tasks (title, status, assignee) VALUES (%s, %s, %s) RETURNING id",
        (data["title"], data.get("status", "pending"), data.get("assignee", "unassigned"))
    )
    task_id = cur.fetchone()[0]
    conn.commit()
    cur.close()
    conn.close()
    get_cache().delete(f"{TEAM}_tasks")
    return jsonify({"message": "Task created", "id": task_id, "team": TEAM}), 201

@app.route("/tasks/<int:task_id>/complete", methods=["PUT"])
def complete_task(task_id):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("UPDATE tasks SET status='completed' WHERE id=%s RETURNING id", (task_id,))
    row = cur.fetchone()
    conn.commit()
    cur.close()
    conn.close()
    if not row:
        return jsonify({"error": "Task not found"}), 404
    get_cache().delete(f"{TEAM}_tasks")
    return jsonify({"message": "Task completed", "id": task_id, "team": TEAM})

@app.route("/health")
def health():
    try:
        conn = get_db()
        conn.close()
        return jsonify({"status": "healthy", "team": TEAM}), 200
    except Exception as e:
        return jsonify({"status": "unhealthy", "error": str(e)}), 500

@app.route("/ready")
def ready():
    try:
        conn = get_db()
        conn.close()
        cache = get_cache()
        cache.ping()
        return jsonify({"status": "ready", "team": TEAM}), 200
    except Exception as e:
        return jsonify({"status": "not ready", "error": str(e)}), 500

if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=5000)
