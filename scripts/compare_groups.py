"""Step 5 - group comparison as in the paper: propensity-score matching on age and MRC
grade, univariate tests, and repeated-split MANOVA / Mahalanobis distance.

    python scripts/compare_groups.py work/features.csv --out work/stats/

features.csv needs: patient_id, group (1 = cases, 0 = comparison), Age, MRC and
the feature columns listed in fasckin.stats.FEATURES.
"""

import argparse
import os
import sys

import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from fasckin import stats  # noqa: E402


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("features_csv")
    ap.add_argument("--out", required=True)
    ap.add_argument("--no-matching", action="store_true")
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)

    df = pd.read_csv(a.features_csv)
    if a.no_matching:
        cases, controls = df[df["group"] == 1], df[df["group"] == 0]
    else:
        cases, controls = stats.propensity_match(df)
        print(f"matched pairs: {len(cases)}; standardized difference in age: "
              f"{stats.standardized_difference(cases['Age'], controls['Age']):.3f}")
        pd.concat([cases, controls]).to_csv(os.path.join(a.out, "matched.csv"), index=False)

    uni = stats.univariate(cases, controls)
    uni.to_csv(os.path.join(a.out, "univariate.csv"), index=False)
    print(uni.round(4).to_string(index=False))

    mv = stats.manova_repeated(pd.concat([cases, controls], ignore_index=True))
    mv.to_csv(os.path.join(a.out, "manova_iterations.csv"), index=False)
    print(f"Pillai's trace {mv['pillai'].mean():.3f} +/- {mv['pillai'].std(ddof=0):.3f} "
          f"(max p {mv['p'].max():.2g}); Mahalanobis distance "
          f"{mv['mahalanobis'].mean():.2f} +/- {mv['mahalanobis'].std(ddof=0):.2f}")


if __name__ == "__main__":
    main()
