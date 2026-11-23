# Streaming neural-network qubit readout with feedback on QICK

Code, firmware sources and results behind the qick feedback classifier project. Everything here
belongs to the final build, **v1.44**, on the Xilinx RFSoC 4x2 (XCZU48DR) running QICK (tProc v2). Two classifiers are
built from the same recorded readout data [16]:

- **NN_live**, a streaming classifier on the readout's decimated stream. It decides 16.3 ns after the last sample, and its
  decision drives a pulse gate (`dac_gate`) on signal generator 0 and the tProc. Measured loop latency is ~176 ns.
- **NN_axi**, a buffered hls4ml classifier in the conventional QICK deployment, whose results the host reads afterwards.

Run every script from this folder's root; paths in the scripts are relative to it. Some folder names are historical
(`campaign_v140L1/`, `campaign_v143/`, `audit_fixes/`). The paths below say what each one holds.


## Layout

| Path | What it holds |
|---|---|
| `rtl/` | **Our RTL**, the eight modules the build adds to QICK's design: `live_window_gate.v` (window gate in front of NN_live), `boxcar_tap.v` (low-latency decimation), `dac_gate.v` (pulse gate on the DAC stream), `live_res_cdc.v` (decision clock crossing), `trig_sync.v` (classify-trigger synchronizer), `seg_stamp.v` / `rf_tap.v` (timestamps and taps for the latency measurement), `live_rec_wreg.v`; and the CDC constraint (`constraints/live_res_cdc.xdc`). Copies of the files the build script reads from `neural_net4_live/` and `neural_net4_live576/`, identical byte for byte |
| `firmware_v1.44/` | The block design as built (`d_1.bd`: QICK's design with our delta), the bitstream (`OG_build_v1.44.bit`, sha256 `986c861a83be8d01d72db967af894e3d01de2b1c861021d1b5821bc183d7b7c6`), hardware handoff (`.hwh`) and the Vivado build log |
| `neural_net4_live576/rtl/`, `neural_net4_live576/constraints/`, `neural_net4_live/rtl/` | Where the build script reads our RTL and constraint from (`rtl/` holds the same files); also `live_res_axis.v`, which the build does not use, and two unused variants of the CDC constraint |
| `neural_net4_live576s/` | NN_live HLS source (`firmware/NN_live.cpp`), C testbench and vectors, Vitis HLS scripts, hls4ml config, ROM generator; packaged core `NN_live 1.5` (zip) with its C-sim and synthesis logs |
| `neural_net4_tlast/` | NN_axi HLS source (hls4ml network + wrapper), testbench, scripts, synthesis reports; packaged core `NN_axi 1.41` (zip) |
| `vivado_scripts/v1.43/from_qick/` | Building our design from QICK's: `nnqick_from_qick.tcl`, the block-design delta, and the implementation script. These made v1.44 |
| `vivado_scripts/v1.43/` | The same design built earlier in our own project (v1.43): block-design edit (stage 1) and implementation with the full report set (stage 2). Kept for reference |
| `audit_fixes/RB_prep/sim/`, `audit_fixes/RB_prep/hls/rtl_sim/` | RTL simulation: custom blocks against reference models (`final_regression.sh`), and window gate + NN_live kernel on a continuous stream (`run_tb.sh`), with logs |
| `scaling_study/` | Multi-classifier resource count (`resource_scaling.py`) and out-of-context timing runs (`run_ooc*.tcl`, `rtl/`); findings |
| `host/` | Board-side server: `nnqick_server.py` (same as `start_nameserver.ipynb`). This holds the QICK metadata patches for the added blocks, the `NNQickSoc` class and the Pyro server |
| `board_tools/` | Host tools: deploy and verify a bitstream, Jupyter access, server start, calibration storage |
| `notebooks/` | Notebook versions of the main workflows (see Notebooks below) |
| `tools/` | Top-level scripts: replay-channel calibration (`run_calibration.py`), replay (`run_loopback.py`), test subsets (`make_test_subsets.py`, and `build_test100k_real.py` for the full 100,000-row set), the leakage audit (`verify_no_leakage.py`), the synthetic-data generator (`qubit_synth_lib.py`, `generate_*.py`), and the on-board scoring harness |
| `calibration/` | Replay-channel calibration (`k.npy`, `c.npy`: the active pair, written by `run_calibration.py`) and the two label-free domain maps (`k2_loopback.npy` / `c2_loopback.npy` on the FIR path, `box_domain_map.json` on the boxcar path) |
| `data/` | Labels and manifests of the test subsets and replays (`test20k_real_*`, `test100k_real_y.npy`, `loopback20k_real_*`, `domain_calib_y.npy`); the arrays themselves are regenerated or fetched into this folder (see Data) |
| `results/` | Small result files that the analyses read back (three-way comparison, calibration ablation, raw reference) |
| `analysis_scripts/diagnostics/` | Every board measurement: fidelity scoring, bit-exact checks, loop latency, tProc path, boxcar check, functional suite, safety tests, drift |
| `analysis_scripts/analysis/`, `analysis_scripts/characterization/` | Offline analyses: fixed-point emulator, linear baselines, calibration ablation, three-way comparison; readout-path characterization |
| `analysis_scripts/bd_delta/` | Generates our block-design delta from QICK's design and checks that QICK's design plus the delta matches ours |
| `campaign_v144/` | The v1.44 data campaign: both boards at once (`run_all.sh`, per board `run_6_3.sh`), second board session (`run_board2*.sh`), 3 h drift (`run_drift_full.sh`), reload and cold-start latency (`run_loads.sh`), and the offline analyses (`run_analyses.sh`); `env.sh` holds the settings they share |
| `campaign_v144/final/` (`latency/`, `tests/`, `board3/threshold/`, `inloop/arms/`, `analysis/{offline,stats,protocol}/`) | Also the measurements and checks added after the main campaign: further loads and stability, carrier, jitter, shot spacing, the on-chip logit check, QICK's threshold feedback, the pulse-gain arms, the offline studies, the statistics (Holm) and the data-protocol audit; `campaign_v144/final/README.md` lists them |
| `firmware_v1.44/reports/`, `firmware_v1.44/variants/`, `rtl/sim/`, `scaling_study/v144/` | Timing reports of the routed v1.44 design; two variant builds with their board runs (tProc at 245.76 MHz, an LDA core in NN_live's place); clock-crossing simulations; the v1.44 scaling recheck |
| `audit_fixes/R18/`, `audit_fixes/R9/`, `audit_fixes/R3_R2/`, `audit_fixes/R10/`, `campaign_v140L1/` | In-loop campaign, synthetic-data study, linear baselines, fixed-point scoring, architecture and window sweeps (scripts called by the campaign and the analysis) |
| `audit_fixes/R18_full/` | The in-loop analysis on all 99,400 rows per board (`analyze_full.py`; its six per-shot inputs are in `DATA_MANIFEST.csv`) |
| `audit_fixes/R5/`, `audit_fixes/R14/`, `audit_fixes/R8_R1/` | Stored results that generators read: the offline baselines of Table II (`R5/evaluate_results.json`), the noise-model separations quoted in Appendix B (`R14/noise_model_table.json`), the matched-filter truncation curves (`R8_R1/out/`) |
| `audit_fixes/R13/` | Classifies the failing setup endpoints of an earlier build (v1.40L10) from a Vivado dump that is not shipped; kept as the method, not used for any v1.44 number |
| `campaign_v140/` | Aligned captures of the v1.40 runs, read by `campaign_v140L1/live20k_stats.py` for the earlier builds' scored sets |
| `analysis_scripts/acquisition/` | Training-set construction (domain maps) and model training/export (`export_signed_domain_model.py`) |
| `models/` | The three deployed networks: NN_live on the boxcar path (`..._w576_box`), NN_live on the FIR path (`..._w576`), NN_axi (`model_v140_200k_...`); and `model_v140L3_w576_...`, an earlier 576-sample network that `campaign_v140L1/check_live_bitexact.py --l3` checks |
| `campaign_v144/final/analysis/` | Analysis of the v1.44 data, and the results ledger: `make_v144_ledger.py` writes `paper_notes/V144_RESULTS.md`, `check_paper_v144.py` checks a draft's numbers against it |
| `campaign_v143/` | Files of the v1.43 campaign that the v1.44 scripts still read, among them the results ledger's row template (`final/analysis/v143_results.json`). The v1.43 ledger scripts here are kept for reference; most of their inputs are not shipped, so they do not run |

## Environment

Python 3.12 (we used 3.12.9 on Windows 11). `requirements.txt` pins the host packages we used; install them with
`pip install -r requirements.txt`. Its comments name what pip does not install:
- Vivado and Vitis HLS 2023.1;
- g++ for the bit-accurate emulator (MSYS2 ucrt64 on Windows, expected at `C:/msys64/ucrt64/bin`);
- Git Bash for the campaign `.sh` scripts.

They also record the software on the boards.

## Data

The recorded readout traces are the public dataset of [16], Zenodo record 14427490
([doi:10.5281/zenodo.14427490](https://doi.org/10.5281/zenodo.14427490)). They are not in this repository.
`DATA_MANIFEST.csv` lists every data file the scripts read that is not shipped, with its size and sha256 and one of
two notes:
- **"derived from the public dataset"**: download the record, or regenerate the file from it;
- **"large data; archive separately"**: the board captures behind the results, too large for the repository.

Where the files go:
- **Repository root:** the dataset's four arrays (`0528_X_train_0_770.npy`, `0528_y_train_0_770.npy`,
  `0528_X_test_0_770.npy`, `0528_y_test_0_770.npy`), and the arrays built from them: the domain-mapped training sets,
  the synthetic sets (`x_50k*`, `x_synth_v2`, `Phi*`) and `X_2_padded_11k`. Scripts read them from the root.
- **`data/`:** the test subsets (`test20k_real_X.npy`, `test100k_real_X.npy`). Their labels and manifests are shipped
  there. `python tools/make_test_subsets.py` writes `test20k_real` from `0528_X_test_0_770.npy`. `test100k_real` is
  the whole test split: its first 20,000 rows are `test20k_real`, and `test100k_real_manifest.json` lists the source
  row of every row (`source_indices`) and the sha256 of both arrays.

The generator scripts are in `tools/` (`generate_*.py`, synthetic data) and `analysis_scripts/acquisition/`
(`build_domain_calibrated_training_set.py`, `build_box_training_set.py`, the domain-mapped training sets).

## Rebuilding the firmware

Tools: Vivado and Vitis HLS 2023.1; QICK firmware sources at commit `779dffa`
([openquantumhardware/qick](https://github.com/openquantumhardware/qick), firmware version 0.2.420, MIT licence). We
use QICK's IP unmodified, together with its `qick_tprocv2_4x2_standard` constraints (`ios.xdc`, `timing.xdc`).

Our design is QICK's standard tProc v2 design for the RFSoC 4x2 with our blocks added. You build QICK's design with
QICK's own scripts, and then one script of ours turns it into ours.

1. **QICK's project.** Check out QICK at commit `779dffa`, then run its project script:
   ```
   cd firmware/projects/qick_tprocv2_4x2_standard
   vivado -mode batch -source proj.tcl
   ```
   This makes `top/top.xpr` with block design `d_1`. You don't need to build QICK's bitstream. Use a full checkout:
   QICK's IP cores pull shared sources from `firmware/hdl/` and `firmware/common_ip_files/`, and IP generation fails
   if those folders are missing. On Windows, keep the
   checkout at a short path (for example `C:\qick`). Vivado fails on paths longer than 260 characters, and QICK's IP
   paths are deep.
2. **Our design on top.** From this repository's root:
   ```
   vivado -mode batch -source vivado_scripts/v1.43/from_qick/nnqick_from_qick.tcl -tclargs <QICK>/firmware/projects/qick_tprocv2_4x2_standard/top/top.xpr <new folder>
   ```
   This saves QICK's project as a new project in `<new folder>` and leaves QICK's own project unchanged. It then
   installs the two HLS cores from their zips, adds our RTL and the CDC constraint, and applies
   `nnqick_bd_delta.tcl` to the block design. Use forward slashes in both paths.
3. **Implementation.** From `<new folder>`, run
   `vivado -mode batch -source <repo>/vivado_scripts/v1.43/from_qick/build_nnqick.tcl`. It's the flow we ran
   (`vivado_scripts/v1.43/build_v1.43.tcl`), with the same checks, constraints, directives and reports, adapted to
   QICK's design name. It writes `OG_build_v1.43.bit` and `.hwh`.

These three steps made the paper's firmware, v1.44: the script's outputs, renamed `OG_build_v1.44`. The scripts sit in
`vivado_scripts/v1.43/` because the design is v1.43's; v1.44 is the build they produced from QICK's project.

**What the delta changes in QICK's design** (`vivado_scripts/v1.43/from_qick/nnqick_bd_delta.tcl`):
- Removes the time tagger and its DMA path.
- Changes six QICK settings:
  - The tProc core clock (`clk_core`) runs at 200 MHz instead of 245.76 MHz.
  - The tProc gets a fourth input port, which receives NN_live's result.
  - Readout 0's broadcaster gets a third output, which feeds the boxcar.
  - The DDR4 buffer is 512 bits wide.
  - The AXI interconnect has five more outputs.
  - The DMA SmartConnect has one fewer input.
- Adds our blocks and wiring, and sets the address map.

We checked the result in Vivado. QICK's design at `779dffa` plus the delta matches our v1.43 block design in every
cell, every setting, all connectivity and the whole address map. The only differences are the instance-name prefix
(`d_1_` instead of `OG_build_`), one unconnected net stub, and two internal address exclusions inside QICK's AXI
interconnect. None of them changes the hardware.

**The exact design.** `firmware_v1.44/d_1.bd` is the block design as built for v1.44. It doesn't depend on QICK's
project scripts, only on QICK's IP repository at `779dffa`, so it still works if a later QICK release reorganises its
standard design. To use it, create a project for `xczu48dr-ffvg1517-2-e` with board part
`realdigital.org:rfsoc4x2:part0:1.0`. Add QICK's `firmware/ip` and the two cores as IP repositories, add our RTL (the eight files in `rtl/`),
add the block design, then QICK's `ios.xdc` and `timing.xdc` and our `rtl/constraints/live_res_cdc.xdc`.

**HLS cores (optional).** The packaged cores are included. To rebuild them, run `vitis_hls -f csim_live.tcl`,
`csynth_live.tcl` and `export_live.tcl` in `neural_net4_live576s/`, and the `*_tlast.tcl` scripts in
`neural_net4_tlast/`.

`analysis_scripts/bd_delta/diff_bd.py` repeats the check above. Regenerating the delta from the two block designs also needs the export of our v1.43 block design, which is not shipped.

The v1.44 build meets all setup and hold constraints at sign-off (WNS 0.000 ns, WHS 0.010 ns; paper Table III). One
bus-skew constraint misses: on the decision's crossing into the DAC domain (`live_res_cdc_1`), the skew is 2.352 ns
against the 2.000 ns set in `rtl/constraints/live_res_cdc.xdc` (slack −0.352 ns). In RTL simulation of the crossing
at 491.52 MHz (`audit_fixes/RB_prep/sim/tb_cdc_skew.sv`), 4.0 ns of skew corrupted none of 3,000 results and 4.5 ns
corrupted 664. No corrupted result appeared in the bit-exact or in-loop runs on either board. The routed timing,
utilization and bus-skew reports are in `paper_tables/table3/data/`; they are the v1.44 build's (the build scripts are
v1.43's, so the checkpoint inside them is named `v1.43_routed.dcp`).

## Running on a board

PYNQ image on the RFSoC 4x2, with QICK installed. Copy `firmware_v1.44/OG_build_v1.44.bit` and its `.hwh`
to the same folder on the board (by default `/home/xilinx/jupyter_notebooks/`) and run `host/nnqick_server.py` there,
or open `host/start_nameserver.ipynb` in the board's Jupyter, with `QICK_NS_HOST` set to the board's address and
`QICK_BITFILE` to the bitstream's path if it is elsewhere. Host scripts reach the board through
Pyro4 (`QICK_NS_HOST`) and its Jupyter server (`PYNQ_JUPYTER_PASSWORD`, default `xilinx`). The server notebook on the
board is expected as `start nameserver.ipynb`; set `QICK_SERVER_NB` if yours has another name. The replay channel is a
coax cable on the same board from signal generator 0's DAC output to readout 0's ADC input (paper Sec. IV); the scripts
use these two channels. Calibrate with `tools/run_calibration.py`, then follow `campaign_v144/run_all.sh`.

The campaign runners read their settings from `campaign_v144/env.sh`: the two boards' addresses (`QICK_BOARD_A`,
`QICK_BOARD_B`, required), the folder with the bitstream (`QICK_TOP`, default `firmware_v1.44`), the build timestamp
the board must report (`QICK_BANNER`, read from the `.hwh` by default, so a rebuilt bitstream needs no edit) and
`PYTHON`. Hand runs of the diagnostics also read `QICK_LIVE_N` (576 for the deployed build) and `QICK_TAG` (the
build tag in output file names, default `v144`). The campaign uses two boards; the single-board steps (`run_6_3.sh A`, `run_drift_full.sh B`, ...) run alone.
The latency study's cold starts need a power cycle by hand: `campaign_v144/README.md` gives the procedure.

We ran the scripts on Windows 11 with Git Bash. The v1.44 campaign scripts change to `$REPO_ROOT`, or to the repository
root found from their own path. Python scripts run from the repository root; the HLS Tcl scripts run in their own
folder (`neural_net4_live576s/`, `neural_net4_tlast/`) and `scaling_study/` scripts as their docstrings say. The host
library is `qick` 0.2.414 (`requirements.txt`); the firmware is built from QICK's sources at `779dffa` (firmware
version 0.2.420), and `host/nnqick_server.py` patches the library's metadata for the added blocks.

## Reproducing the paper's numbers, figures and tables

From the repository root, with `PYTHON` set to your interpreter:
1. **Data.** Fetch the dataset (see Data), then `python tools/make_test_subsets.py` (it will not overwrite the
   shipped subsets without `--force`) and
   `python tools/build_test100k_real.py --src-dir . --manifest-dir data --out data`.
2. **Leakage audit.** `python tools/verify_no_leakage.py`. It lists every check and what it tests; a check whose
   inputs are missing is reported BLOCKED. The run behind the paper is `campaign_v144/final/analysis/verify_no_leakage.log`.
3. **Analyses of the campaign data.** `bash campaign_v144/run_analyses.sh` (log in `campaign_v144/final/analysis/`).
   The paired statistics are in `campaign_v144/final/analysis/stats/` (run order in its README).
4. **Results ledger.** `python campaign_v144/final/analysis/make_v144_ledger.py` writes `paper_notes/V144_RESULTS.md`;
   (it overwrites the shipped copy); `--verify` is the read-only check against its sources. `check_paper_v144.py <draft.txt>` checks a draft's numbers against it.

Other READMEs: `campaign_v144/README.md` (running the campaign, cold starts), `campaign_v144/final/README.md` (what
each result folder holds), `campaign_v144/final/latency/README.md`,
`firmware_v1.44/variants/README.md`, `paper_figures/README.md`, `paper_tables/README.md`.

## Notebooks

`notebooks/` holds self-contained versions of the main workflows, written to be read, run and changed. Each one
carries its own code: nothing is imported from this repository, only numpy, scipy, matplotlib, qick and Pyro4, plus
TensorFlow, QKeras and hls4ml for the training ones. Run them from the `notebooks/` folder; they read data from the
repository root (`DATA_DIR = ".."`) and write to `notebooks/outputs/`.

| Notebook | Needs a board | What it does |
|---|---|---|
| `01_calibrate_replay_channel` | yes | Two-pass calibration of the DAC → coax → ADC loopback, (k, c) |
| `02_replay_recorded_traces` | yes | Shuffled, balanced test subset; predistort, replay, check the class structure survives |
| `03_train_and_export_classifier` | no | Domain map, ternary QKeras network with seed selection, hls4ml export with the firmware's precisions (reproduces the deployed models) |
| `04_bit_accurate_fixed_point` | no | Compile the hls4ml C++ model and compare it with floating point on replayed traces |
| `05_feed_forward_on_the_decision` | yes | The feedback loop: gate calibration, in-loop shots, pulse/gate/decision agreement, unsafe count, loop latency |
| `06_synthetic_readout_data` | no | The synthetic-data generator (reproduces the paper's set bit for bit with the pinned package versions) and what it misses |
| `07_readout_noise` | no | Noise statistics of the recorded data, matched-filter ceiling, decay test |
| `08_nn_live_and_nn_axi_results` | optional | NN_live and NN_axi fidelities from the campaign data, board and classifier comparisons, NN_live bit-exact check; optional live capture |


## Third-party components

The MIT licence in `LICENSE` covers this repository except for the third-party files listed in `NOTICE`:
- hls4ml's `nnet_utils` headers and the code hls4ml generated for our networks, and the Xilinx `ap_types` headers,
  under Apache-2.0 (`LICENSES/Apache-2.0.txt`);
- one QICK file, `audit_fixes/RB_prep/sim/buffer.sv`, used in RTL simulation, under QICK's MIT licence
  (`LICENSES/QICK-MIT.txt`). The firmware build takes QICK's IP from a QICK checkout and does not copy it.

The recorded traces are the public dataset of [16], Zenodo record 14427490, under the licence stated on that record.
