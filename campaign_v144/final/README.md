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
  - **The headline:** `analyze_v144.py` writes `v144_stats.json` and `merged_live.npz`.
  - **Table II and the linear baselines:** the NN_axi emulator (`analyze_axi_emu_v144.py`), the linear baselines
    (`linear_v144.py`, `linear_*`) on the 19,400-row subset, the same baselines on all 99,400 replayed rows of the
    NN_live campaign (`s5_linear_99400_v144.py`, `s5_linear_99400_v144.json`; reads the `live/` captures of
    `DATA_MANIFEST.csv`) and the boxcar against the FIR readout (`box_vs_fir_*`).
  - **The figures and their numbers:** the replay channel's class SNR (`channel_v144.*`), the panels of Fig. 2 with the
    per-shot capture delay (`fig4_lags_v144.py`, `fig2_lags_v144.json`), the loop groups (`loop_groups_*`) and the
    resource scaling (`scaling_v144.*`).
  - **The replay channel's noise and resampling:** the noise the channel adds, per band (`channel_noise_v144.*`), and
    what the linear interpolation of `tools/run_loopback.py` accounts for: its part of the channel's low-pass response,
    the 0.6% time stretch it leaves and the noise power of the replayed traces (`replay_interp_v144.*`). Both read
    `replay20k_A.npy` and `replay20k_B.npy` of `DATA_MANIFEST.csv`.
  - **Subfolders:** the synthetic-data arms (`r9/`) and the architecture sweep on replayed shots (`arch/`).
  - **The number check:** the results ledger (`make_v144_ledger.py`, `v144_results.json`), the exemptions
    (`make_v144_exempt.py`) and the check of every number in the paper (`check_paper_v144.py`).
  - **Logs:** the runs that regenerated the figures and tables (`regen_figs.log`, `regen_tabs.log`) and
    `run_analyses.log`.


## Measurements and checks added after the main campaign

These come from the same v1.44 build and boards. Each one sits next to the campaign folder it extends, and each
script's docstring gives its question and the command that ran it. File names start with the board (`A_`, `B_`). A
`.log` is the console output of the run that wrote the file of the same name. Captures over 5 MB are listed in
`DATA_MANIFEST.csv`.

- **`latency/reloads/` (`rv*`), `latency/stability/`**: 20 further loads per board, and 20 runs on one load of each
  board (`latency_protocol.py` results).
- **`latency/carrier/`**: converter latency against the pulse carrier (`carrier_edge.py`).
- **`latency/jitter/`**: capture-delay jitter without a replayed trace (`jitter_probe.py`).
- **`tests/spacing/`**: the minimum spacing between classified windows (`shot_spacing.py`).
- **`tests/logit_check/`**: NN_live's on-chip sums and logit against the integer reference (`d22_check.py`,
  `nn_live_ref.py`, `d22_v144_logit.py`).
- **`board3/threshold/`**: QICK's own threshold feedback on the same build (`threshold_baseline.py`).
- **`inloop/arms/`**: the conditional pulse's gain arms. It holds the 15,000-row arms (`inloop_arms.py`,
  `arms_analysis.py`) and the full-split arms (`arms_full_analysis.py`).
- **`fig8b/path_slack_sweep.py`**: the loop on QICK's FIR readout against the boxcar path, swept through the late edge.
- **`analysis/offline/`**: analyses without the boards:
  - `lda_99400.py`: LDA paired with NN_live on all 99,400 rows;
  - `window_live.py`: fidelity at live-readout window lengths;
  - `map_trainrows.py` and `map_seeds.sh`: the boxcar domain map refit on training rows, five seeds;
  - `keras_vs_hls4ml.py`: floating-point against fixed-point decisions.
- **`analysis/stats/`**: the paired statistics behind the paper's comparisons. Run them in this order:
  `emulate_live_captures.py`, `t1_holm.py`, `t2346_paired.py`, `t4_find_axi.py`, `t5_estimators.py`,
  `report_tables.py`, `holm_printed.py`, `holm_pass11.py`.
  - `holm_pass11.py` applies the Holm correction over every p-value the paper prints (51 tests); `holm_printed.py`
    is the same count over the 44 printed before the last text pass.
  - `holm_pass*.json` are the recounts after each text pass.
- **`analysis/protocol/`**: the boxcar domain map refit on training rows, scored per board
  (`task2_trainrow_map_perboard.py`, then `task2_summarize.py`). `logs/` holds the leakage audit's run
  (`tools/verify_no_leakage.py`, 29 checks) and its D3 self-test.

The timing of the routed v1.44 design is in `firmware_v1.44/reports/`, and the two variant builds are in
`firmware_v1.44/variants/`. The clock-crossing simulations are in `rtl/sim/`, and the v1.44 scaling recheck is in
`scaling_study/v144/`.

**Older folder names in recorded files.** These files were produced in a working tree that kept them in
`campaign_v144/revision/` and `campaign_v144/revision2/`. Logs, JSON results and reports keep the paths as they were
recorded; the results ledger checks the hashes of several of them. Map those paths as follows:

| Recorded path | Now |
|---|---|
| `campaign_v144/revision/latency/` | `campaign_v144/final/latency/` |
| `campaign_v144/revision/{carrier,jitter}/` | `campaign_v144/final/latency/{carrier,jitter}/` |
| `campaign_v144/revision/spacing/` | `campaign_v144/final/tests/spacing/` |
| `campaign_v144/revision/d22/`, `revision/analysis/d22_v144_logit.*` | `campaign_v144/final/tests/logit_check/` |
| `campaign_v144/revision/threshold/` | `campaign_v144/final/board3/threshold/` |
| `campaign_v144/revision/arms/`, `revision/analysis/arms_analysis.*`, `revision2/arms/` | `campaign_v144/final/inloop/arms/` |
| `campaign_v144/revision/offline/`, `revision/trainrows/` | `campaign_v144/final/analysis/offline/` (`trainrows/` in the manifest) |
| `campaign_v144/revision/scripts/` | beside each result, as listed above |
| `campaign_v144/revision2/stats/`, `revision2/paper_pass/` | `campaign_v144/final/analysis/stats/` |
| `campaign_v144/revision2/protocol/` | `campaign_v144/final/analysis/protocol/` |
| `campaign_v144/revision2/fpga/{reports,tcl}/` | `firmware_v1.44/reports/` |
| `campaign_v144/revision2/fpga/sim/` | `rtl/sim/` |
| `campaign_v144/revision2/fpga/scaling/` | `scaling_study/v144/` |
| `campaign_v144/revision2/rebuilds/build1_tproc245/`, `build2_lda_gate/` | `firmware_v1.44/variants/tproc245/`, `lda_gate/` |
