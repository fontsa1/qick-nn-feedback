#ifndef LDA_LIVE_H_
#define LDA_LIVE_H_

// LDA_live: drop-in replacement for NN_live 1.5 (neural_net4_live576s) with the boxcar-576 LDA as the classifier.
// Same ports, same framing, same res_o layout, same record memory layout, so live_window_gate -> classifier ->
// live_res_cdc_0/1 -> dac_gate / tProc s3 and every host reader are unchanged. Only the classifier differs.

#include "ap_axi_sdata.h"
#include "ap_int.h"
#include "hls_stream.h"

#include "LDA_live_rom.h"
#include "defines.h"

// One readout sample per word, as axis_dyn_readout_v1.m1_axis emits it: bits [15:0] = I, [31:16] = Q, signed.
typedef hls::axis<ap_uint<32>, 0, 0, 0> in_word_t;
typedef hls::stream<in_word_t> live_stream_t;

// Per-shot result (identical layout to NN_live), a one-cycle ap_vld strobe:
//   [15:0]  pseudo-logit, Q.10 (ap_fixed<16,6> raw bits): sat16(((S - LDA_T1) >> LDA_SH) + 16)
//   [44:16] shot index, low 29 bits
//   [63]    decision: S >= LDA_T1   (equivalently logit >= 1/64, as for NN_live)
#define DECISION_LOGIT_MIN 0.015625

#define N_SAMP 576   // window length, samples [0, 576) after the trigger

// Output BRAM, 32-bit words (same map as NN_live.h)
#define HDR_SHOTS     0
#define HDR_FRAME_ERR 1
#define HDR_MAGIC     2     // kept "NNL1" so the host readers accept the records unchanged
#define HDR_CLASSIFIER 3    // new: "LDA1" identifies this core (NN_live leaves word 3 at 0)
#define CAP_BASE      16
#define REC_BASE      1024
#define REC_WORDS     8     // shot, D[31:0], D[47:32] (sign-extended), T1[31:0], LDA_SH, logit, sigmoid(logit), decision
#define N_REC         512
#define OUT_WORDS     (REC_BASE + N_REC * REC_WORDS)   // 5120
#define LIVE_MAGIC    0x4E4E4C31                       // "NNL1"
#define LDA_MAGIC     0x4C444131                       // "LDA1"

// Accumulators: exact integers. |sum_n w*x| <= sum|w| * 32768 < 2^40 for 16-bit weights; 48 bits (a DSP P register).
typedef ap_int<48> lacc_t;

void LDA_live(live_stream_t &in, ap_uint<64> *res_o, ap_uint<32> out[OUT_WORDS]);

#endif
