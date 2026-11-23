# Offline data-protocol checks (2026-11-16)

These checks audit the data protocol of the paper's Appendix B: the leakage audit, the row roles of every
baseline, the domain-map fit rows and the provenance of the cited files. They use only data on the build machine.

- **Where things are:** scripts, json results and `logs/` are in this folder. `provenance_sha256.json` holds the
  sha256 of the 317 cited files, none missing.
- **Paths:** "the release audit" means `tools/verify_no_leakage.py` as it stood on 2026-11-16 (sha256 704b7cad…).
  P-numbers refer to the draft of that date.

## 1. Leakage audit

### 1a. The release audit as shipped

It passes 23 of 23 checks and exits 0 (`logs/release_verify_no_leakage.log`). This is the first log produced by the
current script. The release ships only an older v1.43 log, which came from an earlier version of the script.

**What each check actually tests, compared with what P192 says:**

| Check | What the code tests | Matches P192? |
|---|---|---|
| A1, B1, B2, B5 | Row disjointness by content, an index checksum, row counts | yes |
| B3, B4 | Only 500 sampled rows | sample only |
| C1 | The FIR map's fit input is test rows 1000:1600 | yes |
| C2 | Compares a metadata string; no refit | weak |
| C3, C4 / G5 | Read the v1.40 / v1.41 files | **no** — not the v1.44 files behind the reported numbers |
| D1 | Shape only | weak |
| D2 | 200 rows of the FIR-path file | partly; NN_live's training file is never read |
| D3 | float32 hash vs float64 hash, first 20,000 rows only | **cannot fail** |
| E3, E4 | A file exists; two constants in the script | weak |
| E1, E2, F1, G1–G4 | As described in the paper | yes (F1 skips the boxcar map) |

**Verdict:** the script had 23 checks in seven sets, and several did not test what P192 claims.

### 1b. The fixed copy, `verify_no_leakage_fixed.py`

It passes 29 of 29 checks, with none blocked (`logs/fixed_verify_no_leakage.log`). The original script is not edited.

- **B3/B4:** cover all 20,000 rows, not a sample.
- **C3:** reads the v1.44 per-shot files.
- **C5 (new):** re-derives the reported numbers with rows 1000:1600 removed. It matches `v144_stats.json` to 1e-9.
- **D2:** checks all 900,000 FIR-file rows.
- **D1b/D2b (new):** check NN_live's boxcar training file, 200,000 rows. Every row is bit-identical to the map
  recomputed from `box_domain_map.json`.
- **D3 (rewritten):** a near-duplicate search of all 100,000 test rows, mapped and raw, against both training files.
  It finds 0 hits.
  - **It can now fail.** A self-test planted two test rows in a temporary copy, and the fixed D3 found exactly those
    two. The old D3 found none on the same copy (`logs/fixed_d3_selftest.log`).
- **E2b (new):** the generator pool is disjoint from all 100,000 test rows.
- **F2 (new):** a label-free refit of the boxcar map gives the recorded coefficients exactly.
- **G5:** reads the v1.44 runs.
- **Missing inputs:** recorded as BLOCKED instead of crashing.

### 1c. The v1.44 supplement, `verify_no_leakage_v144.py`

It passes 13 of 13. The rerun is byte-identical to its shipped log. It has no D check for NN_live, so P81's "13 of 13"
is true but doesn't cover NN_live's training data.

### 1d. The earlier builds' checks

The shipped `run_analyses.log` (Nov 9) predates the fig7/fig8b steps that `run_analyses.sh` (Nov 13) now contains. It
was not rerun here, because the script writes into `campaign_v144/final`.

## 2. Training-row domain-map refit

**What the 2026-11-14 work did:** it fit the map on the v1.44 replay of training rows 300000:300600 and retrained five
seeds.

**What it lacked:**
- per-board results;
- a v1.44 test-row control, so the effect of the rows and the effect of the build could not be told apart;
- the right source file in the ledger: its row cites `map_trainrows_s20260905.json`, which holds only one seed.

**P189's figure checks out.** Its −0.016 ± 0.042 comes from per-seed differences of −0.008, −0.007, +0.033, −0.082 and
−0.017. The ± is a seed SD, not a CI.

**New run** (`task2_trainrow_map_perboard.py`, `task2_summary.json`). It reproduces the earlier predictions exactly. It
then adds per-board scoring on all 99,400 rows and a third arm: a map fit on v1.44 test rows 1000:1600. Scoring uses
the float Keras model at p > 0.5.

| Set | Arm | Δ vs deployed map, 5 seeds (mean ± SD) | Δ for the kept seed, s20260904 [95% CI], exact McNemar p |
|---|---|---|---|
| Board A | training-row map | −0.014 ± 0.020 | −0.045 [−0.087, −0.003], p = 0.039 |
| Board A | v1.44 test-row map | +0.003 ± 0.027 | −0.020, p = 0.38 |
| Board B | training-row map | −0.019 ± 0.051 | −0.097 [−0.140, −0.053], p = 1.4e-5 |
| Board B | v1.44 test-row map | −0.012 ± 0.046 | −0.087, p = 1.1e-4 |
| Board mix | training-row map | −0.016 ± 0.042 | −0.082 [−0.126, −0.039], p = 2.7e-4 |
| Board mix | v1.44 test-row map | −0.003 ± 0.049 | −0.071, p = 0.0018 |

**Reading:**
- **Averaged over seeds:** the training-row map makes no detectable difference, so P189 holds in that sense.
- **For the seed the recipe actually keeps:** any refit on a v1.44 capture costs 0.05–0.10 points, whether it is fit
  on training rows or on test rows. So the loss comes from the build and the seed, not from fitting on test rows.
- **The deployed map** was fit on a v1.40 replay. Maps fit on v1.44 shift by −1.25 (training rows) or −0.75
  (test rows), against −0.25 for the deployed map.

## 3. A builder for `test100k_real_X.npy`

`build_test100k_real.py` builds the file from two inputs, `0528_X_test_0_770.npy` and `0528_y_test_0_770.npy`:
1. It re-derives the test20k indices with `default_rng(20260902)`; they match the manifest.
2. It shuffles the other 80,000 rows with `default_rng(20261022)`.

**The result is byte-identical** to the shipped file and to `DATA_MANIFEST.csv:254` (X sha256 8015b629…, y 03035f92…).

Two caveats:
- The recipe's script was not in the release when this audit ran.
- The input arrays were not checked against Zenodo, because there was no network.

## 4. Which rows each model uses

| Model or step | Trained or fit on | Validation / selection | Scored on |
|---|---|---|---|
| NN_live | 0:10000 + 110000:300000, boxcar-mapped (map fit on test rows 1000:1600, v1.40 capture) | 20% inside; seed kept by lowest val_loss of 5 | 99,400 per board |
| NN_axi | the same rows, FIR map (test rows 1000:1600) | the same | 19,400 |
| LDA (95.50) | 0:180000 | ridge chosen on 180000:200000 | 19,400 |
| Matched filter, linear-baselines LDA | 0:200000 | threshold on training scores | 19,400 |
| Boxcar LDA | 0:10000 + 110000:280000 | 280000:300000 | 99,400 |
| Five nonlinear models | 0:180000 | 180000:200000 | 19,400 |
| Augmentation study | the training rows | — | replayed test rows 4000:20000; its channel model is fit on replayed test rows 0:3999 |
| Synthetic generator | 10000:110000 | — | — |
| P195 real-data arms | 0:10000, 110000:130000, 0:50000 | 20% inside | 19,400 |
| Retrain of [16] (P95) | all 900,000 rows | 855000:900000 | 100k test |
| P189 refit | 300000:300600 | — | 99,400 |

**Statements checked:**
- **P96, "all trained on the same 200,000 rows": false.**
  - The network shares 100,000 rows with the matched filter's training set.
  - It shares 80,000 rows with the LDA's.
- **P191, "Every row of the dataset has one role": false.**
  - Rows 10000:110000 are both the generator's fit pool and training rows for the baselines and arms.
  - Replayed test rows 0:3999 both fit the augmentation channel and are scored in the headline sets.
  - Rows 300000:899,999 have roles P191 doesn't list: the [16] retrain and the P189 refit.
- **True:**
  - P78's training ranges for NN_live;
  - the 600 map-fit rows are excluded from every headline number (confirmed by the new check C5);
  - the maps were fit on rows 1000:1599;
  - no test row is in any training set.

## 5. What each check needs

The dry run is `task5_inputs_dryrun.json`.

- **On this machine:** every input of every check exists.
- **From the release alone:** no check set can run.
  - Sets A, B, D, E and G need the derived arrays.
  - Sets C, F and G need the files marked "archive separately".
  - The v1.44 supplement needs the 220 per-shot files, none of which are in the repository (`DATA_MANIFEST.csv`).

## Paper statements these runs contradict

- **P96:** "all trained on the same 200,000 rows" is false.
- **P191:** "Every row has one role" is false.
- **P81/P192:** the shipped checks don't test what P192 (D) says. The fixed copy does, and passes 29 of 29.
- **P189:** −0.016 ± 0.042 is a five-seed mean ± SD, not a CI. For the deployed seed, the refit difference is −0.082 on
  the board mix (p = 0.0003) and −0.097 on board B. A v1.44 test-row refit costs about the same, so the cause is the
  build or the seed, not the test rows.
- **P78/P79/P194:** the design-choice list leaves out the augmentation channel fit on replayed test rows 0:3999.
- **Ledger:** the −0.016 ± 0.042 row cites a file that holds one seed.

## What the release would need to ship

**Scripts and logs:**
- the fixed `tools/verify_no_leakage.py`, with its 29/29 log and the D3 self-test log;
- a v1.44 run log of the 23-check script;
- `tools/build_test100k_real.py`, named in README:71, with the note at DATA_MANIFEST.csv:254 corrected;
- for the refit: `map_trainrows.py`, all five `map_trainrows_s*.json`, `map_seeds.sh`, the `trainrows/*.npz`
  captures, and a per-board summary json for the ledger;
- a rerun `run_analyses.log`.

**Data:**
- the `0528_*` arrays, or a script that derives them from Zenodo;
- `0528_X_train_box_calibrated.npy`, or its builder together with its capture;
- `domain_calib_{raw_X,acquired}.npy` and `box_part2000.partial.npz`;
- the v1.44 `axi/`, `live/` and `inloop/` per-shot files.

## Not done

- **`run_analyses.sh`:** not rerun, because it writes into `campaign_v144/final`.
- **The dataset against Zenodo:** not verified, because there was no network.
- **The delay-corrected map variant:** not re-audited beyond its row ranges.
