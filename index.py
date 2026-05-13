from http.server import BaseHTTPRequestHandler
import yt_dlp
import json
from urllib.parse import urlparse, parse_qs


class handler(BaseHTTPRequestHandler):

    def do_GET(self):

        # =========================
        # GET PARAMS
        # =========================
        query = urlparse(self.path).query
        params = parse_qs(query)

        url = params.get('url', [None])[0]
        action = params.get('action', ['info'])[0]

        # =========================
        # PING / HEALTHCHECK
        # =========================
        if action == 'ping':

            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()

            self.wfile.write(json.dumps({
                "success": True,
                "message": "Server aktif"
            }).encode('utf-8'))

            return

        # =========================
        # URL REQUIRED
        # =========================
        if not url:

            self.send_response(400)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()

            self.wfile.write(json.dumps({
                "success": False,
                "message": "Parameter ?url= tidak ditemukan"
            }).encode('utf-8'))

            return

        # =========================
        # YT-DLP OPTIONS
        # =========================
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'skip_download': True,
            'geo_bypass': True,
            'extractor_retries': 3,
            'http_headers': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36',
                'Accept-Language': 'en-us,en;q=0.5'
            }
        }

        try:

            # =========================
            # EXTRACT INFO
            # =========================
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:

                raw_info = ydl.extract_info(url, download=False)

                # sanitize agar JSON-compatible
                info = ydl.sanitize_info(raw_info)

            # =========================
            # RESPONSE RAW JSON
            # =========================
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()

            self.wfile.write(
                json.dumps(info).encode('utf-8')
            )

        except Exception as e:

            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()

            self.wfile.write(json.dumps({
                "success": False,
                "error": str(e)
            }).encode('utf-8'))
