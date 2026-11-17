"""FLOW-QC-CB 11-17: a shared head hop (QN inverter feeding more than this chain) is re-sited after the xstn moves,
not left at its GPL position (cbn_q01 b_d[460] -> r[0][460]: 280 um pair, 1,740 um built path)."""
import re
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = (ROOT / "tools/die_plan/core_input_chain.tcl").read_text()


def tcl_procs(names):
    out = []
    for name in names:
        m = re.search(r"^proc " + re.escape(name) + r"\s+\{[^\n]*?\}\s+\{", SRC, re.M)
        assert m, name
        i, depth = m.end(), 1
        while depth:
            c = SRC[i]
            i += 1
            if c == "\\":
                i += 1
                continue
            depth += (c == "{") - (c == "}")
        out.append(SRC[m.start():i])
    return "\n".join(out) + "\n"


def run(body):
    with tempfile.TemporaryDirectory() as d:
        f = Path(d) / "probe.tcl"
        f.write_text(tcl_procs(["nc_len", "nc_at", "nc_headhop_plan"]) + body)
        p = subprocess.run(["tclsh", str(f)], capture_output=True, text=True)
    assert p.returncode == 0, p.stdout + p.stderr
    return p.stdout


def test_shared_inverter_goes_to_head_and_dedicated_chain_spreads():
    out = run(r'''
set route {{0 0} {2000 0}}
# bs nearest-first: two dedicated place* buffers, then the shared QN inverter next to the head; 2 hops
foreach r [nc_headhop_plan {1 1 3} 0 0 $route 2] { puts "R $r" }
''')
    rows = {int(l.split()[1]): list(map(float, l.split()[2:])) for l in out.splitlines() if l.startswith("R ")}
    assert rows[2] == [0.0, 0.0]                      # shared cell sits on the head register
    assert rows[1] == [500.0, 0.0] and rows[0] == [750.0, 0.0]   # dedicated cells inside the first hop, nearest cell nearest the stage


def test_nothing_shared_matches_the_unshared_rule():
    out = run(r'''
set route {{0 0} {0 1000} {600 1000}}
foreach r [nc_headhop_plan {1 1} 0 0 $route 3] { puts "R $r" }
''')
    pts = [list(map(float, l.split()[2:])) for l in out.splitlines() if l.startswith("R ")]
    assert pts[0][1] > pts[1][1] > 0                  # spread monotonically from the head


def test_chain_one_uses_the_plan_and_no_longer_skips_a_shared_hop():
    assert "nc_headhop_plan $lc $hx $hy $route $hops" in SRC
    assert "if {$headhop && ![nc_headhop_single $head $bs]} { incr nc_hh_shared; continue }" not in SRC
    assert "OT_NK_HEADHOP_RESITE" in SRC and "nc_hop_stretch" in SRC
