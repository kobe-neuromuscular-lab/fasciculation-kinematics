"""Cut the standardized 1-s segment around a fasciculation (paper Methods 2.2.1).

The segment starts 7 frames before the peak and is 60 frames long
(7 + 53; ~1 s at 43-50 fps).
"""

import os

import cv2

PRE_FRAMES = 7
POST_FRAMES = 53


def segment_name(recording_stem, peak_s):
    """Naming used in the paper's data: <exam>_<clip>_<peak time in ms, 5 digits>."""
    return f"{recording_stem}_{int(peak_s * 1000):05d}"


def extract_segment(video_path, peak_s, out_path, pre=PRE_FRAMES, post=POST_FRAMES):
    """Write frames [round(peak_s * fps) - pre, round(peak_s * fps) + post) to ``out_path``."""
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        raise IOError(f"Cannot open video: {video_path}")
    fps = cap.get(cv2.CAP_PROP_FPS)
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    size = (int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)), int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)))
    peak = round(peak_s * fps)
    start, end = max(0, peak - pre), min(total, peak + post)
    cap.set(cv2.CAP_PROP_POS_FRAMES, start)
    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
    writer = cv2.VideoWriter(str(out_path), cv2.VideoWriter_fourcc(*"XVID"), fps, size)
    for _ in range(start, end):
        ok, frame = cap.read()
        if not ok:
            break
        writer.write(frame)
    writer.release()
    cap.release()
    return out_path
