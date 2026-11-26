"""Upload photographs to the Paradigm photo_booth folder on Google Drive."""

import argparse
import mimetypes
import os
from pathlib import Path

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload

FOLDER_ID = "1_oqjK_5MGjKiUb4oREiCDlEfghpErv3y"
SCOPES = ["https://www.googleapis.com/auth/drive.file"]
FOLDER_MIME_TYPE = "application/vnd.google-apps.folder"


class PhotoBoothUploader:
    """Upload photos headlessly using a previously authorized Google token."""

    def __init__(self, token_file=None):
        default_path = Path.home() / ".paradigm-photo-booth-token.json"
        bundled_path = Path(__file__).resolve().with_name("drive-token.json")
        if bundled_path.is_file():
            default_path = bundled_path
        self.token_file = Path(
            token_file or os.environ.get("DRIVE_TOKEN_FILE") or default_path
        ).expanduser()

    def upload(self, photo_path):
        """Upload an image and return its Google Drive URL."""
        photo = Path(photo_path).expanduser()
        if not photo.is_file():
            raise FileNotFoundError(photo)
        mime_type = mimetypes.guess_type(photo.name)[0] or ""
        if photo.suffix.lower() in {".heic", ".heif"}:
            mime_type = "image/" + photo.suffix[1:].lower()
        if not mime_type.startswith("image/"):
            raise ValueError(f"Unsupported image file: {photo.name}")
        if not self.token_file.is_file():
            raise FileNotFoundError(f"Google OAuth token file missing: {self.token_file}")

        credentials = Credentials.from_authorized_user_file(self.token_file, SCOPES)
        with build("drive", "v3", credentials=credentials) as drive, photo.open("rb") as source:
            result = _upload(drive, photo.name, source, mime_type)
        return result.get("webViewLink") or f"https://drive.google.com/file/d/{result['id']}/view"

    def authorize(self, client_json):
        """Open Google Picker locally and save a token for headless use."""
        flow = InstalledAppFlow.from_client_secrets_file(
            str(client_json), SCOPES, autogenerate_code_verifier=True
        )
        credentials = flow.run_local_server(
            host="127.0.0.1",
            port=0,
            timeout_seconds=300,
            authorization_prompt_message="",
            prompt="consent",
            trigger_onepick="true",
            allow_folder_selection="true",
            file_ids=FOLDER_ID,
        )
        with build("drive", "v3", credentials=credentials) as drive:
            folder = drive.files().get(
                fileId=FOLDER_ID,
                fields="mimeType,capabilities(canAddChildren)",
                supportsAllDrives=True,
            ).execute()
        if folder["mimeType"] != FOLDER_MIME_TYPE or not folder["capabilities"]["canAddChildren"]:
            raise PermissionError("The selected Google account cannot upload to photo_booth.")
        if not credentials.refresh_token:
            raise RuntimeError("Google did not issue a refresh token.")
        fd = os.open(self.token_file, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as token:
            os.fchmod(token.fileno(), 0o600)
            token.write(credentials.to_json())


def _upload(drive, filename, source, mime_type):
    media = MediaIoBaseUpload(source, mimetype=mime_type, resumable=True)
    request = drive.files().create(
        body={"name": filename, "parents": [FOLDER_ID]},
        media_body=media,
        fields="id,webViewLink",
        supportsAllDrives=True,
    )
    result = None
    while result is None:
        _, result = request.next_chunk(num_retries=3)
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--authorize", metavar="CLIENT_JSON", type=Path, required=True)
    args = parser.parse_args()
    uploader = PhotoBoothUploader()
    uploader.authorize(args.authorize)
    print(f"Authorization saved to {uploader.token_file}")
