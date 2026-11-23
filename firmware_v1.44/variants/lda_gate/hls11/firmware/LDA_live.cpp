// LDA_live: streaming linear (LDA / matched-filter) discriminator, a drop-in replacement for NN_live 1.5.
//
// Same structure as NN_live.cpp: one {Q, I} word per readout clock (clk_adc0_x2, 552.96 MHz) from
// live_window_gate, N_SAMP words per trigger with TLAST on the last, ACC_L at II = 1 (the readout cannot stall), the
// decision formed inside the last iteration and written to res_o as a one-cycle ap_vld strobe, and the record written
// afterwards. Only the classifier differs:
//
//   SI = -T1 + sum_n wI[n] * I_n,   SQ = sum_n wQ[n] * Q_n     (exact integers, 16-bit weights from LROM)
//   D  = SI + SQ = S - T1;          decision = D >= 0           (S >= T1 <=> S / 2^F > t, the float LDA rule)
//   logit = sat16((D >> LDA_SH) + 16)                          (pseudo-logit in Q.10; logit >= 1/64 <=> decision)
//
// The two products per sample are kept in two accumulators so each maps onto one DSP48E2 multiply-accumulate.
// The weights come from lda_fit_quant.py (lda_99400.py's box576 recipe, training rows only); the bit-exact
// reference is lda_model.py.

#include "LDA_live.h"
#include "nnet_utils/nnet_activation.h"

struct sigmoid_config8 : nnet::activ_config {     // as parameters.h of NN_live (record word 6 only)
    static const unsigned n_in = 1;
    static const unsigned table_size = 1024;
    static const unsigned io_type = nnet::io_parallel;
    static const unsigned reuse_factor = 1;
    typedef sigmoid_table_t table_t;
};

void LDA_live(live_stream_t &in, ap_uint<64> *res_o, ap_uint<32> out[OUT_WORDS]) {
    #pragma HLS INTERFACE ap_ctrl_none port=return
    // no input register slice: live_window_gate's outputs are registered
    #pragma HLS INTERFACE axis port=in register_mode=off
    #pragma HLS INTERFACE ap_vld port=res_o
    #pragma HLS INTERFACE bram port=out storage_type=ram_1p

    // 1.1: ROM in block RAM with its output register (1.0: LUTRAM, latency 1; its 576-deep decode missed 1.808 ns by 65 ps in the routed build)
    #pragma HLS BIND_STORAGE variable=LROM type=rom_1p impl=bram latency=2

    static ap_uint<32> shots = 0;
    static ap_uint<32> frame_err = 0;

    lacc_t si_acc = -lacc_t(LDA_T1);
    lacc_t sq_acc = 0;
    lacc_t dsum = 0;
    bool early_last = false;
    bool last_ok = false;
    ap_uint<16> logit_raw = 0;
    ap_uint<1> decision = 0;

ACC_L:
    for (int n = 0; n < N_SAMP; n++) {
        #pragma HLS PIPELINE II=1 style=frp
        in_word_t w = in.read();
        ap_int<16> si = w.data.range(15, 0);
        ap_int<16> sq = w.data.range(31, 16);
        ap_uint<32> r = LROM[n];
        ap_int<16> wi = r.range(15, 0);
        ap_int<16> wq = r.range(31, 16);
        ap_int<32> pi = wi * si;
        ap_int<32> pq = wq * sq;
        #pragma HLS BIND_OP variable=pi op=mul impl=dsp
        #pragma HLS BIND_OP variable=pq op=mul impl=dsp
        si_acc += pi;
        sq_acc += pq;
        out[CAP_BASE + n] = w.data;
        bool final_word = (n == N_SAMP - 1);
        if (!final_word && w.last) early_last = true;
        if (final_word) {
            last_ok = w.last;
            lacc_t d = si_acc + sq_acc;            // = S - T1, with this sample included
            dsum = d;
            bool dec_v = !d[47];
            // logit: arithmetic shift (floor), + 1/64, saturating 16-bit cast. Sign tests on wide values only.
            ap_int<48> v = (d >> LDA_SH) + 16;
            bool ovp = (v > 32767), ovn = (v < -32768);
            logit_raw = ovp ? ap_uint<16>(0x7FFF) : ovn ? ap_uint<16>(0x8000) : ap_uint<16>(v.range(15, 0));
            decision = dec_v ? 1 : 0;
            if (w.last && !early_last) {
                ap_uint<64> r64 = 0;
                r64.range(15, 0) = logit_raw;
                r64.range(44, 16) = shots.range(28, 0);
                r64[63] = decision;
                *res_o = r64;
            }
        }
    }

    if (early_last || !last_ok) {
        frame_err++;
        out[HDR_FRAME_ERR] = frame_err;
        if (!last_ok) {
        DRAIN_L:
            while (!in.read().last) {
                #pragma HLS PIPELINE II=1
            }
        }
        return;
    }

    // probability, for the record only (same table sigmoid as NN_live, so word 6 > 0.5 <=> decision)
    q_output_alpha_result_t l10[1];
    result_t l8[1];
    l10[0].range(15, 0) = logit_raw;
    nnet::sigmoid<q_output_alpha_result_t, result_t, sigmoid_config8>(l10, l8);

    int base = REC_BASE + (int)(shots % N_REC) * REC_WORDS;
    ap_uint<32> r_l10 = 0, r_l8 = 0;
    r_l10.range(15, 0) = logit_raw;
    r_l8.range(17, 0) = l8[0].range(17, 0);
    ap_int<16> dhi16 = dsum.range(47, 32);
    ap_int<32> dhi = dhi16;                // sign-extended upper bits (range() alone is unsigned)
    out[base + 0] = shots;
    out[base + 1] = dsum.range(31, 0);
    out[base + 2] = (ap_uint<32>)dhi;
    out[base + 3] = (ap_uint<32>)(ap_int<32>)(LDA_T1 & 0xFFFFFFFFLL);
    out[base + 4] = LDA_SH;
    out[base + 5] = r_l10;
    out[base + 6] = r_l8;
    out[base + 7] = decision;
    shots++;
    out[HDR_SHOTS] = shots;
    out[HDR_FRAME_ERR] = frame_err;
    out[HDR_MAGIC] = LIVE_MAGIC;
    out[HDR_CLASSIFIER] = LDA_MAGIC;
}
