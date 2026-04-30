from http.server import BaseHTTPRequestHandler
import yt_dlp
import json
import requests
from urllib.parse import urlparse, parse_qs

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        # 1. Mengambil URL dan Action dari parameter
        query = urlparse(self.path).query
        params = parse_qs(query)
        
        url = params.get('url', [None])[0]
        action = params.get('action', ['info'])[0] 

        # --- ENDPOINT UPTIMEROBOT / PING ---
        if action == 'ping' or not url:
            self.send_response(200 if action == 'ping' else 400)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            msg = "Server Vercel siap!" if action == 'ping' else "Parameter ?url= tidak ditemukan!"
            self.wfile.write(json.dumps({"success": action == 'ping', "message": msg}).encode('utf-8'))
            return

        # 2. Konfigurasi yt-dlp untuk bypass Bilibili/TikTok/IG
        ydl_opts = {
            'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best/bestvideo',
            'skip_download': True,   
            'quiet': True,
            'no_warnings': True,
            'geo_bypass': True,     
            'extractor_retries': 3,
            'http_headers': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36',
                'Referer': 'https://www.bilibili.tv/',
                'Accept-Language': 'en-us,en;q=0.5'
            }
        }

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                
                # 3. Logika Cerdas Pencari URL Stream
                direct_url = info.get('url')
                
                if not direct_url:
                    if 'requested_formats' in info:
                        vid_format = next((f for f in info['requested_formats'] if f.get('vcodec') != 'none'), None)
                        if vid_format:
                            direct_url = vid_format.get('url')
                    
                    if not direct_url and 'formats' in info:
                        valid_formats = [f for f in info['formats'] if f.get('url') and f.get('vcodec') != 'none']
                        if valid_formats:
                            direct_url = valid_formats[-1].get('url')

                headers_dict = info.get('http_headers', ydl_opts['http_headers'])
                platform_name = info.get('extractor_key', 'video')

                # 4. PERCABANGAN AKSI
                if action == 'download':
                    if not direct_url:
                        raise Exception("Direct URL tidak ditemukan untuk diunduh.")

                    custom_headers = {
                        "User-Agent": headers_dict.get("User-Agent", ydl_opts['http_headers']['User-Agent']),
                        "Accept": "*/*",
                        "Accept-Encoding": "identity", 
                        "Referer": headers_dict.get("Referer", "https://www.bilibili.tv/"),
                        "Sec-Fetch-Dest": "video",
                        "Sec-Fetch-Mode": "no-cors",
                        "Sec-Fetch-Site": "cross-site",
                        "Connection": "keep-alive"
                    }

                    req = requests.get(direct_url, headers=custom_headers, stream=True)
                    
                    if req.status_code in [200, 206]:
                        self.send_response(200)
                        content_type = req.headers.get('Content-Type', 'video/mp4')
                        file_size = req.headers.get('Content-Length')
                        
                        self.send_header('Content-type', content_type)
                        self.send_header('Content-Disposition', f'attachment; filename="{platform_name}_video.mp4"')
                        self.send_header('Access-Control-Allow-Origin', '*')
                        if file_size:
                            self.send_header('Content-Length', file_size)
                        self.end_headers()

                        # PERINGATAN: Di Vercel ini rawan putus jika file > 4.5MB atau butuh > 10 detik
                        for chunk in req.iter_content(chunk_size=16384): 
                            if chunk:
                                self.wfile.write(chunk)
                        return
                    else:
                        raise Exception(f"Gagal mem-proxy file. Status Code: {req.status_code}")

                else:
                    # MODE INFO JSON (Paling aman untuk Vercel)
                    self.send_response(200)
                    self.send_header('Content-type', 'application/json')
                    self.send_header('Access-Control-Allow-Origin', '*')
                    self.end_headers()

                    response_data = {
                        "success": True,
                        "data": {
                            "platform": platform_name,
                            "title": info.get('title', 'Tanpa Judul'),
                            "duration": info.get('duration'),
                            "thumbnail": info.get('thumbnail'),
                            "direct_url": direct_url,
                            "is_audio_missing": "requested_formats" in info 
                        }
                    }
                    self.wfile.write(json.dumps(response_data).encode('utf-8'))
                
        except Exception as e:
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps({
                "success": False, 
                "message": "Terjadi kesalahan saat memproses link.", 
                "error": str(e)
            }).encode('utf-8'))
