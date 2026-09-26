"""Stage 1 - sparse grid tracking to locate a fasciculation in space and time
(paper Methods 2.2.1, Figure 1).

The full recording was first cut into overlapping 2-s windows (0-2 s,
0.5-2.5 s, 1-3 s, ...; see ``split_windows``). Each window was tracked on a
4-pixel grid; the velocity-time curves were displayed, and the peak frame and
epicentre were read off them.

In the original workflow the investigator clicked the epicentre on the video
and typed the peak frame after inspecting the curves (``scripts/pick_peak.py``
reproduces that tool). ``find_peak`` is the automated rule described in the
paper: the peak is the frame with the largest integrated velocity, and the
epicentre is the point with the largest displacement at that frame.
"""

import os

import cv2
import numpy as np

from .tracking import read_gray_frames, track_points

# 4-px grid over the imaging area of the LOGIQ e export (686 x 528 px) used in
# the paper, in full-frame pixels (10,620 points). Adjust for other scanners.
SPARSE_GRID = dict(step=4, x_range=(110, 580), y_range=(40, 400))
SPARSE_LK_PARAMS = dict(
    winSize=(50, 50),
    maxLevel=30,
    criteria=(cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 30, 0.01),
)


def split_windows(video_path, out_dir, window_s=2.0, hop_s=0.5):
    """Cut ``video_path`` into overlapping windows named ``<stem>_<n>.avi`` (n = 1, 2, ...).

    Window n starts at (n - 1) * hop_s seconds.
    """
    os.makedirs(out_dir, exist_ok=True)
    stem = os.path.splitext(os.path.basename(video_path))[0]
    cap = cv2.VideoCapture(str(video_path))
    fps = cap.get(cv2.CAP_PROP_FPS)
    size = (int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)), int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)))
    frames = []
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        frames.append(frame)
    cap.release()
    paths = []
    n_win, hop, n = int(round(window_s * fps)), hop_s * fps, 0
    while int(round(n * hop)) < len(frames):
        start = int(round(n * hop))
        path = os.path.join(out_dir, f"{stem}_{n + 1}.avi")
        writer = cv2.VideoWriter(path, cv2.VideoWriter_fourcc(*"XVID"), fps, size)
        for frame in frames[start:start + n_win]:
            writer.write(frame)
        writer.release()
        paths.append(path)
        n += 1
    return paths


def grid_points(step, x_range, y_range):
    return np.array([(x, y) for y in range(*y_range, step) for x in range(*x_range, step)],
                    dtype=np.float32)


def track_sparse(video_path, grid=SPARSE_GRID, lk_params=SPARSE_LK_PARAMS):
    """Track a sparse grid over the whole window.

    Returns (df, fps) with full-frame coordinates. (The original script saved
    x - 70, i.e. relative to the left edge of the imaging area.)
    """
    frames, fps = read_gray_frames(video_path)
    pts = grid_points(grid["step"], grid["x_range"], grid["y_range"])
    return track_points(frames, pts, lk_params=lk_params, drop_lost=False), fps


def find_peak(df, roi=None):
    """Automated peak/epicentre rule of the paper.

    roi: optional (cx, cy, half) in full-frame pixels restricting the points
    considered (the original tool used a 122 x 122 px box around the clicked
    point). Returns dict(frame, x, y) with x/y in full-frame pixels.
    """
    if roi is not None:
        cx, cy, half = roi
        f0 = df[df["Frame"] == 0]
        inside = f0[(abs(f0["X"] - cx) <= half) & (abs(f0["Y"] - cy) <= half)]
        df = df[df["Point ID"].isin(inside["Point ID"])]
    integrated = df.groupby("Frame")["Length"].mean()
    peak = int(integrated.idxmax())
    at_peak = df[df["Frame"] == peak]
    top = at_peak.loc[at_peak["Length"].idxmax()]
    start = df[(df["Frame"] == 0) & (df["Point ID"] == top["Point ID"])].iloc[0]
    return dict(frame=peak, x=int(round(start["X"])), y=int(round(start["Y"])))


def peak_time_s(window_index, peak_frame, fps, hop_s=0.5):
    """Time of the peak in the full recording (window_index starts at 1)."""
    return (window_index - 1) * hop_s + peak_frame / fps
