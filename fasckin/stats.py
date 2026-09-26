"""Group statistics used in the paper (Methods 2.4).

Input: one row per segment with a ``group`` column (1 = ALS, 0 = comparison),
``patient_id``, ``Age``, ``MRC`` and the feature columns.
"""

import numpy as np
import pandas as pd
from scipy import stats
from scipy.optimize import linear_sum_assignment
from scipy.spatial.distance import cdist, mahalanobis
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler

FEATURES = ["total_ms", "contraction_ms", "relaxation_ms", "directional_anisotropy_05",
            "peak_velocity_um_per_ms", "echogenicity", "relative_echogenicity",
            "active_area_fraction"]
# total = contraction + relaxation exactly, so one of the three durations must be
# left out of the MANOVA; with all three the error matrix is singular and Pillai's
# trace becomes numerically unstable (see docs/paper_vs_code.md).
MANOVA_FEATURES = [f for f in FEATURES if f != "relaxation_ms"]


def propensity_match(df, age="Age", mrc="MRC", group="group"):
    """1:1 matching on the propensity score (logistic regression on age and MRC grade,
    MRC as categorical), solved optimally with the Hungarian algorithm.

    Returns (matched_cases, matched_controls), row-aligned.
    """
    d = df.dropna(subset=[age, mrc]).copy()
    dummies = pd.get_dummies(d[mrc].astype(int), prefix="MRC", drop_first=True)
    age_z = StandardScaler().fit_transform(d[[age]])
    X = pd.concat([dummies, pd.DataFrame(age_z, index=d.index, columns=["age_z"])], axis=1)
    model = LogisticRegression(random_state=42, max_iter=1000).fit(X, d[group])
    d["ps"] = model.predict_proba(X)[:, 1]
    cases, controls = d[d[group] == 1], d[d[group] == 0]
    rows, cols = linear_sum_assignment(cdist(cases[["ps"]], controls[["ps"]]))
    return cases.iloc[rows].copy(), controls.iloc[cols].copy()


def standardized_difference(a, b):
    pooled = np.sqrt((np.var(a, ddof=1) + np.var(b, ddof=1)) / 2)
    return abs(np.mean(a) - np.mean(b)) / pooled if pooled > 0 else 0.0


def univariate(cases, controls, features=FEATURES):
    """Mean +/- SD per group, t-test p value and Cohen's d for each feature.

    The paper's p values were computed with Welch's t-test (unequal variances);
    see docs/paper_vs_code.md.
    """
    out = []
    for f in features:
        a, b = cases[f].dropna(), controls[f].dropna()
        pooled = np.sqrt(((len(a) - 1) * a.var() + (len(b) - 1) * b.var()) / (len(a) + len(b) - 2))
        out.append(dict(feature=f, case_mean=a.mean(), case_sd=a.std(), control_mean=b.mean(),
                        control_sd=b.std(), p_welch=stats.ttest_ind(a, b, equal_var=False).pvalue,
                        p_student=stats.ttest_ind(a, b).pvalue,
                        cohens_d=(a.mean() - b.mean()) / pooled if pooled > 0 else np.nan))
    return pd.DataFrame(out)


def _patient_split(data, test_size, seed):
    rng_state = np.random.get_state()
    np.random.seed(seed)
    by_patient = data.groupby("patient_id")["group"].first()
    test = []
    for g in (1, 0):
        pts = by_patient[by_patient == g].index.tolist()
        test += list(np.random.choice(pts, max(1, int(len(pts) * test_size)), replace=False))
    np.random.set_state(rng_state)
    return data[~data["patient_id"].isin(test)]


def manova_repeated(data, features=MANOVA_FEATURES, n_iter=10, test_size=0.3):
    """MANOVA (Pillai's trace) and Mahalanobis distance between group centroids on the
    70 % patient-level training part of ``n_iter`` stratified random splits
    (seeds 0, 42, 84, ...). Features are z-scored within each split.
    """
    from statsmodels.multivariate.manova import MANOVA

    res = []
    for i in range(n_iter):
        train = _patient_split(data, test_size, seed=i * 42)
        z = pd.DataFrame(StandardScaler().fit_transform(train[features]), columns=features,
                         index=train.index)
        y = train["group"]
        cov_inv = np.linalg.pinv(np.cov(z.T))
        maha = mahalanobis(z[y == 1].mean().values, z[y == 0].mean().values, cov_inv)
        z["grp"] = y.astype(str).values
        mv = MANOVA.from_formula(" + ".join(features) + " ~ grp", data=z).mv_test()
        stat = mv.results["grp"]["stat"]
        res.append(dict(iteration=i + 1, pillai=stat.loc["Pillai's trace", "Value"],
                        F=stat.loc["Pillai's trace", "F Value"],
                        p=stat.loc["Pillai's trace", "Pr > F"], mahalanobis=maha))
    return pd.DataFrame(res)
