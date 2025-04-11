# YouTube Automation: Auto Create and Upload

A fully automated YouTube video generation and uploading tool built with Python and Flask. It fetches motivational quotes, creates aesthetic videos with text overlays and background music, and uploads them directly to your YouTube channel using the YouTube Data API.

> Created by [Yasir Hameed](https://github.com/ysr-hameed)  
> Repository: [Youtube_Automation_Auto_Create_and_Upload](https://github.com/ysr-hameed/Youtube_Automation_Auto_Create_and_Upload)

---

## Features

- Automatically fetches motivational quotes using an API
- Creates a video with text overlays on a background image
- Adds trending or custom background music
- Exports to MP4 format using MoviePy
- Uploads video directly to YouTube with title and description
- Flask-based local web app to manage video generation/upload
- Easy OAuth-based YouTube authentication

---

## Tech Stack

- **Backend**: Python, Flask  
- **Video Editing**: MoviePy, FFMPEG  
- **APIs**: YouTube Data API v3, Quotes API  
- **Google Auth**: `google-auth`, `google-auth-oauthlib`, `google-api-python-client`

---

## Installation

### 1. Clone the Repository

```bash
git clone https://github.com/ysr-hameed/Youtube_Automation_Auto_Create_and_Upload.git
cd Youtube_Automation_Auto_Create_and_Upload
```

### 2. Set Up Virtual Environment (optional but recommended)

```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Download Google OAuth Client Secret

1. Visit [Google Cloud Console](https://console.cloud.google.com/)
2. Create a project and enable **YouTube Data API v3**
3. Go to **APIs & Services > Credentials**
4. Click **Create Credentials > OAuth client ID**
5. Choose **Desktop App** and download the `client_secret.json`
6. Place it in the root of your project directory

---

## Usage

### Run the Flask App

```bash
python app.py
```

### Access the Web Interface

Open your browser and go to:

```
http://127.0.0.1:5000/
```

From here you can:

- Click **Generate Video** to create a motivational video  
- Click **Upload to YouTube** to authorize and publish it

### Authorization

- On first upload, it will open a Google login window for authorization  
- This generates a `token.json` file for future uploads (no need to log in again)

---

## File Structure

```
Youtube_Automation_Auto_Create_and_Upload/
│
├── static/
│   ├── bg.jpg           # Background image used for video
│   └── music.mp3        # Background music
│
├── templates/
│   └── index.html       # Web interface
│
├── app.py               # Flask app entry point
├── generate.py          # Video generation logic
├── upload.py            # YouTube upload logic
├── requirements.txt     # Python dependencies
├── client_secret.json   # Google OAuth credentials
├── token.json           # Generated after first authorization
├── video.mp4            # Output video
└── README.md
```

---

## Requirements

- Python 3.7+  
- FFMPEG installed and available in your system PATH  
- A Google Cloud project with YouTube Data API enabled  
- Internet connection for fetching quotes and uploading videos

---

## Customization

You can easily customize:

- **Quotes API**: Edit `generate.py` to use your own quote source  
- **Background Image**: Replace `static/bg.jpg`  
- **Music Track**: Replace `static/music.mp3`  
- **Video Duration**: Adjust timing in `generate.py`

---

## Screenshots

**Coming Soon** – Add screenshots or demo video links here to showcase the interface.

---

## License

This project is licensed under the **MIT License**. See the `LICENSE` file for details.

---

## Contribution

Contributions, suggestions, and feature requests are welcome!

To contribute:

1. Fork the repository  
2. Create a new branch  
3. Commit your changes  
4. Open a pull request

---

## Developer

**Yasir Hameed**  
- GitHub: [@ysr-hameed](https://github.com/ysr-hameed)  
- YouTube Channel: [@quotezen](https://youtube.com/@quotezen)

---

## Support

If you like this project, consider giving it a **star** on GitHub!  
Found an issue? [Open an issue](https://github.com/ysr-hameed/Youtube_Automation_Auto_Create_and_Upload/issues)

---
