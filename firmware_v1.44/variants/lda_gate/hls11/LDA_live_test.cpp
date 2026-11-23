// csim testbench for LDA_live (structure follows neural_net4_live576s/NN_live_test.cpp).
//
// For every window in <TB>/lda_words.bin (all v1.44 NN_live captures, the words exactly as live_window_gate passed
// them) it streams the N_SAMP words with TLAST on the last, then checks bit for bit against the Python model
// (lda_model.py, <TB>/lda_expect.bin): res_o (logit, shot index, decision), the record words (D, T1, SH, logit,
// decision), that sigmoid(logit) > 0.5 equals the decision, the header counters and magic words, and the capture.
// Then the two framing faults of NN_live_test (short window, missing TLAST): one frame error each, result dropped,
// next window scored correctly. It writes every decision and logit to <TB>/lda_csim_out.bin for scoring.
//
// TB directory: env LDA_TB_DIR, default tb_data. LDA_N=<n> limits the run.

#include <cstdio>
#include <cstdlib>
#include <fstream>
#include <string>
#include <vector>

#include "firmware/LDA_live.h"

static ap_uint<32> out_mem[OUT_WORDS];
static const ap_uint<64> NO_RESULT = 0xDEADBEEFDEADBEEFULL;

static void push_window(live_stream_t &s, const uint32_t *w, int n, bool last_on_final) {
    for (int k = 0; k < n; k++) {
        in_word_t x;
        x.data = w[k];
        x.keep = -1;
        x.strb = -1;
        x.last = (last_on_final && k == n - 1) ? 1 : 0;
        s.write(x);
    }
}

int main() {
    std::string tb = std::getenv("LDA_TB_DIR") ? std::getenv("LDA_TB_DIR") : "tb_data";
    std::ifstream fw(tb + "/lda_words.bin", std::ios::binary), fe(tb + "/lda_expect.bin", std::ios::binary);
    if (!fw || !fe) { std::printf("ERROR: tb_data missing in %s; run lda_model.py --tb\n", tb.c_str()); return 1; }
    int32_t n_all = 0, n_exp = 0;
    fw.read((char *)&n_all, 4);
    fe.read((char *)&n_exp, 4);
    if (n_all != n_exp) { std::printf("ERROR: words/expect disagree\n"); return 1; }
    std::vector<uint32_t> words((size_t)n_all * N_SAMP);
    std::vector<long long> eD(n_all);
    std::vector<int32_t> eL(n_all), eDec(n_all);
    fw.read((char *)words.data(), words.size() * 4);
    fe.read((char *)eD.data(), eD.size() * 8);
    fe.read((char *)eL.data(), eL.size() * 4);
    fe.read((char *)eDec.data(), eDec.size() * 4);
    int n = n_all;
    if (const char *e = std::getenv("LDA_N")) n = std::min(n, std::atoi(e));

    live_stream_t in("in");
    for (int k = 0; k < OUT_WORDS; k++) out_mem[k] = 0;
    std::vector<int32_t> got_dec(n), got_logit(n);
    long bad_res = 0, bad_rec = 0, bad_sig = 0, bad_cap = 0, no_res = 0, ones = 0;
    for (int s = 0; s < n; s++) {
        const uint32_t *w = &words[(size_t)s * N_SAMP];
        push_window(in, w, N_SAMP, true);
        ap_uint<64> res = NO_RESULT;
        LDA_live(in, &res, out_mem);
        int base = REC_BASE + (s % N_REC) * REC_WORDS;
        unsigned lraw = (unsigned)(eL[s] & 0xFFFF);
        if (res == NO_RESULT) { no_res++; got_dec[s] = -1; got_logit[s] = 0; continue; }
        ap_uint<64> r = res;
        got_dec[s] = (int)r[63];
        got_logit[s] = (int)(int16_t)(uint16_t)r.range(15, 0).to_uint();
        ones += got_dec[s];
        if ((unsigned)r.range(15, 0) != lraw || (int)r[63] != eDec[s] || r.range(44, 16) != (unsigned)(s & 0x1FFFFFFF)) bad_res++;
        unsigned long long D = (unsigned long long)eD[s];
        if (out_mem[base + 0] != (unsigned)s || out_mem[base + 1] != (unsigned)(D & 0xFFFFFFFFULL) ||
            out_mem[base + 2] != (unsigned)((D >> 32) & 0xFFFFFFFFULL) ||
            out_mem[base + 3] != (unsigned)(LDA_T1 & 0xFFFFFFFFLL) || out_mem[base + 4] != (unsigned)LDA_SH ||
            out_mem[base + 5] != lraw || out_mem[base + 7] != (unsigned)eDec[s])
            bad_rec++;
        result_t p;
        p.range(17, 0) = out_mem[base + 6].range(17, 0);
        if ((p > (result_t)0.5) != (eDec[s] == 1)) bad_sig++;
        for (int k = 0; k < N_SAMP; k += 97)
            if (out_mem[CAP_BASE + k] != w[k]) bad_cap++;
        if (s < 3 || s % 50000 == 0)
            std::printf("shot %6d  D %lld  logit %d  dec %d  sigmoid %.6f\n", s, eD[s], got_logit[s], got_dec[s], p.to_float());
    }
    bool hdr_ok = out_mem[HDR_SHOTS] == (unsigned)n && out_mem[HDR_FRAME_ERR] == 0 && out_mem[HDR_MAGIC] == LIVE_MAGIC &&
                  out_mem[HDR_CLASSIFIER] == LDA_MAGIC;

    // framing faults (as NN_live_test.cpp)
    long fault_bad = 0;
    const uint32_t *w0 = &words[0];
    ap_uint<64> res;
    unsigned fe0 = out_mem[HDR_FRAME_ERR], sh0 = out_mem[HDR_SHOTS];
    push_window(in, w0, N_SAMP - 1, true);
    push_window(in, w0, N_SAMP, true);
    push_window(in, w0, N_SAMP, true);
    res = NO_RESULT;
    LDA_live(in, &res, out_mem);
    bool p1 = out_mem[HDR_FRAME_ERR] == fe0 + 1 && res == NO_RESULT && out_mem[HDR_SHOTS] == sh0;
    LDA_live(in, &res, out_mem);
    bool p2 = res != NO_RESULT && in.empty() && (int)res[63] == eDec[0] && (unsigned)res.range(15, 0) == (unsigned)(eL[0] & 0xFFFF) &&
              out_mem[HDR_SHOTS] == sh0 + 1;
    std::printf("short window      : frame_err %u -> %u, dropped pass %s, next window scored %s\n", fe0,
                (unsigned)out_mem[HDR_FRAME_ERR], p1 ? "ok" : "WRONG", p2 ? "ok" : "WRONG");
    if (!p1 || !p2) fault_bad++;
    unsigned fe1 = out_mem[HDR_FRAME_ERR], sh1 = out_mem[HDR_SHOTS];
    std::vector<uint32_t> tail(10, 0x00010001u);
    push_window(in, w0, N_SAMP, false);
    push_window(in, tail.data(), 10, true);
    push_window(in, w0, N_SAMP, true);
    res = NO_RESULT;
    LDA_live(in, &res, out_mem);
    bool q1 = out_mem[HDR_FRAME_ERR] == fe1 + 1 && res == NO_RESULT && out_mem[HDR_SHOTS] == sh1;
    LDA_live(in, &res, out_mem);
    bool q2 = res != NO_RESULT && in.empty() && (int)res[63] == eDec[0] && out_mem[HDR_SHOTS] == sh1 + 1;
    std::printf("missing TLAST     : frame_err %u -> %u, dropped pass %s, next window scored %s\n", fe1,
                (unsigned)out_mem[HDR_FRAME_ERR], q1 ? "ok" : "WRONG", q2 ? "ok" : "WRONG");
    if (!q1 || !q2) fault_bad++;

    std::ofstream fo(tb + "/lda_csim_out.bin", std::ios::binary);
    fo.write((const char *)&n, 4);
    fo.write((const char *)got_dec.data(), (size_t)n * 4);
    fo.write((const char *)got_logit.data(), (size_t)n * 4);
    fo.close();

    std::printf("\n=== LDA_live csim: %d shots (decision=1: %ld) ===\n", n, ones);
    std::printf("res_o vs model (logit, index, decision) : %ld mismatches, %ld missing\n", bad_res, no_res);
    std::printf("record words vs model                   : %ld mismatches\n", bad_rec);
    std::printf("sigmoid(logit) > 0.5 vs decision        : %ld mismatches\n", bad_sig);
    std::printf("capture words                           : %ld mismatches\n", bad_cap);
    std::printf("header (shots, frame_err, NNL1, LDA1)   : %s\n", hdr_ok ? "ok" : "WRONG");
    std::printf("framing faults                          : %ld failed\n", fault_bad);
    bool pass = !bad_res && !no_res && !bad_rec && !bad_sig && !bad_cap && hdr_ok && !fault_bad;
    std::printf("LDA_LIVE_CSIM %s\n", pass ? "PASS" : "FAIL");
    return pass ? 0 : 1;
}
