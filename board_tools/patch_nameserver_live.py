"""Adds the NN_live accessors and tracer patch to NNQickSoc in the board's server notebook.

NNQickSoc lives in cell 0 of the board's `start nameserver.ipynb` (see deploy_and_verify.py); host/nnqick_server.py
already contains both changes. This inserts, idempotently:
  * in __init__: an MMIO on mem_dict['axi_bram_ctrl_live'], or None on a bitstream without NN_live;
  * live_present(), live_read_block(start_word, n), live_latest();
  * a tracer patch: QickMetadata._trace_net ignores live_gate_0. The block design fans qick_processor_0/trig_0_o out
    to live_gate_0 as well as axis_avg_buffer_0, and QICK's trace_trigger expects exactly one peer, so without it
    QickSoc() fails in map_signal_paths ("too many values to unpack").
The BRAM layout is defined in neural_net4_live/firmware/NN_live.h.

Only the notebook file is changed; the next kernel restart (a deploy, or start_server.py) picks it up. Run it once per
board, with QICK_NS_HOST set to the board's address, before deploying.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import jupyter_remote as J  # noqa: E402

NB = __import__("os").environ.get("QICK_SERVER_NB", "start nameserver.ipynb")

INIT_ANCHOR = "self._nn_bram_mmio = MMIO(bram_info['phys_addr'], bram_info['addr_range'])"
INIT_ADD = """
        # NN_live record BRAM (absent on builds without NN_live)
        live = self.mem_dict.get('axi_bram_ctrl_live')
        self._live_mmio = MMIO(live['phys_addr'], live['addr_range']) if live else None"""

METHOD_ANCHOR = "    def nn_bram_word_count(self):"

TRACE_ANCHOR = "class NNQickSoc(QickSoc):"
TRACE_ADD = """# --- NN_live tracer patch: hide live_gate_0 from QICK's net tracing; it shares trig_0_o with axis_avg_buffer_0.
_orig_trace_net = _qickip.QickMetadata._trace_net

def _live_trace_net(self, parser, blockname, portname):
    return [x for x in _orig_trace_net(self, parser, blockname, portname)
            if not (len(x) == 2 and x[0] == 'live_gate_0')]

_qickip.QickMetadata._trace_net = _live_trace_net
print("NN_live patch applied: QickMetadata._trace_net ignores live_gate_0")
# --- end NN_live tracer patch ---

"""
METHODS = '''    def live_present(self):
        return self._live_mmio is not None

    def live_read_block(self, start_word, n_words):
        m = self._live_mmio
        return [m.read(4 * (start_word + k)) for k in range(n_words)]

    def live_latest(self):
        """[shots, frame_err, magic] + the newest 8-word record (NN_live.h)."""
        m = self._live_mmio
        hdr = [m.read(0), m.read(4), m.read(8)]
        if hdr[0] == 0:
            return hdr + [0] * 8
        base = 1024 + ((hdr[0] - 1) % 512) * 8
        return hdr + [m.read(4 * (base + k)) for k in range(8)]

'''

def main():
    s, x = J.login()
    nb = J.get_notebook(s, x, NB)
    content = nb["content"]
    cells = content["cells"]
    idx = None
    for i, cell in enumerate(cells):
        src = "".join(cell["source"]) if isinstance(cell["source"], list) else cell["source"]
        if cell.get("cell_type") == "code" and "class NNQickSoc" in src and "start_server(" in src:
            idx = i
            break
    if idx is None:
        raise SystemExit(f"no cell with both 'class NNQickSoc' and 'start_server(' in {NB}")
    src = "".join(cells[idx]["source"]) if isinstance(cells[idx]["source"], list) else cells[idx]["source"]
    done = []
    if "_live_mmio" not in src:
        if src.count(INIT_ANCHOR) != 1 or src.count(METHOD_ANCHOR) != 1:
            raise SystemExit(f"[{J.BOARD_HOST}] accessor anchors not found exactly once; inspect cell {idx} by hand")
        src = src.replace(INIT_ANCHOR, INIT_ANCHOR + INIT_ADD)
        src = src.replace(METHOD_ANCHOR, METHODS + METHOD_ANCHOR)
        done.append("accessors")
    if "_live_trace_net" not in src:
        if src.count(TRACE_ANCHOR) != 1 or "_qickip" not in src:
            raise SystemExit(f"[{J.BOARD_HOST}] tracer anchor not found exactly once; inspect cell {idx} by hand")
        src = src.replace(TRACE_ANCHOR, TRACE_ADD + TRACE_ANCHOR)
        done.append("tracer patch")
    if not done:
        print(f"[{J.BOARD_HOST}] already patched; nothing to do")
        return
    cells[idx]["source"] = src.splitlines(keepends=True)
    J.put_notebook(s, x, NB, content)
    print(f"[{J.BOARD_HOST}] patched cell {idx} of {NB} ({', '.join(done)}); takes effect at the next kernel restart")

if __name__ == "__main__":
    main()
