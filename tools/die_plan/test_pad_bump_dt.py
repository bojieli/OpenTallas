"""S81-PMATX-DT 11-09 (DIE-S81-85): macro_pin OUTPUT pads keep their direct net (dont_touch before buffer_ports).
The hook rows come from gen_phys.pad_bumps, and the names they use exist in the serdes column RTL / PMA abstract."""
import re
import shutil
import subprocess
from pathlib import Path
from types import SimpleNamespace

import gen_phys as G
import test_s81_pma_views as TV

R = Path(__file__).resolve().parents[2]
COL = R / "rtl/dsrom_sys/s81_link/col/ot_pdie_serdes_col.sv"


def _bumps():
    D = TV._kp4_delta()
    part = dict(physical_inst=D.TXM, physical_master="ot_s81_pma_txm", lef="x.lef", origin_um=[1.0, 2.0], orient="MX",
                outline_um=[2246.4, 129.6])
    rx = dict(part, physical_inst=D.RXM, physical_master="ot_s81_pma_rxm")
    t = {"pads": [dict(p) for p in D.PADS], "contents": [{"inst": "u_phy", "physical_parts": [part, rx]}]}
    return G.pad_bumps(SimpleNamespace(types={"t": t}), "t")


def test_rows_are_the_output_pads_only():
    out = [b for b in _bumps() if b["dir"] == "output"]
    tcl = G.pad_bump_dt_tcl(out)
    rows = re.search(r"set pdt_rows \{(.*)\}\n", tcl).group(1)
    assert rows == "{io_pma_tx ot_s81_pma_txm pma_tx 544} {io_pma_tck ot_s81_pma_txm pma_tck 1}"
    assert "io_pma_rx" not in tcl and "setDoNotTouch 1" in tcl and "@ROWS@" not in tcl


def test_names_exist_in_serdes_column_netlist():
    src = COL.read_text()
    txm = re.search(r"module ot_s81_pma_txm\b.*?endmodule", src, re.S).group(0)
    assert re.search(r"output\s+wire\s+\[543:0\]\s+pma_tx\b", txm) and re.search(r"output\s+wire\s+pma_tck\b", txm)
    col = re.search(r"module ot_pdie_serdes_col\b.*?\);", src, re.S).group(0)
    assert re.search(r"\[543:0\]\s+pma_tx\b", col) and "pma_tck" in col
    assert re.search(r"ot_s81_pma_txm\s+u_ptx\s*\(.*\.pma_tx\(pma_tx\), \.pma_tck\(pma_tck\)", src)


def test_tcl_parses():
    tclsh = shutil.which("tclsh")
    if not tclsh:
        return
    tcl = G.pad_bump_dt_tcl([b for b in _bumps() if b["dir"] == "output"])
    r = subprocess.run([tclsh], input=f"puts [info complete {{{tcl}}}]\n", capture_output=True, text=True)
    assert r.stdout.strip() == "1", r.stderr


def test_gen_wires_hook_into_face_flops():
    src = Path(G.__file__).read_text()
    assert 'bump_out = [b for b in pad_bumps(P, tn) if b["dir"] == "output"]' in src
    assert 'hook.write_text("source /work/pad_bump_dt.tcl\\n" + hook.read_text())' in src
