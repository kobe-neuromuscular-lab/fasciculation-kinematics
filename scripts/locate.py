"""Step 1 - locate each event (peak frame and centre) with sparse grid tracking.

    python scripts/locate.py recording.avi --out work --windows 6 --review     # as in the paper
    python scripts/locate.py recording.avi --out work --windows 6              # automatic

The recording is cut into 2-s windows (window n starts at (n - 1) x 0.5 s) and
each selected window is tracked on a 4-px grid. Choose the windows by watching
the video: in the paper, recordings were screened visually first.

--review reproduces the tool used for the paper:
  1. The window plays in a loop. Click the centre of the moving region. The
     122 x 122 px box (green) whose points are plotted next and the 240 x 240 px
     field (red) that stage 2 will track are drawn. Click again to move them;
     press Enter or close the window to confirm.
  2. The per-frame displacement of every grid point inside the green box is
     plotted, one line per point, coloured by position. The video keeps playing
     next to it. Click the plot at the peak frame (the first, contraction peak);
     press Enter or close the window to confirm.
  The clicked position becomes the centre of the stage-2 field.

Without --review the peak frame is the frame with the largest mean displacement
over the whole grid, and the centre is the point that moved most at that frame.

Appends one row per window to <out>/peaks.csv.
"""

import argparse
import os
import sys

import cv2
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from fasckin import config, sparse  # noqa: E402


def read_rgb(path):
    cap = cv2.VideoCapture(path)
    fps = cap.get(cv2.CAP_PROP_FPS) or 30
    frames = []
    while True:
        ok, f = cap.read()
        if not ok:
            break
        frames.append(cv2.cvtColor(f, cv2.COLOR_BGR2RGB))
    cap.release()
    return frames, fps


def draw_boxes(ax, cx, cy, roi_half, field_half, artists):
    from matplotlib.patches import Rectangle

    for a in artists:
        a.remove()
    artists.clear()
    artists.append(ax.add_patch(Rectangle((cx - field_half, cy - field_half), 2 * field_half,
                                          2 * field_half, fill=False, ec="#ff6464", lw=1.5)))
    artists.append(ax.add_patch(Rectangle((cx - roi_half, cy - roi_half), 2 * roi_half, 2 * roi_half,
                                          fill=False, ec="#00ff00", lw=2)))


def play(fig, img, frames, fps, label=None):
    """Loop the video in ``img``; returns the animation object (keep a reference)."""
    from matplotlib.animation import FuncAnimation

    def update(k):
        img.set_data(frames[k])
        if label is not None:
            label.set_text(f"Frame {k}")
        return (img,) if label is None else (img, label)

    return FuncAnimation(fig, update, frames=len(frames), interval=1000 / fps, blit=False)


def review(window_path, df, cfg):
    """Two-step interactive choice of centre and peak frame. Returns dict or None."""
    import matplotlib.pyplot as plt
    from matplotlib.colors import hsv_to_rgb
    from matplotlib.ticker import MultipleLocator

    rv, field_half = cfg["review"], cfg["dense"]["half_size"]
    frames, fps = read_rgb(window_path)

    # Step 1: click the centre on the looping video
    state = {}
    fig, ax = plt.subplots(figsize=(9, 7))
    img = ax.imshow(frames[0])
    label = ax.text(10, 30, "", color="yellow", fontsize=12)
    ax.set_title("Click the centre of the moving region, then press Enter or close")
    ax.set_axis_off()
    boxes = []

    def on_click(ev):
        if ev.inaxes is ax and ev.xdata is not None:
            state["x"] = int(np.clip(ev.xdata, *rv["click_x_range"]))
            state["y"] = int(np.clip(ev.ydata, *rv["click_y_range"]))
            draw_boxes(ax, state["x"], state["y"], rv["roi_half"], field_half, boxes)
            ax.set_title(f"Centre ({state['x']}, {state['y']}) - press Enter or close to confirm")
            fig.canvas.draw_idle()

    fig.canvas.mpl_connect("button_press_event", on_click)
    fig.canvas.mpl_connect("key_press_event", lambda ev: plt.close(fig) if ev.key == "enter" else None)
    anim = play(fig, img, frames, fps, label)  # noqa: F841
    plt.show()
    if "x" not in state:
        return None

    # Step 2: per-point curves inside the ROI, pick the peak frame
    cx, cy, half = state["x"], state["y"], rv["roi_half"]
    f0 = df[df["Frame"] == 0]
    ids = f0[(abs(f0["X"] - cx) <= half) & (abs(f0["Y"] - cy) <= half)]
    if ids.empty:
        print("No grid points inside the box.")
        return None
    (x0, x1), (y0, y1) = rv["color_x_range"], rv["color_y_range"]
    hue = ((ids["X"] - x0) / (x1 - x0)).clip(0, 1).to_numpy() / 2
    val = ((ids["Y"] - y0) / (y1 - y0)).clip(0, 1).to_numpy()
    colors = hsv_to_rgb(np.stack([hue, np.ones_like(hue), val], axis=-1))
    sub = df[df["Point ID"].isin(ids["Point ID"])]

    fig, (ax_c, ax_v) = plt.subplots(1, 2, figsize=(16, 6), gridspec_kw=dict(width_ratios=[1.2, 1]))
    for pid, col in zip(ids["Point ID"], colors):
        s = sub[sub["Point ID"] == pid]
        ax_c.plot(s["Frame"], s["Length"], color=col, lw=0.8)
    ax_c.set_xlabel("Frame")
    ax_c.set_ylabel("Displacement per frame (px)")
    ax_c.xaxis.set_major_locator(MultipleLocator(5))
    ax_c.grid(True, alpha=0.4)
    ax_c.set_title(f"{len(ids)} points around ({cx}, {cy}) - click the peak frame")
    vline = ax_c.axvline(-1, color="k", ls="--")
    img = ax_v.imshow(frames[0])
    label = ax_v.text(10, 30, "", color="yellow", fontsize=12)
    draw_boxes(ax_v, cx, cy, half, field_half, [])
    ax_v.set_axis_off()

    def on_click2(ev):
        if ev.inaxes is ax_c and ev.xdata is not None:
            state["frame"] = int(round(ev.xdata))
            vline.set_xdata([state["frame"]])
            ax_c.set_title(f"Peak frame {state['frame']} - press Enter or close to confirm")
            fig.canvas.draw_idle()

    fig.canvas.mpl_connect("button_press_event", on_click2)
    fig.canvas.mpl_connect("key_press_event", lambda ev: plt.close(fig) if ev.key == "enter" else None)
    anim2 = play(fig, img, frames, fps, label)  # noqa: F841
    plt.show()
    if "frame" not in state:
        return None
    return dict(frame=state["frame"], x=cx, y=cy)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("recording")
    ap.add_argument("--out", required=True)
    ap.add_argument("--windows", type=int, nargs="*", help="window numbers to analyse (1-based)")
    ap.add_argument("--review", action="store_true", help="choose centre and peak interactively")
    ap.add_argument("--config", help="JSON settings file (see configs/)")
    a = ap.parse_args()

    cfg = config.load_config(a.config)
    sp = cfg["sparse"]
    grid = dict(step=sp["grid_step"], x_range=sp["x_range"], y_range=sp["y_range"])
    stem = os.path.splitext(os.path.basename(a.recording))[0]
    paths = sparse.split_windows(a.recording, os.path.join(a.out, "windows"), sp["window_s"], sp["hop_s"])
    rows = []
    for n, path in enumerate(paths, start=1):
        if a.windows and n not in a.windows:
            continue
        df, fps = sparse.track_sparse(path, grid=grid, lk_params=config.lk_params(cfg))
        pk = review(path, df, cfg) if a.review else sparse.find_peak(df)
        if pk is None:
            print(f"{stem} window {n}: skipped")
            continue
        t = sparse.peak_time_s(n, pk["frame"], fps, sp["hop_s"])
        rows.append(dict(recording=stem, source=os.path.abspath(a.recording), window=n, fps=fps,
                         peak_frame=pk["frame"], peak_s=t, x=pk["x"], y=pk["y"],
                         method="review" if a.review else "auto"))
        print(f"{stem} window {n}: peak frame {pk['frame']} ({t:.3f} s), centre ({pk['x']}, {pk['y']})")
    if rows:
        out_csv = os.path.join(a.out, "peaks.csv")
        pd.DataFrame(rows).to_csv(out_csv, mode="a", header=not os.path.exists(out_csv), index=False)


if __name__ == "__main__":
    main()
