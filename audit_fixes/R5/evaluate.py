"""R5: score every saved run (runs/<tag>/test_prob.npy) under our protocol.

Sets: full raw 100k test split (where the reproduction numbers are quoted), the 20k hardware
subset test20k_real (= test split rows manifest.source_indices, raw data, no loopback) and its
19,400-row headline convention (20k rows minus subset rows 1000:1600).
Metric: balanced fidelity 1 - (P(1|0) + P(0|1))/2 with a Wilson 95% CI on accuracy (project
convention; the 100k and 20k sets are exactly 50/50 so accuracy = balanced fidelity there).
Paired comparisons: exact two-sided McNemar (binomial on the discordant pairs).
Decision rules as in each source: reference p >= 0.5 -> 1; ours (task51) p > 0.5 -> 1.

  python audit_fixes/R5/evaluate.py
"""
import json
from math import comb
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]


def wilson(k, n, z=1.959964):
    p, d = k / n, 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    hw = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return 100 * (c - hw), 100 * (c + hw)


def score(pred, y):
    ok = pred == y
    lo, hi = wilson(int(ok.sum()), len(y))
    p10, p01 = float(np.mean(pred[y == 0] != 0)), float(np.mean(pred[y == 1] != 1))
    return dict(fid=100 * (1 - 0.5 * (p10 + p01)), acc=100 * float(ok.mean()), lo=lo, hi=hi,
                p10=100 * p10, p01=100 * p01, n=int(len(y)), k=int(ok.sum()))


def mcnemar_exact(ok_a, ok_b):
    b = int(np.sum(ok_a & ~ok_b)); c = int(np.sum(~ok_a & ok_b)); n = b + c
    if n == 0:
        return b, c, 1.0
    p = 2 * sum(comb(n, i) for i in range(min(b, c) + 1)) / 2 ** n
    return b, c, min(1.0, p)


def main():
    yte = np.load(ROOT / "0528_y_test_0_770.npy").astype(int)
    man = json.loads((ROOT / "data/test20k_real_manifest.json").read_text())
    idx20 = np.asarray(man["source_indices"], dtype=int)
    y20 = np.load(ROOT / "data/test20k_real_y.npy").astype(int)
    assert np.array_equal(yte[idx20], y20), "test20k labels do not match the test split"
    X20 = np.load(ROOT / "data/test20k_real_X.npy", mmap_mode="r")
    Xte = np.load(ROOT / "0528_X_test_0_770.npy", mmap_mode="r")
    for r in (0, 1234, 19999):
        assert np.array_equal(np.asarray(X20[r], dtype=np.float64), np.asarray(Xte[idx20[r]])), r
    keep = np.ones(20000, bool); keep[1000:1600] = False
    sets = {"test100k": (np.arange(len(yte)), yte), "sub20k": (idx20, y20), "sub19400": (idx20[keep], y20[keep])}

    runs = {}
    for d in sorted((HERE / "runs").glob("*")):
        f, rj = d / "test_prob.npy", d / "result.json"
        if not (f.exists() and rj.exists()):
            continue
        p = np.load(f)
        pred = (p >= 0.5).astype(int) if d.name.startswith("exact") else (p > 0.5).astype(int)
        meta = json.loads(rj.read_text())
        runs[d.name] = dict(pred=pred, meta=meta,
                            scores={s: score(pred[i], y) for s, (i, y) in sets.items()})

    out = {"runs": {}, "groups": {}, "mcnemar": []}
    print(f"{'run':22s} {'ep':>3s} {'best':>4s}  " + "  ".join(f"{s:>30s}" for s in sets))
    for name, r in runs.items():
        m = r["meta"]
        line = f"{name:22s} {m['epochs_run']:3d} {m['best_epoch']:4d}  "
        line += "  ".join(f"{v['fid']:6.3f} [{v['lo']:.2f},{v['hi']:.2f}] {v['p10']:.2f}/{v['p01']:.2f}"
                          for v in r["scores"].values())
        print(line)
        out["runs"][name] = dict(scores=r["scores"], epochs_run=m["epochs_run"], best_epoch=m["best_epoch"],
                                 best_val_loss=m["best_val_loss"], seed=m["seed"], lr=m.get("lr", 1e-3),
                                 train_minutes=m["train_seconds"] / 60,
                                 task51_original_acc=m.get("task51_original_acc"))

    groups = {"exact_lr1e-3": [n for n in runs if n.startswith("exact") and n.endswith("lr0.001")],
              "exact_lr1e-4": [n for n in runs if n.startswith("exact") and n.endswith("lr0.0001")],
              "ours_task51_rerun": [n for n in runs if n.startswith("ours")]}
    for g, names in groups.items():
        if not names:
            continue
        out["groups"][g] = {}
        for s in sets:
            v = np.array([runs[n]["scores"][s]["fid"] for n in names])
            out["groups"][g][s] = dict(runs=names, mean=float(v.mean()),
                                       sd=float(v.std(ddof=1)) if len(v) > 1 else None, values=v.tolist())
        print(f"{g:20s} " + "  ".join(
            f"{s}: {out['groups'][g][s]['mean']:.3f}" + (f" +- {out['groups'][g][s]['sd']:.3f}"
                                                         if out['groups'][g][s]['sd'] is not None else "")
            for s in sets) + f"   (n_runs {len(names)})")

    pairs = list(zip(sorted(groups["exact_lr1e-3"], key=lambda n: runs[n]["meta"]["seed"]),
                     sorted(groups["ours_task51_rerun"], key=lambda n: runs[n]["meta"]["seed"])))
    pairs += [(a, b) for a in groups["exact_lr1e-4"] for b in groups["ours_task51_rerun"][:1]]
    pairs += [(a, b) for a in groups["exact_lr1e-4"] for b in groups["exact_lr1e-3"][:1]]
    for a, b in pairs:
        for s, (i, y) in sets.items():
            ok_a, ok_b = runs[a]["pred"][i] == y, runs[b]["pred"][i] == y
            nb, nc, pv = mcnemar_exact(ok_a, ok_b)
            dfid = runs[a]["scores"][s]["fid"] - runs[b]["scores"][s]["fid"]
            out["mcnemar"].append(dict(a=a, b=b, set=s, a_only_correct=nb, b_only_correct=nc, p_exact=pv,
                                       delta_fid=dfid, agree=float(np.mean(runs[a]["pred"][i] == runs[b]["pred"][i]))))
            print(f"McNemar {a} vs {b} [{s}]: dF {dfid:+.3f}  a-only {nb}  b-only {nc}  p_exact {pv:.3g}  "
                  f"decision agreement {100 * out['mcnemar'][-1]['agree']:.2f}%")
    (HERE / "evaluate_results.json").write_text(json.dumps(out, indent=1))
    print("saved", HERE / "evaluate_results.json")


if __name__ == "__main__":
    main()
