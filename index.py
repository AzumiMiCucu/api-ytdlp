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

                self.send_response(400)
                self.send_header("Content-type", "application/json")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()

                self.wfile.write(json.dumps({
                    "success": False,
                    "error": "missing url parameter"
                }).encode())

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

                # penting untuk bilibili
                "http_headers": {
                    "User-Agent": (
                        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/140.0.0.0 Safari/537.36"
                    ),
                    "Referer": "https://www.bilibili.tv/",
                    "Accept-Language": "en-US,en;q=0.9"
                }
            }

            # ======================
            # EXTRACT
            # ======================
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:

                info = ydl.extract_info(
                    url,
                    download=False
                )

                # sanitize seperti yt-dlp -J
                info = ydl.sanitize_info(info)

            # ======================
            # RESPONSE
            # ======================
            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()

            self.wfile.write(
                json.dumps(info).encode("utf-8")
            )

        except Exception as e:

            self.send_response(500)
            self.send_header("Content-type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()

            self.wfile.write(json.dumps({
                "success": False,
                "error": str(e)
            }).encode())
