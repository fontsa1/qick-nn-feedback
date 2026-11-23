"""Tasks 2, 3, 4, 6: paired comparisons on the v1.44 NN_live captures (full 100,000-row test split, both boards).

Inputs (read-only):
  campaign_v144/final/analysis/offline/lda_99400_preds.npz   LDA decisions (fir770, fir576, box576) and NN_live decisions per set
                                                       (A_full, B_full, headline_mosaic), map rows 1000:1600 already removed
  campaign_v144/final/analysis/stats/emu_live_preds.npz     emulate_live_captures.py: per board/run, chip NN_live decision and
                                                       bit-accurate emulator probabilities box576 / fir576 / axi770
  campaign_v144/final/axi/{A,B}_axi_*.npz              on-chip NN_axi probabilities, rows 0-19,999 (to validate axi770)
  test100k_real_y.npy                                  labels
Sets: A = board A every row once (runs 1+2), B likewise; mosaic = run 1 of each board (A rows 0-49,999 + B rows
50,000-99,999), the paper's 95.60% composite; pooled = both boards, each row twice, row-clustered.
Row subsets: all = 99,400 (rows 1000:1600 dropped); dev = rows 0-19,999 minus map rows (19,400); fresh = rows 20,000-99,999 (80,000).
Methods: pstats.py (exact McNemar; paper's normal paired interval; class-stratified paired bootstrap, 20,000 draws;
row-clustered bootstrap + sign-flip test for the pooled set). Differences are in points of balanced fidelity, A - B
as named (e.g. NN_live - LDA).

Writes t2346_paired.json.
"""
import glob, json, re, sys
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[4]; OUT = Path(__file__).resolve().parent
sys.path.insert(0, str(OUT))
from pstats import paired_cmp, paired_cmp_cluster, fid_ci  # noqa: E402

L = np.load(ROOT / "campaign_v144/final/analysis/offline/lda_99400_preds.npz")
E = np.load(OUT / "emu_live_preds.npz")
y100 = np.load(ROOT / "test100k_real_y.npy").astype(int)
MAP = lambda r: (r >= 1000) & (r < 1600)

# ---- per-board arrays indexed by row (0..99,999); NaN-free: every row once per board
B = {}
for b in "AB":
    d = {k: np.full(100000, -1, np.int64) for k in ("nn", "box_emu", "fir576", "axi770", "fir770L", "fir576L", "box576L")}
    for r in "12":
        rows = E[f"{b}{r}_rows"]
        d["nn"][rows] = E[f"{b}{r}_chip"]
        d["box_emu"][rows] = (E[f"{b}{r}_box576"] > .5).astype(int)
        d["fir576"][rows] = (E[f"{b}{r}_fir576"] > .5).astype(int)
        d["axi770"][rows] = (E[f"{b}{r}_axi770"] > .5).astype(int)
        assert np.array_equal(E[f"{b}{r}_y"], y100[rows])
    lr = L[f"{b}_full_rows"]
    for mk in ("fir770", "fir576", "box576"):
        d[mk + "L"][lr] = L[f"{b}_full_{mk}"]
    assert np.array_equal(L[f"{b}_full_NN_live"], d["nn"][lr]), "LDA file's NN_live != chip decisions"
    assert (d["nn"] >= 0).all()
    B[b] = d
# mosaic: run 1 rows of each board
mos = {k: np.where(np.arange(100000) < 50000, B["A"][k], B["B"][k]) for k in B["A"]}
for mk in ("fir770", "fir576", "box576"):  # mosaic LDA file order check
    lr = L["headline_mosaic_rows"]; assert np.array_equal(L[f"headline_mosaic_{mk}"], mos[mk + "L"][lr])
rows = np.arange(100000)
SUB = {"all": ~MAP(rows), "dev": (rows < 20000) & ~MAP(rows), "fresh": rows >= 20000}
ok = lambda pred: pred == y100
res = dict(checks=dict(box_emu_eq_chip={b: int((B[b]["box_emu"] == B[b]["nn"]).sum()) for b in "AB"}))
print("box emulator == chip:", res["checks"]["box_emu_eq_chip"], flush=True)

# ---- NN_axi on-chip (rows 0-19,999) vs axi770 emulated on the live session's FIR buffer
chk = {}
for b in "AB":
    I, P = [], []
    for f in glob.glob(str(ROOT / f"campaign_v144/final/axi/{b}_axi_*.npz")):
        z = np.load(f); I.append(z["idx"]); P.append(z["probs"])
    I = np.concatenate(I); P = np.concatenate(P); o = np.argsort(I); I, P = I[o], P[o]
    chip = (P > .5).astype(int); m = ~MAP(I)
    emu = B[b]["axi770"][I]
    chk[b] = dict(n=int(m.sum()), agree=float(np.mean(chip[m] == emu[m])), chip_axi=fid_ci(chip[m], y100[I][m]),
                  emu_axi_live_fir=fid_ci(emu[m], y100[I][m]), chip_minus_emu=paired_cmp(chip[m] == y100[I][m], emu[m] == y100[I][m], y100[I][m]))
    B[b]["axi_chip_dev"] = (I, chip)
res["checks"]["axi_chip_vs_emulated_on_live_fir_rows0_19999"] = chk
print("axi check:", {b: (chk[b]["agree"], round(chk[b]["chip_axi"]["fid"], 3), round(chk[b]["emu_axi_live_fir"]["fid"], 3)) for b in "AB"}, flush=True)

def cmp_sets(ka, kb, label):
    """ka - kb for boards A, B, mosaic and pooled, on each row subset."""
    out = {}
    for sn, msk in SUB.items():
        o = {}
        for nm, d in (("A", B["A"]), ("B", B["B"]), ("mosaic", mos)):
            o[nm] = dict(fid_a=fid_ci(d[ka][msk], y100[msk]), fid_b=fid_ci(d[kb][msk], y100[msk]),
                         diff=paired_cmp(ok(d[ka])[msk], ok(d[kb])[msk], y100[msk]))
        o["pooled_AB"] = paired_cmp_cluster([ok(B[b][ka])[msk] for b in "AB"], [ok(B[b][kb])[msk] for b in "AB"], y100[msk])
        out[sn] = o
    res[label] = out
    for sn in SUB:
        o = out[sn]
        print(f"{label:22s} {sn:5s} " + "  ".join(
            f"{nm}: {o[nm]['diff']['dF']:+.3f} [{o[nm]['diff']['ci95_boot'][0]:+.3f},{o[nm]['diff']['ci95_boot'][1]:+.3f}] p={o[nm]['diff']['p_exact']:.2g}"
            for nm in ("A", "B", "mosaic")) + f"  pooled: {o['pooled_AB']['dF']:+.3f} [{o['pooled_AB']['ci95_boot'][0]:+.3f},{o['pooled_AB']['ci95_boot'][1]:+.3f}] p_sf={o['pooled_AB']['p_signflip']:.2g}", flush=True)

# NN_live - LDA
for mk in ("fir770", "fir576", "box576"):
    cmp_sets("nn", mk + "L", f"NN_live-LDA_{mk}")
# boxcar (deployed NN_live) - FIR-path network (emulated), each board
cmp_sets("nn", "fir576", "boxcar-FIR")
# emulated NN_axi; NN_axi - NN_live and NN_axi - LDA770
cmp_sets("axi770", "nn", "NN_axi_emu-NN_live")
cmp_sets("axi770", "fir770L", "NN_axi_emu-LDA_fir770")

# Headline fidelities per subset
fids = {}
for sn, msk in SUB.items():
    fids[sn] = {nm: {k: fid_ci(d[k][msk], y100[msk]) for k in ("nn", "axi770", "fir576", "fir770L", "fir576L", "box576L")}
                for nm, d in (("A", B["A"]), ("B", B["B"]), ("mosaic", mos))}
    yy = np.concatenate([y100[msk]] * 2)
    fids[sn]["pooled_AB"] = {k: fid_ci(np.concatenate([B["A"][k][msk], B["B"][k][msk]]), yy) for k in ("nn", "axi770")}
res["fidelity"] = fids
for sn in SUB:
    print("fid", sn, {nm: round(fids[sn][nm]["nn"]["fid"], 3) for nm in fids[sn]}, "axi_emu", {nm: round(fids[sn][nm]["axi770"]["fid"], 3) for nm in fids[sn]})

# board B - board A, same rows
t6 = {}
for k, lab in (("nn", "NN_live"), ("axi770", "NN_axi emulated on live FIR")):
    t6[lab] = {sn: paired_cmp(ok(B["B"][k])[msk], ok(B["A"][k])[msk], y100[msk]) for sn, msk in SUB.items()}
# NN_axi on chip, B - A, 19,400 (independent sessions on the same rows)
Ia, ca = B["A"]["axi_chip_dev"]; Ib, cb = B["B"]["axi_chip_dev"]; assert np.array_equal(Ia, Ib); m = ~MAP(Ia)
t6["NN_axi on chip"] = {"dev": paired_cmp(cb[m] == y100[Ia][m], ca[m] == y100[Ia][m], y100[Ia][m])}
# agreement between boards
t6["agreement_NN_live_all"] = float(np.mean(B["A"]["nn"][SUB["all"]] == B["B"]["nn"][SUB["all"]]))
res["B_minus_A"] = t6
for lab in ("NN_live", "NN_axi emulated on live FIR", "NN_axi on chip"):
    for sn, r in t6[lab].items():
        print(f"B-A {lab} {sn}: {r['dF']:+.3f} normal [{r['ci95_normal'][0]:+.3f},{r['ci95_normal'][1]:+.3f}] boot [{r['ci95_boot'][0]:+.3f},{r['ci95_boot'][1]:+.3f}] {r['A_only']} vs {r['B_only']} p={r['p_exact']:.3g}")
(OUT / "t2346_paired.json").write_text(json.dumps(res, indent=1, default=float))
print("done")
