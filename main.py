from fastapi import FastAPI, Query, HTTPException
import yt_dlp

app = FastAPI()

@app.get("/")
def root():
    return {"status": "ok", "usage": "/info?url=VIDEO_URL"}

@app.get("/info")
def get_info(url: str = Query(..., description="Video URL")):
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

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)

            if info is None:
                raise HTTPException(
                    status_code=500,
                    detail="yt-dlp returned no info (mungkin diblok atau video private)"
                )

            if info.get("_type") == "playlist":
                entries = info.get("entries") or []
                if not entries:
                    raise HTTPException(status_code=500, detail="playlist kosong")
                info = entries[0]
                if info is None:
                    raise HTTPException(status_code=500, detail="entry pertama None")

            return ydl.sanitize_info(info)

    except yt_dlp.utils.DownloadError as e:
        raise HTTPException(status_code=500, detail=f"DownloadError: {str(e)}")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
