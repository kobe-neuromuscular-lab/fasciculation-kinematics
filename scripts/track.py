"""Step 2 - cut the segments, run ultra-dense tracking, compute spatial metrics and
the velocity waveform.

    python scripts/track.py work/peaks.csv --out work [--config my_settings.json]

For every row of peaks.csv:
  <out>/segments/<name>.avi         segment: pre_frames before the peak + post_frames after
                                    (paper: 7 + 53 frames, about 1 s)
  <out>/dense/<name>.csv.gz         dense tracking table (--keep-dense)
  <out>/waveforms/<name>.csv        per-frame displacement: mean of the 5 fastest points
                                    (Length) and mean of the 5 largest values per frame
                                    (Length_frame_top5)
and one row per segment in <out>/spatial.csv (pixel / frame units).
The settings used are saved to <out>/config_used.json.
"""

import argparse
import os
import sys

import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from fasckin import config, dense, segment, spatial, temporal  # noqa: E402


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("peaks_csv")
    ap.add_argument("--out", required=True)
    ap.add_argument("--config", help="JSON settings file (see configs/)")
    ap.add_argument("--keep-dense", action="store_true", help="save the full dense tracking table")
    a = ap.parse_args()

    cfg = config.load_config(a.config)
    lk = config.lk_params(cfg)
    sg, dn, spc, tp = cfg["segment"], cfg["dense"], cfg["spatial"], cfg["temporal"]
    for sub in ("segments", "waveforms", "dense"):
        os.makedirs(os.path.join(a.out, sub), exist_ok=True)
    config.save_config(cfg, os.path.join(a.out, "config_used.json"))

    rows = []
    for _, p in pd.read_csv(a.peaks_csv).iterrows():
        name = segment.segment_name(p["recording"], p["peak_s"])
        seg = segment.extract_segment(p["source"], p["peak_s"], os.path.join(a.out, "segments", name + ".avi"),
                                      pre=sg["pre_frames"], post=sg["post_frames"])
        df, fps, bounds = dense.track_dense(seg, p["x"], p["y"], n_steps=dn["n_steps"], lk_params=lk,
                                            half=dn["half_size"], x_range=dn["center_x_range"],
                                            y_range=dn["center_y_range"])
        if a.keep_dense:
            df.to_csv(os.path.join(a.out, "dense", name + ".csv.gz"), index=False)
        m = spatial.spatial_metrics(df, seg, cutoffs=spc["da_cutoffs"], search=spc["peak_search_frames"],
                                    active_cutoff=spc["active_cutoff"], echo_half=spc["echo_half"],
                                    echo_bg_box=spc["echo_bg_box"])
        pts = temporal.select_moving_points(df, frames=tp["select_frames"], fraction=tp["select_fraction"])
        tr, _ = temporal.retrack(seg, pts, lk_params=lk)
        wave = pd.DataFrame({"Length": temporal.velocity_waveform(tr, frames=tp["select_frames"],
                                                                  n_top=tp["n_top"]),
                             "Length_frame_top5": temporal.frame_top_average(tr, n_top=tp["n_top"])})
        wave.index.name = "Frame"
        wave.to_csv(os.path.join(a.out, "waveforms", name + ".csv"))
        rows.append(dict(segment=name, recording=p["recording"], fps=fps,
                         field_x0=bounds[0], field_y0=bounds[1], field_x1=bounds[2], field_y1=bounds[3], **m))
        print(f"{name}: peak frame {m['max_frame']}, DA(5%) {m.get('directional_anisotropy_05', float('nan')):.3f}, "
              f"peak {m['peak_displacement_px']:.2f} px/frame")
    out_csv = os.path.join(a.out, "spatial.csv")
    pd.DataFrame(rows).to_csv(out_csv, mode="a", header=not os.path.exists(out_csv), index=False)


if __name__ == "__main__":
    main()
