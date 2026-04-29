from http.server import BaseHTTPRequestHandler
import yt_dlp
import json
import requests  # Pastikan Anda menambahkan 'requests' di requirements.txt
from urllib.parse import urlparse, parse_qs

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        # 1. Mengambil URL dan Action dari parameter
        query = urlparse(self.path).query
        params = parse_qs(query)
        
        url = params.get('url', [None])[0]
        # Default action adalah 'info' (mengembalikan JSON), 
        # jika diubah jadi 'download', maka akan mem-proxy file
        action = params.get('action', ['info'])[0] 

        if not url:
            self.send_response(400)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps({"success": False, "message": "Parameter ?url= tidak ditemukan!"}).encode('utf-8'))
            return

        # 2. Konfigurasi yt-dlp Ekstra Kuat
        ydl_opts = {
            'format': 'best',
            'skip_download': True,   
            'quiet': True,
            'no_warnings': True,
            'geo_bypass': True,     
            'extractor_retries': 3
        }

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                
                # 3. LOGIKA CERDAS PENCARI URL
                direct_url = info.get('url')
                if not direct_url and 'formats' in info:
                    valid_formats = [f for f in info['formats'] if f.get('url')]
                    if valid_formats:
                        direct_url = valid_formats[-1].get('url')

                headers_dict = info.get('http_headers', {})
                platform_name = info.get('extractor_key', 'video')

                # 4. PERCABANGAN AKSI (JSON vs DOWNLOAD)
                if action == 'download':
                    # --- MODE PROXY DOWNLOAD ---
                    if not direct_url:
                        raise Exception("Direct URL tidak ditemukan untuk diunduh.")

                    # Mengambil stream dari server asli (IG/TikTok) menyamar menggunakan header asli
                    req = requests.get(direct_url, headers=headers_dict, stream=True)
                    
                    if req.status_code == 200:
                        self.send_response(200)
                        # Mengatur header agar browser langsung mendownload file
                        content_type = req.headers.get('Content-Type', 'video/mp4')
                        self.send_header('Content-type', content_type)
                        self.send_header('Content-Disposition', f'attachment; filename="{platform_name}_download.mp4"')
                        self.send_header('Access-Control-Allow-Origin', '*')
                        self.end_headers()

                        # Stream data ke klien
                        for chunk in req.iter_content(chunk_size=8192):
                            if chunk:
                                self.wfile.write(chunk)
                        return
                    else:
                        raise Exception(f"Gagal mem-proxy file. Status Code: {req.status_code}")

                else:
                    # --- MODE INFO JSON (DEFAULT) ---
                    self.send_response(200)
                    self.send_header('Content-type', 'application/json')
                    self.send_header('Access-Control-Allow-Origin', '*')
                    self.end_headers()

                    response_data = {
                        "success": True,
                        "data": {
                            "platform": platform_name,
                            "headers": headers_dict,
                            "title": info.get('title', 'Tanpa Judul'),
                            "duration": info.get('duration'),
                            "thumbnail": info.get('thumbnail'),
                            "direct_url": direct_url
                        }
                    }
                    self.wfile.write(json.dumps(response_data).encode('utf-8'))
                
        except Exception as e:
            # Handle Error
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            
            error_data = {
                "success": False,
                "message": "Terjadi kesalahan saat memproses link.",
                "error": str(e)
            }
            self.wfile.write(json.dumps(error_data).encode('utf-8'))
