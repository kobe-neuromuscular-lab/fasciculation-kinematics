"""Temporal analysis: velocity waveform and contraction/relaxation durations
(paper Methods 2.3.2, Figure 2c).

1. ``select_moving_points``: from the dense table, keep points whose per-frame
   displacement in Frame 4-10 reaches >= 30 % of the maximum.
2. ``retrack``: track only those points over the whole 1-s segment.
3. ``velocity_waveform``: take the 5 points with the largest displacement at
   the peak frame and average their per-frame displacement -> biphasic curve.
4. Mark the five landmarks (Start, Peak contraction, Reversal, Peak relaxation,
   End) - interactively with ``scripts/mark_landmarks.py`` as in the paper, or
   pass them in - and compute the durations with ``durations``.

Note: the curve shown to the observer (and on which landmarks were read) is
the raw 5-point mean interpolated with a cubic spline (x5) and a Gaussian
filter (sigma = 2 samples); see ``smooth_curve``.
"""

import numpy as np
import pandas as pd
from scipy.interpolate import interp1d
from scipy.ndimage import gaussian_filter1d

from .tracking import DENSE_LK_PARAMS, read_gray_frames, track_points

SELECT_FRAMES = (4, 10)
SELECT_FRACTION = 0.30
LANDMARKS = ("start", "peak_contraction", "reversal", "peak_relaxation", "end")


def select_moving_points(df_dense, frames=SELECT_FRAMES, fraction=SELECT_FRACTION):
    """Points (X, Y at their first qualifying frame) moving >= fraction * max in ``frames``."""
    sub = df_dense[(df_dense["Frame"] >= frames[0]) & (df_dense["Frame"] <= frames[1])]
    sel = sub[sub["Length"] >= sub["Length"].max() * fraction].sort_values(["Point ID", "Frame"])
    return sel.drop_duplicates(subset=["Point ID"], keep="first")[["Point ID", "X", "Y"]].reset_index(drop=True)


def retrack(segment_path, points, lk_params=DENSE_LK_PARAMS):
    """Track ``points`` (DataFrame with X, Y) through the whole segment.

    Point IDs in the result are 0..n-1 in the order of ``points``.
    """
    frames, fps = read_gray_frames(segment_path)
    return track_points(frames, points[["X", "Y"]].to_numpy(), lk_params=lk_params), fps


def velocity_waveform(df_track, frames=SELECT_FRAMES, n_top=5):
    """Mean per-frame displacement (px/frame) of the ``n_top`` fastest points.

    The points are those with the largest displacement at the frame, within
    ``frames``, where the single largest displacement occurs.
    Returns a Series indexed by Frame.
    """
    sub = df_track[(df_track["Frame"] >= frames[0]) & (df_track["Frame"] <= frames[1])]
    max_frame = sub.loc[sub["Length"].idxmax(), "Frame"]
    at = df_track[df_track["Frame"] == max_frame]
    top = at.nlargest(n_top, "Length")["Point ID"]
    return df_track[df_track["Point ID"].isin(top)].groupby("Frame")["Length"].mean()


def frame_top_average(df_track, n_top=5):
    """Per frame, the mean of the ``n_top`` largest displacements among all points
    (the thin blue reference curve of the original landmark tool)."""
    return df_track.groupby("Frame")["Length"].apply(lambda s: s.nlargest(n_top).mean())


def smooth_curve(frames, values, upsample=5, sigma=2.0):
    """Cubic-spline interpolation (x ``upsample``) followed by a Gaussian filter,
    as displayed in the landmark tool."""
    x = np.asarray(frames, dtype=float)
    y = np.asarray(values, dtype=float)
    if len(x) <= 3:
        return x, y
    xs = np.linspace(x.min(), x.max(), len(x) * upsample)
    ys = gaussian_filter1d(interp1d(x, y, kind="cubic")(xs), sigma=sigma)
    return xs, ys


def durations(landmarks, fps):
    """Durations in ms from landmark positions given in (fractional) frames.

    contraction = reversal - start, relaxation = end - reversal, total = end - start.
    """
    ms = 1000.0 / fps
    lm = {k: float(landmarks[k]) for k in LANDMARKS}
    return dict(
        contraction_ms=(lm["reversal"] - lm["start"]) * ms,
        relaxation_ms=(lm["end"] - lm["reversal"]) * ms,
        total_ms=(lm["end"] - lm["start"]) * ms,
        time_to_peak_contraction_ms=(lm["peak_contraction"] - lm["start"]) * ms,
        time_to_peak_relaxation_ms=(lm["peak_relaxation"] - lm["reversal"]) * ms,
        **{f"{k}_frame": v for k, v in lm.items()},
    )


def waveform_table(wave):
    xs, ys = smooth_curve(wave.index.values, wave.values)
    return pd.DataFrame({"Frame": xs, "Length_smoothed": ys})
