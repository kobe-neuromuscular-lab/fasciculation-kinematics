# Published Methods vs. the code that produced the results

We re-ran the analysis code from the study against the saved intermediate
files. This page lists every place where the published Methods text describes
the analysis differently from what the code did. The numbers below come from
the matched dataset (62 ALS and 62 non-ALS segments).

## 1. Directional anisotropy: 5 % cutoff, not 15 %

**Methods 2.3.3** says that points moving less than 15 % of the maximum
displacement were excluded from the directional analysis.

**Code.** The DA values in the Abstract and Results
(0.534 ± 0.245 vs 0.627 ± 0.215, p = 0.028) were computed over points moving
**≥ 5 %** of the maximum. The DA over points moving ≥ 15 % was also computed.
It was not reported.

| Cutoff | ALS | non-ALS | Welch p |
|---|---|---|---|
| ≥ 5 % (reported) | 0.534 ± 0.245 | 0.627 ± 0.215 | 0.028 |
| ≥ 15 % | 0.658 ± 0.244 | 0.734 ± 0.203 | 0.062 |

This package outputs both values, as `directional_anisotropy_05` and
`directional_anisotropy_15`. The active area fraction uses 15 %, as described.

## 2. The landmarks were read on a smoothed curve

**Methods 2.3.3** says all analyses used no noise filtering.

**Code.** The tracking and all spatial metrics use no filtering. However, the
five temporal landmarks were marked on the 5-point mean velocity curve after
cubic-spline interpolation (×5 samples) and a Gaussian filter
(σ = 2 interpolated samples ≈ 0.4 frame). This is `temporal.smooth_curve`.
The durations are the differences between the marked positions.

## 3. Peaks and epicentres were confirmed by an observer

**Methods 2.2.1** describes an automated rule: the peak is the frame with the
largest integrated velocity, and the epicentre is the point with the largest
displacement at that frame.

**Code.** The investigator clicked the epicentre on the video and typed the
peak frame after viewing the velocity curves of the points around the click
(the original tool is reproduced as `scripts/locate.py --review`). Across the
245 recorded fasciculations, the automated rule (`sparse.find_peak`)
restricted to the clicked region agreed with the chosen frame within ±1 frame
in 52 % of cases. Without that restriction, the agreement was 34 %. The rule is
therefore provided as a starting point. The paper's segments came from the
observer-confirmed choices.

## 4. Welch's t-test, not Student's

**Methods 2.4.2** says Student's t-test.

**Code.** The reported p values come from Welch's unequal-variance t-test. The
two tests differ in the third decimal at most (e.g. peak velocity
p = 0.0387 vs 0.0385). `stats.univariate` reports both.

## 5. MANOVA with linearly dependent variables

The MANOVA in **Methods 2.4.3** used eight variables, including total,
contraction and relaxation duration. Total duration equals contraction plus
relaxation exactly. The error matrix is therefore singular, and Pillai's trace
from statsmodels is numerically unstable: re-running the original script gives
an impossible value (≫ 1) in one of the ten iterations, and slightly different
values in the others, depending on floating-point details.

With one redundant duration removed (seven variables, the default in
`stats.MANOVA_FEATURES`), the result is stable:

| | Reported | 7 variables, same splits |
|---|---|---|
| Pillai's trace | 0.317 ± 0.030 | 0.311 ± 0.031 (every iteration p ≤ 0.0011) |
| Mahalanobis distance | 1.10 ± 0.05 | 1.11 ± 0.05 |

The Mahalanobis distance uses a pseudo-inverse, so it does not change when the
redundant variable is removed. The original script also gives 1.11 ± 0.05
today.

## 6. What was tracked over the full 1 s

**Methods 2.3.1** says every pixel was tracked through the 1-s sequence.

**Code.** All 57,600 points were tracked for the first 13 frame steps
(Frame 0–12). The spatial metrics need only these frames, because the peak is
searched in Frames 5–9. The waveform used for the durations comes from a
second run. That run tracks only the points that moved ≥ 30 % of the maximum
displacement in Frames 4–10, over the whole segment. Each such point starts
from its position at the first frame in which it met that threshold. The
5 points used for the waveform are the fastest ones at the frame where the
largest displacement occurs within Frames 4–10.

## 7. Pixel size

The Methods give a pixel pitch of about 60 µm. In fact the pixel size depended
on the depth and field-of-view setting of each recording: 60.6, 68.5, 80.0 or
91.7 µm/px, read from the on-screen scale. Each recording was converted with
its own value (see `fasckin/units.py`), so the reported µm/ms values are
correct. Only the "≈ 60 µm" description is a simplification.

## 8. Details that the Methods do not state

* The DA uses the displacement vectors of the peak frame (row `Frame = k`, the
  motion between video frames k and k + 1). The peak frame is the frame, within Frames 5–9, with the largest *summed*
  displacement over all 57,600 points.
* Echogenicity is measured on the first frame of the segment. Pixels ≤ 5 or
  ≥ 240 are ignored, which removes the background and on-screen annotations.
  The reference for relative echogenicity is the region x 90–600, y 20–420.
* The 240 × 240 field centre was clipped to x 235–452, y 170–266, so the
  field stays inside the imaging area (full-frame pixels, 686 × 528 export).
