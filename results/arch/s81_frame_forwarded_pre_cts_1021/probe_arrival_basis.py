"""Read raw arrival bases in the unchanged failing tiny physical fixture.

Run on the fleet. No placement, clock, reference or acceptance limit is changed.
The existing fixture's late failure is preserved after printing both bases.
"""
import pathlib
import sys

repo = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(repo / 'tools/ref_tile/tests'))
import test_forwarded_soft_clocks as T

original_run = T.F.subprocess.run

PROBE = r'''
set basis_failed [catch {source /w/entries.tcl} basis_error]
foreach name {f0/CLK f1/CLK rs0/CLK rs1/CLK} {
  set pin [get_pins $name]
  set clock [get_clocks ot_forwarded_0]
  puts "BASIS_PIN $name clocks=[get_property $pin clocks] DATA=[ot_ce_fwd_arrival $pin] CLOCK=[ot_ce_clock_wire $pin $clock]"
  foreach vertex [$pin vertices] {
    if {$vertex eq "NULL"} continue
    foreach transition {rise fall} {
      set paths [$vertex path_iterator $transition max]
      while {[$paths has_next]} {
        set path [$paths next]
        puts "BASIS_TAG $name $transition arrival=[sta::time_sta_ui [$path arrival]] tag=[$path tag]"
      }
      $paths finish
    }
  }
}
if {$basis_failed} {error $basis_error}
'''


def instrument(cmd, *args, **kwargs):
    if cmd and cmd[0] == 'docker' and '/w/run.tcl' in cmd:
        roots = [cmd[i + 1][:-3] for i, arg in enumerate(cmd[:-1])
                 if arg == '-v' and cmd[i + 1].endswith(':/w')]
        assert len(roots) == 1
        path = pathlib.Path(roots[0]) / 'run.tcl'
        text = path.read_text()
        assert text.count('source /w/entries.tcl') == 1
        path.write_text(text.replace('source /w/entries.tcl', PROBE))
    return original_run(cmd, *args, **kwargs)


T.F.subprocess.run = instrument
try:
    code, output = T.Actual().flow()
    print(output)
    print('PRESERVED_FIXTURE_RC', code)
    sys.exit(code)
finally:
    T.F.subprocess.run = original_run
