"""Step 4 - merge spatial metrics and landmarks and convert to physical units.

    python scripts/combine.py work/ --um-per-px 68.49 [--clinical clinical.csv]

--um-per-px: lateral pixel size of your export (read it from the scale bar).
--clinical:  optional CSV with a ``recording`` column plus e.g. patient_id,
             group (1/0), Age, MRC - joined onto every segment.

Writes <work>/features.csv with, per segment:
  total_ms, contraction_ms, relaxation_ms      (from the landmarks)
  peak_velocity_um_per_ms                      (peak displacement per frame, converted)
  directional_anisotropy_05 / _15, active_area_fraction,
  echogenicity, relative_echogenicity
"""

import argparse
import os
import sys

import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from fasckin import units  # noqa: E402


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("work")
    ap.add_argument("--um-per-px", type=float, required=True)
    ap.add_argument("--clinical")
    a = ap.parse_args()

    sp = pd.read_csv(os.path.join(a.work, "spatial.csv"))
    lm = pd.read_csv(os.path.join(a.work, "landmarks.csv"))
    df = sp.merge(lm, on="segment", how="left")
    df["um_per_px"] = a.um_per_px
    df["peak_velocity_um_per_ms"] = units.px_per_frame_to_um_per_ms(
        df["peak_displacement_px"], a.um_per_px, df["fps"])
    if a.clinical:
        df = df.merge(pd.read_csv(a.clinical), on="recording", how="left")
    out = os.path.join(a.work, "features.csv")
    df.to_csv(out, index=False)
    print(f"{len(df)} segments -> {out}")


if __name__ == "__main__":
    main()
