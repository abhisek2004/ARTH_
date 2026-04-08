# ARTH — Content Hosting Platform

A minimal, modern content hosting platform built with Flask + MongoDB.

## Features

- Publish: Images, Videos, Stories, Letters, Articles, News
- Separate pages for Media, Writing, and News
- File upload support (image & video)
- Clean, responsive design

## Setup

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Start MongoDB

Make sure MongoDB is running locally:

```bash
mongod
```

Or set a custom URI via environment variable:

```bash
export MONGO_URI="mongodb://localhost:27017/"
```

### 3. Run the app

```bash
python app.py
```

Open [http://localhost:5000](http://localhost:5000)

## Project Structure

```
contentplatform/
├── app.py                  # Flask backend
├── requirements.txt
├── templates/
│   ├── base.html           # Shared layout + design system
│   ├── index.html          # Homepage (all content)
│   ├── media.html          # Images & Videos page
│   ├── writing.html        # Stories, Letters, Articles page
│   ├── news.html           # News page
│   ├── upload.html         # Publish / upload form
│   └── post.html           # Single post view
└── static/
    └── uploads/            # Uploaded files stored here
```

## MongoDB Schema

Collection: `contents`

```json
{
  "title": "string",
  "category": "image|video|story|letter|article|news",
  "description": "string",
  "content_text": "string",
  "file_url": "string or null",
  "created_at": "datetime"
}
```

## Customization

- Change `MONGO_URI` env var to use a remote database (e.g. MongoDB Atlas)
- Increase `MAX_CONTENT_LENGTH` in `app.py` for larger uploads
