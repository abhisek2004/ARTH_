import os
import sqlite3
from datetime import datetime, timezone
from bson import ObjectId
from pymongo import MongoClient
import streamlit as st


def get_secret(name, default=None):
    try:
        return st.secrets.get(name, default)
    except Exception:
        return os.environ.get(name, default)


class SQLiteCursor:
    def __init__(self, docs):
        self._docs = [dict(d) for d in docs]

    def sort(self, key, direction):
        reverse = True if direction == -1 else False
        self._docs.sort(key=lambda d: d.get(key) or datetime.min.replace(
            tzinfo=timezone.utc), reverse=reverse)
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
            d["created_at"] = datetime.fromisoformat(r["created_at"]).replace(
                tzinfo=None) if r["created_at"] else None
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
            doc["created_at"] = datetime.now(timezone.utc).replace(tzinfo=None)
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


@st.cache_resource
def get_collection():
    uri = get_secret("MONGO_URI", "")
    if uri:
        try:
            client = MongoClient(
                uri, serverSelectionTimeoutMS=4000, connectTimeoutMS=4000, socketTimeoutMS=4000)
            client.admin.command("ping")
            db_name = get_secret("MONGO_DB", None)
            db = client.get_database(db_name) if db_name else (
                client.get_default_database() or client["contentplatform"])
            coll_name = get_secret("MONGO_COLLECTION", "contents")
            return db[coll_name], "mongo"
        except Exception:
            pass
    path = os.path.join(os.path.dirname(__file__), "content.db")
    return SQLiteCollection(path), "sqlite"


def serialize(doc):
    d = dict(doc)
    if isinstance(d.get("_id"), ObjectId):
        d["_id"] = str(d["_id"])
    return d


st.set_page_config(page_title="Canvas (Streamlit)",
                   page_icon="🖼️", layout="centered")
st.title("Canvas")
st.caption("Publish and discover content")

coll, backend = get_collection()
total = coll.count_documents({})
st.info(f"Backend: {backend} • Posts: {total}")

with st.form("publish"):
    title = st.text_input("Title *")
    category = st.selectbox(
        "Category *",
        ["", "image", "video", "story", "letter", "article", "news"],
        format_func=lambda x: "Select…" if x == "" else x,
    )
    description = st.text_input("Short Description")
    content_text = st.text_area("Content / Body Text", height=180)
    image_url = st.text_input("Image URL (optional)")
    submitted = st.form_submit_button("Publish")
    if submitted:
        if not title or not category:
            st.error("Title and category are required.")
        else:
            doc = {
                "title": title.strip(),
                "category": category.strip(),
                "description": description.strip() if description else None,
                "content_text": content_text.strip() if content_text else None,
                "file_url": None,
                "thumbnail_url": image_url.strip() if image_url else None,
                "created_at": datetime.now(timezone.utc).replace(tzinfo=None),
            }
            res = coll.insert_one(doc)
            st.success(f"Published! ID: {str(res.inserted_id)}")
            st.experimental_rerun()

filter_choice = st.selectbox(
    "Filter", ["all", "media", "writing", "news"], index=0)
if filter_choice == "media":
    query = {"category": {"$in": ["image", "video"]}}
elif filter_choice == "writing":
    query = {"category": {"$in": ["story", "letter", "article"]}}
elif filter_choice == "news":
    query = {"category": "news"}
else:
    query = {}

posts = [serialize(p) for p in coll.find(
    query).sort("created_at", -1).limit(20)]
for p in posts:
    with st.container(border=True):
        if p.get("thumbnail_url"):
            st.image(p["thumbnail_url"], use_container_width=True)
        st.markdown(f"**{p.get('title', '(untitled)')}**")
        created = p.get("created_at")
        if created:
            try:
                created_str = created.strftime("%b %d, %Y")
            except Exception:
                created_str = ""
        else:
            created_str = ""
        st.caption(f"{p.get('category', '')} • {created_str}")
        if p.get("description"):
            st.write(p["description"])
        if p.get("content_text"):
            with st.expander("Read more"):
                st.write(p["content_text"])
