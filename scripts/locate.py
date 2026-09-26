"""Step 1 - locate fasciculations in a recording with sparse grid tracking.

    python scripts/locate.py recording.avi --out work/            # all 2-s windows, automatic
    python scripts/locate.py recording.avi --out work/ --windows 5 12 --review

For each 2-s window (0-2 s, 0.5-2.5 s, ...) the sparse grid is tracked and the
peak frame / epicentre are found automatically. In the paper the recordings
were screened visually first, so pass ``--windows`` to analyse only the
windows that contain a fasciculation. ``--review`` shows the integrated
velocity curve and the video so the peak and epicentre can be checked or
corrected by clicking (this is how the paper's peaks were confirmed).

Appends one row per window to <out>/peaks.csv.
"""

import argparse
import os
import sys

import cv2
import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from fasckin import sparse  # noqa: E402


def review(window_path, df, auto):
    """Show curve + video. Click the curve to set the peak frame, click the image to set
    the epicentre, close the window to accept."""
    import matplotlib.pyplot as plt

    cap = cv2.VideoCapture(window_path)
    frames = []
    while True:
        ok, f = cap.read()
        if not ok:
            break
        frames.append(cv2.cvtColor(f, cv2.COLOR_BGR2RGB))
    cap.release()
    state = dict(auto)
    curve = df.groupby("Frame")["Length"].mean()
    fig, (ax_c, ax_v) = plt.subplots(1, 2, figsize=(14, 5), gridspec_kw=dict(width_ratios=[1, 1.3]))
    ax_c.plot(curve.index, curve.values, color="red")
    ax_c.set_xlabel("Frame")
    ax_c.set_ylabel("Mean displacement per frame (px)")
    vline = ax_c.axvline(state["frame"], color="k", ls="--")
    img = ax_v.imshow(frames[min(state["frame"] + 1, len(frames) - 1)])
    dot, = ax_v.plot([state["x"]], [state["y"]], "o", mfc="none", mec="lime", ms=14, mew=2)
    ax_v.set_axis_off()

    def redraw():
        vline.set_xdata([state["frame"]])
        img.set_data(frames[min(state["frame"] + 1, len(frames) - 1)])
        dot.set_data([state["x"]], [state["y"]])
        ax_c.set_title(f"peak frame {state['frame']}  epicentre ({state['x']}, {state['y']})")
        fig.canvas.draw_idle()

    def on_click(ev):
        if ev.inaxes is ax_c and ev.xdata is not None:
            state["frame"] = int(round(ev.xdata))
        elif ev.inaxes is ax_v and ev.xdata is not None:
            state["x"], state["y"] = int(round(ev.xdata)), int(round(ev.ydata))
        redraw()

    def on_move(ev):
        if ev.inaxes is ax_c and ev.xdata is not None:
            k = max(0, min(int(round(ev.xdata)) + 1, len(frames) - 1))
            img.set_data(frames[k])
            fig.canvas.draw_idle()

    fig.canvas.mpl_connect("button_press_event", on_click)
    fig.canvas.mpl_connect("motion_notify_event", on_move)
    redraw()
    plt.show()
    return state


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("recording")
    ap.add_argument("--out", required=True)
    ap.add_argument("--windows", type=int, nargs="*", help="window numbers to analyse (1-based)")
    ap.add_argument("--review", action="store_true")
    a = ap.parse_args()

    stem = os.path.splitext(os.path.basename(a.recording))[0]
    win_dir = os.path.join(a.out, "windows")
    paths = sparse.split_windows(a.recording, win_dir)
    rows = []
    for n, path in enumerate(paths, start=1):
        if a.windows and n not in a.windows:
            continue
        df, fps = sparse.track_sparse(path)
        pk = sparse.find_peak(df)
        if a.review:
            pk = review(path, df, pk)
        t = sparse.peak_time_s(n, pk["frame"], fps)
        rows.append(dict(recording=stem, source=os.path.abspath(a.recording), window=n, fps=fps,
                         peak_frame=pk["frame"], peak_s=t, x=pk["x"], y=pk["y"]))
        print(f"{stem} window {n}: peak frame {pk['frame']} ({t:.3f} s), epicentre ({pk['x']}, {pk['y']})")
    out_csv = os.path.join(a.out, "peaks.csv")
    pd.DataFrame(rows).to_csv(out_csv, mode="a", header=not os.path.exists(out_csv), index=False)


if __name__ == "__main__":
    main()
