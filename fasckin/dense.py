"""Stage 2 - ultra-dense tracking of a 240 x 240 px field (paper Methods 2.2.2 and 2.3.1).

Every pixel of the field is tracked (57,600 points). For the spatial metrics
only the first 13 frame steps (Frame 0-12) are needed, because the peak
frame is searched in Frame 5-9; the temporal waveform is obtained afterwards by
re-tracking a subset of points over the whole segment (see ``temporal.py``).
"""

import numpy as np

from .tracking import DENSE_LK_PARAMS, read_gray_frames, track_points

HALF_SIZE = 120  # 240 x 240 px field
# The field centre is clipped so the field stays inside the imaging area of the
# LOGIQ e export (686 x 528 px). Adjust for other scanners/exports.
CENTER_X_RANGE = (235, 452)
CENTER_Y_RANGE = (170, 266)
N_STEPS = 13


def field_bounds(cx, cy, width, height, half=HALF_SIZE,
                 x_range=CENTER_X_RANGE, y_range=CENTER_Y_RANGE):
    cx = float(np.clip(cx, *x_range))
    cy = float(np.clip(cy, *y_range))
    x0, y0 = max(0, int(cx - half)), max(0, int(cy - half))
    x1, y1 = min(width, int(cx + half)), min(height, int(cy + half))
    return x0, y0, x1, y1


def track_dense(segment_path, cx, cy, n_steps=N_STEPS, lk_params=DENSE_LK_PARAMS, **bounds_kw):
    """Track every pixel of the field centred on the epicentre (cx, cy), full-frame pixels.

    Returns (df, fps, bounds). ``df`` has columns Frame, Point ID, X, Y, Length, angle
    with full-frame coordinates.
    """
    frames, fps = read_gray_frames(segment_path, max_frames=n_steps + 1)
    h, w = frames[0].shape
    x0, y0, x1, y1 = field_bounds(cx, cy, w, h, **bounds_kw)
    pts = [(x, y) for y in range(y0, y1) for x in range(x0, x1)]
    df = track_points(frames, pts, lk_params=lk_params, n_steps=n_steps, with_angle=True)
    return df, fps, (x0, y0, x1, y1)
