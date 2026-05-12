"""
Helper script to get YouTube OAuth2 refresh token.
Run once to authenticate:  python scripts/get_youtube_token.py

Prerequisites:
1. Create OAuth2 credentials in Google Cloud Console
2. Enable YouTube Data API v3
3. Set YOUTUBE_CLIENT_ID and YOUTUBE_CLIENT_SECRET in .env
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
import json

SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube",
    "https://www.googleapis.com/auth/youtubepartner",
]

CLIENT_CONFIG = {
    "installed": {
        "client_id": os.getenv("YOUTUBE_CLIENT_ID", "YOUR_CLIENT_ID"),
        "client_secret": os.getenv("YOUTUBE_CLIENT_SECRET", "YOUR_CLIENT_SECRET"),
        "redirect_uris": ["urn:ietf:wg:oauth:2.0:oob", "http://localhost"],
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
    }
}


def get_refresh_token():
    flow = InstalledAppFlow.from_client_config(CLIENT_CONFIG, SCOPES)
    credentials = flow.run_local_server(port=8080, prompt="consent", access_type="offline")

    print("\n✅ Authentication successful!\n")
    print("=" * 60)
    print(f"YOUTUBE_REFRESH_TOKEN={credentials.refresh_token}")
    print("=" * 60)
    print("\nAdd this to your .env file.")

    with open("youtube_credentials.json", "w") as f:
        json.dump({
            "refresh_token": credentials.refresh_token,
            "client_id": CLIENT_CONFIG["installed"]["client_id"],
            "client_secret": CLIENT_CONFIG["installed"]["client_secret"],
        }, f, indent=2)
    print("✅ Credentials saved to youtube_credentials.json")


if __name__ == "__main__":
    get_refresh_token()
