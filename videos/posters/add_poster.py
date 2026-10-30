"""Give each video a designed first frame, since X uses the first frame as the thumbnail.

Captures posters/poster.html?v=N to posters/poster-N.png (Playwright, Edge), then overlays it on the
project's renders/video.mp4: fully opaque on frame 0, fading out from FADE_START to FADE_END so the
opening (which fades up from black) plays as before. Writes renders/video_poster.mp4 and a smaller
renders/video_poster_share.mp4. Audio is copied untouched.

    python posters/add_poster.py            (from videos/, with ffmpeg on PATH)
"""
import pathlib
import subprocess

from playwright.sync_api import sync_playwright

HERE = pathlib.Path(__file__).resolve().parent
VIDEOS = {1: "massive-movie-map", 2: "mmm-same-director", 3: "mmm-hollywood-pays"}
FADE_START, FADE_END = 0.25, 0.6


def capture():
    with sync_playwright() as p:
        b = p.chromium.launch(channel="msedge")
        pg = b.new_page(viewport={"width": 1080, "height": 1080})
        for v in VIDEOS:
            pg.goto((HERE / "poster.html").as_uri() + f"?v={v}")
            pg.evaluate("document.fonts.ready")
            pg.wait_for_load_state("networkidle")
            pg.wait_for_timeout(500)
            pg.screenshot(path=str(HERE / f"poster-{v}.png"))
        b.close()


def overlay(v, project):
    src = HERE.parent / project / "renders" / "video.mp4"
    png = HERE / f"poster-{v}.png"
    fade = f"fade=t=out:st={FADE_START}:d={FADE_END - FADE_START}:alpha=1"
    graph = f"[1:v]format=rgba,{fade}[p];[0:v][p]overlay=0:0:eof_action=pass:format=auto,format=yuv420p[v]"
    out = src.with_name("video_poster.mp4")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(src), "-loop", "1", "-t", str(FADE_END + 0.1), "-framerate", "30", "-i", str(png),
                    "-filter_complex", graph, "-map", "[v]", "-map", "0:a", "-c:v", "libx264", "-preset", "slow", "-crf", "16",
                    "-profile:v", "high", "-movflags", "+faststart", "-c:a", "copy", str(out)], check=True)
    share = src.with_name("video_poster_share.mp4")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(out), "-c:v", "libx264", "-preset", "slow", "-b:v", "2800k",
                    "-maxrate", "3500k", "-bufsize", "7000k", "-profile:v", "high", "-pix_fmt", "yuv420p", "-movflags", "+faststart",
                    "-c:a", "aac", "-b:a", "160k", str(share)], check=True)
    print(f"{project}: {out.name} {out.stat().st_size / 1e6:.1f} MB, {share.name} {share.stat().st_size / 1e6:.1f} MB")


if __name__ == "__main__":
    capture()
    for v, project in VIDEOS.items():
        overlay(v, project)
