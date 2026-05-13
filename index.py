from http.server import BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import yt_dlp
import json


class handler(BaseHTTPRequestHandler):

    def do_GET(self):
        try:
            # ======================
            # QUERY PARAMS
            # ======================
            query = urlparse(self.path).query
            params = parse_qs(query)
            url = params.get("url", [None])[0]

            if not url:
                self._respond(400, {"success": False, "error": "missing url parameter"})
                return

            # ======================
            # YT-DLP OPTIONS
            # ======================
            ydl_opts = {
                "quiet": True,
                "no_warnings": True,
                "skip_download": True,
                "geo_bypass": True,
                "extractor_retries": 5,
                "socket_timeout": 30,
                "http_headers": {
                    "User-Agent": (
                        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/140.0.0.0 Safari/537.36"
                    ),
                    "Referer": "https://www.bilibili.tv/",
                    "Accept-Language": "en-US,en;q=0.9",
                },
            }

            # ======================
            # EXTRACT
            # ======================
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)

                # Guard: extract_info can return None
                if info is None:
                    self._respond(500, {"success": False, "error": "yt-dlp returned no info (unsupported URL or private video)"})
                    return

                # If it's a playlist, unwrap the first entry
                if info.get("_type") == "playlist":
                    entries = info.get("entries") or []
                    if not entries:
                        self._respond(500, {"success": False, "error": "playlist is empty"})
                        return
                    info = entries[0]
                    if info is None:
                        self._respond(500, {"success": False, "error": "first playlist entry is None"})
                        return

                info = ydl.sanitize_info(info)

            self._respond(200, info)

        except yt_dlp.utils.DownloadError as e:
            self._respond(500, {"success": False, "error": f"DownloadError: {str(e)}"})
        except Exception as e:
            self._respond(500, {"success": False, "error": str(e)})

    def _respond(self, status: int, data: dict):
        self.send_response(status)
        self.send_header("Content-type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode("utf-8"))
