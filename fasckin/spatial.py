"""Spatial metrics at the peak fasciculation frame (paper Methods 2.3.3, Figure 3).

Input is the dense-tracking table from ``dense.track_dense``.
"""

import cv2
import numpy as np

PEAK_SEARCH_FRAMES = (5, 9)


def peak_frame(df, search=PEAK_SEARCH_FRAMES):
    """Frame (within ``search``) with the largest summed displacement over all points."""
    sub = df[(df["Frame"] >= search[0]) & (df["Frame"] <= search[1])]
    return int(sub.groupby("Frame")["Length"].sum().idxmax())


def directional_anisotropy(angles):
    """Length of the mean unit vector of ``angles`` (radians): 1 = all points move the
    same way, 0 = directions cancel out."""
    angles = np.asarray(angles, dtype=float)
    if angles.size == 0:
        return np.nan
    return float(np.hypot(np.cos(angles).mean(), np.sin(angles).mean()))


def echogenicity(frame_gray, x, y, half=20, bg_box=(90, 20, 600, 420)):
    """Mean grey level in a 40 x 40 px box around (x, y), and relative to the image mean.

    Pixels <= 5 or >= 240 (background, annotations) are ignored. ``bg_box`` is the
    (x0, y0, x1, y1) imaging area used as the reference for relative echogenicity.
    """
    h, w = frame_gray.shape
    xi, yi = int(x), int(y)
    roi = frame_gray[max(0, yi - half):min(h, yi + half), max(0, xi - half):min(w, xi + half)]
    roi = roi[(roi > 5) & (roi < 240)]
    bx0, by0, bx1, by1 = bg_box
    bg = frame_gray[by0:min(h, by1), bx0:min(w, bx1)]
    bg = bg[(bg > 5) & (bg < 240)]
    echo = float(roi.mean()) if roi.size else np.nan
    mean_bg = float(bg.mean()) if bg.size else np.nan
    return echo, echo / mean_bg if mean_bg else np.nan


def spatial_metrics(df, segment_path=None, cutoffs=(0.05, 0.15)):
    """Compute the per-segment spatial features.

    Returned keys (pixel / frame units; convert with ``units``):
      max_frame                  peak frame (Frame 5-9, largest summed displacement)
      peak_displacement_px       largest per-frame displacement at the peak frame
      active_area_fraction       share of points moving >= 15 % of the peak displacement
      directional_anisotropy_05  DA over points moving >= 5 % of the peak displacement
      directional_anisotropy_15  DA over points moving >= 15 % of the peak displacement
      epicenter_x, epicenter_y   position (Frame 1) of the point with the peak displacement
      echogenicity, relative_echogenicity  (only if ``segment_path`` is given)

    The DA values reported in the paper's Results/Table 2 are
    ``directional_anisotropy_05`` (see docs/paper_vs_code.md).
    """
    mf = peak_frame(df)
    at_peak = df[df["Frame"] == mf]
    peak = at_peak["Length"].max()
    top = at_peak.loc[at_peak["Length"].idxmax()]
    out = dict(max_frame=mf, peak_displacement_px=float(peak),
               active_area_fraction=float((at_peak["Length"] >= 0.15 * peak).mean()))
    for c in cutoffs:
        moving = at_peak[at_peak["Length"] >= c * peak]
        out[f"directional_anisotropy_{int(round(c * 100)):02d}"] = directional_anisotropy(moving["angle"])
    f1 = df[(df["Frame"] == 1) & (df["Point ID"] == top["Point ID"])].iloc[0]
    out["epicenter_x"], out["epicenter_y"] = float(f1["X"]), float(f1["Y"])
    if segment_path is not None:
        cap = cv2.VideoCapture(str(segment_path))
        ok, frame = cap.read()
        cap.release()
        if ok:
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            out["echogenicity"], out["relative_echogenicity"] = echogenicity(gray, f1["X"], f1["Y"])
    return out
