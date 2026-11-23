"""Where the paper's figure and table generators write, and their --check mode.

The figures and tables in paper_figures/ and paper_tables/ are shipped beside their generators as the reference
outputs. A generator run must not overwrite them by accident, so by default it writes under build/ at the repository
root, at the same relative path (build/paper_figures/fig5/..., build/paper_tables/table2/...). Options, taken out of
sys.argv before the generator reads its own arguments:

  (none)        write under build/
  --out DIR     write to DIR instead (created if needed)
  --in-place    write next to the generator, replacing the shipped reference outputs (to update them on purpose)
  --check       write to a temporary folder, then compare every output with the shipped copy; exit 1 if any differs

What --check compares: text outputs (.json, .tex, .md, .csv, .txt) line by line with line endings ignored; .png by
decoded pixels; .npz array by array. .pdf and .svg embed a creation date and random element ids, so they are not
compared; each has a .png twin that is.

A generator that reads another generator's output (fig4_data.py -> make_fig4_replay_apparatus.py, the fig8 panels ->
make_fig8_combined.py, loop_groups_values.json -> Fig. 5 and Table I) reads it with src(): the copy this run's output
folder holds if there is one, the shipped copy otherwise.

Use in a generator:
    import figout
    OUT = figout.setup(__file__)
    fig.savefig(OUT.path("fig5_window_tradeoff.png"))       # a file beside the generator
    OUT.path_in_repo("campaign_v144/final/analysis/x.json")  # a file elsewhere in the repository
    np.load(OUT.src("fig4_data.npz"))                        # an earlier step's output
    OUT.finish()                                            # prints where the outputs went; runs the check
"""
import shutil
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TEXT = {".json", ".tex", ".md", ".csv", ".txt"}
SKIP = {".pdf", ".svg"}


class Out:
    def __init__(self, script, mode, out_dir):
        self.here = Path(script).resolve().parent
        self.rel = self.here.relative_to(ROOT)
        self.mode = mode
        if mode == "in-place":
            self.base = ROOT
        elif mode == "check":
            self.base = Path(tempfile.mkdtemp(prefix="figout_check_"))
        elif out_dir is not None:
            self.base = None
            self.dir = Path(out_dir).resolve()
        else:
            self.base = ROOT / "build"
        if self.base is not None:
            self.dir = self.base / self.rel
        self.dir.mkdir(parents=True, exist_ok=True)
        self.written = []                       # (output path, shipped reference path)

    def path(self, name):
        """Output path for a file that ships beside the generator."""
        p = self.dir / name
        p.parent.mkdir(parents=True, exist_ok=True)
        self.written.append((p, self.here / name))
        return p

    def path_in_repo(self, rel):
        """Output path for a file that ships elsewhere in the repository (rel from the repository root)."""
        p = (self.base / rel) if self.base is not None else self.dir / Path(rel).name
        p.parent.mkdir(parents=True, exist_ok=True)
        self.written.append((p, ROOT / rel))
        return p

    def src(self, name, folder=None):
        """An earlier step's output: this run's copy if the output folder has one, else the shipped one.
        folder: the generator folder it belongs to, from the repository root (default: this generator's)."""
        rel = Path(folder) if folder else self.rel
        mine = (self.base / rel / name) if self.base is not None else self.dir / name
        return mine if mine.exists() else ROOT / rel / name

    def finish(self):
        if self.mode != "check":
            print(f"outputs in {self.dir}" + ("" if self.mode == "in-place" else " (shipped copies untouched; --in-place replaces them)"))
            return
        bad = []
        for new, ref in self.written:
            if not new.exists() or new.suffix in SKIP:
                continue
            if not ref.exists():
                bad.append(f"{ref.relative_to(ROOT)}: no shipped copy")
            elif not same(new, ref):
                bad.append(f"{ref.relative_to(ROOT)}: differs")
        n = sum(1 for new, _ in self.written if new.exists() and new.suffix not in SKIP)
        shutil.rmtree(self.base, ignore_errors=True)
        if bad:
            print("CHECK FAILED:\n  " + "\n  ".join(bad))
            sys.exit(1)
        print(f"CHECK OK: {n} outputs equal the shipped copies (pdf/svg not compared)")


def same(a, b):
    if a.suffix in TEXT:
        return a.read_text(encoding="utf-8").splitlines() == b.read_text(encoding="utf-8").splitlines()
    if a.suffix == ".png":
        import numpy as np
        from PIL import Image
        x, y = np.asarray(Image.open(a)), np.asarray(Image.open(b))
        return x.shape == y.shape and bool((x == y).all())
    if a.suffix == ".npz":
        import numpy as np
        x, y = np.load(a, allow_pickle=True), np.load(b, allow_pickle=True)
        return sorted(x.files) == sorted(y.files) and all(np.array_equal(x[k], y[k]) for k in x.files)
    return a.read_bytes() == b.read_bytes()


def setup(script):
    """Reads and removes --out DIR, --in-place and --check from sys.argv; returns the Out for this generator."""
    args, mode, out_dir, i = sys.argv[1:], "build", None, 0
    rest = []
    while i < len(args):
        if args[i] == "--check":
            mode = "check"
        elif args[i] == "--in-place":
            mode = "in-place"
        elif args[i] == "--out" and i + 1 < len(args):
            mode, out_dir = "out", args[i + 1]
            i += 1
        else:
            rest.append(args[i])
        i += 1
    sys.argv[1:] = rest
    return Out(script, mode, out_dir)
