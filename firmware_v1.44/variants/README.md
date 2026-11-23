# `firmware_v1.44/variants/`: two variant builds of v1.44

Each build changes one thing from v1.44. Both ran on both boards on 2026-11-18. The paper uses them in Sec. IX: the
tProc routes at QICK's stock core clock, and an LDA core in NN_live's place as a control.

| | `tproc245/` (v1.44t245) | `lda_gate/` (v1.44lda) |
|---|---|---|
| Change from v1.44 | tProc core clock at QICK's stock 245.76 MHz (v1.44: 200 MHz) | NN_live replaced by an LDA core with the same interface (boxcar, 576 samples), `LDA_live` |
| Block-design change | the six `/clk_core` parameters (`bd_diff_vs_v144.md`) | one IP reference (`bd_diff_vs_v144.md`) |
| Timing | setup missed by 35 ps in the 552.96 MHz readout clock (QICK's stock readout blocks); core clock met | see `build2_summary.md`; the `hls11/` core (v1.1, weights in block RAM) is the one run on the boards |
| Board results | `board/`: loop latency and QICK's threshold feedback per board | `board/`: loop latency, bit-exact decisions on all 100,000 shots (`board/live/check_board_lda.json`), fidelity |

- **Results:** `RESULTS_BOARD_2026-11-18.md` summarizes the board runs, including the full-split pulse-gain arms. Those
  arms are in `campaign_v144/final/inloop/arms/`.
- **Building:** `REPORT.md` covers the builds, the timing and the post-route remedies. Each build's summary (per-clock
  timing, bus skew, utilization) is written by `summarize_build.py`.
- **Scripts:** the build scripts (`build_*.tcl`, `nnqick_*.tcl`, `hls*/project.tcl`), the LDA model and its quantized
  weights (`lda_model.py`, `lda_fit_quant.py`), its C-simulation score (`lda_csim_score.py`), its RTL simulation
  (`rtl_sim/`) and the board runners (`run_board_b*.sh`, `board_queue.sh`).
- **Settings:** the scripts read the settings of `campaign_v144/env.sh` (`QICK_BOARD_A`, `QICK_BOARD_B`, `QICK_TOP`,
  `QICK_BANNER`, `PYTHON`) and four more:
  - `QICK_REPO`: this repository's root;
  - `QICK_WORK`: a scratch folder for the Vivado and Vitis HLS runs;
  - `QICK_SRC`: a QICK checkout at commit 779dffa;
  - `V144_BUILD_DIR`: the v1.44 Vivado run folder, for comparisons with the v1.44 build.
- **Captures:** the per-shot captures (`.npz`) are listed in `DATA_MANIFEST.csv` for the archive.
