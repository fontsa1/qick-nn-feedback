"""Summary: reads task2_results.json + task2_preds_*.npz (this folder) and the earlier map_trainrows files
(campaign_v144/final/analysis/offline/map_trainrows_s*.json, map_trainrows_preds_s*.npz), and writes task2_summary.json:
  - reproduction: this run's mosaic predictions vs the earlier ones, shot by shot, per seed and arm
  - P189's number re-derived from the earlier jsons (mean +- SD over five seeds of the paired difference)
  - per board (A, B) and mosaic: each arm's fidelity per seed, mean +- SD, and the paired difference to the deployed-map
    arm per seed (exact McNemar, 95 % CI), seed mean +- SD; and the deployed recipe's own selection (lowest val_loss)
"""
import glob, json, sys
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[4]; OUT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "audit_fixes" / "R3_R2"))
from r3_stats import fstats, paired, calmask  # noqa: E402

R = json.load(open(OUT / "task2_results.json"))
seeds = sorted({v["seed"] for v in R["runs"].values()})
arms = [a for a in ("deployed", "trainrow", "v144testrow") if all(f"{a}_s{s}" in R["runs"] for s in seeds)]
P = {k: np.load(OUT / f"task2_preds_{k}.npz") for k in R["runs"]}
y = P[f"deployed_s{seeds[0]}"]["y"]; rows = P[f"deployed_s{seeds[0]}"]["rows"]
S = dict(seeds=seeds, arms=arms, chip=R["eval"])

# ---- reproduction against the earlier run (its eval order: sorted glob, A run1 rows<50000 then B run1 rows>=50000)
order = []
for b, cond in (("A", lambda r: r < 50000), ("B", lambda r: r >= 50000)):
    for f in sorted(glob.glob(str(ROOT / f"campaign_v144/final/live/{b}_run1_*.npz"))):
        r = np.load(f)["rows"]; m = cond(r) & calmask(r); order.append(r[m])
order = np.concatenate(order)
pos = np.searchsorted(rows, order)
assert np.array_equal(rows[pos], order)
rep, old = {}, {}
for s in seeds:
    f = ROOT / f"campaign_v144/final/analysis/offline/map_trainrows_preds_s{s}.npz"
    j = json.load(open(ROOT / f"campaign_v144/final/analysis/offline/map_trainrows_s{s}.json"))
    old[s] = j
    if not f.exists():
        continue
    z = np.load(f)
    assert np.array_equal(z["y"], y[pos])
    for a_old, a_new in (("deployed_map", "deployed"), ("trainrow_map", "trainrow")):
        if f"{a_new}_s{s}" in P:
            rep[f"{a_new}_s{s}"] = int((z[a_old] != P[f"{a_new}_s{s}"]["mosaic"][pos]).sum())
S["reproduction_mosaic_shots_differing_from_2026_11_14"] = rep
d_old = np.array([old[s]["trainrow_vs_deployed_map"]["dF"] for s in seeds])
S["P189_rederived_from_2026_11_14_jsons"] = dict(per_seed=d_old.tolist(), mean=float(d_old.mean()), sd_ddof1=float(d_old.std(ddof=1)),
                                                 sd_ddof0=float(d_old.std()), p_exact=[old[s]["trainrow_vs_deployed_map"]["p_exact"] for s in seeds],
                                                 paper_P189="-0.016 +- 0.042 points (five seeds)")

# ---- per board
for ev in ("A", "B", "mosaic"):
    E = {}
    for a in arms:
        f = [R["runs"][f"{a}_s{s}"][ev]["fid"] for s in seeds]
        E[a] = dict(fid_per_seed=f, mean=float(np.mean(f)), sd=float(np.std(f, ddof=1)),
                    val_loss_per_seed=[R["runs"][f"{a}_s{s}"]["val_loss"] for s in seeds])
        sel = seeds[int(np.argmin(E[a]["val_loss_per_seed"]))]
        E[a]["selected_seed"] = sel; E[a]["selected"] = R["runs"][f"{a}_s{sel}"][ev]
        if a != "deployed":
            pr = [paired(P[f"{a}_s{s}"][ev], P[f"deployed_s{s}"][ev], y) for s in seeds]
            d = np.array([p["dF"] for p in pr])
            E[a]["vs_deployed_per_seed"] = pr
            E[a]["vs_deployed_mean_sd"] = [float(d.mean()), float(d.std(ddof=1))]
            sd_ = E["deployed"]["selected_seed"]
            E[a]["vs_deployed_selected_models"] = dict(seed_arm=sel, seed_deployed=sd_, **paired(P[f"{a}_s{sel}"][ev], P[f"deployed_s{sd_}"][ev], y))
    S[ev] = E
(OUT / "task2_summary.json").write_text(json.dumps(S, indent=1, default=float))

print("reproduction (shots differing from the earlier mosaic preds):", rep)
print("P189 from the earlier jsons: per seed", np.round(d_old, 4), f"mean {d_old.mean():+.4f} SD(n-1) {d_old.std(ddof=1):.4f} SD(n) {d_old.std():.4f}")
for ev in ("A", "B", "mosaic"):
    print(f"\n== {ev}  (chip NN_live {R['eval'][ev]['NN_live_chip']['fid']:.3f})")
    for a in arms:
        e = S[ev][a]
        line = f"  {a:12s} fid/seed " + " ".join(f"{v:.3f}" for v in e["fid_per_seed"]) + f"  mean {e['mean']:.3f} sd {e['sd']:.3f}  selected s{e['selected_seed']} {e['selected']['fid']:.3f} [{e['selected']['fid_ci'][0]:.2f}, {e['selected']['fid_ci'][1]:.2f}]"
        print(line)
        if a != "deployed":
            print("     vs deployed per seed: " + "  ".join(f"{p['dF']:+.3f} ({p['A_only']}/{p['B_only']}, p {p['p_exact']:.3g})" for p in e["vs_deployed_per_seed"])
                  + f"  mean {e['vs_deployed_mean_sd'][0]:+.3f} +- {e['vs_deployed_mean_sd'][1]:.3f}")
            q = e["vs_deployed_selected_models"]
            print(f"     selected models (lowest val_loss): {q['dF']:+.3f} [{q['dF_ci'][0]:+.3f}, {q['dF_ci'][1]:+.3f}], {q['A_only']} vs {q['B_only']}, exact p {q['p_exact']:.3g}")
