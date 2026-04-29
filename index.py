from http.server import BaseHTTPRequestHandler
import yt_dlp
import json
from urllib.parse import urlparse, parse_qs

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        # 1. Mengambil URL dari parameter
        query = urlparse(self.path).query
        params = parse_qs(query)
        url = params.get('url', [None])[0]

        # Konfigurasi Header CORS agar bisa diakses bot Baileys Anda
        self.send_response(200 if url else 400)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()

        if not url:
            self.wfile.write(json.dumps({"success": False, "message": "Parameter ?url= tidak ditemukan!"}).encode('utf-8'))
            return

        # 2. Konfigurasi yt-dlp Ekstra Kuat untuk Semua Platform
        ydl_opts = {
            'format': 'best',        # Meminta kualitas terbaik yang tergabung (video+audio)
            'skip_download': True,   # WAJIB di Vercel agar server tidak crash
            'quiet': True,
            'no_warnings': True,
            'geo_bypass': True,      # Membantu menembus blokir wilayah (berguna untuk IG/TikTok)
            'extractor_retries': 3   # Coba ulang 3x jika server platform sedang sibuk
        }

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                
                # 3. LOGIKA CERDAS PENCARI URL
                # Beberapa platform (seperti Twitter/IG) tidak menaruh link di info.get('url')
                # Melainkan menyembunyikannya di dalam array 'formats'
                direct_url = info.get('url')
                
                if not direct_url and 'formats' in info:
                    # Ambil semua link yang valid di dalam array formats
                    valid_formats = [f for f in info['formats'] if f.get('url')]
                    if valid_formats:
                        # Biasanya format terbaik/terbesar ada di urutan paling akhir
                        direct_url = valid_formats[-1].get('url')

                # 4. Merakit hasil JSON
                response_data = {
                    "success": True,
                    "data": {
                        "platform": info.get('extractor_key'), # Memberitahu bot ini dari platform apa (Tiktok, Twitter, dll)
                        "title": info.get('title', 'Tanpa Judul'),
                        "duration": info.get('duration'),
                        "thumbnail": info.get('thumbnail'),
                        "direct_url": direct_url
                    }
                }
                
                self.wfile.write(json.dumps(response_data).encode('utf-8'))
                
        except Exception as e:
            # Jika video di-private, dihapus, atau butuh login (seperti beberapa video IG/FB)
            error_data = {
                "success": False,
                "message": "Gagal mengekstrak link. Pastikan video bersifat publik.",
                "error": str(e)
            }
            self.wfile.write(json.dumps(error_data).encode('utf-8'))
