from flask import Flask, render_template, request, redirect, url_for, jsonify, flash
from pymongo import MongoClient
from bson import ObjectId
from datetime import datetime
import os
import uuid
from werkzeug.utils import secure_filename
from dotenv import load_dotenv
from pathlib import Path
import copy
import sqlite3

_BASE_DIR = Path(__file__).resolve().parent
load_dotenv(_BASE_DIR / ".env")
if not os.environ.get("MONGO_URI"):
    load_dotenv(_BASE_DIR / ".env.example")

app = Flask(__name__)
app.secret_key = "contentplatform_secret_key_2024"


class InMemoryCursor:
    def __init__(self, docs):
        self._docs = [dict(d) for d in docs]

    def sort(self, key, direction):
        reverse = True if direction == -1 else False
        self._docs.sort(key=lambda d: d.get(
            key) or datetime.min, reverse=reverse)
        return self

    def limit(self, n):
        self._docs = self._docs[:n]
        return self

    def __iter__(self):
        return iter(self._docs)


class InMemoryCollection:
    def __init__(self):
        self._docs = []

    def _match(self, doc, query):
        if not query:
            return True
        for k, v in query.items():
            if k == "category":
                if isinstance(v, dict) and "$in" in v:
                    if doc.get("category") not in v["$in"]:
                        return False
                else:
                    if doc.get("category") != v:
                        return False
            elif k == "_id":
                if doc.get("_id") != v:
                    return False
            else:
                if doc.get(k) != v:
                    return False
        return True

    def find(self, query=None):
        matched = [d for d in self._docs if self._match(d, query or {})]
        return InMemoryCursor(matched)

    def find_one(self, query):
        for d in self._docs:
            if self._match(d, query or {}):
                return dict(d)
        return None

    def insert_one(self, doc):
        if not doc.get("_id"):
            doc["_id"] = ObjectId()
        if not doc.get("created_at"):
            doc["created_at"] = datetime.utcnow()
        self._docs.append(doc)

        class R:
            def __init__(self, _id):
                self.inserted_id = _id
        return R(doc["_id"])

    def count_documents(self, query=None):
        return len([1 for _ in self.find(query or {})])


class SQLiteCursor:
    def __init__(self, docs):
        self._docs = [dict(d) for d in docs]

    def sort(self, key, direction):
        reverse = True if direction == -1 else False
        self._docs.sort(key=lambda d: d.get(
            key) or datetime.min, reverse=reverse)
        return self

    def limit(self, n):
        self._docs = self._docs[:n]
        return self

    def __iter__(self):
        return iter(self._docs)


class SQLiteCollection:
    def __init__(self, path):
        self._path = str(path)
        self._ensure()

    def _conn(self):
        return sqlite3.connect(self._path)

    def _ensure(self):
        conn = self._conn()
        cur = conn.cursor()
        cur.execute(
            "CREATE TABLE IF NOT EXISTS posts ("
            "id TEXT PRIMARY KEY, "
            "title TEXT, "
            "category TEXT, "
            "description TEXT, "
            "content_text TEXT, "
            "file_url TEXT, "
            "thumbnail_url TEXT, "
            "created_at TEXT)"
        )
        conn.commit()
        conn.close()

    def _row_to_doc(self, row):
        keys = ["id", "title", "category", "description",
                "content_text", "file_url", "thumbnail_url", "created_at"]
        r = dict(zip(keys, row))
        d = {
            "_id": ObjectId(r["id"]) if r["id"] else ObjectId(),
            "title": r["title"],
            "category": r["category"],
            "description": r["description"],
            "content_text": r["content_text"],
            "file_url": r["file_url"],
            "thumbnail_url": r["thumbnail_url"],
        }
        try:
            d["created_at"] = datetime.fromisoformat(
                r["created_at"]) if r["created_at"] else None
        except Exception:
            d["created_at"] = None
        return d

    def _build_where(self, query):
        if not query:
            return "", []
        where = []
        params = []
        for k, v in query.items():
            if k == "category":
                if isinstance(v, dict) and "$in" in v:
                    placeholders = ",".join(["?"] * len(v["$in"]))
                    where.append(f"category IN ({placeholders})")
                    params.extend(list(v["$in"]))
                else:
                    where.append("category = ?")
                    params.append(v)
            elif k == "_id":
                where.append("id = ?")
                params.append(str(v))
            else:
                where.append(f"{k} = ?")
                params.append(v)
        clause = " WHERE " + " AND ".join(where) if where else ""
        return clause, params

    def find(self, query=None):
        clause, params = self._build_where(query or {})
        conn = self._conn()
        cur = conn.cursor()
        cur.execute(
            "SELECT id,title,category,description,content_text,file_url,thumbnail_url,created_at FROM posts" + clause,
            params,
        )
        rows = cur.fetchall()
        conn.close()
        docs = [self._row_to_doc(r) for r in rows]
        return SQLiteCursor(docs)

    def find_one(self, query):
        clause, params = self._build_where(query or {})
        conn = self._conn()
        cur = conn.cursor()
        cur.execute(
            "SELECT id,title,category,description,content_text,file_url,thumbnail_url,created_at FROM posts" + clause + " LIMIT 1",
            params,
        )
        row = cur.fetchone()
        conn.close()
        return self._row_to_doc(row) if row else None

    def insert_one(self, doc):
        if not doc.get("_id"):
            doc["_id"] = ObjectId()
        if not doc.get("created_at"):
            doc["created_at"] = datetime.utcnow()
        conn = self._conn()
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO posts (id,title,category,description,content_text,file_url,thumbnail_url,created_at) "
            "VALUES (?,?,?,?,?,?,?,?)",
            (
                str(doc["_id"]),
                doc.get("title"),
                doc.get("category"),
                doc.get("description"),
                doc.get("content_text"),
                doc.get("file_url"),
                doc.get("thumbnail_url"),
                doc["created_at"].isoformat(),
            ),
        )
        conn.commit()
        conn.close()

        class R:
            def __init__(self, _id):
                self.inserted_id = _id
        return R(doc["_id"])

    def count_documents(self, query=None):
        clause, params = self._build_where(query or {})
        conn = self._conn()
        cur = conn.cursor()
        cur.execute("SELECT COUNT(1) FROM posts" + clause, params)
        n = cur.fetchone()[0]
        conn.close()
        return n


MONGO_URI = os.environ.get("MONGO_URI", "")
MONGO_COLLECTION = os.environ.get("MONGO_COLLECTION", "contents")
use_memory = False
db = None
contents = None
if MONGO_URI:
    try:
        client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000,
                             connectTimeoutMS=5000, socketTimeoutMS=5000)
        client.admin.command("ping")
        MONGO_DB = os.environ.get("MONGO_DB")
        db = client.get_database(MONGO_DB) if MONGO_DB else (
            client.get_default_database() or client["contentplatform"])
        contents = db[MONGO_COLLECTION]
    except Exception:
        use_memory = True
else:
    use_memory = True
if use_memory:
    DB_PATH = os.path.join(os.path.dirname(__file__), "content.db")
    try:
        db = type("DB", (), {"name": "sqlite"})()
        contents = SQLiteCollection(DB_PATH)
    except Exception:
        db = type("DB", (), {"name": "memory"})()
        contents = InMemoryCollection()

# File upload config
UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), "static", "uploads")
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif",
                      "webp", "mp4", "mov", "avi", "mkv", "webm"}
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["MAX_CONTENT_LENGTH"] = 100 * 1024 * 1024  # 100MB

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

CATEGORIES = {
    "media": ["image", "video"],
    "writing": ["story", "letter", "article"],
    "news": ["news"],
}


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def serialize(doc):
    doc["_id"] = str(doc["_id"])
    if isinstance(doc.get("created_at"), datetime):
        doc["created_at_iso"] = doc["created_at"].isoformat() + "Z"
    return doc


@app.route("/health")
def health():
    return jsonify(
        {
            "ok": True,
            "db": getattr(db, "name", None),
            "collection": MONGO_COLLECTION,
            "count": contents.count_documents({}),
        }
    )


@app.route("/")
def index():
    all_posts = list(contents.find().sort("created_at", -1).limit(12))
    all_posts = [serialize(p) for p in all_posts]
    return render_template("index.html", posts=all_posts, page="home")


@app.route("/media")
def media():
    posts = list(contents.find(
        {"category": {"$in": ["image", "video"]}}).sort("created_at", -1))
    posts = [serialize(p) for p in posts]
    return render_template("media.html", posts=posts, page="media")


@app.route("/writing")
def writing():
    posts = list(contents.find(
        {"category": {"$in": ["story", "letter", "article"]}}).sort("created_at", -1))
    posts = [serialize(p) for p in posts]
    return render_template("writing.html", posts=posts, page="writing")


@app.route("/news")
def news():
    posts = list(contents.find({"category": "news"}).sort("created_at", -1))
    posts = [serialize(p) for p in posts]
    return render_template("news.html", posts=posts, page="news")


@app.route("/post/<post_id>")
def view_post(post_id):
    try:
        oid = ObjectId(post_id)
    except Exception:
        return "Post not found", 404

    post = contents.find_one({"_id": oid})
    if not post:
        return "Post not found", 404
    post = serialize(post)
    return render_template("post.html", post=post, page="view")


@app.route("/upload", methods=["GET", "POST"])
def upload():
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        category = request.form.get("category", "").strip()
        description = request.form.get("description", "").strip()
        content_text = request.form.get("content_text", "").strip()
        image_url = request.form.get("image_url", "").strip()

        if not title or not category:
            flash("Title and category are required.", "error")
            return redirect(url_for("upload"))

        file_url = None
        thumbnail_url = image_url or None
        if "file" in request.files:
            file = request.files["file"]
            if file and file.filename and allowed_file(file.filename):
                ext = file.filename.rsplit(".", 1)[1].lower()
                filename = f"{uuid.uuid4().hex}.{ext}"
                filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)
                file.save(filepath)
                file_url = f"/static/uploads/{filename}"
                if ext in {"png", "jpg", "jpeg", "gif", "webp"}:
                    thumbnail_url = thumbnail_url or file_url

        doc = {
            "title": title,
            "category": category,
            "description": description,
            "content_text": content_text,
            "file_url": file_url,
            "thumbnail_url": thumbnail_url,
            "created_at": datetime.utcnow(),
        }
        result = contents.insert_one(doc)
        flash("Content published successfully!", "success")
        return redirect(url_for("view_post", post_id=str(result.inserted_id)))

    return render_template("upload.html", page="upload")


@app.route("/api/posts")
def api_posts():
    category = request.args.get("category")
    query = {"category": category} if category else {}
    posts = list(contents.find(query).sort("created_at", -1).limit(20))
    return jsonify([serialize(p) for p in posts])


if __name__ == "__main__":
    app.run(debug=True, port=5000)
