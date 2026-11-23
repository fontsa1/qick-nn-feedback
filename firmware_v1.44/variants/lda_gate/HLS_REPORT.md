# Build 2, HLS part: LDA_live 1.0 (streaming boxcar-576 LDA, drop-in for NN_live 1.5)

A linear discriminator through the same gate. Everything here is offline (no board).

## The LDA (which one, fitted on what)

- The paper's like-for-like linear control on the boxcar path: `lda_99400.py`'s **box576** model
  (`campaign_v144/final/analysis/offline/lda_99400.py`), refitted here by `lda_fit_quant.py` with the same code path:
  class moments on rows [0, 180k) of NN_live's own training set `0528_X_train_box_calibrated.npy`
  (rows 0:10000 + 110000:300000 of `0528_X_train_0_770`), ridge chosen by validation fidelity on rows [180k, 200k) of
  the same training set (ridge 1e-3, validation 96.145 %, as `lda_99400.json`), threshold from the training scores
  (t = -0.67194). **No test row is used** for the fit, the ridge, the threshold, the bit width or the logit scale.
- Check: the refitted float LDA reproduces `lda_99400_preds.npz` box576 decisions on every row of all three sets
  (agreement 1.000 on headline mosaic, A_full, B_full).

## Fixed point (choices)

| item | value | why |
|---|---|---|
| weights | signed 16 bit, wq = round(w * 2^22) (F = 22, the largest that fits) | a DSP48E2 takes 27x18; 16 bits costs nothing extra; 12 bits would also do (1 flip on 99,400) |
| products / sums | exact integers: 16x16 -> 32 bit, two 48-bit accumulators (I and Q) | bit-exact, no rounding anywhere; worst case |S| < 2^37 |
| threshold | decision = S >= T1, T1 = floor(t * 2^22) + 1 = -2,818,315 | equals the float rule S/2^F > t |
| res_o[15:0] | pseudo-logit sat16(((S - T1) >> 12) + 16), Q.10 | keeps every NN_live host rule: decision <=> logit >= 1/64 (raw 16, the tProc's fb_thr = 16) <=> sigmoid word > 0.5. SH = 12 maps the training class-mean separation to about +-8; no window on disk saturates |
| record | word1/2 = S - T1 (64-bit, sign-extended), word3 = T1, word4 = SH, word5 = logit, word6 = sigmoid(logit) (hls4ml table, as NN_live), word7 = decision | same 8-word layout and addresses; header word 2 stays "NNL1" so host readers accept it, new header word 3 = "LDA1" (0x4C444131) identifies the core |
| ports / framing / pragmas | identical to NN_live.cpp (ap_ctrl_none, axis in_r with register_mode=off, ap_vld res_o, ram_1p out[5120], frame-error counting and drain) | drop-in: the block design changes only the cell's VLNV |
| instance name in the BD | kept `NN_live_0` | every connection, pblock, OOC run name, report filter and build check stays as in v1.44 |

Quantization study (`lda_quant.json`, on the stored gate windows, float vs fixed, decisions that differ):

| weight bits | 6 | 8 | 10 | 12 | 14 | **16** | 18 |
|---|---|---|---|---|---|---|---|
| headline mosaic flips (of 99,400) | 186 | 36 | 15 | 1 | 1 | **1** | 0 |

## Verification

- **csim** (`hls/csim_lda.log`): all 200,000 v1.44 NN_live captures on disk (both boards, both runs, the words exactly
  as the gate passed them, `live_words`), streamed through LDA_live and compared bit for bit with the Python model
  `lda_model.py`: res_o 0 mismatches, record words 0, sigmoid>0.5 == decision 0, capture 0, header ok, both framing
  faults (short window, missing TLAST) handled as NN_live. `LDA_LIVE_CSIM PASS`.
- **RTL sim** (`rtl_sim/tb_lda.sv`, copy of NN_live's tb_live.sv with the DUT swapped; `rtl_sim/xsim_lda.txt`):
  live_window_gate + generated LDA_live Verilog vs QICK's buffer.sv and vs the Python model on 24 real windows
  (12 extreme, 12 nearest the threshold): 0 mismatches. **Latency: gate TLAST beat -> res_o_ap_vld = 8 cycles
  = 14.5 ns** (NN_live 1.5 in the same testbench: 9 cycles = 16.3 ns).

## Fidelity: fixed point vs float vs NN_live (csim on the stored windows, `lda_csim_score.json`)

| set (n = 99,400 each) | LDA fixed (csim) | LDA float | fixed - float | NN_live (v1.44, same shots) | NN_live - LDA fixed, 95 % CI, exact p |
|---|---|---|---|---|---|
| headline mosaic (A run 1 rows <50k + B run 1 rows >=50k) | 95.473 | 95.472 | +0.001 (1 flip) | 95.600 | +0.128 [+0.077, +0.179], p = 1.0e-6 |
| board A, full split | 95.466 | 95.465 | +0.001 (1 flip) | 95.547 | +0.081 [+0.030, +0.133], p = 0.0022 |
| board B, full split | 95.475 | 95.475 | 0.000 (0 flips) | 95.616 | +0.141 [+0.090, +0.192], p = 8.5e-8 |

Quantization loss: none measurable (one decision of 99,400 changes on board A's rows, in LDA's favour). These are
replay numbers on windows captured by v1.44; on hardware the windows are re-acquired, so the board run measures the
same classifier on fresh captures (and `check_board_lda.py` re-checks it bit for bit against `lda_model.py`).

## C-synthesis (552.96 MHz target, 1.808 ns, 12.5 % uncertainty; `hls/reports/`)

| | LDA_live 1.0 | NN_live 1.5 |
|---|---|---|
| estimated clock | 1.501 ns | 1.501 ns |
| ACC_L | II = 1, iteration latency 10, 584 cycles | II = 1, iteration latency 11, 585 cycles |
| last sample -> res_o (RTL sim) | **8 cycles, 14.5 ns** | 9 cycles, 16.3 ns |
| LUT / FF (csynth estimate) | 1,531 / 1,171 | 2,625 / 1,958 |
| DSP | 2 | 4 |
| BRAM_18K | 1 (sigmoid table, record only) | 1 |

Routed numbers are in `REPORT.md` (from the full build). IP: `ip/xilinx_com_hls_LDA_live_1_0.zip`
(sha256 e219dee4358806ed3c51fcea02304f5c53c28b3faec68f0ed2d9ba0034f0dd65), VLNV `xilinx.com:hls:LDA_live:1.0`.

## Files

`lda_fit_quant.py` (+ `.log`, `lda_quant.json`, `lda_weights.npz`, `lda_quant_preds.npz`), `lda_model.py`
(bit-exact model and csim vector writer), `hls/` (sources, testbench, Tcl, `run_hls.bat`, logs, reports),
`lda_csim_score.py` (+ `.json`, `.log`), `rtl_sim/` (testbench, vector maker, run script, xsim log),
`check_board_lda.py` (for after the board run). The HLS project itself and the 456 MB csim vectors are in
`$QICK_WORK/hls_lda/` (regenerate the vectors with `lda_model.py --tb <dir>`).
