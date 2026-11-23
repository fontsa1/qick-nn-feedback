"""Is the per-shot capture-delay jitter a property of the replay, or of the trigger/capture path?

P68/P190 report that replayed traces arrive with a per-shot time shift of up to one decimated sample. This probe removes
the replay: a fixed const pulse (sharp edge, no recorded trace, no predistortion) is played and its rising edge captured
on readout 0, and the edge's 50% crossing is interpolated per shot. Two pacings:
  host   one acquire per shot (as the replay campaigns run: the tProc program is restarted for every shot)
  tproc  REPS repetitions inside one program (the tProc paces the shots; no host restart between them)
If the edge position scatters by about a sample in the host-paced run but not in the tProc-paced one, the jitter comes from
how each acquire starts (trigger/clock alignment at program start), not from the replay; it would then also affect a live
readout window started the same way. Both readout paths (FIR, boxcar) are checked.

"""
import argparse, json, os, sys
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[4]
os.chdir(ROOT)
sys.path.insert(0, str(ROOT / "analysis_scripts" / "diagnostics"))
import latency_loop as L  # noqa: E402  (brings up soc)
from qick.asm_v2 import AveragerProgramV2  # noqa: E402

soc, soccfg = L.soc, L.soccfg
FS = soccfg["readouts"][0]["fs"] / 8          # decimated MHz

class EdgeProg(AveragerProgramV2):
    def __init__(s, sc, cf):
        super().__init__(sc, reps=cf["reps"], final_delay=cf["final_delay"], cfg=cf)

    def _initialize(s, cf):
        s.declare_gen(ch=0, nqz=1)
        s.declare_readout(ch=0, length=cf["ro_len"])
        s.add_pulse(ch=0, name="c", style="const", length=cf["p_len"], freq=cf["freq"], phase=0.0, gain=cf["gain"], ro_ch=0)
        s.add_readoutconfig(ch=0, name="r", freq=cf["freq"], gen_ch=0)

    def _body(s, cf):
        s.send_readoutconfig(ch=0, name="r", t=0)
        s.pulse(ch=0, name="c", t=cf["t_pulse"])
        s.trigger(ros=[0], pins=[0, len(s.soccfg["tprocs"][0]["output_pins"]) - 1], t=cf["trig"], width=1.0)

def edges(caps):
    """50% crossing of |IQ| on the rising edge, interpolated, in samples, per capture."""
    out = []
    for cp in caps:
        m = np.hypot(cp[:, 0], cp[:, 1]); p = np.median(m[-60:])
        i = int(np.argmax(m >= 0.5 * p))
        out.append(np.nan if i == 0 else i - 1 + (0.5 * p - m[i - 1]) / (m[i] - m[i - 1]))
    return np.array(out)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--shots", type=int, default=300)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    base = dict(reps=1, final_delay=10.0, ro_len=0.6, p_len=0.8, freq=50.0, gain=0.5, t_pulse=0.1, trig=0.0)
    out = dict(host=os.environ.get("QICK_NS_HOST"), banner=str(soc.get_cfg().get("fw_timestamp", "")), fs_decimated_mhz=FS, runs={})
    for path, sel in (("box", dict(sel=1, shift=7, m=11)), ("fir", dict(sel=0))):
        soc.box_config(**sel)
        host = [np.asarray(EdgeProg(soccfg, base).acquire_decimated(soc, progress=False)).reshape(-1, int(round(base["ro_len"] * FS)), 2)[0]
                for _ in range(a.shots)]
        e_h = edges(host)
        # tProc-paced: reps per program are limited by the 16,384-sample decimated buffer, so run batches of 40
        e_t = []
        for k in range(0, a.shots, 40):
            iq = np.asarray(EdgeProg(soccfg, dict(base, reps=min(40, a.shots - k))).acquire_decimated(soc, progress=False))
            e_t.append(edges(iq.reshape(-1, iq.shape[-2], 2)))
        e_t = np.concatenate(e_t)
        r = {}
        for nm, e in (("host", e_h), ("tproc", e_t)):
            frac = e - np.floor(np.nanmedian(e))
            r[nm] = dict(n=int(np.isfinite(e).sum()), median_samples=float(np.nanmedian(e)), sd_samples=float(np.nanstd(e)),
                         sd_ns=float(np.nanstd(e) / FS * 1e3), range_samples=float(np.nanmax(e) - np.nanmin(e)),
                         hist_rounded=dict(zip(*[x.tolist() for x in np.unique(np.round(e[np.isfinite(e)]), return_counts=True)])))
            print(f"{path:3s} {nm:5s}: edge {r[nm]['median_samples']:.2f} samples, sd {r[nm]['sd_samples']:.3f} samples "
                  f"({r[nm]['sd_ns']:.2f} ns), range {r[nm]['range_samples']:.2f}", flush=True)
        out["runs"][path] = r
        json.dump(out, open(a.out, "w"), indent=1, default=float)
    soc.box_config(sel=1, shift=7, m=11)
    print("JITTER DONE; boxcar path restored", flush=True)

if __name__ == "__main__":
    main()
