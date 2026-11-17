"""Production-width ordered rows cover each real bit once, in face order."""
import re
import sys
import subprocess
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from kit_istations import ordered_station_row


def test_production_rank_coverage_and_order():
    for width in (257, 1167, 1168, 1264):
        lines = ordered_station_row('u_ist_frame_int_o0_0', width, 1069, 1226.88,
                                    'frame_int_o0', 'N', [2200, 1300])
        script = r"""
set names {}
for {set i 0} {$i < @WIDTH@} {incr i} {
  lappend names [format {u_bound.u_ist_frame_int_o0_0.q[%d]} $i]
}
lappend names {u_bound.u_ist_frame_int_o0_0.eq}
proc is_place {pat x y tag} {
  global names
  set i 0
  foreach name $names {
    if {[string match $pat $name]} { puts "$i $x" }
    incr i
  }
}
""".replace('@WIDTH@', str(width)) + '\n'.join(lines)
        run = subprocess.run(['tclsh'], input=script, text=True, capture_output=True, check=True)
        assert not run.stderr, run.stderr
        hits = [line.split() for line in run.stdout.splitlines()]
        assert len(hits) == width + 1
        sites = {int(bit): float(x) for bit, x in hits}
        assert len(sites) == width + 1
        xs = [sites[bit] for bit in range(width)]
        assert xs == sorted(xs)
        assert min(xs) == 979 and max(xs) == 1159
        assert sites[width] == 1069


def test_unaffected_and_outline():
    for face, width in [('N', 256), ('E', 1168), ('W', 1168), (None, 1168)]:
        assert ordered_station_row('u_ist_b_0', width, 20, 30, 'b', face, [100, 100]) == [
            'is_place {*u_ist_b_0[./]*} 20 30 ist:b']
    lines = ordered_station_row('u_ist_b_0', 1168, 20, 30, 'b', 'S', [100, 100])
    xs = [float(l.split('} ')[1].split()[0]) for l in lines[1:-1]]
    assert min(xs) == 2 and max(xs) == 98
