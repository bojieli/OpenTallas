"""regional_taps(_balance).tcl pure planners (GEOM-REVIEW-3 06:59 vsw f6s: 22-ps pad quantum + frozen it0 target left
the tap window at 20.7 vs 20; a 1-sink region kept its own tap).  Procs are lifted from the hooks and run in tclsh."""
import re
import shutil
import subprocess
from pathlib import Path

import pytest

HERE = Path(__file__).parent


def proc(path, name):
    s = (HERE / path).read_text()
    i = s.index(f"proc {name} ")
    j = s.index("{", s.index("}", i) + 1)          # body opens after the arg list
    d = 0
    for k in range(j, len(s)):
        d += {"{": 1, "}": -1}.get(s[k], 0)
        if d == 0:
            return s[i:k + 1]
    raise AssertionError(name)


def tcl(script):
    if not shutil.which("tclsh"):
        pytest.skip("tclsh unavailable")
    p = subprocess.run(["tclsh"], input=script, text=True, capture_output=True)
    assert p.returncode == 0, p.stderr
    return p.stdout


SIM = r'''
# true pad delay per cell (unknown to the tool) and initial means of the f6s taps (TT, placement RC)
set true 13.0
set means {h3_7 314.6 h2_1 333.0 h3_2 330.1 h3_5 320.4 mtap0 336.9}
set step 10.0; set prev {}; set last {}
for {set it 0} {$it < 8} {incr it} {
  if {[dict size $last]} { set step [rb_learn $prev $means $last $step] }
  set plan [rb_plan $means $step 5.0]
  if {![dict size $plan]} break
  set prev $means; set last $plan
  dict for {t nb} $plan { dict set means $t [expr {[dict get $means $t] + $nb * $true}] }
}
set lo 1e9; set hi -1e9; dict for {t v} $means { set lo [expr {min($lo,$v)}]; set hi [expr {max($hi,$v)}] }
puts "WIN [format %.2f [expr {$hi-$lo}]] STEP [format %.2f $step] IT $it"
'''


def test_balance_converges_inside_window_with_unknown_cell_delay():
    out = tcl(proc("regional_taps_balance.tcl", "rb_plan") + "\n" + proc("regional_taps_balance.tcl", "rb_learn") + SIM)
    win, step = map(float, re.search(r"WIN (\S+) STEP (\S+)", out).groups())
    assert win <= 10.0, out                 # inside 20 with margin, not at the edge
    assert abs(step - 13.0) < 0.5, out      # the per-cell delay was measured, not assumed


def test_target_is_retaken_every_pass():
    """mutant: the old tool froze the target at the it0 maximum -> the window stays wider than 20."""
    frozen = proc("regional_taps_balance.tcl", "rb_plan").replace(
        "set hi -1e18; dict for {t v} $means { set hi [expr {max($hi,$v)}] }", "global hi0; set hi $hi0")
    out = tcl(frozen + "\n" + proc("regional_taps_balance.tcl", "rb_learn")
              + "\nset hi0 336.9\nset ::true 22.0\n" + SIM.replace("set true 13.0", "set true 22.0"))
    assert float(re.search(r"WIN (\S+)", out).group(1)) > 20.0, out
    out = tcl(proc("regional_taps_balance.tcl", "rb_plan") + "\n" + proc("regional_taps_balance.tcl", "rb_learn")
              + SIM.replace("set true 13.0", "set true 22.0"))
    assert float(re.search(r"WIN (\S+)", out).group(1)) <= 20.0, out


def test_plan_skips_gaps_inside_tolerance_and_half_step():
    out = tcl(proc("regional_taps_balance.tcl", "rb_plan") + '\nputs [rb_plan {a 100 b 96 c 80 d 70} 10.0 5.0]\n')
    assert out.split() == ["c", "2", "d", "3"], out


def test_small_regions_fold_into_nearest_full_tap():
    out = tcl(proc("regional_taps.tcl", "rt_fold_plan") + r'''
set tapnet {0 {10 10 n0} 1 {50 10 n1} 2 {10 50 n2} 3 {50 50 n3} 4 {90 50 n4}}
puts "A [rt_fold_plan {0 400 1 1 2 399 3 49 4 0} $tapnet 50]"
puts "B [rt_fold_plan {0 10 1 1} $tapnet 50]"
''')
    a = dict(zip(*[iter(out.split("A ")[1].split("\n")[0].split())] * 2))
    assert a == {"1": "0", "3": "2"}, out    # 1-sink region 1 -> nearest full (0); 49 -> 2; empty region 4 untouched
    assert out.split("B")[1].strip() == "", out   # nothing big enough: no merge
