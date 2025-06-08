"""handle connections"""

import base64
import os

import requests
from src.config import get_config
from src.static_types import ConfigType, TAChannel, TAVideo


import os
import logging
from logging.handlers import RotatingFileHandler

logfile_name = '/app/logs/' + os.path.basename(__file__).split('.')[0] + '.log'
logging.basicConfig(
    handlers=[
        RotatingFileHandler(
            logfile_name,
            # Limit the size to 10000000Bytes ~ 10MB 
            maxBytes=10000000,
            backupCount=5
        )
    ],
    format='%(asctime)s %(levelname)-4s %(filename)s:%(funcName)s %(message)s',
    level=logging.INFO,
    datefmt='%Y-%m-%d %H:%M:%S')

CONFIG: ConfigType = get_config()
TIMEOUT = 180
#EXPECTED_ENV = {"ta_url", "ta_token", "emby_url", "emby_token", "ta_video_path"} # js_folder is optional
EXPECTED_ENV = {'ta_video_path', 'emby_token', 'ta_url', 'emby_folder', 'ta_token', 'emby_url'} # js_folder is optional


class Jellyfin:
    """connect to Jellyfin"""

    headers: dict = {
        "Authorization": "MediaBrowser Token=" + CONFIG["emby_token"]
    }
    base: str = CONFIG["emby_url"]

    def get(self, path: str) -> dict:
        """make a get request"""
        url: str = f"{self.base}/{path}"
        logging.info(f"url: {url}")
        response = requests.get(url, headers=self.headers, timeout=TIMEOUT, verify=False)
        if response.ok:
            return response.json()

        print(response.text)
        return {}

    def post(self, path: str, data: dict | bool) -> None:
        """make a post request"""
        url: str = f"{self.base}/{path}"
        logging.info(f"url: {url}")
        response = requests.post(
            url, headers=self.headers, json=data, timeout=TIMEOUT, verify=False
        )
        if not response.ok:
            print(response.text)
        return response.text

    def post_img(self, path: str, thumb_base64: bytes) -> None:
        """set image"""
        url: str = f"{self.base}/{path}"
        logging.info(f"url: {url}")
        new_headers: dict = self.headers.copy()
        new_headers.update({"Content-Type": "image/jpeg"})
        response = requests.post(
            url, headers=new_headers, data=thumb_base64, timeout=TIMEOUT, verify=False
        )
        if not response.ok:
            print(response.text)
        return response.text

    def ping(self) -> None:
        """ping the server"""
        response = self.get("Users")
        if not response:
            raise ConnectionError("failed to connect to emby")

        print("[connection] verified emby connection")


class TubeArchivist:
    """connect to Tube Archivist"""

    ta_token: str = CONFIG["ta_token"]
    headers: dict = {"Authorization": f"Token {ta_token}"}
    base: str = CONFIG["ta_url"]

    def get_video(self, video_id: str) -> TAVideo:
        """get video metadata"""
        url: str = f"{self.base}/api/video/{video_id}/"
        response = requests.get(url, headers=self.headers, timeout=TIMEOUT)

        if response.ok:
            ta_video: TAVideo = response.json()
            return ta_video

        raise ValueError(f"video not found in TA: {url}")

    def get_channel(self, channel_id: str) -> TAChannel | None:
        """get channel metadata"""
        url: str = f"{self.base}/api/channel/{channel_id}/"
        response = requests.get(url, headers=self.headers, timeout=TIMEOUT)
        if response.ok:
            ta_channel: TAChannel = response.json()
            return ta_channel

        print(f"channel not found in TA: {url}")
        return None

    def get_thumb(self, path: str) -> bytes:
        """get encoded thumbnail from ta"""
        url: str = CONFIG["ta_url"] + path
        response = requests.get(
            url, headers=self.headers, stream=True, timeout=TIMEOUT
        )
        base64_thumb: bytes = base64.b64encode(response.content)

        return base64_thumb

    def ping(self) -> None:
        """ping tubearchivist server"""
        url: str = f"{self.base}/api/ping/"
        response = requests.get(url, headers=self.headers, timeout=TIMEOUT)

        if not response:
            raise ConnectionError("failed to connect to tube archivist")

        print("[connection] verified tube archivist connection")


def env_check() -> None:
    """check for expected environment"""

    if not CONFIG:
        raise ValueError("could not build config.")

    if not os.path.exists(CONFIG["ta_video_path"]):
        raise FileNotFoundError(
            "failed to access ta_video_path", CONFIG["ta_video_path"]
        )

    if not set(CONFIG) == EXPECTED_ENV:
        raise ValueError(
            f"expected environment {EXPECTED_ENV} but got {set(CONFIG)}"
        )


def clean_overview(overview_raw: str) -> str:
    """parse and clean raw overview text"""
    if len(overview_raw) > 500:
        overview_raw = overview_raw[:500] + " ..."

    desc_clean: str = overview_raw.replace("\n", "<br>")

    return desc_clean
