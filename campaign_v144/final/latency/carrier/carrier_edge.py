"""Does the converter path's latency depend on the pulse's carrier frequency, up to the
qubit-drive band (4.5 GHz)?

The DAC tile's sample rate and interpolation and the ADC tile's decimation are fixed in the build; the carrier is the
generator's and the readout's NCO, set at run time. This plays a const pulse (sharp edge) on gen 0 at each carrier and
captures it on readout 0 (FIR path) with the readout NCO at the same frequency. Above fs_adc/2 = 2457.6 MHz the ADC
sees the tone in its second Nyquist zone; the NCO at the same nominal frequency folds onto it. Per carrier: the edge's
50% |IQ| crossing, interpolated (latency_loop's convention), 300 host-paced shots. Differences against 50 MHz are the
carrier-dependent part of DAC tile + cable + ADC tile + front-end analog delay; everything digital after the mixers is
common to all carriers.

"""
import argparse, json, os, sys
from pathlib import Path
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import jitter_probe as J  # noqa: E402  (brings up soc; EdgeProg, edges)

soc, soccfg, FS = J.soc, J.soccfg, J.FS

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--freqs", default="50,500,1500,2400,3000,4000,4500,4800")
    ap.add_argument("--shots", type=int, default=300)
    ap.add_argument("--gain", type=float, default=0.5)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    soc.box_config(sel=1, shift=7, m=11)
    out = dict(host=os.environ.get("QICK_NS_HOST"), banner=str(soc.get_cfg().get("fw_timestamp", "")), fs_decimated_mhz=FS,
               fs_adc_mhz=soccfg["readouts"][0]["fs"], runs={})
    nro = int(round(0.6 * FS))
    for f in (float(x) for x in a.freqs.split(",")):
        base = dict(reps=1, final_delay=10.0, ro_len=0.6, p_len=0.8, freq=f, gain=a.gain, t_pulse=0.1, trig=0.0)
        try:
            caps = [np.asarray(J.EdgeProg(soccfg, base).acquire_decimated(soc, progress=False)).reshape(-1, nro, 2)[0]
                    for _ in range(a.shots)]
        except Exception as e:
            out["runs"][str(f)] = dict(error=f"{type(e).__name__}: {e}"); print(f"{f:7.1f} MHz: {e}", flush=True); continue
        caps = np.array(caps); e = J.edges(caps)
        plat = float(np.median(np.hypot(caps[:, -60:, 0], caps[:, -60:, 1])))
        r = dict(n=int(np.isfinite(e).sum()), edge_median=float(np.nanmedian(e)), edge_sd=float(np.nanstd(e)),
                 edge_ns=float(np.nanmedian(e) / FS * 1e3), plateau=plat)
        out["runs"][str(f)] = r
        print(f"{f:7.1f} MHz: edge {r['edge_median']:.3f} samples ({r['edge_ns']:.2f} ns), sd {r['edge_sd']:.3f}, "
              f"plateau {plat:.0f}, n {r['n']}", flush=True)
        json.dump(out, open(a.out, "w"), indent=1, default=float)
    ref = out["runs"].get("50.0", {}).get("edge_ns")
    if ref is not None:
        for f, r in out["runs"].items():
            if "edge_ns" in r: r["minus_50MHz_ns"] = r["edge_ns"] - ref
        print("relative to 50 MHz (ns):", {f: round(r.get("minus_50MHz_ns", float("nan")), 2) for f, r in out["runs"].items()})
    json.dump(out, open(a.out, "w"), indent=1, default=float)
    print("CARRIER DONE", flush=True)

if __name__ == "__main__":
    main()
