"""Policy checks for native59 density-group merging (no OpenROAD run)."""
from pathlib import Path
import subprocess


def pure_helpers():
    s = Path(__file__).with_name("n59_density_subtaps.tcl").read_text()
    env = next(x for x in s.splitlines() if x.startswith("proc n59st_env "))
    geom = s[s.index("proc n59st_cent "):s.index("# a legal-ish location")]
    merge = s[s.index("proc n59st_merge_small "):s.index("set n59st_rows {}")]
    return env + "\n" + geom + merge


def test_merge_preserves_members_and_respects_load_and_radius():
    script = pure_helpers() + r"""
set a [list [list 0 0 {a}]]
set b [list [list 10 0 {b c}]]
set far [list [list 300 0 {d}]]
set merged [n59st_merge_small [list $a $b $far] 4 20]
if {[llength $merged] != 2} {error "near small groups did not merge"}
set members {}
foreach group $merged {
  if {[n59st_w $group] > 4 || [n59st_rad $group] > 20} {error "policy overrun"}
  foreach unit $group {lappend members {*}[lindex $unit 2]}
}
if {[lsort $members] ne {a b c d}} {error "lost or duplicated sinks"}
set heavy [list [list 0 0 {x y z}]]
set heavy2 [list [list 1 0 {u v w}]]
if {[llength [n59st_merge_small [list $heavy $heavy2] 4 20]] != 2} {error "cap ignored"}
set far2 [list [list 100 0 {k}]]
if {[llength [n59st_merge_small [list $a $far2] 4 20]] != 2} {error "radius ignored"}
puts DENSITY_GROUPS_PASS
"""
    run = subprocess.run(["tclsh"], input=script, text=True, capture_output=True, check=True)
    assert "DENSITY_GROUPS_PASS" in run.stdout
    assert not run.stderr


def test_adapter_tcl_is_complete():
    p = Path(__file__).with_name("n59_density_subtaps.tcl")
    script = "set f [open {" + str(p) + "}]; set s [read $f]; close $f\nputs [info complete $s]\n"
    run = subprocess.run(["tclsh"], input=script, text=True, capture_output=True, check=True)
    assert run.stdout.strip() == "1"
