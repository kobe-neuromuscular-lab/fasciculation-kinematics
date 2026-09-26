"""Make a SIMULATED features table (random numbers, no patient data) to try
scripts/compare_groups.py.

    python examples/simulate_features.py examples/data/simulated_features.csv
"""

import sys

import numpy as np
import pandas as pd


def main(path):
    rng = np.random.default_rng(1)
    rows = []
    for group, n_pat, shift in [(1, 40, 1.0), (0, 30, 0.0)]:
        for p in range(n_pat):
            age = rng.normal(64 if group else 60, 14)
            mrc = int(rng.choice([2, 3, 4, 5], p=[0.1, 0.15, 0.3, 0.45]))
            for _ in range(int(rng.integers(1, 5))):
                contraction = rng.normal(160 + 35 * shift, 40)
                relaxation = rng.normal(330 + 55 * shift, 100)
                rows.append(dict(
                    patient_id=f"{'A' if group else 'N'}{p:03d}", recording=f"{'A' if group else 'N'}{p:03d}",
                    group=group, Age=round(age), MRC=mrc,
                    contraction_ms=contraction, relaxation_ms=relaxation,
                    total_ms=contraction + relaxation,
                    directional_anisotropy_05=float(np.clip(rng.normal(0.63 - 0.09 * shift, 0.23), 0, 1)),
                    peak_velocity_um_per_ms=abs(rng.normal(9.5 - 3 * shift, 7)),
                    echogenicity=rng.normal(100 - 15 * shift, 40),
                    relative_echogenicity=rng.normal(1.1 - 0.12 * shift, 0.4),
                    active_area_fraction=float(np.clip(rng.normal(0.67 - 0.06 * shift, 0.2), 0, 1))))
    pd.DataFrame(rows).to_csv(path, index=False)
    print(f"{len(rows)} simulated segments -> {path}")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "simulated_features.csv")
