"""Generates paper_notes/V144_RESULTS.md and v144_results.json: the only list of results the paper may call v1.44.

Lists the same results in the same order as campaign_v143/final/analysis/make_v143_ledger.py, so the two ledgers can be
compared row by row.

The rules that keep other results out:
  1. Nobody edits the .md. It is written here, and --verify fails if it or any source file has changed since.
  2. A value enters only through src(), which refuses a file unless its path names v1.44 and it passes a build check.
  3. Each row states how strong its build evidence is:
       banner     the file or its own log holds the v1.44 build banner read from the board during the run
       bracketed  no banner in the file; the same uninterrupted runner logged the banner before and after it
       build-file a Vivado report named v1.44, identical to the one saved from the v1.44 build
       name+date  named v1.44 and dated after the build, with no banner; weakest, listed at the end of the file
  4. A result whose source does not exist yet is shown as PENDING with no value. A source that exists and fails a check
     stops the script. --verify fails while anything is pending, so a partial file cannot pass for a finished one.
  5. In a checkout without the board captures listed in DATA_MANIFEST.csv, --verify recomputes every result it can and
     reports the rest as not rechecked; any other missing or changed source, or an edited .md, still fails.

  .venv/Scripts/python.exe campaign_v144/final/analysis/make_v144_ledger.py [--verify]
"""
import fnmatch
import functools
import glob
import hashlib
import json
import math
import os
import re
import sys
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[3]
os.chdir(ROOT)
sys.path.insert(0, "audit_fixes/R3_R2")
from r3_stats import fstats, paired, calmask  # noqa: E402

MD = Path("paper_notes/V144_RESULTS.md")
JS = Path("campaign_v144/final/analysis/v144_results.json")
TEMPLATE = Path("campaign_v143/final/analysis/v143_results.json")
BANNER = "Nov  7 19:57:07"
BIT = Path(os.environ.get("V144_BIT", "firmware_v1.44/OG_build_v1.44.bit"))    # the shipped bitstream; sha256 checked below
BIT_SHA = "986c861a83be8d01d72db967af894e3d01de2b1c861021d1b5821bc183d7b7c6"
BUILT = datetime(2026, 11, 7, 19, 57, 7).timestamp()
# The Vivado project's own report folder (the build kept the v1.43_* report names; the design there is v1.44). Only on
# the build machine: set V144_REPORTS to compare the shipped reports with it, and to check file dates.
REPORTS = Path(os.environ["V144_REPORTS"]) if os.environ.get("V144_REPORTS") else None
D = "campaign_v144/final/"
B2 = D + "board2/"
LK = D + "leak_energy/"
TR = "firmware_v1.44/reports/"
HOSTS = (("10.1.9.26", "A"), ("10.1.4.105", "B"))


class Pending(Exception):
    """A source does not exist yet."""


def need(path):
    if not Path(path).exists():
        raise Pending(str(path))
    return path


TEXT = {".json", ".log", ".md", ".txt", ".rpt", ".tsv", ".csv", ".py", ".sh"}


def sha(p):
    """sha256 of the file; text files with line endings normalised, so a checkout's CRLF/LF conversion changes nothing."""
    b = Path(p).read_bytes()
    if Path(p).suffix in TEXT:
        b = b.replace(b"\r\n", b"\n")
    return hashlib.sha256(b).hexdigest()


SRC, ROWS, BLOCKED = {}, [], []


def src(path, kind, log=None):
    """Admits a source file, raises Pending if it does not exist yet, or stops. Returns the path."""
    p = str(path).replace("\\", "/")
    if p in SRC:
        return p
    need(p)
    assert re.search(r"v144|v1\.44", p), f"path does not name v1.44: {p}"
    assert not re.search(r"v1\.?4[0-3]|v1\.?3\d", Path(p).name), f"file name names another build: {p}"
    if REPORTS is not None:   # on the build machine only: file dates survive there, not in a checkout
        assert Path(p).stat().st_mtime > BUILT, f"older than the v1.44 build: {p}"
    if kind == "banner":
        t = Path(need(log or p)).read_text(encoding="utf-8", errors="ignore")
        assert BANNER in t, f"no v1.44 banner in {log or p}"
    elif kind == "bracketed":
        board = log
        for q in (f"{D}inloop/{board}_inloop_0_100000.log", f"{D}axi/{board}_axi_0.log"):
            assert BANNER in Path(need(q)).read_text(encoding="utf-8", errors="ignore"), q
        for ph in ("live1", "live2"):
            assert json.load(open(need(f"{D}calib/{board}_{ph}.json")))["bit_sha256"] == BIT_SHA, ph
    elif kind == "build-file":
        name = Path(p).name.replace("v1.44_", "v1.43_", 1)
        if REPORTS is not None:
            assert sha(p) == sha(REPORTS / name), f"differs from the report saved from the build: {p}"
    else:
        assert kind == "name+date", kind
    SRC[p] = dict(kind=kind, sha256=sha(p)[:16])
    return p


def attempt(fn, *args):
    """Runs one group of rows. Rows finished before a missing source stay in the ledger."""
    try:
        fn(*args)
    except Pending as e:
        BLOCKED.append(str(e))


def row(section, key, value, text, source, note=""):
    """text = every form the value may take in the paper, e.g. ['95.55']."""
    ROWS.append(dict(section=section, key=key, value=value, text=[str(t) for t in (text if isinstance(text, list) else [text])], source=source, kind=SRC[source]["kind"], note=note))


def fid(section, key, s, source, note=""):
    row(section, key, f"{s['fid']:.2f}% [{s['fid_ci'][0]:.2f}, {s['fid_ci'][1]:.2f}], P(1|0) {s['p10']:.2f}, P(0|1) {s['p01']:.2f}, n = {s['n']:,}",
        [f"{s['fid']:.2f}", f"{s['fid_ci'][0]:.2f}", f"{s['fid_ci'][1]:.2f}", f"{s['p10']:.2f}", f"{s['p01']:.2f}", f"{s['n']:,}"], source, note)


def pv(p):
    return f"{p:.2f}" if p >= 0.01 else f"{p:.1g}"


def pair(section, key, s, source, note=""):
    row(section, key, f"{s['A_only']} vs {s['B_only']}, exact p = {pv(s['p_exact'])}, difference {s['dF']:+.3f} [{s['dF_ci'][0]:+.3f}, {s['dF_ci'][1]:+.3f}]",
        [str(s["A_only"]), str(s["B_only"]), pv(s["p_exact"]), f"{s['dF']:+.3f}"[1:], f"{s['dF_ci'][0]:+.3f}"[1:], f"{s['dF_ci'][1]:+.3f}"[1:], f"{s['p_exact']:.3f}", f"{s['dF_ci'][0]:+.2f}"[1:], f"{s['dF_ci'][1]:+.2f}"[1:]], source, note)


def stats():
    """The analysis output, once the campaign data has been analysed. Checked against both boards' runners."""
    f = D + "analysis/v144_stats.json"
    need(f)
    for b in "AB":
        src(f"{D}inloop/{b}_inloop_0_100000.log", "banner")
        src(f"{D}axi/{b}_axi_0.log", "banner")
    src(f, "bracketed", "A")
    SRC.pop(f)                   # admit it once for each board's bracket
    src(f, "bracketed", "B")
    return f, json.load(open(f))


def merged():
    f = D + "analysis/merged_live.npz"
    src(f, "bracketed", "A")
    return np.load(f)


def loop_groups():
    return json.load(open(need(D + "analysis/loop_groups_values_v144.json")))


# ----------------------------------------------------------------------- the analysis output
def nn_live():
    f, S = stats()
    T = S["bit_exact"]
    n = sum(v["n"] for v in T.values())
    assert all(v["all"] == v["n"] == 50000 for v in T.values()), T
    row("NN_live", "Bit-exact shots (window, sums, sigmoid, decision), both boards", f"{n:,}/{n:,}", [f"{n:,}"], f)
    L = S["live"]
    assert L["window_eq_buffer"] == {"A": 100000, "B": 100000}
    fid("NN_live", "Headline, 99,400 rows, run 1", L["headline"], f)
    fid("NN_live", "Full 100,000 rows, run 1", L["full100k"], f)
    fid("NN_live", "Fresh 80,000 rows", L["fresh80k"], f)
    fid("NN_live", "19,400 subset, board A", L["headline_subset19400_boardA"], f)
    fid("NN_live", "19,400 subset, board B", L["headline_subset19400_boardB"], f)
    fid("NN_live", "All 99,400 traces on board A", L["A_all"], f)
    fid("NN_live", "All 99,400 traces on board B", L["B_all"], f)
    pair("NN_live", "Boards A vs B, identical 99,400 traces", L["A_vs_B"], f)
    row("NN_live", "DAC-clipped shots, A / B", f"{L['dac_clipped_shots']['A']} / {L['dac_clipped_shots']['B']}", [L["dac_clipped_shots"]["A"]], f)


def replay_decisions():
    f, _ = stats()
    M = merged()
    cal = calmask(M["rows"]); da, db, yy = M["dec_A"][cal], M["dec_B"][cal], M["y"][cal]
    wa, wb = da != yy, db != yy
    both, either = 100 * float((wa & wb).mean()), 100 * float((wa | wb).mean())
    trace = 100 * 2 * both / (2 * both + (either - both))
    agree = 100 * float((da == db).mean())
    row("Replay channel", "Decisions agree between boards", f"{agree:.2f}%", [f"{agree:.2f}"], f)
    row("Replay channel", "Wrong on both boards / on at least one", f"{both:.2f}% / {either:.2f}%", [f"{both:.2f}", f"{either:.2f}"], f)
    row("Replay channel", "Share of error that belongs to the trace / to replay noise", f"{trace:.0f}% / {100 - trace:.0f}%", [f"{trace:.0f}", f"{100 - trace:.0f}"], f)


def inloop():
    f, S = stats()
    for b in "AB":
        r = S["inloop"][b]; lp = r["loop"]
        assert BANNER in r["banner"], r["banner"]
        fid("In the loop", f"Board {b}, 99,400 rows", r["inloop"], f)
        fid("In the loop", f"Board {b}, 19,400 subset", r["inloop_subset19400"], f)
        fid("In the loop", f"Board {b}, fresh 80,000 rows", r["inloop_fresh80k"], f)
        pair("In the loop", f"Board {b}, vs its gate-idle run", r["inloop_vs_gate_idle"], f)
        row("In the loop", f"Board {b}, pulse == gate == decision", f"{lp['correct']:,}/{r['n']:,}", [f"{lp['correct']:,}"], f)
        row("In the loop", f"Board {b}, stale / late / unsafe / binding rejects", f"{lp['stale']} / {lp['late']} / {lp['unsafe']} / {lp['binding_rejects']}", ["0"], f)
        row("In the loop", f"Board {b}, slack", f"{1e3 * r['slack_us']:.0f} ns", [f"{abs(1e3 * r['slack_us']):.0f}"], f)
        row("In the loop", f"Board {b}, DAC-clipped shots", f"{lp['dac_clipped_shots']}", [lp["dac_clipped_shots"]], f)
    N = S["inloop"]["A"]["n"] + S["inloop"]["B"]["n"]
    row("In the loop", "In-loop shots, both boards", f"{N:,}", [f"{N:,}"], f)
    ub = S["inloop"]["A"]["loop"]["late_rate_upper95"]
    row("In the loop", "Late-rate 95% upper bound, per board / pooled", f"{100 * ub:.4f}% / {100 * (1 - 0.05 ** (1 / N)):.4f}%", [f"{100 * ub:.3f}", f"{100 * (1 - 0.05 ** (1 / N)):.4f}"], f)
    pair("In the loop", "Boards A vs B", S["inloop"]["A_vs_B"], f)
    pair("In the loop", "Boards A vs B, 19,400 subset", S["inloop"]["A_vs_B_subset19400"], f)
    for b in "AB":
        pair("In the loop", f"Board {b}, vs gate-idle, 19,400 subset", S["inloop"][b]["inloop_vs_gate_idle_subset19400"], f)


def axi():
    f, S = stats()
    for b in "AB":
        x = S["axi"][b]
        fid("NN_axi", f"Board {b}, 19,400 rows, TLAST, no host alignment", x["subset19400"], f)
        pair("NN_axi", f"Board {b}, vs NN_live in the same session", x["axi_vs_live_same_session"], f)
        pair("NN_axi", f"Board {b}, vs NN_live run on the same rows", x["axi_vs_live_run"], f)
    pair("NN_axi", "Boards A vs B", S["axi"]["A_vs_B"], f)
    fid("NN_axi", "Both boards pooled, 38,800 shots", S["axi"]["both_boards_pooled"], f)


def timing_checks():
    """Timing argument in the paper: NN_live vs NN_axi on the same 20,000 rows of one board."""
    f, _ = stats()
    M = merged()
    for b in "AB":
        I, P, Y = [], [], []
        for g in glob.glob(f"{D}axi/{b}_axi_*.npz"):
            z = np.load(g, allow_pickle=True); I.append(z["idx"]); P.append(z["probs"]); Y.append(z["y"])
        if not I:
            raise Pending(f"{D}axi/{b}_axi_*.npz")
        I = np.concatenate(I); o = np.argsort(I); dx = (np.concatenate(P)[o] > .5).astype(int); yx = np.concatenate(Y)[o].astype(int)
        assert len(I) == 20000, (b, len(I))
        dl = M[f"dec_{b}"][:20000]
        fid("Timing checks", f"Board {b}, NN_live, same 20,000 rows", fstats(dl, yx), f)
        fid("Timing checks", f"Board {b}, NN_axi, same 20,000 rows", fstats(dx, yx), f)
        pair("Timing checks", f"Board {b}, NN_live vs NN_axi, 20,000 rows", paired(dl, dx, yx), f)


# ----------------------------------------------------------------------- NN_axi vs its emulator, and the linear baselines on v1.44 replays
def emulator():
    ae = src(D + "analysis/axi_emu_v144.json", "banner", D + "axi/A_axi_0.log"); AE = json.load(open(ae))
    assert all(AE[b]["identical"] == AE[b]["n"] == 20000 for b in "AB")
    row("NN_axi", "Identical to its bit-accurate emulator on the recorded window, both boards", "40,000/40,000", ["40,000", "20,000"], ae)
    for b in "AB":
        fid("NN_axi", f"Emulator, board {b}, 19,400 rows", AE[b]["emu_subset19400"], ae)


def linear(b):
    q = src(D + f"analysis/linear_v144_{b}.json", "banner", D + f"axi/{b}_axi_0.log"); Q = json.load(open(q))
    fid("Linear baselines", f"Matched filter, board {b}", Q["linear_baselines"]["200000"]["MF"]["h19400"], q)
    W_ = Q["window_tradeoff"]
    fid("Linear baselines", f"LDA, 770 samples, board {b}", W_["770"]["h19400"], q)
    fid("Linear baselines", f"LDA, 576 samples, board {b}", W_["576"]["h19400"], q)
    pair("Linear baselines", f"LDA, 576 vs 640 samples, board {b}", W_["576"]["vs640"]["h19400"], q)
    pair("Linear baselines", f"LDA, 770 vs 640 samples, board {b}", W_["770"]["vs640"]["h19400"], q)


# ----------------------------------------------------------------------- drift
def drift(h, b):
    p = src(f"{D}drift_full/drift_{h}.json", "banner", f"{D}drift_full/{b}_drift.log")
    J = json.load(open(p)); ph = np.array([s["phase"] for s in J["samples"]])
    spread = abs(ph - ph.mean()).max()
    row("Drift, 3 h", f"Board {b}, phase mean, SD, largest distance from mean", f"{ph.mean():.2f} deg, {ph.std(ddof=1):.3f} deg, {spread:.2f} deg", [f"{spread:.2f}", f"{ph.std(ddof=1):.2f}"], p)
    s0, s1 = [], []
    for tag, out in (("start", s0), ("end", s1)):
        for f in J[f"score_{tag}"]:
            z = np.load(f.replace("\\", "/"), allow_pickle=True); out.append((z["idx"], z["probs"], z["y"]))
    i0, i1 = (np.concatenate([x[0] for x in s]) for s in (s0, s1))
    assert np.array_equal(i0, i1) and len(i0) == 6000
    a, c, y = (np.concatenate([x[1] for x in s0]) > .5).astype(int), (np.concatenate([x[1] for x in s1]) > .5).astype(int), np.concatenate([x[2] for x in s0]).astype(int)
    q = paired(c, a, y)
    row("Drift, 3 h", f"Board {b}, end minus start, 6,000 paired shots", f"{q['dF']:+.2f} points, {q['B_only']} vs {q['A_only']}, p = {pv(q['p_exact'])}", [f"{q['dF']:+.2f}"[1:], "6,000"], p)


# ----------------------------------------------------------------------- tProc path, safety, swap, phase
def tproc_box(b):
    q = src(f"{B2}{b}_tproc_box_v144.json", "banner"); J = json.load(open(q))
    for v in ("nobranch", "qick"):
        g_ = [x for x in J["points"] if x["variant"] == v and x["fresh"] == x["n"] == x["br_eq_dec"] == x["played_eq_br"]][0]
        row("tProc path", f"Board {b}, boxcar path, {v}, earliest clean margin", f"{g_['L_median']:.1f} ns at +{1e3 * g_['margin']:.0f} ns, {g_['fresh']}/{g_['n']} fresh", [f"{g_['L_median']:.1f}", f"{g_['L_median']:.0f}"], q)


def tproc_fir(b):
    q = src(f"{B2}{b}_tproc_fir_v144.json", "banner"); J = json.load(open(q))
    g_ = [x for x in J["points"] if abs(x["margin"] - 0.035) < 1e-6][0]
    row("tProc path", f"Board {b}, FIR path, same margin as the old L5 value", f"{g_['L_median']:.1f} ns", [f"{g_['L_median']:.1f}"], q)


def boxcar_mr(b):
    q = src(f"{B2}{b}_boxcar_mr_v144.json", "banner", f"{B2}{b}_boxcar_mr_v144.log"); J = json.load(open(q))
    row("Safety and tests", f"Boxcar vs raw buffer, board {b}, with banner", f"{J['shots_exact']}/{J['shots']} shots exact, {J['verdict']}", [], q)


def leak():
    """Leaked energy over blanked shots, Gaussian conditional pulse (analysis_scripts/diagnostics/leak_energy_check.py)."""
    lk = {}
    for b in "AB":
        for thr in (8, 2000):
            q = src(f"{LK}{b}_v144_leak_thr{thr}.json", "banner", f"{LK}{b}_v144_leak_thr{thr}.log"); lk[b, thr] = (q, json.load(open(q)))
            assert lk[b, thr][1]["control_sees_leak"], (b, thr)
    u = {b: 100 * lk[b, 8][1]["max_upper_ci_lead_2_4"] for b in "AB"}
    row("Safety and tests", "Leaked energy, gate blanking every window, DELAY from the first nonzero sample (nz_thr 8): largest upper 95% bound at leads 2-4, A / B",
        f"{u['A']:.3f}% / {u['B']:.3f}%, {lk['A', 8][1]['shots']} shots per setting; positive control resolves a leak",
        [f"{max(u.values()):.2f}", str(lk["A", 8][1]["shots"])], lk["A", 8][0], "B's file is " + lk["B", 8][0])
    m = {b: 100 * lk[b, 2000][1]["leads"]["4"]["frac_mean"] for b in "AB"}
    row("Safety and tests", "Leaked energy with DELAY from the 2000-amplitude crossing (nz_thr 2000), lead 4 mean, A / B",
        f"{m['A']:.3f}% / {m['B']:.3f}%", [f"{m['A']:.2f}", f"{m['B']:.2f}"], lk["A", 2000][0], "B's file is " + lk["B", 2000][0])


def gate_saving():
    q = src(f"{B2}A_tproc_box_v144.json", "banner")
    La = [x for x in json.load(open(q))["points"] if x["variant"] == "nobranch" and x["fresh"] == x["n"]][0]["L_median"]
    L = loop_groups()["high"]["L_50"]
    row("tProc path", f"Gate saving over the tProc path: board A tProc minus L_50 ({L:.1f}), and its population worth at T1 = 32 us", f"{La - L:.0f} ns; {(La - L) / 960:.2f} to {(La - L) / 320:.2f} points", [f"{La - L:.0f}", f"{(La - L) / 960:.2f}", f"{(La - L) / 320:.2f}"], q, "t/(3 T1) and t/T1")


def _f(path):
    z = np.load(path, allow_pickle=True); y = z["y"].astype(int); d = (z["live_rec"][:, 7] & 1).astype(int)
    return fstats(d, y), float(np.degrees(np.angle(complex(z["k"]))))


def swap(t, lab):
    q = src(f"{B2}swap_{t}_v144.npz", "banner", f"{B2}swap_{t}.log"); fs, ang = _f(q)
    fid("Calibration swap", f"{lab}, 2,000 shots, arg(k) {ang:.1f} deg", fs, q)


def swap_phase():
    ka, kb = (_f(src(f"{B2}swap_{t}_v144.npz", "banner", f"{B2}swap_{t}.log"))[1] for t in ("A_own", "B_own"))
    row("Calibration swap", "Phase difference of the boards in that session", f"{abs(ka - kb):.1f} deg", [f"{abs(ka - kb):.0f}", f"{abs(ka - kb):.1f}"], f"{B2}swap_B_own_v144.npz")


def phrst():
    q = src(f"{B2}A_phrst_probe_v144.json", "banner"); J = json.load(open(q))
    assert len(J["loads"]) == 4 and all(BANNER in l["banner"] for l in J["loads"])
    for m_ in ("none", "both"):
        row("Phase across loads", f"Board A, 4 loads, mode {m_}: mean per load", ", ".join(f"{float(np.degrees(np.angle(np.exp(1j * np.radians(l['modes'][m_]['shots'])).mean()))):.0f}" for l in J["loads"]) + " deg", [], q)


# ----------------------------------------------------------------------- offline analyses of the v1.44 data
def box_vs_fir():
    q = src(D + "analysis/box_vs_fir_v144.json", "banner", D + "axi/A_axi_0.log"); J = json.load(open(q))
    assert J["box_emu_eq_chip"] == J["n"] == 100000
    fid("Boxcar vs FIR", "Boxcar, 19,400, board A", J["subset19400"]["box"], q)
    fid("Boxcar vs FIR", "FIR model, 19,400, board A", J["subset19400"]["fir"], q)
    pair("Boxcar vs FIR", "Boxcar vs FIR, 19,400", J["subset19400"]["paired"], q)
    pair("Boxcar vs FIR", "Boxcar vs FIR, 99,400", J["all99400"]["paired"], q)


def synthetic():
    q = src(D + "analysis/r9/r9_stats_v144.json", "banner", D + "axi/A_axi_0.log"); J = json.load(open(q))["19400"]
    for c_ in J["comparisons"]:
        row("Synthetic data", f"{c_['A']} minus {c_['B']}", f"{c_['diff']:+.2f} [{c_['ci95'][0]:+.2f}, {c_['ci95'][1]:+.2f}]", [f"{c_['diff']:+.2f}"[1:], f"{c_['ci95'][0]:+.2f}"[1:], f"{c_['ci95'][1]:+.2f}"[1:]], q)


def nonlinear():
    q = src(D + "analysis/arch/arch_sweep2_src_v144.json", "banner", D + "axi/A_axi_0.log"); J = json.load(open(q))
    row("Nonlinear models", "LDA, 20,000 rows: raw / replayed", f"{J['lda_ref']['src20k']:.2f}% / {J['lda_ref']['loop20k']:.2f}%", [f"{J['lda_ref']['src20k']:.2f}", f"{J['lda_ref']['loop20k']:.2f}"], q)
    for k_ in ("seg_hgb", "seg_mlp", "bin_mlp", "cnn1d", "bin_gru"):
        v_ = J[k_]; t_ = v_["loop20k_vs_t4"]
        row("Nonlinear models", f"{k_}: raw / replayed, vs LDA", f"{v_['src20k']:.2f}% / {v_['loop20k']:.2f}%, {t_['delta']:+.2f}, p = {pv(t_['p'])}", [f"{v_['src20k']:.2f}", f"{v_['loop20k']:.2f}", f"{abs(t_['delta']):.2f}", pv(t_["p"])], q)


def channel():
    q = src(D + "analysis/channel_v144.json", "banner", D + "axi/A_axi_0.log"); J = json.load(open(q))
    row("Replay channel", "Class SNR per sample, source / replayed board A (rms mean separation over rms noise)", f"{J['snr_source']:.2f} / {J['snr_A']:.2f}", [f"{J['snr_source']:.2f}", f"{J['snr_A']:.2f}"], q)
    row("Replay channel", "Capture delay against the aligned source, 4,000 shots", f"{min(J['lags'], key=int)}-{max(J['lags'], key=int)} samples", [], q)


# ----------------------------------------------------------------------- Fig. 7
def fig7():
    F7 = D + "fig7/"
    fv = src(F7 + "fig7_capture_A_v144.json", "banner")
    src(F7 + "fig7_capture_B_v144.json", "banner"); src(F7 + "fig7_sweep_A_v144.json", "banner"); src(F7 + "fig7_sweep_B_v144.json", "banner")
    V = json.load(open(need(F7 + "fig7_values_v144.json")))
    row("Readout path", "Boxcar saves, board A", f"{V['saved_ns']:.1f} ns", [f"{V['saved_ns']:.1f}"], fv)
    im = dict(zip(V["image_dBc"]["M"], V["image_dBc"]["box_measured"]))
    _fir = V["saved_ns"] + 9 * 1e3 / 552.96 + 5 * 1e3 / 552.96
    row("Readout path", "QICK FIR path, mixer output to decimated edge: saving + boxcar path (9 cycles + group delay (M-1)/2 = 5 samples)", f"{_fir:.1f} ns", [f"{_fir:.0f}"], fv, "check: FIR core C_LATENCY 67 cycles + 120-tap group delay 59.5/4423.68 us = 134.6 ns")
    row("Readout path", "Image rejection at M = 11, board A", f"{im[11]:.1f} dB", [f"{abs(im[11]):.1f}"], fv)


# ----------------------------------------------------------------------- Table III
sys.path.insert(0, "firmware_v1.44/reports")
import vivado_reports as R3  # noqa: E402
R3.HIER, R3.FLAT, R3.TIMING = (Path(TR) / f"v1.44_{r}.rpt" for r in ("routed_util_hier", "routed_utilization", "routed_timing"))


def summary(path):
    """WNS, failing setup endpoints and total endpoints from the Design Timing Summary; requires timing met."""
    t = Path(path).read_text(errors="ignore")
    assert "All user specified timing constraints are met." in t, "v1.44 report does not state timing met"
    v = re.search(r"WNS\(ns\).*?\n\s*-+.*?\n\s*(-?[\d.]+)\s+(-?[\d.]+)\s+(\d+)\s+(\d+)", t, flags=re.S)
    return float(v[1]), int(v[3]), int(v[4]), t


def implementation():
    for r in ("routed_timing", "routed_util_hier", "routed_utilization"):
        src(f"{TR}v1.44_{r}.rpt", "build-file")
    tt, tu = f"{TR}v1.44_routed_timing.rpt", f"{TR}v1.44_routed_util_hier.rpt"
    blk = R3.blocks()
    live, ax = blk["NN_live_0"], blk["NN_axi_0"]
    wns, fails, _, t = summary(tt)
    assert fails == 0 and wns >= 0, (wns, fails)
    row("Implementation", "NN_live LUT / FF", f"{live['lut']:,} / {live['ff']:,}", [f"{live['lut']:,}", f"{live['ff']:,}"], tu)
    row("Implementation", "NN_axi LUT / FF", f"{ax['lut']:,} / {ax['ff']:,}", [f"{ax['lut']:,}", f"{ax['ff']:,}", f"{100 * ax['lut'] / 425280:.1f}"], tu)
    row("Implementation", "WNS / failing setup endpoints", f"{wns:.3f} ns / {fails}", [f"{abs(wns):.3f}", fails], tt)
    m = re.search(r"^clk_pl_0\s+(-?[\d.]+)", t, flags=re.M)
    row("Implementation", "NN_axi clock (clk_pl_0) WNS", f"{float(m[1]):+.3f} ns", [m[1], f"{float(m[1]):.2f}"], tt)
    _loop = ["boxcar_tap_0", "dac_gate_0", "live_gate_0", "live_res_cdc_0", "live_res_cdc_1", "trig_sync_0"]   # Table III's loop logic
    _rt = live["lut"] + sum(blk[b]["lut"] for b in _loop)
    row("Implementation", "Real-time path LUT (NN_live + loop logic, Table III)", f"{_rt:,} (about {round(_rt, -2):,})", [f"{_rt:,}", f"{round(_rt, -2):,}"], tu)
    row("Implementation", "NN_live LUT, rounded for prose", f"about {round(live['lut'], -1):,}", [f"{round(live['lut'], -1):,}"], tu)
    row("Implementation", "Failing endpoints: NN_live / its clock crossing / stock readouts 1 and 2", f"{fails} / {fails} / {fails}", [fails], tt, "zero failing setup endpoints in the whole design")


def scaling():
    f = "scaling_study/resource_scaling_v144.json"
    _rs = json.load(open(need(f)))
    tu = src(f"{TR}v1.44_routed_util_hier.rpt", "build-file")
    assert _rs["per_unit"]["classifier"]["lut"] == sum(R3.blocks()[n]["lut"] for n in ("NN_live_0", "boxcar_tap_0", "live_gate_0", "live_res_cdc_0", "live_res_cdc_1", "trig_sync_0"))
    _n = [v["n_max"] for k, v in _rs["n_max"].items() if "front end none" not in k]
    row("Implementation", "Classifier units that fit with a per-tone front end (scaling_study/resource_scaling.py, SCALING_OUT=resource_scaling_v144.json)", f"{min(_n)} to {max(_n)}", [min(_n), max(_n)], tu)


# ----------------------------------------------------------------------- loop latency and tests
def latency():
    G = loop_groups()
    for name in ("low", "high"):                 # every load in both groups: the banner read from the board in that load's own run
        for load in G[name]["loads"]:
            sub = "cold" if "_c" in load else "reloads"
            q = f"{D}latency/{sub}/{load}.json"
            assert BANNER in Path(need(q)).read_text(errors="ignore"), f"no v1.44 banner in {q}"
    g = src(D + "analysis/loop_groups_values_v144.json", "banner", f"{D}latency/reloads/{G['low']['loads'][0]}.json")
    for name in ("low", "high"):
        x = G[name]
        row("Loop latency", f"L_50, {name} load group ({x['n_loads']} loads)", f"{x['L_50']:.1f} ns, range {x['L_50_min']:.1f}-{x['L_50_max']:.1f}", [f"{x['L_50']:.1f}", f"{x['L_50_min']:.1f}", f"{x['L_50_max']:.1f}"], g)
        row("Loop latency", f"Segments, {name} group: S_fe, S_NN, S_CDC, S_gate, S_conv", ", ".join(f"{v:.1f}" for v in x["segs"].values()) + " ns", [f"{v:.1f}" for v in x["segs"].values()], g)
    _h = G["high"]["segs"]
    row("Loop latency", f"Our logic (S_NN + S_CDC + S_gate) / converters and cable (S_conv), rounded, {G['high']['L_50']:.0f} ns group", f"{_h['S_nn'] + _h['S_cdc'] + _h['S_gate']:.0f} / {_h['S_conv']:.0f} ns", [f"{_h['S_nn'] + _h['S_cdc'] + _h['S_gate']:.0f}", f"{_h['S_conv']:.0f}", f"{G['high']['L_50']:.0f}", f"{G['low']['L_50']:.0f}"], g)
    _win = 575 / 552.96e6 * 1e9          # window's first to last sample: 575 intervals at the decimated rate (design constant)
    _mr = (_win + G["high"]["L_50"]) / 1000
    row("Loop latency", f"Measure-and-react time in replay time: window (575 intervals at 552.96 MS/s) + L_50 of the {G['high']['L_50']:.0f} ns group",
        f"{_win:.1f} + {G['high']['L_50']:.1f} ns = {_mr:.2f} us", [f"{_win:.1f}", f"{_mr:.2f}"], g)
    _sc = (G["low"]["segs"]["S_conv"] + _h["S_conv"]) / 2
    row("Loop latency", "Converters and cable, mean of the two load groups", f"{_sc:.1f} ns ({G['low']['segs']['S_conv']:.1f} and {_h['S_conv']:.1f})", [f"{_sc:.0f}"], g)


def fig8b():
    _b = src(D + "fig8b/A_gate_probe.log", "banner")
    src(D + "fig8b/B_gate_probe.log", "banner")
    _v = json.load(open(need(D + "fig8b/fig8b_values_v144.json")))
    _l = {b: [x for x in _v[b] if x["slack_ns"] == -66.0][0]["late"] for b in "AB"}
    row("Loop latency", "Fig. 8(b), late at -66 ns, boards A / B, of 40", f"{_l['A']} / {_l['B']}", [_l["A"], _l["B"]], _b)


def tests(b):
    for name, stem in (("Binding fault test", "binding_fault"), ("Fail-safe test", "fail_safe"), ("tProc decision test", "tproc_decision")):
        f = f"{D}tests/{b}_{stem}.json"; lg = f[:-5] + ".log"
        need(f)
        has = Path(lg).exists() and BANNER in Path(lg).read_text(encoding="utf-8", errors="ignore")
        p = src(f, "banner", lg) if has else src(f, "name+date")
        row("Safety and tests", f"{name}, board {b}", str(json.load(open(p)).get("verdict")), [], p)
    f = f"{D}tests/{b}_functional.json"
    p = src(f, "banner", f[:-5] + ".log"); j = json.load(open(p))["summary"]
    assert j["ERROR"] == 0, j
    row("Safety and tests", f"QICK functional suite, board {b}", f"{j['PASS']} pass, {j['WARN']} warning, {j['FAIL']} fail, {j['NOT WIRED']} not wired", [j["PASS"], j["WARN"], j["FAIL"]], p)


# ----------------------------------------------------------------------- offline analyses added after the main campaign
def _clean(points, v=None):
    return [x for x in points if (v is None or x["variant"] == v) and x.get("forced_ok", True) and x["fresh"] == x["n"] == x["br_eq_dec"] == x["played_eq_br"]]


def tproc_fir_earliest(b):
    q = src(f"{B2}{b}_tproc_fir_v144.json", "banner"); J = json.load(open(q))
    g_ = _clean(J["points"], "nobranch")[0]
    row("tProc path", f"Board {b}, FIR path (NN_live result), earliest clean margin", f"{g_['L_median']:.1f} ns at +{1e3 * g_['margin']:.0f} ns, {g_['fresh']}/{g_['n']} fresh", [f"{g_['L_median']:.1f}", f"{g_['L_median']:.0f}"], q)


def tproc_thr(b):
    """B1: QICK's own threshold feedback, readout 0's averager into the tProc (analysis_scripts/diagnostics/tproc_threshold_v144.py)."""
    q = src(f"{D}board3/{b}_tproc_thr_v144.json", "banner", f"{D}board3/{b}_tproc_thr.log"); J = json.load(open(q))
    pts = [dict(x, _src=q) for x in J["points"]]
    fine = f"{D}board3/{b}_tproc_thr_fine_v144.json"          # the +80..+100 ns pass, 5 ns steps
    if Path(fine).exists():
        q2 = src(fine, "banner", f"{D}board3/{b}_tproc_thr_fine.log"); pts += [dict(x, _src=q2) for x in json.load(open(q2))["points"]]
    pts = sorted(pts, key=lambda x: x["margin"])                # stable: at equal margins the coarse pass comes first
    for v, lab in (("qickthr", "read_and_jump"), ("nobranch", "no-jump form")):
        g_ = _clean(pts, v)
        if g_:
            g_ = g_[0]; q = g_["_src"]
            row("tProc path", f"Board {b}, QICK threshold feedback ({lab}), earliest clean margin", f"{g_['L_median']:.1f} ns at +{1e3 * g_['margin']:.0f} ns, {g_['fresh']}/{g_['n']} fresh", [f"{g_['L_median']:.1f}", f"{g_['L_median']:.0f}"], q)


def s2_aug():
    q = src(D + "analysis/s2/arch_aug_v144.json", "bracketed", "A"); J = json.load(open(q))
    for arm in ("seg_mlp", "bin_mlp", "bin_gru", "cnn1d"):
        r = J[f"{arm}_aug"]; v = r["vs_lda_clean"]
        row("Replay-channel augmentation", f"{arm} trained on augmented data vs LDA, board A replay, 16,000 shots", f"{r['loop16k']:.2f}%, {v['delta']:+.2f} points, b {v['b']} vs c {v['c']}, p = {pv(v['p'])}",
            [f"{r['loop16k']:.2f}", f"{abs(v['delta']):.2f}", pv(v["p"])], q)
    row("Replay-channel augmentation", "Deployed 4-unit network: chip (clean) / retrained on augmented data", f"{J['t4_clean']:.2f}% / {J['t4_aug']:.2f}%", [f"{J['t4_clean']:.2f}", f"{J['t4_aug']:.2f}"], q)
    row("Replay-channel augmentation", "LDA on the same 16,000 shots", f"{J['lda_clean']:.2f}%", [f"{J['lda_clean']:.2f}"], q)


def s5_linear():
    f = D + "analysis/s5_linear_99400_v144.json"
    src(f, "bracketed", "A"); SRC.pop(f); q = src(f, "bracketed", "B"); J = json.load(open(q))
    for k, lab in (("LDA_window576", "LDA, window 576"), ("LDA_window770", "LDA, window 770"), ("MF", "matched filter")):
        for s_, slab in (("headline", "run 1, 99,400 rows"), ("A_all", "board A, 99,400 rows"), ("B_all", "board B, 99,400 rows")):
            r = J[s_][k]; v = r["vs_NN_live"]
            row("Linear baselines", f"{lab}, {slab}, vs NN_live on the same shots", f"{r['fid']['fid']:.2f}%, {v['dF']:+.3f} points, {v['A_only']} vs {v['B_only']}, exact p = {pv(v['p_exact'])}",
                [f"{r['fid']['fid']:.2f}", f"{abs(v['dF']):.2f}", pv(v["p_exact"])], q)


# ----------------------------------------------------------------------- measurements added after the main campaign


def rev_reloads():
    """#26: 20 further bitstream loads per board; L_50 per load from the protocol summary."""
    loads = {}
    q = src("campaign_v144/final/latency/reloads/summary_A.md", "banner")      # the last summary written; it holds both boards' tables
    for part in re.split(r"^## ", Path(q).read_text(encoding="utf-8"), flags=re.M)[1:]:
        host = part.split(":", 1)[0].strip()
        b = dict(HOSTS)[host]
        loads[b] = [float(m) for m in re.findall(r"^\| rv\d+ \| pass \| 100/100 \| ([\d.]+) ±", part, re.M)]
    for b in "AB":
        v = loads[b]
        assert len(v) == 20, (b, len(v))
        lo, hi = [x for x in v if x < 175], [x for x in v if x >= 175]
        row("Loop latency", f"Board {b}, 20 further loads: low / high group", f"{len(lo)} loads {min(lo):.2f}–{max(lo):.2f} ns / {len(hi)} loads {min(hi):.2f}–{max(hi):.2f} ns",
            [str(len(lo)), str(len(hi)), f"{min(lo):.2f}", f"{max(hi):.2f}"], q)
    allv = loads["A"] + loads["B"]
    lo, hi = [x for x in allv if x < 175], [x for x in allv if x >= 175]
    row("Loop latency", "Both boards, 40 further loads: low / high group, gap", f"{len(lo)} / {len(hi)} loads; {min(lo):.2f}–{max(lo):.2f} / {min(hi):.2f}–{max(hi):.2f} ns; gap {min(hi) - max(lo):.2f} ns",
        ["40", str(len(lo)), str(len(hi)), f"{min(lo):.2f}", f"{max(lo):.2f}", f"{min(hi):.2f}", f"{max(hi):.2f}", f"{min(hi) - max(lo):.2f}"], q)


def rev_stability():
    """#78: one load per board measured 20 times over about 110 min."""
    for b in "AB":
        v, t = [], []
        for f in sorted(glob.glob(f"campaign_v144/final/latency/stability/{b}_st*.json")):
            q = src(f.replace("\\", "/"), "banner")
            J = json.load(open(q))
            v.append(J["points"]["op"]["L_50"]["mean"]); t.append(datetime.strptime(J["settings"]["time"], "%Y-%m-%d %H:%M:%S"))
        assert len(v) == 20, (b, len(v))
        span = (max(t) - min(t)).total_seconds() / 60
        row("Loop latency", f"Board {b}, one load, 20 runs: span, mean, s.d.", f"{span:.0f} min, {np.mean(v):.2f} ns, s.d. {np.std(v, ddof=1):.2f} ns",
            [f"{span:.0f}", f"{np.mean(v):.2f}", f"{np.std(v, ddof=1):.2f}"], q)


def rev_arms():
    """#27: in-loop fidelity with the conditional pulse at gain 0, 0.6 (nominal), 1.0 and with the gate off."""
    q = src("campaign_v144/final/inloop/arms/arms_analysis.json", "banner")
    J = json.load(open(q))
    for b in "AB":
        A = J[b]["arms"]
        f = {k: A[k]["all"]["fid"] for k in ("nominal", "zero", "max", "gateoff")}
        ps = [v["p_exact"] for v in J[b]["paired_vs_nominal"].values()]
        row("In the loop", f"Board {b}, pulse-gain arms ({J[b]['n']:,} rows): nominal / zero / max / gate off",
            " / ".join(f"{v:.2f}%" for v in f.values()) + (f"; smallest exact p vs nominal {min(ps):.2f}" if ps else ""),
            [f"{v:.2f}" for v in f.values()] + ([f"{min(ps):.2f}"] if ps else []) + [f"{J[b]['n']:,}"], q)


def rev_carrier_jitter_spacing():
    """#39 converter latency vs carrier; #66 capture jitter; #75 minimum clean shot period."""
    for b in "AB":
        q = src(f"campaign_v144/final/latency/carrier/{b}_carrier.json", "banner"); J = json.load(open(q))
        d = [abs(r["minus_50MHz_ns"]) for r in J["runs"].values()]
        top = max(float(c) for c in J["runs"])
        row("Readout path", f"Board {b}, edge shift vs the 50 MHz carrier, carriers up to {top:.0f} MHz", f"at most {max(d):.2f} ns", [f"{max(d):.2f}", f"{top:.0f}"], q)
        q = src(f"campaign_v144/final/latency/jitter/{b}_jitter.json", "banner"); J = json.load(open(q))
        r = J["runs"]["box"]["host"]
        row("Readout path", f"Board {b}, per-shot capture jitter, no recorded trace (s.d.)", f"{r['sd_samples']:.2f} samples, {r['sd_ns']:.1f} ns", [f"{r['sd_samples']:.2f}", f"{r['sd_ns']:.1f}"], q)
        q = src(f"campaign_v144/final/tests/spacing/{b}_spacing.json", "banner"); J = json.load(open(q))
        clean = [p["period_us_nominal"] for p in J["points"] if p["clean"]]
        kept = all(p[t]["n_new"] == J["reps"] and p[t]["frame_err"] == 0 and p[t]["consecutive"] for p in J["points"] for t in ("t0", "t1"))
        row("In the loop", f"Board {b}, shortest clean shot period; record path kept up at every spacing", f"{min(clean):.1f} µs; {'yes' if kept else 'no'}",
            [f"{min(clean):.1f}"], q)


def rev_logit():
    """#22: the chip's logit and decision against an integer reference on every v1.44 capture."""
    q = src("campaign_v144/final/tests/logit_check/d22_v144_logit.txt", "name+date")
    S = json.loads(re.search(r"SUMMARY (\{.*\})", Path(q).read_text(encoding="utf-8")).group(1))
    assert S["logit_mismatch"] == 0 and S["decision_mismatch"] == 0
    row("NN_live", "Logit and decision equal to the integer reference, both boards", f"{S['shots'] - S['logit_mismatch']:,}/{S['shots']:,} and {S['shots'] - S['decision_mismatch']:,}/{S['shots']:,}",
        [f"{S['shots']:,}"], q)


def rev_keras():
    """#71: the floating-point Keras model against the chip, on the chip's own input windows (headline, 99,400 shots)."""
    q = src("campaign_v144/final/analysis/offline/keras_vs_hls4ml.json", "name+date"); H = json.load(open(q))["headline"]
    row("NN_live", "Floating-point model's decisions equal to the chip's, same rule (logit >= 1/64), headline shots",
        f"{H['float_vs_chip_decisions_agree']:,}/{H['n']:,}", [f"{H['float_vs_chip_decisions_agree']:,}", f"{H['n']:,}"], q)
    row("NN_live", "Floating-point vs fixed-point (hls4ml) probability, largest difference, headline shots",
        f"{H['prob_absdiff_max']:.3f}", [f"{H['prob_absdiff_max']:.3f}"], q)


def rev_map_trainrows():
    """#13: the boxcar domain map refit on 600 training rows; deployed recipe retrained with each map, 5 seeds."""
    d = []
    for f in sorted(glob.glob("campaign_v144/final/analysis/offline/map_trainrows_s2026090[1-5].json")):
        q = src(f.replace("\\", "/"), "name+date")
        d.append(json.load(open(q))["trainrow_vs_deployed_map"]["dF"])
    assert len(d) == 5
    row("Replay channel", "Domain map fit on training rows vs test rows: headline change, 5 seeds", f"{np.mean(d):+.3f} ± {np.std(d, ddof=1):.3f} points",
        [f"{np.mean(d):+.3f}"[1:], f"{np.std(d, ddof=1):.3f}"], q)


def rev_live_window():
    """#12 (S3): LDA on raw traces at live-readout window lengths (100,000 test rows)."""
    q = src(D + "analysis/s3/s3_live_window_lda.json", "name+date"); J = json.load(open(q))
    for n in ("320", "576"):
        r = J["points"][n]
        row("Linear baselines", f"LDA on raw traces, first {n} recorded samples ({r['qubit_time_us']:.2f} µs)", f"{r['test']['fid']:.2f}%",
            [f"{r['test']['fid']:.2f}", f"{r['qubit_time_us']:.2f}"], q)


# ----------------------------------------------------------------------- offline checks added with text pass 7
def rev2_stats():
    """Paired statistics (campaign_v144/final/analysis/stats/): per-board NN_live vs LDA, NN_axi emulated on the full split, the 80,000 unused rows."""
    q = src("campaign_v144/final/analysis/stats/t2346_paired.json", "name+date"); J = json.load(open(q))
    g = lambda p: functools.reduce(lambda d, k: d[k], p.split("/"), J)
    m = max(abs(x) for k in ("NN_live-LDA_fir770", "NN_live-LDA_fir576", "NN_live-LDA_box576") for b in "AB" for c in ("ci95_normal", "ci95_boot") for x in g(f"{k}/all/{b}/diff")[c])
    row("Linear baselines", "NN_live vs LDA (FIR-770, FIR-576, boxcar-576), each board, 99,400: largest 95% CI bound", f"{m:.3f} points (within 0.2)", [f"{m:.2f}", "0.2"], q)
    for path, lab in (("NN_live-LDA_fir770/all/A/diff", "NN_live vs LDA FIR-770, board A, 99,400"), ("NN_axi_emu-NN_live/all/A/diff", "NN_axi emulated on the recorded FIR windows vs NN_live, board A, 99,400"),
                      ("NN_axi_emu-NN_live/all/B/diff", "NN_axi emulated on the recorded FIR windows vs NN_live, board B, 99,400"),
                      ("boxcar-FIR/fresh/A/diff", "Boxcar vs FIR, board A, the 80,000 unused rows"), ("boxcar-FIR/fresh/B/diff", "Boxcar vs FIR, board B, the 80,000 unused rows")):
        d = g(path)
        row("Paired statistics", lab, f"{d['dF']:+.3f} points, {d['A_only']} vs {d['B_only']}, exact p = {pv(d['p_exact'])}", [f"{abs(d['dF']):.2f}", pv(d["p_exact"])], q)
    pb = max(g("boxcar-FIR/fresh/A/diff")["p_exact"], g("boxcar-FIR/fresh/B/diff")["p_exact"])
    row("Paired statistics", "Boxcar vs FIR on the 80,000 unused rows, bound over both boards", f"p ≤ {pb:.2g}", [f"{math.ceil(pb * 1e4) / 1e4:.4f}"], q)
    for b in "AB":
        f = g(f"fidelity/fresh/{b}/nn")["fid"]; ft = str(Decimal(repr(f)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))
        row("Paired statistics", f"NN_live, board {b}, the 80,000 unused rows", f"{f:.3f}%", [ft], q)
    q = src("campaign_v144/final/analysis/stats/t5_estimators.json", "name+date"); T = json.load(open(q))
    row("Paired statistics", "Noise s.d. per sample, pooled over both states, I / Q (fit-pool traces)", f"{T['sigma']['E2_pooled_I']:.1f} / {T['sigma']['E2_pooled_Q']:.1f}",
        [f"{T['sigma']['E2_pooled_I']:.0f}", f"{T['sigma']['E2_pooled_Q']:.0f}"], q)
    k = T["kurtosis"]["K1_P20_pooled_IQ"]; st = T["stationarity"]; o = T["offset_ratio"]
    dev = 100 * max(st["S1_P20_I_max_over_mean"] - 1, 1 - st["S1_P20_I_min_over_mean"])
    row("Paired statistics", "Noise excess kurtosis, fit pool, pooled", f"{k:+.4f}", [f"{abs(k):.2f}"], q)
    row("Paired statistics", "Noise s.d. per sample, largest deviation from its mean across the trace", f"±{dev:.2f}%", [f"{dev:.1f}"], q)
    row("Paired statistics", "Common-mode offset vs white-noise prediction, both states pooled, I / Q", f"{o['O2_P20_pooled_I']:.3f} / {o['O2_P20_pooled_Q']:.3f}",
        [f"{o['O2_P20_pooled_I']:.1f}", f"{o['O2_P20_pooled_Q']:.1f}"], q)
    q = src("campaign_v144/final/analysis/stats/holm_pass7.json", "name+date"); H = json.load(open(q))
    mh = max(t["holm"] for t in H["tests"] if t["holm"] < 0.05)
    row("Paired statistics", "Holm over every p-value printed after pass 7: tests / survivors / largest surviving adjusted p", f"{H['n']} / {H['survivors']} / {mh:.4f}",
        [H["n"], f"{math.ceil(mh * 100) / 100:.2f}"], q)


def rev2_protocol():
    """Data protocol (campaign_v144/final/analysis/protocol/REPORT.md): the fixed audit, the per-board map refit, the row roles."""
    q = src("campaign_v144/final/analysis/protocol/logs/fixed_verify_no_leakage.log", "name+date")
    m = re.search(r"VERDICT: (\d+)/(\d+) checks passed, 0 failed, 0 blocked", Path(q).read_text(encoding="utf-8", errors="ignore"))
    assert m and m[1] == m[2]
    row("Data protocol", "Fixed leakage audit (verify_no_leakage_fixed.py): checks passed", f"{m[1]} of {m[2]}", [m[1]], q)
    q = src("campaign_v144/final/analysis/protocol/task2_summary.json", "name+date"); T = json.load(open(q))
    for arm, lab in (("trainrow", "training rows 300,000-300,599"), ("v144testrow", "the map's test rows of the v1.44 capture")):
        s = T["mosaic"][arm]["vs_deployed_selected_models"]
        row("Data protocol", f"Map refit on {lab} vs the deployed map, deployed seed, run-1 mix, 99,400", f"{s['dF']:+.3f} points, {s['A_only']} vs {s['B_only']}, exact p = {pv(s['p_exact'])}",
            [f"{abs(s['dF']):.2f}", pv(s["p_exact"])], q, "rows 300,000-300,599 from the refit's capture names")
    q = src("campaign_v144/final/analysis/protocol/REPORT.md", "name+date"); t = Path(q).read_text(encoding="utf-8")
    assert "| Matched filter, linear-baselines LDA | 0:200000 |" in t and "all 900,000 rows" in t and "300000:300600" in t and "replayed test rows 0:3999" in t
    row("Data protocol", "Row roles read from the scripts: baselines 0-199,999; retrain of [16] 900,000 rows; map refit 300,000-300,599; augmentation channel fit on subset rows 0-3,999",
        "design constants", ["199,999", "900,000", "300,000", "300,599", "3,999"], q)


def rev2_fpga():
    """FPGA checks (firmware_v1.44/reports/): decision-path slack, out-of-context scaling margins."""
    q = src("firmware_v1.44/reports/v144_decision_path_slack.tsv", "name+date")
    T = {(c[0], c[1]): float(c[2]) for c in (l.split("\t") for l in Path(q).read_text().splitlines()[1:])}
    sl = [T[(s, "setup")] for s in ("nnlive_internal", "nnlive_to_cdc0", "nnlive_to_cdc1")]
    row("Implementation", "Setup slack inside NN_live and on its outputs (v1.44 routed)", f"{min(sl) * 1000:.0f} to {max(sl) * 1000:.0f} ps", [f"{min(sl) * 1000:.0f}", f"{max(sl) * 1000:.0f}"], q)
    f = src("scaling_study/v144/FINDINGS_v144.md", "name+date"); t = Path(f).read_text(encoding="utf-8")
    ooc = {(m[1], m[2], m[3]): float(m[4]) for m in re.finditer(r"^\| (\d+) \| (\w+) \| ([\w.]+) \| ([+-]?[\d.]+) \|", t, flags=re.M)}
    vals = [ooc[("1", "pb", "v1.41")], ooc[("2", "pb", "v1.41")], ooc[("4", "pb", "v1.41")], ooc[("16", "free", "v1.41")], ooc[("8", "pb", "T")]]
    row("Implementation", "Out-of-context margins, deployed RTL N = 1, 2, 4 (pblock), 16 (device); variant T N = 8", " / ".join(f"{v:+.3f}" for v in vals),
        [f"{vals[0]:.2f}", f"{vals[1]:.2f}", f"{vals[2]:.3f}", f"{vals[4]:.3f}"], f)
    pen = vals[0] - max(sl)
    row("Implementation", "Integration cost: OOC N = 1 margin minus the worst NN_live-path slack in v1.44", f"at least {pen:.3f} ns", [f"{pen:.2f}"], f)


def rev2_pass8():
    """Numbers pass 8 adds: shot spacing, the stock front end's share of S_fe, the Holm recount after pass 8."""
    for b in "AB":
        q = src(f"campaign_v144/final/tests/spacing/{b}_spacing.json", "name+date")
        J = json.load(open(q)); bad = [p["period_us_nominal"] for p in J["points"] if not p["clean"]]
        row("Further measurements", f"Board {b}, longest shot period that failed", f"{max(bad):.2f} µs", [f"{max(bad):.1f}"], q)
    q = src(D + "analysis/loop_groups_values_v144.json", "name+date"); J = json.load(open(q)); box = (9 + 5) / 552.96e-3
    v = [J[g]["segs"]["S_fe"] - box for g in ("low", "high")]
    row("Feed-forward loop", "QICK stock front end inside S_fe (S_fe minus the boxcar path's 9 + 5 cycles), low / high group", f"{v[0]:.1f} / {v[1]:.1f} ns", [f"{round(v[0]):.0f}"], q)
    q = src("campaign_v144/final/analysis/stats/holm_pass8.json", "name+date"); H = json.load(open(q))
    mh = max(t["holm"] for t in H["tests"] if t["holm"] < 0.05)
    row("Paired statistics", "Holm over every p-value printed after pass 8: tests / survivors / largest surviving adjusted p", f"{H['n']} / {H['survivors']} / {mh:.4f}",
        [H["n"], f"{math.ceil(mh * 100) / 100:.2f}"], q)


def rev2_board():
    """Board runs of the variant builds (firmware_v1.44/variants/RESULTS_BOARD_2026-11-18.md): tProc at 245.76 MHz (build 1), the LDA core through
    the gate (build 2b), the pulse-gain arms on the full split, the Holm recount after pass 9."""
    B1, B2 = "firmware_v1.44/variants/tproc245/", "firmware_v1.44/variants/lda_gate/"
    q = src(B1 + "reports/v1.44t245_routed_timing.rpt", "name+date"); t = Path(q).read_text(encoding="utf-8", errors="ignore")
    wns = float(re.search(r"WNS\(ns\).*\n.*\n\s+([-\d.]+)", t)[1])
    row("Variant builds", "Build 1 (tProc core at 245.76 MHz): design WNS", f"{wns * 1000:.0f} ps", [f"{-wns * 1000:.0f}"], q)
    thr = {}
    for b in "AB":
        q = src(f"{B1}board/{b}_threshold_t245.json", "name+date"); e = json.load(open(q))["threshold"]["fir"]["earliest_clean"]
        thr[b] = e["L_median"]
        row("Variant builds", f"Board {b}, tProc 245.76 MHz: QICK threshold feedback (FIR), earliest clean margin",
            f"{e['L_median']:.1f} ns at +{1e3 * e['margin']:.0f} ns, {e['fresh']}/{e['n'] - 1} fresh", [f"{e['L_median']:.1f}"], q)
        q = src(f"{B1}board/{b}_b1_latency.json", "name+date"); L = json.load(open(q))["points"]["op"]["L_50"]["mean"]
        row("Variant builds", f"Board {b}, tProc 245.76 MHz: gate loop L_50 (one load)", f"{L:.2f} ns", [f"{L:.1f}"], q)
    q200 = {b: f"{D}board3/{b}_tproc_thr_v144.json" for b in "AB"}
    t200 = {}
    for r_ in ROWS:   # the 200 MHz rows of tproc_thr(), which runs before this group
        m_ = re.match(r"Board ([AB]), QICK threshold feedback \(read_and_jump\), earliest clean margin$", r_["key"])
        if m_:
            t200[m_[1]] = float(r_["value"].split()[0])
    if len(t200) == 2:
        dl = [t200[b] - thr[b] for b in "AB"]; lo = min(min(thr.values()), *t200.values()); hi = max(max(thr.values()), *t200.values())
        row("Variant builds", "QICK threshold feedback, 200 minus 245.76 MHz tProc, A / B; range over both clocks",
            f"{dl[0]:.1f} / {dl[1]:.1f} ns; {lo:.1f}–{hi:.1f} ns", [f"{round(sum(dl) / 2):.0f}", f"{round(lo, -1):.0f}", f"{round(hi, -1):.0f}"], src(q200["A"], "name+date"))
    q = src(B2 + "reports/v1.44lda11_routed_util_hier.rpt", "name+date")
    m = re.search(r"^\|\s+NN_live_0\s+\|\s+\S+\s+\|\s+(\d+)", Path(q).read_text(encoding="utf-8", errors="ignore"), flags=re.M)
    row("Variant builds", "LDA_live 1.1 in NN_live's slot (build 2b): routed LUTs", f"{int(m[1]):,}", [f"{int(m[1]):,}"], q)
    for b in "AB":
        q = src(f"{B2}board/{b}_b2_latency.json", "name+date"); J = json.load(open(q))
        cyc = next(c["detail"] for c in J["checks"] if c["name"] == "op_nn_cycles")
        L = J["points"]["op"]["L_50"]["mean"]
        row("Variant builds", f"Board {b}, LDA_live: gate loop L_50 (one load); result − last sample", f"{L:.2f} ns; {cyc}", [f"{L:.1f}", "9 cycles"], q)
    q = src(B2 + "board/live/check_board_lda.json", "name+date"); C = json.load(open(q))
    bx = C["bit_exact_vs_lda_model"]; assert bx["D"] == bx["logit"] == bx["dec"] == 0
    row("Variant builds", "LDA_live on the boards: shots bit-exact against lda_model.py (D, logit, decision)", f"{bx['n']:,} of {bx['n']:,}", [f"{bx['n']:,}"], q)
    h = C["sets"]["headline_mosaic"]; pr = h["NN_live_vs_LDA_live"]
    row("Variant builds", "LDA_live on the boards, headline mosaic: LDA_live / NN_live (v1.44, same rows); NN − LDA, exact p",
        f"{h['LDA_live_board']['fid']:.2f}% / {h['NN_live_v144_same_rows']['fid']:.2f}%; {pr['dF']:+.3f}, p = {pr['p_exact']:.3f}",
        [f"{h['LDA_live_board']['fid']:.2f}", f"{h['NN_live_v144_same_rows']['fid']:.2f}", f"{pr['p_exact']:.2f}"], q)
    q = src(B2 + "lda_csim_score.json", "name+date"); h = json.load(open(q))["sets"]["headline_mosaic"]; pr = h["NN_live_vs_LDA_fixed"]
    row("Variant builds", "LDA_live model on the stored windows, headline mosaic: LDA; NN − LDA, exact p",
        f"{h['LDA_fixed_csim']['fid']:.2f}%; {pr['dF']:+.3f}, p = {pr['p_exact']:.1e}",
        [f"{h['LDA_fixed_csim']['fid']:.2f}", f"{pr['dF']:.2f}", f"{pr['p_exact']:.1e}".replace("e-0", "e-")], q)
    q = src("campaign_v144/final/inloop/arms/arms_full_analysis.json", "name+date"); A = json.load(open(q))
    for b in "AB":
        z = A[b]["paired_vs_nominal"]["zero"]
        row("Variant builds", f"Board {b}, pulse-gain arms on 99,400 traces: zero − nominal [95% CI], exact p",
            f"{z['dF']:+.3f} [{z['dF_ci'][0]:+.3f}, {z['dF_ci'][1]:+.3f}], p = {z['p_exact']:.3f}",
            [f"{abs(z['dF']):.2f}", f"{z['p_exact']:.3f}" if z["p_exact"] < 0.1 else f"{z['p_exact']:.2f}",
             f"{abs(z['dF_ci'][0]):.2f}", f"{abs(z['dF_ci'][1]):.2f}"], q)
    q = src("campaign_v144/final/analysis/stats/holm_pass9.json", "name+date"); H = json.load(open(q))
    mh = max(t["holm"] for t in H["tests"] if t["holm"] < 0.05)
    adj = {t["test"]: t["holm"] for t in H["tests"]}
    row("Paired statistics", "Holm over every p-value printed after pass 9: tests / survivors / largest surviving adjusted p", f"{H['n']} / {H['survivors']} / {mh:.4f}",
        [H["n"], f"{math.ceil(mh * 1000) / 1000:.3f}"], q)
    a1, a2 = adj["In the loop: Board B, vs its gate-idle run"], adj["zero vs nominal pulse gain, board A, 99,400"]
    row("Paired statistics", "Holm-adjusted p after pass 9: board B in-loop vs gate-idle; zero vs nominal gain, board A", f"{a1:.3f}; {a2:.3f}", [f"{a1:.2f}", f"{a2:.2f}"], q)


def pass9b():
    """Numbers text pass 9b adds from results already on hand."""
    sd = []
    for b in "AB":   # P68: edge scatter at the 500 and 1,500 MHz carriers
        q = src(f"campaign_v144/final/latency/carrier/{b}_carrier.json", "banner"); J = json.load(open(q))
        sd += [(J["runs"][c]["edge_sd"], J["runs"][c]["edge_sd"] * 1e3 / J["fs_decimated_mhz"]) for c in ("500.0", "1500.0")]
    lo, hi = min(sd), max(sd)
    row("Readout path", "Edge s.d. at the 500 and 1,500 MHz carriers, both boards: samples; ns", f"{lo[0]:.3f}–{hi[0]:.3f}; {min(s[1] for s in sd):.3f}–{max(s[1] for s in sd):.3f}",
        [f"{lo[0]:.2f}", f"{hi[0]:.2f}", f"{min(s[1] for s in sd):.2f}", f"{max(s[1] for s in sd):.2f}"], src("campaign_v144/final/latency/carrier/A_carrier.json", "banner"))
    tu = src(f"{TR}v1.44_routed_util_hier.rpt", "build-file"); t = Path(tu).read_text(encoding="utf-8", errors="ignore")
    lut = lambda n: int(re.search(r"^\|\s+" + re.escape(n) + r"\s+\|\s+\S+\s+\|\s+(\d+)", t, flags=re.M)[1])
    a, ld, nn = lut("NN_axi_0"), lut("grp_NN_axi_Pipeline_LOAD_L_fu_569"), lut("grp_NN_fu_597")
    row("Implementation", "NN_axi LUTs: whole / window load loop / NN()", f"{a:,} / {ld:,} / {nn:,}", [f"{a:,}", f"{ld:,}", f"{nn:,}"], tu)
    # below the earliest clean margin the port value does not track the shot's own window sum (|r| ~ 0), so the
    # 'fresh' count there is chance agreement, not a count of stale shots; the paper prints the correlation instead
    lo, hi, cl, q0 = [], [], set(), None
    for b in "AB":
        q = src(f"campaign_v144/final/board3/threshold/{b}_threshold.json", "banner"); J = json.load(open(q))["threshold"]["fir"]; q0 = q0 or q
        m0 = J["earliest_clean"]["margin"]; cl.add(m0)
        lo += [abs(p["r_port_host"]) for p in J["points"] if p["margin"] < m0]
        hi += [p["r_port_host"] for p in J["points"] if p["margin"] >= m0]
        late = max(p["margin"] for p in J["points"] if p["margin"] < m0)
    assert len(cl) == 1; m0 = 1e3 * cl.pop()
    row("tProc path", "Boards A and B, QICK threshold feedback (FIR): latest unclean margin; max |r| (port vs own window sum) below the earliest clean margin; min r from it; earliest clean margin",
        f"{1e3 * late:.0f} ns; {max(lo):.2f}; {min(hi):.2f}; {m0:.0f} ns", [f"{1e3 * late:.0f}", f"{max(lo):.2f}", f"{min(hi):.2f}", f"{m0:.0f}"], q0)
    q = src(D + "analysis/s3/s3_live_window_lda.json", "name+date"); s = json.load(open(q))["points"]["770"]["test"]
    row("Linear baselines", "LDA on raw traces, all 770 recorded samples, 100,000 test traces", f"{s['fid']:.3f}%",
        [str(Decimal(repr(round(s['fid'], 6))).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))], q)
    q = src("campaign_v144/final/analysis/stats/t2346_paired.json", "name+date"); J = json.load(open(q))
    for b in "AB":
        d = J["NN_live-LDA_fir770"]["fresh"][b]["diff"]
        row("Paired statistics", f"NN_live vs LDA FIR-770, board {b}, the 80,000 unused rows", f"{d['dF']:+.3f} points, {d['A_only']} vs {d['B_only']}, exact p = {d['p_exact']:.2g}",
            [f"{abs(d['dF']):.2f}", f"{d['p_exact']:.0e}".replace("e-0", "e-") if d["p_exact"] < 1e-3 else f"{d['p_exact']:.2f}"], q)
    d = J["B_minus_A"]["NN_live"]["all"]
    row("Paired statistics", "NN_live, board B − board A, 99,400 [95% CI]", f"{d['dF']:+.3f} [{d['ci95_normal'][0]:+.3f}, {d['ci95_normal'][1]:+.3f}]",
        [f"{d['dF']:.2f}", f"{d['ci95_normal'][0]:.2f}", f"{d['ci95_normal'][1]:.2f}"], q)
    q = src("campaign_v144/final/analysis/stats/holm_pass9b.json", "name+date"); H = json.load(open(q))
    mh = max(t["holm"] for t in H["tests"] if t["holm"] < 0.05)
    row("Paired statistics", "Holm over every p-value printed after pass 9b: tests / survivors / largest surviving adjusted p", f"{H['n']} / {H['survivors']} / {mh:.4f}",
        [H["n"], f"{math.ceil(mh * 1000) / 1000:.3f}"], q)
    adj = {t["test"]: t["holm"] for t in H["tests"]}
    a1, a2 = adj["In the loop: Board B, vs its gate-idle run"], adj["zero vs nominal pulse gain, board A, 99,400"]
    row("Paired statistics", "Holm-adjusted p after pass 9b: board B in-loop vs gate-idle; zero vs nominal gain, board A", f"{a1:.3f}; {a2:.3f}", [f"{a1:.2f}", f"{a2:.2f}"], q)


# ----------------------------------------------------------------------- run every group
assert sha(BIT) == BIT_SHA
for fn in (nn_live, replay_decisions, inloop, axi, timing_checks, emulator, leak, gate_saving, swap_phase, phrst, box_vs_fir, synthetic, nonlinear, channel, fig7, implementation, scaling, latency, fig8b):
    attempt(fn)
def pass11():
    """Numbers text pass 11 adds, from results already on hand."""
    # P128, P156, P181, P184: shot spacing; board B's fine sweep is the only one between 6.5 and 11.5 us
    per = {}
    for b, f in (("A", "A_spacing.log"), ("B", "B_spacing_fine.log")):
        q = src(f"campaign_v144/final/tests/spacing/{f}", "banner"); t = Path(q).read_text(encoding="utf-8", errors="ignore")
        pts = [(float(m[1]), m[2] == "CLEAN") for m in re.finditer(r"period ~([\d.]+) us\): (CLEAN|NOT CLEAN)", t)]
        per[b] = (min(p for p, c in pts if c), max(p for p, c in pts if not c))
    row("In the loop", "Shot spacing: shortest clean period A (coarse sweep) / B (fine sweep); longest failing period on B",
        f"{per['A'][0]:.2f} / {per['B'][0]:.2f} µs; {per['B'][1]:.2f} µs", [f"{per['A'][0]:.1f}", f"{per['B'][0]:.1f}", f"{per['B'][1]:.1f}"], src("campaign_v144/final/tests/spacing/B_spacing_fine.log", "banner"))
    rate = []
    for b in "AB":
        q = src(f"{D}inloop/{b}_inloop_0_100000.log", "banner")
        rate.append(float(re.findall(r"([\d.]+) shots/s", Path(q).read_text(encoding="utf-8", errors="ignore"))[-1]))
    row("In the loop", "In-loop campaign: shot rate A / B; time between shots", f"{rate[0]:.2f} / {rate[1]:.2f} shots/s; {1 / max(rate):.3f}–{1 / min(rate):.3f} s",
        [f"{1 / (sum(rate) / 2):.2f}"], src(f"{D}inloop/A_inloop_0_100000.log", "banner"))
    # P139: the boxcar path's cost, to NN_live and to LDA at 576 samples
    q = src(D + "analysis/box_vs_fir_v144.json", "name+date"); dF = json.load(open(q))["all99400"]["paired"]["dF"]
    row("Readout path", "Boxcar minus FIR path, NN_live, board A, 99,400 rows (unrounded)", f"{dF:+.4f} points", [f"{dF:.2f}"], q)
    q = src("campaign_v144/final/analysis/offline/lda_box_vs_fir.json", "name+date"); r = json.load(open(q))["headline_mosaic"]["box576-fir576"]
    row("Linear baselines", "LDA at 576 samples, boxcar minus FIR path, headline 99,400; exact p", f"{r['dF']:+.4f} points, {r['a_only']} vs {r['b_only']}, p = {r['p_exact']:.2g}",
        [f"{abs(r['dF']):.2f}", f"{r['p_exact']:.0e}".replace("e-0", "e-"), "576"], q)
    # P152, P179, P182, P185: the tProc routes at both core clocks, earliest margin with every shot fresh
    B1 = "firmware_v1.44/variants/tproc245/board/"

    def first(q, v):
        for p in json.load(open(q))["points"]:
            if p["variant"] == v and p["fresh"] == p["n"]:
                return p["L_median"]
    L = {}
    for b in "AB":
        for clk, q in (("200", src(f"{D}board2/{b}_tproc_box_v144.json", "banner")), ("245", src(f"{B1}{b}_tproc_box_t245.json", "name+date"))):
            L[b, clk, "nb"], L[b, clk, "j"] = first(q, "nobranch"), first(q, "qick")
        L[b, "fir"] = first(src(f"{D}board2/{b}_tproc_fir_v144.json", "banner"), "nobranch")
        L[b, "b1"] = json.load(open(src(f"{B1}{b}_b1_latency.json", "name+date")))["points"]["op"]["L_50"]["mean"]
    row("tProc path", "tProc branch on the boxcar path, 245.76 MHz core (build 1), earliest clean margin, no-jump / jump form, A; B",
        f"{L['A', '245', 'nb']:.1f} / {L['A', '245', 'j']:.1f} ns; {L['B', '245', 'nb']:.1f} / {L['B', '245', 'j']:.1f} ns",
        [f"{L['A', '245', 'nb']:.1f}", f"{L['B', '245', 'nb']:.1f}", f"{min(L[b, '245', 'nb'] for b in 'AB'):.0f}", f"{max(L[b, '245', 'j'] for b in 'AB'):.0f}"], src(f"{B1}A_tproc_box_t245.json", "name+date"))
    lo200 = min(L[b, "200", "nb"] for b in "AB"); hi200 = max(L[b, "200", "j"] for b in "AB")
    l50 = {"A": 175.9, "B": 173.9}   # each board's campaign L_50 group (latency rows above): A upper, B lower
    box = [L[b, "fir"] - L[b, "200", "nb"] for b in "AB"]; gate = [L[b, "200", "nb"] - l50[b] for b in "AB"]
    g245 = [L[b, "245", "nb"] - L[b, "b1"] for b in "AB"]; tot = [L[b, "fir"] - l50[b] for b in "AB"]
    row("tProc path", "Measured saving against the tProc branch on the FIR path, A / B: total; boxcar path; gate (200 MHz); gate (245.76 MHz); tProc branch range at 200 MHz",
        f"{tot[0]:.1f} / {tot[1]:.1f}; {box[0]:.1f} / {box[1]:.1f}; {gate[0]:.1f} / {gate[1]:.1f}; {g245[0]:.1f} / {g245[1]:.1f}; {lo200:.1f}–{hi200:.1f} ns",
        [f"{5 * round(sum(tot) / 10):.0f}", f"{min(box):.0f}", f"{max(box):.0f}", f"{10 * round(sum(gate) / 20):.0f}", f"{10 * round(sum(g245) / 20):.0f}", f"{hi200:.0f}"],
        src(f"{D}board2/A_tproc_box_v144.json", "banner"))
    w = [(t, t / (3 * 32000) * 100, t / (2 * 32000) * 100) for t in (140, 160)]
    row("tProc path", "Gate saving 140 / 160 ns at T1 = 32 us: t/(3T1); t/(2T1), points", f"{w[0][1]:.3f} / {w[1][1]:.3f}; {w[0][2]:.3f} / {w[1][2]:.3f}",
        [f"{w[0][1]:.2f}", f"{w[1][1]:.2f}", f"{w[0][2]:.2f}", f"{w[1][2]:.2f}"], src(f"{D}board2/A_tproc_box_v144.json", "banner"))
    thb = {}
    for b in "AB":
        q = src(f"campaign_v144/final/board3/threshold/{b}_threshold.json", "banner"); thb[b] = json.load(open(q))["threshold"]["box"]["earliest_clean"]["L_median"]
    row("tProc path", "QICK threshold feedback fed from the boxcar path, earliest clean margin, A / B", f"{thb['A']:.1f} / {thb['B']:.1f} ns",
        [f"{thb['A']:.1f}", f"{thb['B']:.1f}"], src("campaign_v144/final/board3/threshold/A_threshold.json", "banner"))
    q = src(f"{B1}B_threshold_t245.json", "name+date"); t245 = json.load(open(q))["threshold"]["fir"]["earliest_clean"]["L_median"]
    row("Variant builds", "QICK threshold feedback over both tProc clocks and both boards: lowest; highest (earliest clean margins)",
        f"{t245:.1f}; 521.8 ns", [f"{t245:.0f}", "522"], q)
    # P156, P198: leaked energy, DELAY from the 2000-amplitude crossing, over the three leads of the measurement
    fr, ub = [], []
    for b in "AB":
        q = src(f"{D}leak_energy/{b}_v144_leak_thr2000.json", "banner"); J = json.load(open(q))
        for k in ("2", "3", "4"):
            fr.append(100 * J["leads"][k]["frac_mean"]); ub.append(100 * J["leads"][k]["frac_ci"][1])
    row("Safety and tests", "Leaked energy, DELAY from the 2000-amplitude crossing, leads 2-4, both boards: mean range; largest upper 95% bound",
        f"{min(fr):.3f}–{max(fr):.3f}%; {max(ub):.3f}%", [f"{min(fr):.2f}", f"{max(fr):.2f}", f"{max(ub):.2f}"], src(f"{D}leak_energy/B_v144_leak_thr2000.json", "banner"))
    # P163: the largest L_50 shift over every sensitivity set (gain, phase, no stimulus) of the reloads and cold starts
    sh = []
    for f in sorted(glob.glob("campaign_v144/final/latency/reloads/*.json")) + sorted(glob.glob(D + "latency/cold/*.json")):
        s = json.load(open(f)).get("sensitivity") or {}
        if "base" in s:
            sh += [(abs(v["L_50"]["mean"] - s["base"]["L_50"]["mean"]), f.replace("\\", "/"), k) for k, v in s.items() if k != "base" and isinstance(v, dict) and "L_50" in v]
    m = max(sh); q = src(m[1], "name+date")
    row("Loop latency", "Largest L_50 shift over all sensitivity sets (gain, carrier phase, no stimulus)", f"{m[0]:.3f} ns ({Path(m[1]).name}, {m[2]})", [f"{m[0]:.1f}"], q)
    # P178: the fixed-ridge LDA on all 770 samples; the augmented models against the deployed network
    q = src(D + "analysis/s5_linear_99400_v144.json", "name+date"); r = json.load(open(q))["headline"]["LDA_ridge0.01"]
    row("Linear baselines", "LDA, fixed ridge 1e-2, 770 samples, run 1, 99,400 rows, vs NN_live on the same shots",
        f"{r['fid']['fid']:.2f}%, {r['vs_NN_live']['dF']:+.3f} points, exact p = {r['vs_NN_live']['p_exact']:.2g}",
        [f"{r['fid']['fid']:.2f}", f"{r['vs_NN_live']['p_exact']:.3f}", "770"], q)
    q = src(D + "analysis/s2/arch_aug_v144.json", "name+date"); P = json.load(open(q))["paired_vs_t4"]
    dd = [P[f"{m_}_aug_vs_t4_clean"] for m_ in ("seg_mlp", "bin_mlp", "bin_gru", "cnn1d")]
    row("Linear baselines", "Augmented models vs the deployed 4-unit network, board A replay, 16,000 shots: gain range; largest p",
        f"{min(x['delta'] for x in dd):.3f}–{max(x['delta'] for x in dd):.3f} points; p ≤ {max(x['p'] for x in dd):.3f}",
        [f"{min(x['delta'] for x in dd):.2f}", f"{max(x['delta'] for x in dd):.2f}", f"{math.ceil(max(x['p'] for x in dd) * 100) / 100:.2f}"], q)
    # P180: the first LDA build (weights in logic)
    q = src("firmware_v1.44/variants/lda_gate/reports/v1.44lda_routed_timing.rpt", "name+date")
    wns = float(re.search(r"WNS\(ns\).*\n.*\n\s+([-\d.]+)", Path(q).read_text(encoding="utf-8", errors="ignore"))[1])
    row("Variant builds", "Build 2 (LDA_live 1.0, weights in logic): design WNS", f"{wns * 1000:.0f} ps", [f"{-wns * 1000:.0f}"], q)
    # P152, P201: the session shift of the same bit-exact LDA; board A's nominal arm against its gate-idle run 2
    a = json.load(open(src("firmware_v1.44/variants/lda_gate/lda_csim_score.json", "name+date")))["sets"]["headline_mosaic"]["LDA_fixed_csim"]["fid"]
    q = src("firmware_v1.44/variants/lda_gate/board/live/check_board_lda.json", "name+date")
    b_ = json.load(open(q))["sets"]["headline_mosaic"]["LDA_live_board"]["fid"]
    row("Variant builds", "Same bit-exact LDA, headline mosaic: later board session minus stored v1.44 windows", f"{b_ - a:+.3f} points", [f"{b_ - a:.2f}"], q)
    q = src("campaign_v144/final/inloop/arms/arms_full_analysis.json", "name+date"); r = json.load(open(q))["A"]["final_run2"]
    pr = r["paired"]["nominal"]
    row("Variant builds", "Board A, nominal-gain arm vs gate-idle run 2 (rows 50,000-99,999): difference, exact p",
        f"{pr['dF']:+.3f}, p = {pr['p_exact']:.3f}, n = {r['n']:,}", [f"{pr['dF']:.2f}", f"{pr['p_exact']:.2f}", f"{r['n']:,}"], q)
    q = src("campaign_v144/final/analysis/stats/holm_pass11.json", "name+date"); H = json.load(open(q))
    row("Paired statistics", "Holm over every p-value printed after pass 11: tests / survivors / largest surviving adjusted p",
        f"{H['n']} / {H['survivors']} / {H['max_surviving_adjusted']:.4f}", [H["n"], f"{math.ceil(H['max_surviving_adjusted'] * 1000) / 1000:.3f}"], q)
    a1, a2 = H["adj_p201"]["boardB_inloop"], H["adj_p201"]["boardA_zero"]
    row("Paired statistics", "Holm-adjusted p after pass 11: board B in-loop vs gate-idle; zero vs nominal gain, board A", f"{a1:.3f}; {a2:.3f}", [f"{a1:.2f}", f"{a2:.2f}"], q)


def pass12():
    """Numbers the paper quotes since its twelfth revision: the per-shot spread of the tProc routes, the failing
    endpoints of the 245.76 MHz build, the LDA core's block RAM and per-board counts, the loop's per-shot tail, the
    2000-crossing leak as pulse area, and L_50 one slack step later."""
    sd = []
    for b in "AB":   # the tProc routes at the points the text quotes
        q = src(f"{B2}{b}_tproc_box_v144.json", "banner"); P = json.load(open(q))["points"]
        sd += [_clean(P, v)[0]["L_sd"] for v in ("nobranch", "qick")]
        q = src(f"{B2}{b}_tproc_fir_v144.json", "banner"); sd.append(_clean(json.load(open(q))["points"], "nobranch")[0]["L_sd"])
        q = src(f"{D}board3/{b}_tproc_thr_v144.json", "banner", f"{D}board3/{b}_tproc_thr.log"); pts = json.load(open(q))["points"]
        fine = f"{D}board3/{b}_tproc_thr_fine_v144.json"
        if Path(fine).exists():
            pts += json.load(open(src(fine, "banner", f"{D}board3/{b}_tproc_thr_fine.log")))["points"]
        sd.append(_clean(sorted(pts, key=lambda x: x["margin"]), "qickthr")[0]["L_sd"])
    row("tProc path", "tProc routes (branch on the boxcar path, both forms; branch on the FIR path; QICK threshold feedback), both boards: per-shot s.d. range",
        f"{min(sd):.2f}\u2013{max(sd):.2f} ns over {len(sd)} medians", [f"{max(sd):.0f}"], src(f"{B2}A_tproc_box_v144.json", "banner"))
    q = src("firmware_v1.44/variants/tproc245/reports/v1.44t245_routed_timing.rpt", "name+date"); t = Path(q).read_text(encoding="utf-8", errors="ignore")
    intra = t[t.index("Intra Clock Table"):t.index("Inter Clock Table")]
    fail = {m[1]: (float(m[2]), int(m[4])) for m in re.finditer(r"^\s+(\S+)\s+(-?[\d.]+)\s+(-?[\d.]+)\s+(\d+)\s+\d+", intra, flags=re.M)}
    bad = {k: v for k, v in fail.items() if v[1] > 0}
    assert list(bad) == ["clk_out1_d_1_clk_adc0_x2_0"] and fail["clk_out1_d_1_clk_core_0"][0] >= 0, fail
    row("Variant builds", "Build 1 (tProc core at 245.76 MHz): failing setup endpoints, all in the ADC-side readout clock; tProc core clock WNS",
        f"{bad['clk_out1_d_1_clk_adc0_x2_0'][1]} endpoints; core {fail['clk_out1_d_1_clk_core_0'][0]:+.3f} ns", [f"{bad['clk_out1_d_1_clk_adc0_x2_0'][1]}"], q)
    q = src("firmware_v1.44/variants/lda_gate/reports/v1.44lda11_routed_util_hier.rpt", "name+date")
    m = re.search(r"^\|\s+NN_live_0\s+\|\s+\S+\s+\|\s+(\d+)\s+\|\s+\d+\s+\|\s+\d+\s+\|\s+\d+\s+\|\s+\d+\s+\|\s+(\d+)\s+\|\s+(\d+)\s+\|\s+\d+\s+\|\s+(\d+)",
                  Path(q).read_text(encoding="utf-8", errors="ignore"), flags=re.M)
    bram = int(m[2]) + int(m[3]) / 2
    row("Variant builds", "LDA_live 1.1 in NN_live's slot (build 2b): RAMB36 + RAMB18 as 36-kb tiles; DSP", f"{m[2]} + {m[3]} = {bram:g} tiles; {m[4]} DSP", [f"{bram:g}"], q)
    lv = "firmware_v1.44/variants/lda_gate/board/live/"
    q = src(lv + "check_board_lda.json", "name+date"); n_all = json.load(open(q))["bit_exact_vs_lda_model"]["n"]
    nb = {}
    for b, (lo, hi) in (("A", (0, 50000)), ("B", (50000, 100000))):   # one capture file per 1,000 rows (data archive)
        nb[b] = sum(e - s for s, e in ((s, s + 1000) for s in range(lo, hi, 1000)) if need(f"{lv}{b}_run1_{s}_{e}.npz"))
    assert nb["A"] + nb["B"] == n_all, (nb, n_all)
    row("Variant builds", "LDA_live on the boards: bit-exact shots per board, A / B", f"{nb['A']:,} / {nb['B']:,}", [f"{nb['A']:,}"], q)
    G = loop_groups(); tail = {}
    for name in ("low", "high"):   # every shot of the group's campaign loads at the operating slack
        a = []
        for load in G[name]["loads"]:
            z = np.load(need(f"{D}latency/{'cold' if '_c' in load else 'reloads'}/{load}.npz"), allow_pickle=False)
            col = list(z["columns"]).index("L_50"); x = z["row_op"][:, col]; a += list(x[np.isfinite(x)])
        a = np.array(a); tail[name] = (np.percentile(a, 99), a.max(), len(a))
    g = src(D + "analysis/loop_groups_values_v144.json", "banner", f"{D}latency/reloads/{G['low']['loads'][0]}.json")
    row("Loop latency", "Per-shot L_50 tail, lower / upper group: 99th percentile; largest shot",
        f"{tail['low'][0]:.2f} / {tail['high'][0]:.2f}; {tail['low'][1]:.2f} / {tail['high'][1]:.2f} ns ({tail['low'][2]:,} and {tail['high'][2]:,} shots)",
        [f"{tail['low'][0]:.1f}", f"{tail['high'][0]:.1f}", f"{tail['low'][1]:.1f}", f"{tail['high'][1]:.1f}"], g)
    step = json.load(open(src(f"{D}latency/reloads/{G['low']['loads'][0]}.json", "banner")))["settings"]["tick_ns"]
    lo, hi = G["low"]["L_50"] + step, G["high"]["L_50"] + step
    row("Loop latency", "L_50 one slack step (one tProc tick) later than the campaign's, lower / upper group", f"{lo:.1f} / {hi:.1f} ns (step {step:.3f} ns)",
        [f"{lo:.0f}", f"{hi:.0f}", f"{step:.2f}"], g)
    # the leak of the 2000-crossing calibration as a share of the Gaussian pulse's area (its rotation), taking the leak
    # as the pulse's leading part; the pulse shape is the measurement's own (sigma, length), centred as QICK draws it
    q = src(f"{LK}B_v144_leak_thr2000.json", "banner", f"{LK}B_v144_leak_thr2000.log"); J = json.load(open(q))
    ub = max(json.load(open(src(f"{LK}{b}_v144_leak_thr2000.json", "banner")))["leads"][k]["frac_ci"][1] for b in "AB" for k in ("2", "3", "4"))
    tt = np.linspace(0, J["cp_len_us"], 200001); g_ = np.exp(-(tt - J["cp_len_us"] / 2) ** 2 / (2 * J["sigma_us"] ** 2))
    E = np.cumsum(g_ ** 2); E /= E[-1]; A_ = np.cumsum(g_); A_ /= A_[-1]
    area = A_[np.searchsorted(E, ub)]; flip = math.sin(math.pi * area / 2) ** 2
    row("Safety and tests", "Leak of the 2000-crossing calibration at its largest upper 95% bound, as a share of the Gaussian pulse's area; flip probability on a pi pulse",
        f"{100 * ub:.3f}% of energy = {100 * area:.2f}% of area; {100 * flip:.3f}%", [f"{100 * area:.1f}", f"{100 * flip:.2f}"], q,
        "leak taken as the pulse's leading part")


def pass18():
    """Pass 18 (2026-11-23): numbers the comment replies put into the text."""
    q = src("campaign_v144/final/latency/reloads/summary_A.md", "banner")
    pulses = [(int(a), int(b)) for a, b in re.findall(r"^\| rv\d+ \| pass \| (\d+)/(\d+) \|", Path(q).read_text(encoding="utf-8"), re.M)]
    assert len(pulses) == 40 and all(a == b for a, b in pulses), pulses
    n = {b for _, b in pulses}; assert n == {100}, n
    row("Safety and tests", "40 further loads (20 per board), stale decisions blanked: pulses played / shots per load; no late decision",
        f"{sum(a for a, _ in pulses):,}/{sum(b for _, b in pulses):,}, 100 shots per load", ["40", "100"], q)
    q = src(D + "analysis/channel_v144.json", "banner", D + "axi/A_axi_0.log"); J = json.load(open(q))
    row("Replay channel", "Class SNR per sample, replayed board B (rms mean separation over rms noise)", f"{J['snr_B']:.2f}", [f"{J['snr_B']:.2f}"], q)
    q = src(D + "analysis/channel_noise_v144.json", "name+date"); J = json.load(open(q))
    for b in "AB":
        x = [y for y in J["boards"][b]["bands"] if (y["lo"], y["hi"]) == (60, 150)][0]
        row("Replay channel", f"Board {b}: share of the added noise's power at 60-150 MHz (white noise: share of bins); added / source noise power there",
            f"{100 * x['share']:.0f}% (white {100 * x['white_share']:.1f}%); {x['vs_source']:.2f}x", [f"{100 * x['share']:.0f}"], q,
            "residual of arch_aug.fit_channel on 4,000 fit shots")
    q = src(D + "analysis/s2/board_B/arch_aug_v144_B.json", "name+date"); J = json.load(open(q))
    for arm in ("seg_mlp", "bin_mlp", "bin_gru", "cnn1d"):
        r = J[f"{arm}_aug"]; v = r["vs_lda_clean"]; t = J["paired_vs_t4"][f"{arm}_aug_vs_t4_clean"]
        row("Replay-channel augmentation", f"{arm} trained on augmented data vs LDA / vs the chip's 4-unit network, board B replay, 16,000 shots",
            f"{r['loop16k']:.2f}%, {v['delta']:+.2f} points (p = {pv(v['p'])}); {t['delta']:+.2f} points (p = {pv(t['p'])})",
            [f"{r['loop16k']:.2f}", f"{abs(v['delta']):.2f}", pv(v["p"]), f"{abs(t['delta']):.2f}", pv(t["p"])], q)
    q2 = src("campaign_v144/final/analysis/stats/holm_pass18.json", "name+date"); H = json.load(open(q2))
    mh = -(-H["max_surviving_adjusted"] * 1000 // 1) / 1000
    row("Round-2 statistics", "Holm over every p-value printed after pass 18: tests / survivors / largest surviving adjusted p (rounded up)",
        f"{H['n']} / {H['survivors']} / {H['max_surviving_adjusted']:.4f}", [str(H["n"]), f"{mh:.3f}"], q2)
    row("Replay-channel augmentation", "Board B: deployed 4-unit network, chip (clean) / retrained on augmented data; LDA", f"{J['t4_clean']:.2f}% / {J['t4_aug']:.2f}%; {J['lda_clean']:.2f}%",
        [f"{J['t4_clean']:.2f}", f"{J['t4_aug']:.2f}", f"{J['lda_clean']:.2f}"], q)


def replay_interp():
    """The replay's linear interpolation: its part of the replay channel's low-pass response, the time stretch it leaves
    and the noise power of the replayed traces (replay_interp_v144.py)."""
    q = src(D + "analysis/replay_interp_v144.json", "name+date"); J = json.load(open(q))
    i = [k for k, bd in enumerate(J["bands_MHz"]) if tuple(bd) == (60, 150)][0]
    iv = J["interp_dB"][i]
    row("Replay channel", "Linear interpolation's power response at 60-150 MHz, relative to 0-20 MHz (sinc^4 formula, checked by simulation)",
        f"{iv:+.2f} dB", [f"{abs(iv):.1f}"], q)
    for b in "AB":
        r = J["boards"][b]
        row("Replay channel", f"Board {b}: replay channel's power response at 60-150 MHz relative to 0-20 MHz; the interpolation's part of it",
            f"{r['channel_dB'][i]:+.2f} dB; {100 * r['interp_share'][i]:.0f}%", [f"{abs(r['channel_dB'][i]):.1f}"], q)
        st = 100 * (1 / r["stretch_a"] - 1)
        row("Replay channel", f"Board {b}: time stretch of the replayed traces, fitted on the class means (expected {100 * (1 / J['stretch_expected_a'] - 1):.2f}%)",
            f"{st:.2f}%, {r['drift_over_fit_samples']:.1f} samples over samples 8-759", [f"{st:.1f}", f"{r['drift_over_fit_samples']:.1f}"], q)
        row("Replay channel", f"Board {b}: within-class noise power, replayed over source scaled by the fitted gain squared",
            f"{r['noise_power_ratio']:.3f} ({r['noise_power_ratio_dB']:+.2f} dB)", [f"{100 * (r['noise_power_ratio'] - 1):.0f}"], q)


for fn in (s2_aug, s5_linear, rev_reloads, rev_stability, rev_arms, rev_carrier_jitter_spacing, rev_logit, rev_keras, rev_map_trainrows, rev_live_window,
           rev2_stats, rev2_protocol, rev2_fpga, rev2_pass8, pass18, replay_interp):
    attempt(fn)
for b in "AB":
    for fn in (linear, tproc_box, tproc_fir, boxcar_mr, tests, tproc_fir_earliest, tproc_thr):
        attempt(fn, b)
for h, b in HOSTS:
    attempt(drift, h, b)
attempt(rev2_board)
attempt(pass9b)
attempt(pass11)
attempt(pass12)
for t, lab in (("A_own", "Board A, own calibration"), ("B_own", "Board B, own calibration"), ("B_on_A_calibration", "Board B on board A's calibration")):
    attempt(swap, t, lab)


# ----------------------------------------------------------------------- the v1.43 ledger sets the rows and their order
def norm(k):
    """Row name without the numbers that a build measures, so the same row matches on both builds."""
    k = re.sub(r",? ?arg\(k\) -?[\d.]+ deg", "", k)
    k = re.sub(r" \(\d+ loads\)", "", k)
    k = re.sub(r" L_50 \([\d.]+\)", " L_50", k)
    k = re.sub(r", rounded, \d+ ns group", ", rounded", k)
    return re.sub(r"SCALING_OUT=resource_scaling_v14\d", "SCALING_OUT=resource_scaling", k)


def expected(s, key):
    """Where a pending row's source will be."""
    if key.startswith("Classifier units"):
        return "scaling_study/resource_scaling_v144.json"
    for a, b_ in ((r"^campaign_v140L1/A_v143_(\w+\.json)$", D + r"tests/A_\1"), (r"^campaign_v143/pre_6_3/(B_\w+\.json)$", D + r"tests/\1"),
                  (r"^campaign_v140L1/v143_fig8b/", D + "fig8b/"), (r"^paper_figures/fig7/", D + "fig7/"), (r"axi_emu\.json$", "axi_emu_v144.json"),
                  (r"v1\.43_", "v1.44_")):
        s = re.sub(a, b_, s)
    return s.replace("v143", "v144")


have = {(r["section"], norm(r["key"])): r for r in ROWS}
assert len(have) == len(ROWS), "two rows share a name"
template = json.load(open(TEMPLATE))["rows"]
names = {(r["section"], norm(r["key"])) for r in template}
final, pending = [], []
for t in template:
    n_ = norm(t["key"])
    if (t["section"], n_) in have:
        final.append(have[(t["section"], n_)])
    else:
        p = dict(section=t["section"], key=n_, value="PENDING", text=[], source=expected(t["source"], t["key"]), kind="pending", note="")
        final.append(p); pending.append(p)
extra = [r for r in ROWS if (r["section"], norm(r["key"])) not in names]
for r in extra:                                     # results v1.44 has and v1.43 did not, at the end of their section
    same = [i for i, x in enumerate(final) if x["section"] == r["section"]]
    if same:
        final.insert(max(same) + 1, r)
    else:                                           # a section v1.43 did not have: at the end
        final.append(r)

# ----------------------------------------------------------------------- output
order = list(dict.fromkeys(r["section"] for r in final))
done = len(final) - len(pending)
out = ["# v1.44 results ledger", "", "**Generated by `campaign_v144/final/analysis/make_v144_ledger.py`. Do not edit by hand.** Add a result by adding it to that script,",
       "which refuses any source that fails a build check. `--verify` fails if this file or a source has changed since it was generated, or while any result is pending.", "",
       f"Build: `{BIT.name}`, sha256 `{BIT_SHA[:16]}...`, banner `{BANNER} 2026`.", "",
       f"Status: **{done} of {len(final)} results filled, {len(pending)} pending.** A PENDING row has no value yet; its Source column names the file it is waiting for.", "",
       "Evidence: **banner** = the v1.44 banner read from the board during that run; **bracketed** = banner logged before and after by the same uninterrupted runner; "
       "**build-file** = the report saved from the v1.44 build; **name+date** = named v1.44 and dated after the build, no banner (weakest).", ""]
for sec in order:
    out += [f"## {sec}", "", "| Result | Value | Evidence | Source |", "|---|---|---|---|"]
    for r in final:
        if r["section"] == sec:
            out.append(f"| {r['key']} | {r['value']} | {r['kind']} | `{r['source']}` |")
    out.append("")
weak = sorted(p for p, v in SRC.items() if v["kind"] == "name+date")
out += ["## Sources with weak build evidence", "", "These carry no banner. Confirm them or re-measure before submission.", ""] + [f"- `{p}`" for p in weak] + [""]
text = "\n".join(out)
payload = dict(rows=final, sources=SRC, pending=len(pending), waiting_for=sorted(set(BLOCKED)), md_sha256=hashlib.sha256(text.encode()).hexdigest())
if "--verify" in sys.argv:
    old = json.load(open(JS))
    # Board captures too large for the repository are listed in DATA_MANIFEST.csv and not shipped. Their results
    # cannot be recomputed here; they are counted as not rechecked, and every other result must still match.
    listed = {l.split(",")[0] for l in Path("DATA_MANIFEST.csv").read_text(encoding="utf-8").splitlines()[1:] if l}
    unshipped = {p for p in old["sources"] if not Path(p).exists() and p in listed}
    blocked = {b.replace("\\", "/") for b in BLOCKED}
    unshipped |= {b for b in blocked if b in listed or (any(c in b for c in "*?") and fnmatch.filter(listed, b))}
    bad = [p + ("" if Path(p).exists() else " (missing)") for p, v in old["sources"].items()
           if p not in unshipped and (not Path(p).exists() or sha(p)[:16] != v["sha256"])]
    bad += [f"{b} (missing, and not in DATA_MANIFEST.csv)" for b in sorted(blocked - unshipped)]
    if hashlib.sha256(MD.read_text(encoding="utf-8").encode()).hexdigest() != old["md_sha256"]:
        bad.append(f"{MD} was edited after it was generated")
    skipped = 0
    if not unshipped:                                # every source present: the file must regenerate exactly
        if MD.read_text(encoding="utf-8") != text or old["md_sha256"] != payload["md_sha256"]:
            bad.append(f"{MD} differs from what its sources give")
        if pending:
            bad.append(f"{len(pending)} results still pending")
    else:                                            # compare row by row, skipping rows whose source is not shipped
        now = {(r["section"], norm(r["key"])): r for r in final if r["kind"] != "pending"}
        for r in old["rows"]:
            if r["source"] in unshipped:
                skipped += 1
                continue
            n = now.pop((r["section"], norm(r["key"])), None)
            if n is None and blocked and blocked <= unshipped:   # its group stopped at a capture that is not shipped
                skipped += 1
                continue
            if n is None or str(n["value"]) != str(r["value"]):
                bad.append(f"result '{r['key']}' ({r['value']}) not reproduced")
        bad += [f"result '{r['key']}' not in the ledger" for r in now.values()]
    note = (f"; {skipped} rest on {len(unshipped)} board captures not shipped (DATA_MANIFEST.csv) and were not rechecked"
            if skipped else "")
    print("VERIFY", "FAILED: " + ", ".join(bad) if bad else f"OK: {len(old['rows']) - skipped} of {len(old['rows'])} results "
          f"rechecked against {len(old['sources']) - len(unshipped)} sources{note}")
    sys.exit(1 if bad else 0)
MD.write_text(text, encoding="utf-8")
JS.write_text(json.dumps(payload, indent=1, default=str))
print(f"wrote {MD}: {done} of {len(final)} filled, {len(pending)} pending, {len(extra)} new rows, {len(SRC)} sources, {len(weak)} weak")
print("new rows:", [r["key"] for r in extra])
print("waiting for:", *sorted(set(BLOCKED)), sep="\n  ")
