# fasciculation-kinematics

Code for **R. Sugisawa, K. Sekiguchi, et al. "Quantitative Spatiotemporal Analysis of
Ultrasound Images of Fasciculations in ALS." *Muscle & Nerve* 2026.
https://doi.org/10.1002/mus.70338**

It measures how a small region of muscle moves on B-mode ultrasound video. It
tracks every pixel of a 240 × 240 px field with pyramidal Lucas–Kanade optical
flow and computes:

| Feature | Meaning | Paper |
|---|---|---|
| `total_ms`, `contraction_ms`, `relaxation_ms` | Durations between five landmarks on the velocity waveform | 2.3.2, Fig. 2 |
| `peak_velocity_um_per_ms` | Largest per-frame displacement at the peak frame | 2.3.3 |
| `directional_anisotropy_05` / `_15` | How uniformly the moving points travel in one direction (1 = all together, 0 = cancel out) | 2.3.3, Fig. 3 |
| `active_area_fraction` | Share of the field moving ≥ 15 % of the peak displacement | 2.3.3 |
| `echogenicity`, `relative_echogenicity` | Grey level around the epicentre (absolute, and relative to the image) | 2.3.3 |

The motion-tracking parts (steps 1–3) do not depend on fasciculations. They
apply to any short, local tissue motion that is visible on B-mode video.

**No patient data are included.** The recordings are not public because of
privacy and ethical restrictions (see the paper's Data Availability
Statement). The `examples/` folder makes synthetic videos, so the whole
pipeline can be run.

## Install

```bash
git clone https://github.com/<owner>/fasciculation-kinematics
cd fasciculation-kinematics
pip install -r requirements.txt
```

Tested with Python 3.12, OpenCV 4.9, NumPy 1.26, pandas 2.1, SciPy 1.11,
scikit-learn 1.4, statsmodels 0.14 and matplotlib 3.7.

## Quick start (synthetic data, about 1 minute)

```bash
python examples/make_synthetic.py work/data
python scripts/locate.py work/data/coherent.avi      --out work --windows 2
python scripts/locate.py work/data/heterogeneous.avi --out work --windows 2
python scripts/track.py work/peaks.csv --out work
python scripts/mark_landmarks.py work          # opens a window; click 5 landmarks per segment
python scripts/combine.py work --um-per-px 68.49
```

`work/features.csv` then holds one row per segment. The synthetic twitch lasts
700 ms, and the coherent example should give a directional anisotropy near 1
while the heterogeneous one gives a clearly lower value.

To try the statistics step, use a simulated table:

```bash
python examples/simulate_features.py work/sim.csv
python scripts/compare_groups.py work/sim.csv --out work/stats
```

## Pipeline

```
recording.avi
  │ 1  scripts/locate.py         split into 2-s windows (0.5-s hop) → sparse 4-px grid tracking
  │                              → peak frame + epicentre (automatic; --review to check by clicking)
  ▼ peaks.csv
  │ 2  scripts/track.py          1-s segment (peak − 7 … peak + 53 frames)
  │                              → ultra-dense tracking of the 240 × 240 px field (57,600 points, Frame 0–12)
  │                              → spatial metrics at the peak frame
  │                              → re-track the moving points over the whole segment → velocity waveform
  ▼ spatial.csv, waveforms/*.csv
  │ 3  scripts/mark_landmarks.py Start / Peak contraction / Reversal / Peak relaxation / End
  ▼ landmarks.csv
  │ 4  scripts/combine.py        merge + unit conversion (µm/px from your scale bar, fps from the video)
  ▼ features.csv
  │ 5  scripts/compare_groups.py propensity-score matching (age, MRC) → Welch t-tests, Cohen's d
  ▼                              → MANOVA + Mahalanobis distance over 10 patient-level 70/30 splits
```

The library code is in `fasckin/`. Each module's docstring gives the paper
section it implements. The tracking parameters are those in the paper:
50 × 50 px window, `maxLevel = 30`, and termination at 30 iterations or
0.01 px.

### Output conventions

* `Frame = k` is the position in video frame *k + 1*. `Length` at `Frame = k`
  is the displacement from frame *k* to *k + 1* (px/frame), so it is a
  velocity. It is 0 at `Frame = 0`.
* `angle` is `atan2(dy, dx)` in image coordinates (y points down).
* Coordinates are full-frame pixels.

### Adapting to other data

These values are tied to the scanner and export used in the paper (GE LOGIQ e,
686 × 528 px export, 39–50 fps). Check them before using other data:

* `fasckin/sparse.py` `SPARSE_GRID`: the imaging area covered by the sparse grid.
* `fasckin/dense.py` `CENTER_X_RANGE`, `CENTER_Y_RANGE`: keep the 240 × 240
  field inside the image.
* `fasckin/spatial.py` `echogenicity(bg_box=...)`: the reference area for
  relative echogenicity.
* `--um-per-px`: pixel size. Read it from the on-screen scale bar. It changes
  with depth and field of view.
* Search windows (`PEAK_SEARCH_FRAMES = (5, 9)`, `SELECT_FRAMES = (4, 10)`):
  these assume the segment starts 7 frames before the peak.

## How this code relates to the paper

The paper's results were produced by a series of single-purpose scripts. This
repository combines them into one package.

* We re-ran the package on stored recordings from the study (14 segments across
  all diagnostic groups) and compared the output with the saved intermediate
  files. Dense tracking and all spatial metrics matched to 5–6 significant
  digits. The velocity waveforms matched within 0.003 px/frame. Run on the
  saved features, propensity matching selected exactly the same 62 pairs, and
  the univariate results equal the published values.
* [`docs/original_scripts.md`](docs/original_scripts.md) maps the original
  scripts to the modules in this package.

## Citation

If you use this code, please cite the paper (see `CITATION.cff`).

## License

MIT. See `LICENSE`.

## Contact

Kenji Sekiguchi, Division of Neurology, Kobe University Graduate School of
Medicine (sekiguch@med.kobe-u.ac.jp). Please use GitHub issues for questions
about the code.
