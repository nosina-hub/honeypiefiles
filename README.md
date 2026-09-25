# ੈ✩‧₊˚ rgb ascii renderer 🎀

> turn any video into real-time colored ascii art that plays right in your terminal ✨

![python](https://img.shields.io/badge/python-3.8+-c9b6e4?style=flat-square&logo=python&logoColor=white)
![license](https://img.shields.io/badge/license-MIT-f7c5d5?style=flat-square)
![terminal](https://img.shields.io/badge/runs%20in-terminal-b8d4f5?style=flat-square)

---

## 💙 what is this

each frame of your video gets converted into a grid of ascii characters — every character colored with the **exact rgb value** of that pixel using ansi true-color escape codes. it's like watching a movie but make it terminal art 🎞️🩷

---

## 🩷 setup

```bash
pip install opencv-python numpy imageio-ffmpeg pygame
```

you'll also need **ffmpeg** for audio:

```bash
# mac
brew install ffmpeg

# linux
sudo apt install ffmpeg

# windows → https://ffmpeg.org/download.html
```

---

## 💙 usage

```bash
# drop a video in the folder and run
python ascii_renderer.py your_video.mp4

# more columns = more detail (needs a wide terminal!)
python ascii_renderer.py your_video.mp4 --cols 200

# richer character set
python ascii_renderer.py your_video.mp4 --detailed

# cap the fps if it's too fast
python ascii_renderer.py your_video.mp4 --fps 24

# no audio
python ascii_renderer.py your_video.mp4 --no-audio
```

---

## 🌸 how it works

```
video frame  →  resize to terminal size
     ↓
pixel brightness  →  ascii character  ( space · . : = * # @ )
     ↓
pixel rgb  →  ansi true-color escape code  \033[38;2;R;G;Bm
     ↓
delta render  →  only redraws pixels that changed from last frame
     ↓
raw bytes  →  written directly to stdout for max speed 🚀
```

the delta rendering is what keeps it smooth — instead of repainting the whole screen every frame (25 kb/frame 😭), it only updates the pixels that actually changed (~2 kb/frame 🎉)

---

## 💜 tips for best results

- use a **monospace font** in your terminal (fira code, jetbrains mono, etc.)
- make the font **really small** for more resolution
- **high contrast videos** look the best
- fullscreen your terminal before running 🖥️

---

## 🩵 built with

- `opencv-python` — frame decoding
- `numpy` — vectorized pixel math
- `imageio-ffmpeg` — audio extraction
- `pygame` — audio playback
- pure ansi escape codes for color 💅

---
> [✨ live demo](https://claude.ai/artifact/Ce9B5yb2Q7hKQBnhGGZqHp)
*made with 🩷 because terminal art is cool*
