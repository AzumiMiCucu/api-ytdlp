from http.server import BaseHTTPRequestHandler, HTTPServer
import yt_dlp
import json
import requests  
import os
from urllib.parse import urlparse, parse_qs

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        # 1. Mengambil URL dan Action dari parameter
        query = urlparse(self.path).query
        params = parse_qs(query)
        
        url = params.get('url', [None])[0]
        action = params.get('action', ['info'])[0] 

        # --- ENDPOINT KHUSUS UPTIMEROBOT ---
        if action == 'ping':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps({"status": "Server Render hidup dan siap mem-proxy!"}).encode('utf-8'))
            return
        # -----------------------------------

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
                    # --- MODE PROXY BYPASS (STREAMING LANGSUNG TANPA /TMP) ---
                    if not direct_url:
                        raise Exception("Direct URL tidak ditemukan untuk diunduh.")

                    # Memalsukan header agar terlihat seperti browser asli (Bypass 403)
                    custom_headers = {
                        "User-Agent": headers_dict.get("User-Agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"),
                        "Accept": "*/*",
                        "Accept-Encoding": "identity", # Mencegah kompresi gzip/deflate yang merusak stream video
                        "Referer": headers_dict.get("Referer", "https://www.tiktok.com/" if "tiktok" in platform_name else "https://www.instagram.com/"),
                        "Sec-Fetch-Dest": "video",
                        "Sec-Fetch-Mode": "no-cors",
                        "Sec-Fetch-Site": "cross-site",
                        "Connection": "keep-alive"
                    }

                    # Melakukan request stream langsung ke CDN IG/TikTok
                    req = requests.get(direct_url, headers=custom_headers, stream=True)
                    
                    # CDN video seringkali mengembalikan 206 (Partial Content) atau 200 (OK)
                    if req.status_code in [200, 206]:
                        self.send_response(200)
                        
                        # Set header untuk memaksa browser klien mendownload file
                        content_type = req.headers.get('Content-Type', 'video/mp4')
                        file_size = req.headers.get('Content-Length')
                        
                        self.send_header('Content-type', content_type)
                        self.send_header('Content-Disposition', f'attachment; filename="{platform_name}_video.mp4"')
                        self.send_header('Access-Control-Allow-Origin', '*')
                        
                        # Beri tahu ukuran file jika ada (membantu progress bar di browser pengguna)
                        if file_size:
                            self.send_header('Content-Length', file_size)
                            
                        self.end_headers()

                        # Piping/Streaming langsung dari sumber ke pengguna dalam ukuran kecil (chunk)
                        for chunk in req.iter_content(chunk_size=16384): # 16KB chunk
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

# ==========================================
# BLOK WAJIB UNTUK RENDER.COM
# ==========================================
if __name__ == '__main__':
    # Render memberikan port dinamis melalui Environment Variable 'PORT'
    # Jika dijalankan di lokal, akan menggunakan port 8000
    port = int(os.environ.get('PORT', 8000))
    server_address = ('0.0.0.0', port)
    
    httpd = HTTPServer(server_address, handler)
    print(f"🚀 Server berjalan dan mendengarkan di port {port}...")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    httpd.server_close()
    print("Server dihentikan.")
