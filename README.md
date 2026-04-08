# ARTH_
Artificial Research &amp; Technology Hub


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


### Diagram
![website_content_flowchart](https://github.com/user-attachments/assets/58689a6b-d8d8-4787-9af1-615efd5e6ff9)

![flask_app_architecture_layers](https://github.com/user-attachments/assets/a2a600a7-5c17-4098-be3f-790500852cad)

![arth_use_case_diagram](https://github.com/user-attachments/assets/794f6bb9-da95-4ab1-8e72-3ef0fa9212a6)

![dfd_level0_arth_context_diagram](https://github.com/user-attachments/assets/4a17effa-4377-4662-af4a-9697f1c0c5d5)

![dfd_level1_arth_content_platform](https://github.com/user-attachments/assets/017791a3-020d-4167-b470-810f9c088687)


### Screenshot

<img width="2580" height="1700" alt="127 0 0 1_5000_" src="https://github.com/user-attachments/assets/790f53d2-482c-46ed-a8f8-c699ffc44b31" />

<img width="2580" height="1700" alt="127 0 0 1_5000_ (1)" src="https://github.com/user-attachments/assets/453f470d-8e40-4322-9d7d-02688dcdce49" />

<img width="2580" height="1700" alt="127 0 0 1_5000_media" src="https://github.com/user-attachments/assets/b0172bf6-e932-43fc-ad19-3696f386ee89" />

<img width="2580" height="1700" alt="127 0 0 1_5000_post_69d5d294de6993010a2b18c7" src="https://github.com/user-attachments/assets/3e54d1b4-7333-4b1d-ba00-70743ac80f8c" />

<img width="2580" height="1700" alt="127 0 0 1_5000_news" src="https://github.com/user-attachments/assets/f4b58db0-3cf4-4fb2-974f-d336ef57b4c9" />

<img width="2580" height="1700" alt="127 0 0 1_5000_upload" src="https://github.com/user-attachments/assets/5b4f18d0-f6a2-4d9d-ad08-9a65588aaa46" />

<img width="2580" height="1700" alt="127 0 0 1_5000_ (2)" src="https://github.com/user-attachments/assets/0892884d-5e10-4ec7-b355-f0046e916232" />


