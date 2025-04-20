import os
import json
import random
import requests
import subprocess
from flask import Flask, request, redirect, session
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from googleapiclient.http import MediaFileUpload
from google.auth.transport.requests import Request as GoogleRequest
import textwrap
import urllib3

urllib3.disable_warnings()

app = Flask(__name__)
app.secret_key = "your_secret_key"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CLIENT_SECRET_FILE = os.path.join(BASE_DIR, "client_secret.json")
TOKENS_FILE = os.path.join(BASE_DIR, "tokens.json")
OUTPUT_DIR = os.path.join(BASE_DIR, "output")
BACKGROUND = os.path.join(BASE_DIR, "background.jpg")
FONT_PATH = os.path.join(BASE_DIR, "font.ttf")
AUDIO_FOLDER = os.path.join(BASE_DIR, "trending_songs")

REDIRECT_URI = "https://ysrautomation.pythonanywhere.com/auth/callback"

SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube.readonly",
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/userinfo.profile",
    "openid"
]

TOPICS = [
    "life", "love", "happiness", "motivation", "inspiration", "success",
    "friendship", "wisdom", "business", "sadness", "dreams", "hope",
    "reality", "time", "failure", "strength", "fear", "peace", "family",
    "change", "adventure", "trust", "patience", "gratefulness", "courage",
    "positivity", "joy", "beauty", "health", "knowledge"
]

QUOTE_API_URL = "http://api.quotable.io/quotes"
TAGS_API_URL = "http://api.quotable.io/tags"


# === HELPERS ===
def load_tokens():
    if os.path.exists(TOKENS_FILE):
        with open(TOKENS_FILE, "r") as f:
            return json.load(f)
    return {}

def save_tokens(data):
    with open(TOKENS_FILE, "w") as f:
        json.dump(data, f, indent=2)

def get_valid_tags():
    try:
        res = requests.get(TAGS_API_URL, timeout=5, verify=False)
        return [tag['slug'] for tag in res.json()]
    except:
        return []

def fetch_random_quote(valid_tags):
    tag = random.choice(valid_tags or TOPICS)
    params = {"tags": tag, "limit": 3}
    response = requests.get(QUOTE_API_URL, params=params, verify=False)

    if response.status_code == 200:
        quotes = response.json().get("results", [])
        if quotes:
            quote = random.choice(quotes)
            return format_text(quote['content'], quote['author'])

    return ("Zindagi ke kuch\nraaste akelay hote hai.", "Unknown")

def format_text(quote, author):
    wrapped = textwrap.fill(quote, width=20)
    return wrapped, author

def select_audio():
    if not os.path.exists(AUDIO_FOLDER):
        return None
    files = [f for f in os.listdir(AUDIO_FOLDER) if f.endswith(".mp3")]
    return os.path.join(AUDIO_FOLDER, random.choice(files)) if files else None

def create_video(quote, author, audio, output_file):
    width, height = 1080, 1920
    font_size = 70
    author_size = 40
    duration = 4.5
    fade = 1.5

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    quote_safe = quote.replace(":", "\\:").replace("'", "\\'")
    author_safe = author.replace(":", "\\:").replace("'", "\\'")

    drawtext_main = (
        f"drawtext=fontfile={FONT_PATH}:text='{quote_safe}':"
        f"x=60:y=(h-text_h)/2:fontsize={font_size}:fontcolor=white:"
        f"line_spacing=30:box=1:boxcolor=black@0.5:boxborderw=20"
    )

    drawtext_author = (
        f"drawtext=fontfile={FONT_PATH}:text='- {author_safe}':"
        f"x=w-tw-30:y=h-th-30:fontsize={author_size}:fontcolor=white"
    )

    fade_filter = f"fade=t=in:st=0:d={fade},fade=t=out:st={duration-fade}:d={fade}"
    vf = f"zoompan=z='1.05':d=125:s={width}x{height}:fps=25,{drawtext_main},{drawtext_author},{fade_filter}"

    cmd = [
        "ffmpeg", "-y", "-loop", "1", "-i", BACKGROUND, "-i", audio,
        "-t", str(duration), "-vf", vf,
        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "18", "-preset", "slow",
        "-c:a", "aac", "-b:a", "192k", "-shortest", output_file
    ]

    subprocess.run(cmd, check=True)

def upload_video(creds, file_path, title, desc):
    youtube = build("youtube", "v3", credentials=creds, cache_discovery=False)
    request_body = {
        "snippet": {
            "title": title,
            "description": desc,
            "tags": ["quote", "motivation", "life"],
            "categoryId": "22"
        },
        "status": {"privacyStatus": "public"}
    }

    media = MediaFileUpload(file_path, mimetype="video/mp4", resumable=True)
    response = youtube.videos().insert(
        part="snippet,status", body=request_body, media_body=media
    ).execute()

    return response["id"]


# === ROUTES ===
@app.route("/")
def home():
    return "Start here: /auth to connect your YouTube"

@app.route("/auth")
def auth():
    flow = Flow.from_client_secrets_file(
        CLIENT_SECRET_FILE,
        scopes=SCOPES,
        redirect_uri=REDIRECT_URI
    )
    auth_url, state = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        prompt="consent"
    )
    session["state"] = state
    return redirect(auth_url)

@app.route("/auth/callback")
def callback():
    state = session.get("state")
    if not state:
        return "Missing session state. Try again."

    flow = Flow.from_client_secrets_file(
        CLIENT_SECRET_FILE,
        scopes=SCOPES,
        state=state,
        redirect_uri=REDIRECT_URI
    )
    flow.fetch_token(authorization_response=request.url)
    creds = flow.credentials

    user_info_service = build("oauth2", "v2", credentials=creds, cache_discovery=False)
    user_info = user_info_service.userinfo().get().execute()
    email = user_info["email"]

    tokens = load_tokens()
    tokens[email] = json.loads(creds.to_json())
    save_tokens(tokens)

    return f"Tokens saved for {email}. Now visit /upload-all to post video."

@app.route("/upload-all")
def upload_all():
    tags = get_valid_tags()
    tokens = load_tokens()
    results = {}

    for email, data in tokens.items():
        try:
            creds = Credentials.from_authorized_user_info(data, SCOPES)

            if creds.expired and creds.refresh_token:
                creds.refresh(GoogleRequest())
                tokens[email] = json.loads(creds.to_json())
                save_tokens(tokens)

            quote, author = fetch_random_quote(tags)
            audio = select_audio()
            if not audio:
                results[email] = "No audio file found"
                continue

            filename = os.path.join(OUTPUT_DIR, f"{email.replace('@', '_')}_video.mp4")
            create_video(quote, author, audio, filename)

            video_id = upload_video(creds, filename, quote[:40], f"Quote by {author}")
            results[email] = f"Uploaded: https://youtube.com/watch?v={video_id}"
        except Exception as e:
            results[email] = f"Error: {str(e)}"

    return results