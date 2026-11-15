# What is in `campaign_v144/final/`

Every measurement of the final build (v1.44, banner `Nov  7 19:57:07`) and the analysis that turns it into the paper's
numbers. `campaign_v144/run_all.sh` wrote the measurement folders, apart from the cold starts, which were run by hand
(`campaign_v144/README.md`). `campaign_v144/run_analyses.sh` wrote `analysis/`. File names start with the board
(`A_`, `B_`) or its address (`10.1.9.26` = board A, `10.1.4.105` = board B). A `.log` holds the console output of the
step that wrote the file of the same name. Files too large for the repository are listed with their sha256 in
`DATA_MANIFEST.csv`: `live/` (200 files) and the two `inloop/*_0_100000.npz`. The folders `fig7/` and `fig8b/` keep the
draft's figure numbers. In the paper they are Fig. 6 and Fig. 7(b).

- **`run_all.log`, `runner_A.log`, `runner_B.log`, `RUN_ALL_FINISHED`**: the campaign's progress log with one line per
  step and its return code, the two board runners' logs, and the empty end marker.
- **`tests/`**: the checks each board ran right after loading, each a `.json` result and its `.log`.
  - **Load and calibration:** `*_load.*` (deploy, server restart and banner check) and `*_calib.log`.
  - **QICK's functional suite:** `*_functional`.
  - **The fault tests of Appendix C:** the wrong-shot binding test (`*_binding_fault`) and the gate held in reset or
    disabled (`*_fail_safe`).
  - **The tProc path check:** `*_tproc_decision`, 400 shots.
- **`calib/`**: the calibration before each phase of the main campaign (`*_live1`, `*_live2`, `*_inloop`, `*_axi`,
  `*_drift_full`): the stored complex gain `k` (`*_k.npy`), the offset `c` (`*_c.npy`), and a `.json` naming the board,
  phase, time, bitstream hash and git commit.
- **`live/`** (in the manifest): NN_live on every test row, 1,000 rows per file.
  - **Runs:** run 1 is board A on rows 0–49,999 and board B on rows 50,000–99,999. Run 2 swaps the halves.
  - **Each file holds:** the recorded window, NN_live's result words, the FIR and boxcar streams and the labels.
  - **Used by:** `analysis/analyze_v144.py`, for the headline and the bit-exact check.
- **`inloop/`**: the feed-forward loop on all 100,000 rows per board (`*_inloop_0_100000`, in the manifest), and the
  20-shot smoke test that had to pass before it (`*_SMOKE`). These are the in-loop counts of Sec. IX and Appendix C.
- **`axi/`**: NN_axi on the 20,000-row subset, ten chunks of 2,000 per board (in the manifest), with their logs. These
  give Table II's NN_axi row and the emulator comparison (`analysis/axi_emu_v144.json`).
- **`drift_full/`**: the 3 h stability run, 6,000 shots scored at the start and at the end on the start calibration,
  per board. The `.json` holds the probe samples over the 3 h, the stored `k` and both scores.
- **`cal_repeat/`**: eight calibrations in a row on one load per board (`cal_repeat_<host>.json`, one `.npz` of captured
  shots per repeat, `run_<host>.txt`). They give the spread of `arg k` against the probe (Appendix A).
- **`board2/`**: measurements outside the main campaign.
  - **tProc-path loop:** with the boxcar and with the FIR readout (`*_tproc_box`, `*_tproc_fir`).
  - **Boxcar check:** the boxcar output against a model applied to the raw buffer (`*_boxcar_mr`).
  - **Calibration swap:** board B on board A's calibration, and each board on its own (`swap_*.log`, with
    `k_B_saved.npy` and `c_B_saved.npy`).
  - **Phase across loads:** four fresh loads of board A (`A_phrst_load*`, `A_phrst_probe_v144.json`).
- **`latency/`**: the loop-latency study behind L_50 and its two load groups. It holds 5 reloads per board
  (`reloads/`) and 2 cold starts per board (`cold/`). Each load has its deploy, calibration, boxcar-path probe and
  protocol files, and each folder has a `summary.md`. Its `README.md` explains the closure check's centre.
- **`fig8b/`**: the gate-slack sweep per board (`*_gate_probe_box.npz` and its log) and the figure made from it
  (`make_fig8b_v144.py`, values, pdf, png, svg). This is Fig. 7(b) of the paper.
- **`fig7/`**: the rising-edge captures and the frequency sweeps per board (`fig7_capture_*`, `fig7_sweep_*`), with
  `make_fig7_v144.py` and its values. This is Fig. 6 of the paper.
- **`leak_energy/`**: the energy that reaches the DAC before the pulse's 50% point, at two detection thresholds (2,000
  and 8 counts), per board.
- **`logs/`**: console logs of the main campaign's long steps (each phase's calibration, the two NN_live runs and the
  Fig. 6 capture and sweep) that do not sit next to their outputs.
- **`analysis/`**: everything computed from the folders above.
  - **The headline:** `analyze_v144.py` writes `v144_stats.json` and the git-ignored `merged_live.npz`.
  - **Table II and the linear baselines:** the NN_axi emulator (`analyze_axi_emu_v144.py`), the linear baselines
    (`linear_v144.py`, `linear_*`) and the boxcar against the FIR readout (`box_vs_fir_*`).
  - **The figures and their numbers:** the replay channel's class SNR (`channel_v144.*`), the panels of Fig. 2 with the
    per-shot capture delay (`fig4_lags_v144.py`, `fig2_lags_v144.json`), the loop groups (`loop_groups_*`) and the
    resource scaling (`scaling_v144.*`).
  - **Subfolders:** the synthetic-data arms (`r9/`) and the architecture sweep on replayed shots (`arch/`).
  - **The number check:** the results ledger (`make_v144_ledger.py`, `v144_results.json`), the exemptions
    (`make_v144_exempt.py`) and the check of every number in the paper (`check_paper_v144.py`).
  - **Logs:** the runs that regenerated the figures and tables (`regen_figs.log`, `regen_tabs.log`) and
    `run_analyses.log`.
