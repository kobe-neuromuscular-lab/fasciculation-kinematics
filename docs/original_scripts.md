# Where the original scripts went

The study's analysis was run as a series of single-purpose scripts with
hard-coded paths. This table maps each of them to the package. The originals
are not included, because they contain local paths and clinical-table
look-ups. Their logic is reproduced here and was checked against their saved
output.

| Order | Original script | What it did | Now |
|---|---|---|---|
| 1 | `split_2s_by0.5s.py` | 2-s windows every 0.5 s | `sparse.split_windows` |
| 2 | `grid_class tracking -v4 (fas).py` | sparse 4-px grid tracking of each window | `sparse.track_sparse` (rebuilt from the saved output; the script file itself was later overwritten; see below) |
| 3 | `master_analysis(fas) v2.py` | click epicentre, view curves, type peak frame → `fas_wave_timing.csv` | `scripts/locate.py --review`, `sparse.find_peak` |
| 4 | `split_1s_by twitch timing.py` | 1-s segment, peak − 7 … + 53 frames | `segment.extract_segment` |
| 5 | `grid_class tracking -v8.2 (fas) - calc1.5.py` | dense 240 × 240 tracking, Frame 0–12, angle | `dense.track_dense` |
| 6 | `check_area twist degree(finalize1+2+3) -v2.py` | peak frame, DA, active area, echogenicity, clinical merge | `spatial.spatial_metrics` (Moran's I, computed but not reported, is omitted) |
| 7 | `check_area twist degree(finalize for simp.py` | re-track points ≥ 30 % over the whole segment | `temporal.select_moving_points`, `temporal.retrack` |
| 8 | `length vs frame.py` | interactive five-landmark marking → `twitch_param.csv` | `temporal.velocity_waveform`, `temporal.smooth_curve`, `scripts/mark_landmarks.py` |
| 9 | `check_allcsv -wave analysis simpson area - integrate fasresult.py`, `pdv frame to milisecond.py` | merge and convert to µm, ms, µm/ms | `scripts/combine.py`, `units` |
| 10 | `make propensity.py` | PSM (Hungarian), balance | `stats.propensity_match` |
| 11 | `check_allcsv box -for matched data.py` | Welch t-tests, Cohen's d, box plots | `stats.univariate` |
| 12 | `MANOVA.py` | MANOVA + Mahalanobis, 10 patient-level splits | `stats.manova_repeated` |

## Checks against the original output

We used stored recordings and the saved intermediate files (not distributed).

* **Sparse tracking.** The saved output of one 2-s window was compared (all
  10,620 points × 85 frames). 98.7 % of coordinates agreed within 0.01 px. The
  integrated velocity curve differed by at most 0.003 px/frame, against a
  curve peak of 1.26.
* **Dense tracking and spatial metrics.** 14 segments were checked (ALS,
  cervical spondylosis, SBMA, SMA and other neurogenic). Displacements agreed
  within 1 × 10⁻⁵ px (the rounding of the saved files). Peak frame, peak
  displacement, both DA values, active area fraction, epicentre and
  echogenicity were identical to 5–6 significant digits.
* **Waveform.** The same 14 segments were checked. The 5-point waveforms
  differed by at most 0.003 px/frame. The original re-tracking started from
  coordinates rounded to 6 digits, which explains the small difference.
* **Statistics.** Run on the saved features, propensity matching selected the
  identical 62 pairs. Means, SDs and p values equal the published values. For
  the MANOVA, see `paper_vs_code.md` §5.
