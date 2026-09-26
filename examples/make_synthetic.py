"""Make synthetic B-mode-like recordings containing one "fasciculation" each, so the
pipeline can be run without patient data.

    python examples/make_synthetic.py examples/data

Writes coherent.avi (fibres move together, high directional anisotropy) and
heterogeneous.avi (neighbouring patches move in different directions, low
anisotropy), 686 x 528 px, 43 fps, 3 s, with the twitch peaking at ~1.25 s.
"""

import os
import sys

import cv2
import numpy as np
from scipy.ndimage import gaussian_filter

W, H, FPS, SECONDS = 686, 528, 43, 3.0
AREA = (110, 40, 580, 400)  # imaging area x0, y0, x1, y1


def speckle(seed):
    rng = np.random.default_rng(seed)
    img = gaussian_filter(rng.random((H, W)), 1.2)
    img = (img - img.min()) / (img.max() - img.min())
    img = gaussian_filter(rng.random((H, W)) ** 3, 0.8) * 0.6 + img * 0.4
    # horizontal fascicle-like bands
    img *= 0.75 + 0.25 * np.sin(np.arange(H)[:, None] / 7.0)
    out = np.zeros((H, W), np.float32)
    x0, y0, x1, y1 = AREA
    out[y0:y1, x0:x1] = img[y0:y1, x0:x1] * 220
    return out


def twitch_profile(t, onset=1.10, rise=0.20, relax=0.50, amp=6.0):
    """Displacement (px) of the moving tissue: smooth rise, slower return."""
    s = t - onset
    if s <= 0:
        return 0.0
    if s <= rise:
        return amp * 0.5 * (1 - np.cos(np.pi * s / rise))
    if s <= rise + relax:
        return amp * 0.5 * (1 + np.cos(np.pi * (s - rise) / relax))
    return 0.0


def make(path, heterogeneous, seed=0, center=(340, 220), amp=6.0):
    base = speckle(seed)
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    cx, cy = center
    envelope = np.exp(-(((xx - cx) / 45.0) ** 2 + ((yy - cy) / 22.0) ** 2))
    if heterogeneous:
        rng = np.random.default_rng(seed + 1)
        # each ~20-px patch moves in its own direction
        theta = rng.uniform(-np.pi, np.pi, (H // 20 + 1, W // 20 + 1)).astype(np.float32)
        theta = cv2.resize(theta, (W, H), interpolation=cv2.INTER_NEAREST)
    else:
        theta = np.full((H, W), 0.15, np.float32)
    ux, uy = np.cos(theta) * envelope, np.sin(theta) * envelope
    writer = cv2.VideoWriter(path, cv2.VideoWriter_fourcc(*"XVID"), FPS, (W, H))
    rng = np.random.default_rng(seed + 2)
    for k in range(int(SECONDS * FPS)):
        a = twitch_profile(k / FPS, amp=amp)
        frame = cv2.remap(base, xx - a * ux, yy - a * uy, cv2.INTER_LINEAR)
        frame = np.clip(frame + rng.normal(0, 1.0, frame.shape), 0, 255).astype(np.uint8)
        writer.write(cv2.cvtColor(frame, cv2.COLOR_GRAY2BGR))
    writer.release()
    print("wrote", path)


if __name__ == "__main__":
    out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(__file__), "data")
    os.makedirs(out, exist_ok=True)
    make(os.path.join(out, "coherent.avi"), heterogeneous=False, seed=0)
    make(os.path.join(out, "heterogeneous.avi"), heterogeneous=True, seed=10, amp=10.0)
