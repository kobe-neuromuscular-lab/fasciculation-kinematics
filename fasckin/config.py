"""All tunable settings in one place.

The defaults are the settings used in the paper (GE LOGIQ e, 686 x 528 px export,
39-50 fps, fasciculations lasting < 1 s). To analyse other data, copy
``configs/paper_logiq_e.json``, change what you need and pass it with
``--config`` to any script. Keys you leave out keep their default.

Coordinates are full-frame pixels (x to the right, y down). Frame numbers follow
the tracking-table convention (see fasckin/tracking.py).
"""

import copy
import json

import cv2

DEFAULTS = {
    # Lucas-Kanade parameters (all stages)
    "lk": {"win_size": 50, "max_level": 30, "max_iter": 30, "eps": 0.01},
    # Stage 1: 2-s windows tracked on a sparse grid
    "sparse": {
        "window_s": 2.0,          # window length
        "hop_s": 0.5,             # step between window starts
        "grid_step": 4,           # grid spacing (px)
        "x_range": [110, 580],    # grid covers the imaging area [start, stop)
        "y_range": [40, 400],
    },
    # Stage 1 review tool (the interactive step used for the paper)
    "review": {
        "click_x_range": [130, 557],  # a click is clipped to this range
        "click_y_range": [65, 371],
        "roi_half": 61,               # curves are drawn for points within +/- 61 px of the click
        "color_x_range": [70, 620],   # colour scale of the curves (x -> hue, y -> brightness)
        "color_y_range": [0, 400],
    },
    # 1-s segment around the peak
    "segment": {"pre_frames": 7, "post_frames": 53},
    # Stage 2: ultra-dense tracking
    "dense": {
        "half_size": 120,             # field = 2 * half_size square (240 x 240 px)
        "center_x_range": [235, 452], # field centre is clipped so the field stays in the image
        "center_y_range": [170, 266],
        "n_steps": 13,                # frame steps tracked for the spatial metrics; null = all
    },
    # Spatial metrics
    "spatial": {
        "peak_search_frames": [5, 9],  # peak = frame with the largest summed displacement here
        "da_cutoffs": [0.0, 0.05, 0.15],
        "active_cutoff": 0.15,
        "echo_half": 20,               # echogenicity box = 2 * echo_half square
        "echo_bg_box": [90, 20, 600, 420],  # x0, y0, x1, y1 reference area
    },
    # Temporal waveform
    "temporal": {"select_frames": [4, 10], "select_fraction": 0.30, "n_top": 5},
}


def _merge(base, override):
    for k, v in override.items():
        if k.startswith("_"):
            continue
        if k not in base:
            raise KeyError(f"Unknown setting: {k}")
        if isinstance(base[k], dict):
            if not isinstance(v, dict):
                raise TypeError(f"Setting '{k}' must be an object")
            _merge(base[k], v)
        else:
            base[k] = v
    return base


def load_config(path=None):
    """Defaults, overridden by the JSON file at ``path`` (if given)."""
    cfg = copy.deepcopy(DEFAULTS)
    if path:
        with open(path, encoding="utf-8") as f:
            _merge(cfg, json.load(f))
    return cfg


def lk_params(cfg):
    lk = cfg["lk"]
    return dict(winSize=(lk["win_size"], lk["win_size"]), maxLevel=lk["max_level"],
                criteria=(cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, lk["max_iter"], lk["eps"]))


def save_config(cfg, path):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2)
