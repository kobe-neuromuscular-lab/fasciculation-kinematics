"""Step 2 - cut 1-s segments, run ultra-dense tracking, compute spatial metrics and
the velocity waveform.

    python scripts/track.py work/peaks.csv --out work/

For every row of peaks.csv:
  <out>/segments/<name>.avi         1-s segment (7 frames before the peak + 53 after)
  <out>/dense/<name>.csv.gz         dense tracking, Frame 0-12, 57,600 points (--keep-dense)
  <out>/waveforms/<name>.csv        5-point mean displacement per frame (raw)
and one row per segment in <out>/spatial.csv (pixel / frame units).
"""

import argparse
import os
import sys

import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from fasckin import dense, segment, spatial, temporal  # noqa: E402


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("peaks_csv")
    ap.add_argument("--out", required=True)
    ap.add_argument("--keep-dense", action="store_true", help="save the full dense tracking table")
    a = ap.parse_args()

    for sub in ("segments", "waveforms", "dense"):
        os.makedirs(os.path.join(a.out, sub), exist_ok=True)
    rows = []
    for _, p in pd.read_csv(a.peaks_csv).iterrows():
        name = segment.segment_name(p["recording"], p["peak_s"])
        seg = segment.extract_segment(p["source"], p["peak_s"], os.path.join(a.out, "segments", name + ".avi"))
        df, fps, bounds = dense.track_dense(seg, p["x"], p["y"])
        if a.keep_dense:
            df.to_csv(os.path.join(a.out, "dense", name + ".csv.gz"), index=False)
        m = spatial.spatial_metrics(df, seg)
        tr, _ = temporal.retrack(seg, temporal.select_moving_points(df))
        wave = temporal.velocity_waveform(tr)
        wave.rename("Length").to_csv(os.path.join(a.out, "waveforms", name + ".csv"))
        rows.append(dict(segment=name, recording=p["recording"], fps=fps,
                         field_x0=bounds[0], field_y0=bounds[1], **m))
        print(f"{name}: peak frame {m['max_frame']}, DA(5%) {m['directional_anisotropy_05']:.3f}, "
              f"peak {m['peak_displacement_px']:.2f} px/frame")
    out_csv = os.path.join(a.out, "spatial.csv")
    pd.DataFrame(rows).to_csv(out_csv, mode="a", header=not os.path.exists(out_csv), index=False)


if __name__ == "__main__":
    main()
