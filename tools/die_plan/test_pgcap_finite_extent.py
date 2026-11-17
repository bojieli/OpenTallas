"""Finite PG guards cover the real stripe without creating remote pin blockages."""
import subprocess
from pathlib import Path

SRC = Path(__file__).with_name("pg_pair_cap.tcl")

def run(script):
    p = subprocess.run(["tclsh"], input="source {" + str(SRC) + "}\n" + script,
                       text=True, capture_output=True, check=True)
    assert not p.stderr, p.stderr
    return p.stdout

MOCK = r"""
namespace eval ord {
 proc get_db_block {} {return blk}
 proc get_db_tech {} {return tech}
}
proc tech {m args} {return 1000}
proc die {m args} {return [dict get {xMin 0 yMin 0 xMax 604800 yMax 1226880} $m]}
proc blk {m args} {return [dict get {getDieArea die getNets net} $m]}
proc net {m args} {return [dict get {isSpecial 1 getSigType GROUND getSWires sw} $m]}
proc sw {m args} {return {w0 w1}}
proc L {m args} {
 switch $m {getName {return M5} getDirection {return VERTICAL} getWidth {return 24} getSpacing {return 72}}
}
proc w0 {m args} {return [dict get {isVia 0 getTechLayer L xMin 228780 xMax 228900 yMin 369337 yMax 458483} $m]}
proc w1 {m args} {return [dict get {isVia 0 getTechLayer L xMin 228780 xMax 228900 yMin 887737 yMax 976883} $m]}
proc set_global_routing_region_adjustment {region args} {puts "CUT $region"}
"""

def cuts(text):
    return [[float(v) for v in line.split()[1:]] for line in text.splitlines() if line.startswith("CUT ")]

def test_real_disjoint_straps_keep_both_spacing_guards():
    out = run(MOCK + "set ::env(OT_PGCAP_FINITE_EXTENT) 1\not_pgcap_add\n")
    r = cuts(out)
    assert len(r) == 2, "same-column distinct straps must not be deduplicated"
    for box, (lo, hi) in zip(r, [(369.337, 458.483), (887.737, 976.883)]):
        assert box[0] <= 228.780 and box[2] >= 228.900
        assert box[1] <= lo - .084 and box[3] >= hi + .084
        assert box[3] < 1193.376, "remote clock tap must remain reachable"
    # Old full-column form is the negative control for the remote-site predicate.
    old = cuts(run(MOCK + "ot_pgcap_add\n"))
    assert len(old) == 1 and old[0][1] == 0 and old[0][3] == 1226.88
    assert old[0][1] <= 1193.376 <= old[0][3]

def test_default_and_explicit_off_keep_legacy_regions():
    assert cuts(run(MOCK + "ot_pgcap_add\n")) == cuts(run(MOCK + "set ::env(OT_PGCAP_FINITE_EXTENT) 0\not_pgcap_add\n"))

def test_round_outward_and_clip_preserve_covered_geometry():
    text = run(r"""
for {set i 0} {$i < 100} {incr i} {
 set a [expr {$i*197-100}]; set b [expr {$i*653-100}]
 puts "BOX $a $b [expr {$a+121}] [expr {$b+803}] [ot_pgcap_finite_region [list $a $b [expr {$a+121}] [expr {$b+803}]] {0 0 604800 1226880} 570 10]"
}
""")
    for line in text.splitlines():
        a,b,c,d,x0,y0,x1,y1 = map(int,line.split()[1:])
        assert x0 <= max(a,0) and y0 <= max(b,0)
        assert x1 >= c and y1 >= d
        assert min(x0,y0) >= 0


def test_generator_passes_finite_switch_and_rejects_invalid_value():
    import ast, os
    source = SRC.with_name("gen_phys.py").read_text()
    fn = next(x for x in ast.parse(source).body if isinstance(x, ast.FunctionDef) and x.name == "pgcap_cfg")
    scope = {"os": os}
    exec(compile(ast.Module(body=[fn], type_ignores=[]), str(SRC.with_name("gen_phys.py")), "exec"), scope)
    previous = dict(os.environ)
    try:
        os.environ["OT_PGCAP"] = "1"
        os.environ["OT_PGCAP_FINITE_EXTENT"] = "1"
        assert "export OT_PGCAP_FINITE_EXTENT = 1" in scope["pgcap_cfg"]()
        os.environ["OT_PGCAP_FINITE_EXTENT"] = "2"
        try:
            scope["pgcap_cfg"]()
        except SystemExit:
            pass
        else:
            raise AssertionError("invalid finite switch accepted")
    finally:
        os.environ.clear()
        os.environ.update(previous)
