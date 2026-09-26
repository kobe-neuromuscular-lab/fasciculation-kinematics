"""Pyramidal Lucas-Kanade point tracking shared by every stage of the pipeline.

Output convention (kept identical to the scripts used for the paper):

* Row ``Frame = k`` holds the position of each point in video frame ``k + 1``
  (the first video frame is only the reference image).
* ``Length`` is the Euclidean displacement in pixels between the positions at
  ``Frame = k - 1`` and ``Frame = k``, i.e. the displacement per frame
  interval. ``Length`` is 0 at ``Frame = 0`` by definition.
* ``angle`` (optional) is ``atan2(dy, dx)`` of that same displacement, in
  radians, image coordinates (y points down). It is 0 at ``Frame = 0``.
"""

import cv2
import numpy as np
import pandas as pd

# Parameters reported in the paper (Methods 2.3.1).
DENSE_LK_PARAMS = dict(
    winSize=(50, 50),
    maxLevel=30,
    criteria=(cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 30, 0.01),
)


def read_gray_frames(video_path, max_frames=None, crop=None):
    """Read a video as a list of grayscale frames.

    crop: optional (x0, y0, x1, y1) applied to every frame before conversion.
    """
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        raise IOError(f"Cannot open video: {video_path}")
    fps = cap.get(cv2.CAP_PROP_FPS)
    frames = []
    while max_frames is None or len(frames) < max_frames:
        ok, frame = cap.read()
        if not ok:
            break
        if crop is not None:
            x0, y0, x1, y1 = crop
            frame = frame[y0:y1, x0:x1]
        frames.append(cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY))
    cap.release()
    return frames, fps


def track_points(frames, points, lk_params=None, n_steps=None, with_angle=False, drop_lost=True):
    """Track ``points`` (N x 2, x/y in pixels) through ``frames``.

    n_steps: number of frame-to-frame steps to track (default: all). The paper's
    dense stage used 13 steps (Frame 0-12).

    drop_lost: if True, a point whose LK status becomes 0 is dropped from then
    on but keeps its original ``Point ID``. (The original dense-stage scripts
    re-numbered the surviving points instead; in the recordings analysed in the
    paper no point was lost in that stage, so both give identical output.) If
    False, every point is kept with OpenCV's best estimate, as the sparse
    stage did.
    """
    lk_params = lk_params or DENSE_LK_PARAMS
    p0 = np.asarray(points, dtype=np.float32).reshape(-1, 1, 2)
    ids = np.arange(len(p0))
    prev_xy = None
    old = frames[0]
    last = len(frames) - 1 if n_steps is None else min(n_steps, len(frames) - 1)
    chunks = []
    for k in range(last):
        new = frames[k + 1]
        p1, st, _ = cv2.calcOpticalFlowPyrLK(old, new, p0, None, **lk_params)
        if p1 is None:
            break
        keep = st.ravel() == 1 if drop_lost else np.ones(len(ids), dtype=bool)
        xy = p1.reshape(-1, 2)[keep]
        ids = ids[keep]
        if prev_xy is None:
            d = np.zeros_like(xy)
        else:
            d = xy - prev_xy[keep]
        chunk = {
            "Frame": np.full(len(ids), k),
            "Point ID": ids,
            "X": xy[:, 0],
            "Y": xy[:, 1],
            "Length": np.hypot(d[:, 0], d[:, 1]),
        }
        if with_angle:
            chunk["angle"] = np.where(k == 0, 0.0, np.arctan2(d[:, 1], d[:, 0]))
        chunks.append(pd.DataFrame(chunk))
        prev_xy = xy
        p0 = xy.reshape(-1, 1, 2)
        old = new
    return pd.concat(chunks, ignore_index=True)
