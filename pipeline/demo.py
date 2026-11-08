from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pipeline.io_utils import write_text


DEMO_HTML_TEMPLATE = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Subtitle MVP Demo</title>
  <style>
    :root {
      --bg-0: #091117;
      --bg-1: #15212b;
      --text-main: #f5f2ea;
      --text-dim: #c6c2b8;
      --accent: #d39d2f;
      --panel: rgba(13, 21, 28, 0.94);
      --subtitle-panel: #12171d;
    }
    body {
      margin: 0;
      font-family: "Palatino Linotype", "Book Antiqua", Palatino, "Times New Roman", serif;
      background:
        radial-gradient(circle at 15% 12%, #1b2c38 0%, rgba(27, 44, 56, 0) 45%),
        linear-gradient(135deg, var(--bg-0), var(--bg-1));
      color: var(--text-main);
      min-height: 100vh;
      display: grid;
      place-items: center;
      padding: clamp(10px, 2.5vw, 24px);
      box-sizing: border-box;
    }
    .container {
      width: min(1100px, 100%);
      height: min(94vh, 900px);
      background: var(--panel);
      border: 1px solid rgba(211, 157, 47, 0.38);
      border-radius: 18px;
      box-shadow: 0 18px 46px rgba(0, 0, 0, 0.5);
      overflow: hidden;
      display: grid;
      grid-template-rows: auto 2fr 1fr;
      animation: panel-in 320ms ease-out;
    }
    @keyframes panel-in {
      from { opacity: 0; transform: translateY(12px); }
      to { opacity: 1; transform: translateY(0); }
    }
    .header {
      padding: 14px 16px;
      background: rgba(9, 15, 20, 0.62);
      border-bottom: 1px solid rgba(211, 157, 47, 0.3);
      font-weight: 700;
      letter-spacing: 0.03em;
    }
    .video-stage {
      min-height: 0;
      display: flex;
      align-items: center;
      justify-content: center;
      background: #050709;
      padding: 12px;
    }
    video {
      width: 100%;
      max-width: 100%;
      max-height: 100%;
      display: block;
      background: #000;
      border-radius: 10px;
    }
    .live-stage {
      min-height: 0;
      display: grid;
      place-items: center;
      padding: clamp(14px, 2.8vw, 28px);
      background: linear-gradient(180deg, rgba(8, 12, 16, 0.68), rgba(8, 12, 16, 0.95));
    }
    .live-region {
      width: min(92%, 960px);
      min-height: 62%;
      background: var(--subtitle-panel);
      border: 1px solid rgba(211, 157, 47, 0.44);
      border-radius: 16px;
      box-shadow: inset 0 0 0 1px rgba(255, 255, 255, 0.04), 0 10px 28px rgba(0, 0, 0, 0.45);
      color: var(--text-main);
      display: flex;
      align-items: center;
      justify-content: center;
      padding: clamp(16px, 3.2vw, 34px);
      text-align: center;
      line-height: 1.34;
      font-weight: 800;
      font-size: clamp(24px, 3.2vw, 44px);
      letter-spacing: 0.015em;
      text-shadow: 0 1px 1px rgba(0, 0, 0, 0.55);
    }
    @media (max-width: 800px) {
      .container {
        height: min(96vh, 860px);
      }
      .header {
        font-size: 0.95rem;
      }
    }
  </style>
</head>
<body>
  <main class="container">
    <div class="header">Subtitle Extraction MVP Demo</div>
    <section class="video-stage">
      <video id="video" controls preload="metadata">
        <source src="__VIDEO_FILE__" type="video/mp4">
      </video>
    </section>
    <section class="live-stage">
      <div id="liveRegion" class="live-region" aria-live="polite"></div>
    </section>
  </main>

  <script>
    const DEFAULT_VIDEO_VOLUME = 0.5;
    const INITIAL_SUBTITLE_DELAY_MS = 900;
    const GENERATED_SUBTITLES = __SUBTITLE_DATA__;

    const video = document.getElementById("video");
    const liveRegion = document.getElementById("liveRegion");
    let currentLiveText = "";
    let pendingLiveUpdate = null;
    let activeCueSignature = "";
    let playbackStarted = false;

    video.volume = DEFAULT_VIDEO_VOLUME;

    function setupGeneratedTrack() {
      const generatedTrack = video.addTextTrack("subtitles", "Generated subtitles", "es");
      generatedTrack.mode = "showing";

      if (typeof window.VTTCue !== "function" && typeof window.TextTrackCue !== "function") {
        return generatedTrack;
      }

      for (const item of GENERATED_SUBTITLES) {
        let cue = null;
        if (typeof window.VTTCue === "function") {
          cue = new window.VTTCue(item.start, item.end, item.text);
        } else if (typeof window.TextTrackCue === "function") {
          cue = new window.TextTrackCue(item.start, item.end, item.text);
        }

        if (cue) {
          generatedTrack.addCue(cue);
        }
      }

      return generatedTrack;
    }

    setupGeneratedTrack();

    function clearPendingLiveUpdate() {
      if (pendingLiveUpdate !== null) {
        clearTimeout(pendingLiveUpdate);
        pendingLiveUpdate = null;
      }
    }

    function applyLiveText(text) {
      if (text !== currentLiveText) {
        liveRegion.textContent = text;
        currentLiveText = text;
      }
    }

    function findActiveSubtitle(time) {
      for (const item of GENERATED_SUBTITLES) {
        if (time >= item.start && time < item.end) {
          return item;
        }
      }
      return null;
    }

    function updateLiveRegion() {
      const time = video.currentTime;
      const activeSubtitle = findActiveSubtitle(time);

      if (!activeSubtitle) {
        clearPendingLiveUpdate();
        activeCueSignature = "";
        applyLiveText("");
        return;
      }

      const cueSignature = `${activeSubtitle.start}|${activeSubtitle.end}|${activeSubtitle.text}`;
      if (cueSignature === activeCueSignature) {
        return;
      }

      clearPendingLiveUpdate();

      const startsAtZero = activeSubtitle.start <= 0.001;
      if (startsAtZero && !playbackStarted) {
        return;
      }

      if (startsAtZero && time < INITIAL_SUBTITLE_DELAY_MS / 1000) {
        const remainingDelayMs = Math.max(0, INITIAL_SUBTITLE_DELAY_MS - Math.floor(time * 1000));
        pendingLiveUpdate = setTimeout(() => {
          const now = video.currentTime;
          const stillActive = now >= activeSubtitle.start && now < activeSubtitle.end;
          if (stillActive) {
            applyLiveText(activeSubtitle.text);
            activeCueSignature = cueSignature;
          }
          pendingLiveUpdate = null;
        }, remainingDelayMs);
        return;
      }

      applyLiveText(activeSubtitle.text);
      activeCueSignature = cueSignature;
    }

    video.addEventListener("timeupdate", updateLiveRegion);
    video.addEventListener("loadedmetadata", updateLiveRegion);
    video.addEventListener("seeked", updateLiveRegion);
    video.addEventListener("play", () => {
      playbackStarted = true;
      updateLiveRegion();
    });
  </script>
</body>
</html>
"""


def build_demo_html(video_file: str, subtitles_payload: list[dict[str, Any]]) -> str:
    html = DEMO_HTML_TEMPLATE.replace("__VIDEO_FILE__", video_file)
    return html.replace("__SUBTITLE_DATA__", json.dumps(subtitles_payload, ensure_ascii=False))


def export_demo_page(output_dir: Path, video_file_name: str, subtitles_payload: list[dict[str, Any]]) -> Path:
    html_path = output_dir / "subtitles_demo.html"
    write_text(html_path, build_demo_html(video_file_name, subtitles_payload))
    return html_path
