import os
import json
import random
import requests
import subprocess
from flask import Flask, redirect, request, session, url_for
from google_auth_oauthlib.flow import Flow
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.auth.transport.requests import Request
import urllib3
import warnings

# Suppress SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Suppress oauth2client cache warning

app = Flask(__name__)
app.secret_key = "your_secret_key"

# Define paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FONT_FILE = os.path.join(BASE_DIR, "Poppins-Regular.ttf")
OUTPUT_FILE = os.path.join(BASE_DIR, "output.mp4")
MUSIC_FOLDER = os.path.join(BASE_DIR, "trending_songs")
TOKEN_FILE = os.path.join(BASE_DIR, "tokens.json")
CLIENT_SECRET_FILE = os.path.join(BASE_DIR, "client_secrets.json")

# Google API settings
SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]
REDIRECT_URI = "https://ysrautomation.pythonanywhere.com/auth/callback"

# Ensure token file exists
if not os.path.exists(TOKEN_FILE):
    with open(TOKEN_FILE, "w") as f:
        json.dump({}, f)

# ** Step 1: Authenticate with YouTube **
@app.route("/auth")
def authenticate_youtube():
    flow = Flow.from_client_secrets_file(
        CLIENT_SECRET_FILE, scopes=SCOPES, redirect_uri=REDIRECT_URI
    )
    authorization_url, state = flow.authorization_url(prompt="consent")
    session["state"] = state
    return redirect(authorization_url)
# ** Step 2: Handle Google Callback & Save Token **
@app.route("/auth/callback")
def auth_callback():
    state = session.get("state")
    if not state:
        return "❌ Authentication failed: Missing state."

    flow = Flow.from_client_secrets_file(
        CLIENT_SECRET_FILE, scopes=SCOPES, redirect_uri=REDIRECT_URI, state=state
    )
    flow.fetch_token(authorization_response=request.url)

    credentials = flow.credentials
    with open(TOKEN_FILE, "w") as f:
        json.dump(json.loads(credentials.to_json()), f, indent=4)

    return redirect(url_for("automate"))

def get_credentials():
    """Retrieve and refresh OAuth credentials."""
    if not os.path.exists(TOKEN_FILE):
        return None  # Force re-authentication

    try:
        with open(TOKEN_FILE, "r") as token_file:
            token_data = json.load(token_file)

        # Ensure required fields are present
        required_keys = ["token", "refresh_token", "client_id", "client_secret", "token_uri"]
        if not all(key in token_data for key in required_keys):
            print("❌ Missing required fields in tokens.json. Re-authentication required.")
            return None

        credentials = Credentials.from_authorized_user_info(token_data)

        if credentials.expired and credentials.refresh_token:
            credentials.refresh(Request())

            # Save updated tokens
            with open(TOKEN_FILE, "w") as token_file:
                json.dump(json.loads(credentials.to_json()), token_file, indent=4)

        return credentials

    except (json.JSONDecodeError, ValueError) as e:
        print(f"❌ Error loading tokens.json: {e}")
        return None  # Force re-authentication
def fetch_unique_quote():
    try:
        response = requests.get("https://api.quotable.io/random", verify=False, timeout=5)
        if response.status_code == 200:
            data = response.json()
            return data.get("content", "Error fetching quote"), data.get("author", "Unknown")
    except requests.exceptions.RequestException as e:
        return f"Error fetching quote: {str(e)}", "Unknown"

# Example usage
quote, author = fetch_unique_quote()
print(f'"{quote}" - {author}')

# ** Step 5: Generate Video with Text Overlay **
def generate_video(quote, author):
    words = quote.split()
    lines = []
    line = ""

    for word in words:
        if len(line) + len(word) <= 25:
            line += word + " "
        else:
            lines.append(line.strip())
            line = word + " "
    lines.append(line.strip())

    text_filters = []
    y_offset = 0.12  # Starting Y offset for the quote

    # Effect for fade-in start: Zoom-in effect (scale up)
    fade_in_effect = "[0:v]scale=iw*1.1:ih*1.1,zoompan=z='if(gte(pzoom\,1.0)\,1.0\,pzoom+0.02)':s=1080x1920:d=200"

    # Generate the quote lines
    for line in lines:
        text_filters.append(
            f"drawtext=fontfile='{FONT_FILE}':text='{line}':fontcolor=white:fontsize=65:x=w*0.10:y=h*{y_offset}:alpha='if(lt(t\\,1)\\,0\\,if(lt(t\\,2)\\,(t-1)/1\\,1))'"
        )
        y_offset += 0.065  # Adjusting the space for the next line

    # Adjust y_offset for the author's name to be below the last quote line
    author_text = f"~ {author}"

    # Handle long author name (break into multiple lines if needed)
    max_line_length = 25  # Max characters per line for the author's name
    author_lines = []
    while len(author_text) > max_line_length:
        split_index = author_text.rfind(' ', 0, max_line_length)
        if split_index == -1:  # No space found, break the word
            split_index = max_line_length
        author_lines.append(author_text[:split_index])
        author_text = author_text[split_index:].strip()
    author_lines.append(author_text)

    # Add the author lines to the filters
    author_y_offset = y_offset + 0.065  # Adding extra space below the last quote line
    for i, line in enumerate(author_lines):
        text_filters.append(
            f"drawtext=fontfile='{FONT_FILE}':text='{line}':fontcolor=white:fontsize=50:x=w*0.5-text_w/2:y=h*{author_y_offset + 0.065*i}:alpha='if(lt(t\\,1)\\,0\\,if(lt(t\\,2)\\,(t-1)/1\\,1))'"
        )

    # FFmpeg command to generate the video (7 seconds, zoom-in effect)
    ffmpeg_command = f"""
    ffmpeg -y -f lavfi -i color=c=black:s=1080x1920:d=7 -vf "{fade_in_effect},{','.join(text_filters)}" -preset slow -crf 18 -c:v libx264 -t 7 {OUTPUT_FILE}
    """
    subprocess.run(ffmpeg_command, shell=True)

    # Handle background music if available
    music_file = get_random_song()
    if music_file:
        OUTPUT_WITH_AUDIO = os.path.join(BASE_DIR, "output_with_audio.mp4")
        ffmpeg_audio_command = f"""
        ffmpeg -y -i {OUTPUT_FILE} -i "{music_file}" -filter_complex "[1:a]afade=t=in:ss=0:d=2,afade=t=out:st=6:d=2[a1];[a1]volume=0.5[a2]" -map 0:v -map "[a2]" -shortest -preset slow -crf 18 -c:v libx264 -c:a aac -b:a 192k {OUTPUT_WITH_AUDIO}
        """
        subprocess.run(ffmpeg_audio_command, shell=True)
        os.replace(OUTPUT_WITH_AUDIO, OUTPUT_FILE)

    # Adding fade-out effect before the last second of video (for quote and author)
    fade_out_effect = f"fade=t=out:st=6:d=1"  # Fade-out starting at 6 seconds, lasts 1 second

    # Update final video with fade-out effect for both quote and author
    ffmpeg_final_command = f"""
    ffmpeg -y -i {OUTPUT_FILE} -vf "{fade_out_effect}" -preset slow -crf 18 -c:v libx264 -t 7 {OUTPUT_FILE}
    """
    subprocess.run(ffmpeg_final_command, shell=True)

# ** Step 6: Get a Random Trending Song **
def get_random_song():
    songs = [f for f in os.listdir(MUSIC_FOLDER) if f.endswith((".mp3", ".wav", ".aac", ".m4a"))]
    return os.path.join(MUSIC_FOLDER, random.choice(songs)) if songs else None

# ** Step 7: Upload Video to YouTube **
@app.route("/")
def automate():
    credentials = get_credentials()
    if credentials is None:
        return redirect(url_for("authenticate_youtube"))

    youtube = build("youtube", "v3", credentials=credentials)

    quote, author = fetch_unique_quote()
    generate_video(quote, author)

    viral_tags = [
        "motivation", "inspiration", "success", "mindset", "hustle", "grind", "lifequotes",
        "wisdom", "selfgrowth", "entrepreneur", "positivity", "focus", "leadership", "vision",
        "goals", "selfmade", "dreambig", "wealth", "powerful", "neverquit", "believe", "attitude",
        "selfdiscipline", "winner", "happiness", "hustlemode", "quotesdaily", "billionairemindset",

        # High-Engagement Hashtags
        "determination", "mentality", "ambition", "growth", "motivationmonday", "successquotes",
        "hardwork", "stayfocused", "selfimprovement", "businessquotes", "dreamchaser", "dedication",
        "mindsetmatters", "grindmode", "nevergiveup", "unstoppable", "selfdevelopment", "greatness",
        "millionairemindset", "bossmindset", "successdriven", "manifestation", "entrepreneurmindset",
        "moneyquotes", "businessmotivation", "mindovermatter", "goalsetter", "disciplineequalsfreedom",
        "riseandgrind", "growthmindset", "winnersmindset", "selfgrowthjourney", "hustleharder",
        "betteryourself", "motivationalquotes", "grinddontstop", "successtips", "positivemindset",
        "manifestyourdreams", "goaldigger", "neverbackdown", "winnersneverquit", "personaldevelopment",
        "dreambigworkhard", "entrepreneurlifestyle", "inspirationalquotes", "driventosucceed",
        "hustlersambition", "wealthmindset", "powerofpositivity", "businessmindset", "believeinyourself",
        "passionandpurpose", "selfbelief", "workethic", "staymotivated", "keeppushing", "pushyourself",
        "levelup", "buildyourempire", "createthelifeyouwant", "nothingisimpossible", "workhardstayhumble",
        "positivevibes", "strongmind", "beyourownboss", "noexcuses", "hustleandflow", "successiskey",
        "keepgoing", "nevergiveupquotes", "fearless", "becomebetter", "inspiredaily", "selfconfidence",
        "highperformance", "staydriven", "motivationalmindset", "thinkandgrowrich", "powerthoughts",
        "buildyourdreams", "focusedandfearless", "goaloriented", "unstoppablemindset", "hustlersmindset",

        # Trending & Viral Hashtags
        "millionairelifestyle", "richmindset", "growthquotes", "lawofattraction", "powerofmindset",
        "financialfreedom", "dreambigger", "stayhungry", "businessgrowth", "grindhustle", "goalcrusher",
        "dailyquotes", "wealthyhabits", "unstoppableforce", "focusonyourgoals", "highperformancehabits",
        "millionairesecrets", "alphamentality", "investinyourself", "innerpower", "hardworkpaysoff",
        "wintheday", "winningmentality", "lifesuccess", "nevergiveupmindset", "billionairelifestyle",
        "getmotivated", "mindsetcoach", "yourfuture", "gamechanger", "levelupmindset", "keepmovingforward",
        "bossmoves", "moneytalks", "stayrelentless", "selfmastery", "createyourfuture", "neversettle","grindhard", "selfmadebillionaire", "successmindset", "goalsetter", "neversettle", "riseandshine",
    "worksmart", "entrepreneurialmindset", "chasingdreams", "positivethinking", "unstoppableforce",
    "neverstopdreaming", "ambitioniskey", "getthingsdone", "keepgrinding", "motivationalmindset",
    "hustletime", "dreamchasers", "workhardstayhumble", "workforit", "achievegreatness", "inspireothers"
    ]

    title_tags = random.sample(viral_tags, 3)
    title = f"{' '.join(quote.split()[:5])}... #shorts #{title_tags[0]}, #{title_tags[1]}, #{title_tags[2]}"

    random.shuffle(viral_tags)
    description = f"{quote}\n\nFollow us for daily motivation!\n\n" + ' '.join([f"#{tag}" for tag in viral_tags])
    video_tags = random.sample(viral_tags, 10)

    try:
        request = youtube.videos().insert(
            part="snippet,status",
            body={
                "snippet": {
                    "title": title,
                    "description": description,
                    "tags": video_tags,
                    "categoryId" : "27"
                },
                "status": {"privacyStatus": "public"},
            },
            media_body=MediaFileUpload(OUTPUT_FILE, mimetype="video/mp4"),
        )
        response = request.execute()
        return f"✅ Video uploaded successfully! Video ID: {response['id']}"
    except Exception as e:
        return f"❌ Upload failed: {str(e)}"
if __name__ == "__main__":
    app.run(debug=True)