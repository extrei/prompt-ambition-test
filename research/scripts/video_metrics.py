"""Objective style metrics measured from the rendered videos (160x90, 10 fps).

usage: python3 video_metrics.py P1=<video.mp4> P2=<video.mp4> P3=<video.mp4> > ../data/video_metrics.json

  motion      mean absolute pixel change between consecutive samples (0-255)
  cuts        samples whose change is > 28 and > 3x the local 9-sample mean (hard cuts)
  still_pct   share of samples whose change is < 1.0 (the picture barely moves)
  colorful    Hasler & Suesstrunk (2003) colourfulness, mean per frame
  hue_bins    of 24 hue bins, how many hold > 2% of saturated pixels (S > .35, V > 60)
"""
import json, subprocess, sys
import numpy as np

W, H, FPS = 160, 90, 10

def analyse(path):
    raw = subprocess.run(['ffmpeg', '-v', 'error', '-i', path, '-vf', f'fps={FPS},scale={W}:{H}', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-'],
                         capture_output=True, check=True).stdout
    a = np.frombuffer(raw, np.uint8).reshape(-1, H, W, 3).astype(np.float32)
    diff = np.abs(a[1:] - a[:-1]).mean(axis=(1, 2, 3))
    cuts = int(((diff > 28) & (diff > 3 * np.convolve(diff, np.ones(9) / 9, 'same'))).sum())
    R, G, B = a[..., 0], a[..., 1], a[..., 2]
    rg, yb = R - G, .5 * (R + G) - B
    colorful = np.hypot(rg.std(axis=(1, 2)), yb.std(axis=(1, 2))) + .3 * np.hypot(rg.mean(axis=(1, 2)), yb.mean(axis=(1, 2)))
    mx, mn = a.max(-1), a.min(-1)
    sat = (mx - mn) / (mx + 1e-3)
    px = a[::5].reshape(-1, 3) / 255
    keep = (sat[::5].reshape(-1) > .35) & (mx[::5].reshape(-1) > 60)
    px = px[keep]
    r, g, b = px.T; M, m = px.max(1), px.min(1); d = M - m + 1e-6
    hue = np.where(M == r, ((g - b) / d) % 6, np.where(M == g, (b - r) / d + 2, (r - g) / d + 4)) * 60
    p = np.histogram(hue, bins=24, range=(0, 360))[0]; p = p / p.sum()
    secs = len(a) // FPS
    return dict(
        cuts=cuts, motion=round(float(diff.mean()), 2), still_pct=round(float((diff < 1).mean() * 100), 1),
        colorful=round(float(colorful.mean()), 1), hue_bins=int((p > .02).sum()),
        motion_sec=[round(float(diff[i * FPS:(i + 1) * FPS].mean()), 2) for i in range(secs)],
    )

if __name__ == '__main__':
    out = {}
    for arg in sys.argv[1:]:
        k, p = arg.split('=', 1)
        out[k] = analyse(p)
    json.dump(out, sys.stdout)
