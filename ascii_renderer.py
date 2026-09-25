#!/usr/bin/env python3
"""RGB ASCII video renderer — plays a video as colored ASCII art in the terminal.

Requires: pip install -r requirements.txt
"""

import argparse
import os
import shutil
import subprocess
import sys
import tempfile
import time

import cv2
import numpy as np

ASCII_SHORT = " .:-=+*#%@"
ASCII_LONG  = " .`-_':,;^=+/\"|)\\<>)iv%xclrs{*}I?!][1taeo7zjLunT#JCwfy325F6gpSD4VXbYkEZO0mqhd8PHQGUAlk@W$B#"

CHAR_ASPECT = 0.5   # terminal glyphs are ~2x taller than wide
COLOR_BITS  = 5     # quantise each RGB channel to 2^5=32 levels (reduces unique ANSI codes)


def enable_windows_ansi():
    if os.name == "nt":
        try:
            import ctypes
            kernel32 = ctypes.windll.kernel32
            kernel32.SetConsoleMode(kernel32.GetStdHandle(-11), 7)
        except Exception:
            os.system("")


def get_frame_data(frame, cols, rows, ramp):
    """Resize frame and return (char_grid, quantised_rgb) as numpy arrays."""
    small = cv2.resize(frame, (cols, rows), interpolation=cv2.INTER_AREA)
    rgb   = small[:, :, ::-1].astype(np.uint8)                     # BGR→RGB

    # Quantise colours → fewer unique ANSI codes per row
    shift = 8 - COLOR_BITS
    qrgb  = (rgb >> shift) << shift

    gray  = 0.299 * rgb[..., 0] + 0.587 * rgb[..., 1] + 0.114 * rgb[..., 2]
    idx   = (gray * ((len(ramp) - 1) / 255.0)).astype(np.uint8)
    np.clip(idx, 0, len(ramp) - 1, out=idx)

    ramp_arr  = np.array(list(ramp), dtype="U1")
    char_grid = ramp_arr[idx]                                        # shape (rows, cols)
    return char_grid, qrgb


def full_frame(chars, colors, cols, rows):
    """Render every cell — used for the very first frame."""
    r, g, b = colors[..., 0], colors[..., 1], colors[..., 2]
    lines = []
    for y in range(rows):
        row_r, row_g, row_b = r[y], g[y], b[y]
        row_chars = chars[y]
        changed = np.ones(cols, dtype=bool)
        changed[1:] = (
            (row_r[1:] != row_r[:-1]) |
            (row_g[1:] != row_g[:-1]) |
            (row_b[1:] != row_b[:-1])
        )
        ci_arr = np.where(changed)[0]
        parts  = []
        for ci in range(len(ci_arr)):
            i   = ci_arr[ci]
            end = int(ci_arr[ci + 1]) if ci + 1 < len(ci_arr) else cols
            parts.append(f"\033[38;2;{row_r[i]};{row_g[i]};{row_b[i]}m")
            parts.append("".join(row_chars[i:end]))
        parts.append("\033[0m")
        lines.append("".join(parts))
    return "\033[H" + "\n".join(lines)


def delta_frame(prev_chars, prev_colors, cur_chars, cur_colors, cols, rows):
    """Only emit escape codes for cells that changed since the previous frame.
    Uses absolute cursor positioning (\033[row;colH) to skip unchanged runs,
    which keeps the output tiny (~2–4 KB vs ~25 KB for a full redraw)."""
    parts = ["\033[H"]
    for y in range(rows):
        row_changed = (cur_chars[y] != prev_chars[y]) | np.any(
            cur_colors[y] != prev_colors[y], axis=1
        )
        if not row_changed.any():
            continue
        xs      = np.where(row_changed)[0]
        prev_x  = -2                               # force first cursor jump
        cr, cg, cb = cur_colors[y, :, 0], cur_colors[y, :, 1], cur_colors[y, :, 2]
        for xi in range(len(xs)):
            x = xs[xi]
            if x != prev_x + 1:
                parts.append(f"\033[{y + 1};{x + 1}H")
            parts.append(f"\033[38;2;{cr[x]};{cg[x]};{cb[x]}m{cur_chars[y, x]}")
            prev_x = x
    parts.append("\033[0m")
    return "".join(parts)


# ── Audio helpers ─────────────────────────────────────────────────────────────

def prepare_audio(video_path):
    try:
        import imageio_ffmpeg
        ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        return None

    tmp      = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
    wav_path = tmp.name
    tmp.close()

    cmd = [
        ffmpeg_exe, "-y", "-i", video_path,
        "-vn", "-ac", "2", "-ar", "44100", "-f", "wav", wav_path,
    ]
    try:
        subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
        return wav_path
    except Exception:
        return None


def start_audio(wav_path):
    try:
        import pygame
    except Exception:
        return None
    try:
        pygame.mixer.init()
        pygame.mixer.music.load(wav_path)
        pygame.mixer.music.play()
        return pygame
    except Exception:
        return None


# ── Main render loop ──────────────────────────────────────────────────────────

def render_video(video_path, cols=160, fps=None, ramp=ASCII_SHORT, with_audio=True):
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print(f"Error: cannot open video '{video_path}'")
        sys.exit(1)

    video_fps  = cap.get(cv2.CAP_PROP_FPS) or 24
    target_fps = fps or video_fps
    frame_delay = 1.0 / target_fps

    video_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    video_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    term = shutil.get_terminal_size((cols, 40))
    cols = min(cols, term.columns - 1)
    aspect_rows = int(cols * (video_h / video_w) * CHAR_ASPECT)
    rows = max(8, min(aspect_rows, term.lines - 1))

    enable_windows_ansi()
    print(f"[ASCII Renderer] {cols}×{rows} @ {target_fps:.1f} fps — Ctrl+C to quit")
    time.sleep(0.5)

    wav_path = audio = None
    if with_audio:
        print("[Audio] preparing…", flush=True)
        wav_path = prepare_audio(video_path)
        if wav_path:
            audio = start_audio(wav_path)
        if not audio:
            msg = ("imageio-ffmpeg not found" if not wav_path else "pygame not found")
            print(f"[Audio] {msg} — running without audio", flush=True)
        time.sleep(0.5)

    # Use a raw binary stdout for faster writes
    raw_out = sys.stdout.buffer if hasattr(sys.stdout, "buffer") else open(
        sys.stdout.fileno(), "wb", closefd=False
    )

    sys.stdout.write("\033[?25l\033[2J\033[H")
    sys.stdout.flush()

    frame_count = skipped = 0
    start_time  = time.monotonic()
    next_time   = start_time + frame_delay

    prev_chars = prev_colors = None

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                break

            now = time.monotonic()

            # Drop frame if we're more than one frame behind
            if now > next_time + frame_delay:
                skipped  += 1
                next_time = now + frame_delay
                continue

            cur_chars, cur_colors = get_frame_data(frame, cols, rows, ramp)

            if prev_chars is None:
                output = full_frame(cur_chars, cur_colors, cols, rows)
            else:
                output = delta_frame(prev_chars, prev_colors, cur_chars, cur_colors, cols, rows)

            raw_out.write(output.encode())
            raw_out.flush()

            prev_chars, prev_colors = cur_chars, cur_colors
            frame_count += 1

            remaining = next_time - time.monotonic()
            if remaining > 0.001:
                time.sleep(remaining)
            next_time += frame_delay

    except KeyboardInterrupt:
        pass
    finally:
        cap.release()
        sys.stdout.write("\033[?25h\033[0m\033[2J\033[H")
        sys.stdout.flush()
        if audio:
            try:
                audio.mixer.music.stop()
                audio.mixer.quit()
            except Exception:
                pass
        if wav_path:
            try:
                os.remove(wav_path)
            except Exception:
                pass

        total      = time.monotonic() - start_time
        fps_actual = frame_count / total if total > 0 else 0
        print(f"[Done] {frame_count} rendered, {skipped} skipped in {total:.1f}s ({fps_actual:.1f} fps)")


# ── Entry point ───────────────────────────────────────────────────────────────

def find_default_video():
    for name in os.listdir("."):
        if name.lower().endswith((".mp4", ".mkv", ".avi", ".mov", ".webm", ".m4v", ".gif")):
            return name
    return None


def main():
    parser = argparse.ArgumentParser(description="RGB ASCII Video Renderer")
    parser.add_argument("video",      nargs="?", help="Path to video file (auto-detected if omitted)")
    parser.add_argument("--cols",     type=int,   default=160, help="ASCII columns (default: 160)")
    parser.add_argument("--fps",      type=float, default=None, help="FPS cap (default: match video)")
    parser.add_argument("--detailed", action="store_true",      help="Use longer ASCII ramp")
    parser.add_argument("--no-audio", action="store_true",      help="Disable audio")
    args = parser.parse_args()

    video = args.video or find_default_video()
    if not video:
        print("Error: no video file found. Pass a path: python ascii_renderer.py video.mp4")
        sys.exit(1)

    ramp = ASCII_LONG if args.detailed else ASCII_SHORT
    render_video(video, cols=args.cols, fps=args.fps, ramp=ramp, with_audio=not args.no_audio)


if __name__ == "__main__":
    main()
