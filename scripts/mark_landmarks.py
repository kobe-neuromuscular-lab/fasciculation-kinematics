"""Step 3 - mark the five temporal landmarks on each velocity waveform (paper Figure 2c,
Video S4).

    python scripts/mark_landmarks.py work/            # interactive, all unmarked segments
    python scripts/mark_landmarks.py work/ --set coherent_01197 3 7 12.5 21 33

Interactive: moving the cursor over the curve shows the matching ultrasound
frame. Click five times in order - Start, Peak contraction, Reversal, Peak
relaxation, End - drag a line to adjust it, then close the window to save.
Landmark positions are fractional frames on the smoothed curve.

Results go to <work>/landmarks.csv (one row per segment, re-marking overwrites).
"""

import argparse
import glob
import os
import sys

import cv2
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from fasckin import temporal  # noqa: E402

COLORS = ["green", "orange", "purple", "brown", "black"]


def mark(wave, video_path, title):
    import matplotlib.pyplot as plt

    xs, ys = temporal.smooth_curve(wave.index.values, wave.values)
    cap = cv2.VideoCapture(video_path)
    frames = []
    while True:
        ok, f = cap.read()
        if not ok:
            break
        frames.append(cv2.cvtColor(f, cv2.COLOR_BGR2RGB))
    cap.release()

    fig, (ax, ax_v) = plt.subplots(1, 2, figsize=(15, 6), gridspec_kw=dict(width_ratios=[1.2, 1]))
    ax.plot(xs, ys, color="red", lw=2)
    ax.set_xlabel("Frame")
    ax.set_ylabel("Displacement per frame (px), mean of 5 points")
    cursor = ax.axvline(0, color="k", ls="--", alpha=0.6)
    img = ax_v.imshow(frames[1])
    ax_v.set_axis_off()
    pos, lines, drag = {}, {}, {"name": None}
    names = temporal.LANDMARKS

    def title_update():
        nxt = next((n for n in names if n not in pos), None)
        ax.set_title(f"{title} - click: {nxt}" if nxt else f"{title} - drag to adjust, close to save")

    def show(x):
        # Row Frame = k is video frame k + 1 (see fasckin/tracking.py).
        img.set_data(frames[max(0, min(int(round(x)) + 1, len(frames) - 1))])

    def on_press(ev):
        if ev.inaxes is not ax or ev.xdata is None:
            return
        for n, ln in lines.items():
            if abs(ln.get_xdata()[0] - ev.xdata) < (xs.max() - xs.min()) * 0.02:
                drag["name"] = n
                return
        nxt = next((n for n in names if n not in pos), None)
        if nxt:
            pos[nxt] = ev.xdata
            lines[nxt] = ax.axvline(ev.xdata, color=COLORS[names.index(nxt)], lw=2, label=nxt)
            ax.legend(loc="upper right")
            title_update()
            fig.canvas.draw_idle()

    def on_move(ev):
        if ev.inaxes is not ax or ev.xdata is None:
            return
        x = float(np.clip(ev.xdata, xs.min(), xs.max()))
        if drag["name"]:
            pos[drag["name"]] = x
            lines[drag["name"]].set_xdata([x])
        cursor.set_xdata([x])
        show(x)
        fig.canvas.draw_idle()

    def on_release(ev):
        drag["name"] = None

    fig.canvas.mpl_connect("button_press_event", on_press)
    fig.canvas.mpl_connect("motion_notify_event", on_move)
    fig.canvas.mpl_connect("button_release_event", on_release)
    title_update()
    plt.show()
    return pos if len(pos) == len(names) else None


def save(work, name, fps, pos):
    row = dict(segment=name, **temporal.durations(pos, fps))
    path = os.path.join(work, "landmarks.csv")
    df = pd.read_csv(path) if os.path.exists(path) else pd.DataFrame()
    if len(df):
        df = df[df["segment"] != name]
    pd.concat([df, pd.DataFrame([row])], ignore_index=True).to_csv(path, index=False)
    print(f"{name}: total {row['total_ms']:.1f} ms, contraction {row['contraction_ms']:.1f} ms, "
          f"relaxation {row['relaxation_ms']:.1f} ms")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("work")
    ap.add_argument("--set", nargs=6, metavar=("SEGMENT", "START", "PEAK_C", "REVERSAL", "PEAK_R", "END"),
                    help="record landmarks (in frames) without the GUI")
    ap.add_argument("--redo", action="store_true", help="also show segments already marked")
    a = ap.parse_args()

    spatial = pd.read_csv(os.path.join(a.work, "spatial.csv")).set_index("segment")
    if a.set:
        name, vals = a.set[0], [float(v) for v in a.set[1:]]
        save(a.work, name, spatial.loc[name, "fps"], dict(zip(temporal.LANDMARKS, vals)))
        return
    done_path = os.path.join(a.work, "landmarks.csv")
    done = set(pd.read_csv(done_path)["segment"]) if os.path.exists(done_path) and not a.redo else set()
    for wf in sorted(glob.glob(os.path.join(a.work, "waveforms", "*.csv"))):
        name = os.path.splitext(os.path.basename(wf))[0]
        if name in done:
            continue
        wave = pd.read_csv(wf, index_col="Frame")["Length"]
        pos = mark(wave, os.path.join(a.work, "segments", name + ".avi"), name)
        if pos is None:
            print(f"{name}: not all five landmarks marked - skipped")
            continue
        save(a.work, name, spatial.loc[name, "fps"], pos)


if __name__ == "__main__":
    main()
