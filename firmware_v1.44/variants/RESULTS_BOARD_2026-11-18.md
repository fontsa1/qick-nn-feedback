# Board results of the variant builds, 2026-11-18

Both boards ran `firmware_v1.44/variants/board_queue.sh` (b1, arms, lda) to completion. Both are back on v1.44 with its calibration.

## Pulse-gain arms, full split (v1.44)

- **Script and output:** `arms/arms_full_analysis.py` writes `arms/arms_full_analysis.json`; the raw data are `arms/{A,B}_arms_full.npz`.
- **Data:** 99,400 traces per board (rows 0-99,999 without the 600 map rows).
- **Checks:** every trace fresh, none late, and decision == on-chip record on all traces.

| Board | Nominal (gain 0.6) | Zero (gain 0) | Zero − nominal [95% CI] | Exact McNemar p |
|---|---|---|---|---|
| A | 95.611 | 95.532 | −0.078 [−0.146, −0.011] | 0.024 |
| B | 95.573 | 95.575 | +0.002 [−0.066, +0.070] | 0.98 |

- **Board B:** the pulse makes no difference, so it does not explain board B's in-loop vs gate-idle deficit (P201).
- **Board A:** the difference runs the other way, with zero gain worse. It is one more test for the Holm family and is not
  adjusted here.
- **Against the gate-idle v1.44 captures of the same rows:** the nominal arm differs by
  - A: +0.008 (run 1 rows, p = 0.90) and +0.117 (run 2 rows, p = 0.018);
  - B: −0.078 (p = 0.12) and −0.006 (p = 0.93).

## LDA_live (build 2b, `v1.44lda11`, timing met: WNS 0.000 ns, 0 failing endpoints)

- **Bitstream:** sha256 b2416b0665f34aa1…, banner `Nov 17 20:42:27`.
- **Checks:** functional, binding-fault, fail-safe, leak and gate-sweep all rc=0, and smoke 20/20 on both boards.
- **Bit-exact:** D, logit and decision equal `lda_model.py` on all 100,000 shots.
- **Output:** `lda_gate/board/live/check_board_lda.json`.

| Set | n | LDA_live (board) | NN_live v1.44, same rows | NN − LDA [95% CI] | Exact McNemar p |
|---|---|---|---|---|---|
| Headline mosaic | 99,400 | 95.537 | 95.600 | +0.063 [−0.009, +0.136] | 0.093 |
| Board A (rows < 50k) | 49,400 | 95.615 | 95.636 | +0.021 [−0.081, +0.124] | 0.70 |
| Board B (rows ≥ 50k) | 50,000 | 95.459 | 95.565 | +0.106 [+0.003, +0.209] | 0.052 |

The fixed-point C-sim of the same LDA scores 95.473 on the headline mosaic (`lda_csim_score.json`).

### Latency (`latency_protocol_lda.py`, delay 29, 100 shots at the operating threshold)

| Board | L_50 ns (sd) | Counter ns | L_buf ns | Boxcar path ns | Self-checks |
|---|---|---|---|---|---|
| A | 173.62 (1.56) | 174.95 | 175.52 | 114.76 | 2 FAIL |
| B | 173.66 (1.47) | 174.66 | 175.29 | 113.45 | all PASS |

- **Board A's two FAILs** (`path_minus_adv` 2.86 vs 1.4 ± 1.0 ns; `op_lbuf_minus_l50` +1.89 vs 2.86 ± 0.85 ns) both
  follow from the boxcar path. It measured 1.3 ns longer on this load than on board B, which is the load-dependent
  converter step of P163.
- **Board A's other checks** pass: segment sum = counter, 9 cycles result − last, and 100/100 pulses.
- **Board A's L_50 is still usable**, but it is from a single load.

## Build-1 remedy (incremental route of build 1 at 245.76 MHz)

- **Stopped:** at 05:25 after 31 min of log silence in route phase 11, under the hang rule.
- **Not usable anyway:** its intermediate WNS was −0.311 ns, worse than build 1's −0.035 ns.
- **Build 1** stays as built, and its board results stand.
