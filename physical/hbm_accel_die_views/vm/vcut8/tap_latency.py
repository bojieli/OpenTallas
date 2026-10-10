#!/usr/bin/env python3
"""tap_latency.py (vm8-seam 2026-10-10): per-tap source latency for a VM8 vertical-cut half (make_vm_vcut8.py taps).

The die balances the half's tap leaves (ck<f><i>) so that every pin register arrives at the same insertion REF; the block
STA models that with  set_clock_latency -source (REF - f_tap)  on each tap port, f_tap = the mean clock arrival of the
posedge pin registers that tap drives (the negedge lockups are skipped) on the CTS db of the job's calibrate run.  REF = the largest tap mean (all
latencies >= 0: the die only adds delay).  Both TT and FF are measured; the SDC picks by the loaded library corner.

    tap_latency.py --base <calibrate ORFS results base glob> --sdc OUT.sdc --env OUT.env [--image openroad/orfs:latest]
writes OUT.sdc (set_clock_latency -source per tap, TT / FF branch) and OUT.env (FCL_REF_TT=.. FCL_REF_FF=..)."""
import argparse, glob, json, subprocess, tempfile
from pathlib import Path

PLAT = "/OpenROAD-flow-scripts/flow/platforms/asap7"
TCL = r"""
foreach l [glob {PLAT}/lib/NLDM/*RVT_{C}*] {{ read_liberty $l }}
foreach l [glob {PLAT}/lib/NLDM/*_LVT_{C}_*] {{ if {{![string match *FAKE* $l]}} {{ read_liberty $l }} }}
read_db /base/{db}
read_sdc /base/{sdc}
source {PLAT}/setRC.tcl
estimate_parasitics -placement
set_propagated_clock [all_clocks]
set fo [open /t/{C}.txt w]
set blk [ord::get_db_block]
foreach bt [$blk getBTerms] {{
  set n [regsub {{\[0\]$}} [$bt getName] {{}}]
  if {{![regexp {{^ck[wens][0-9]*$}} $n]}} {{ continue }}
  # walk the clock tree in the db: through buffers / inverters to the sequential clock pins
  set todo [list [$bt getNet]]; set seen [dict create]; set s 0.0; set k 0
  while {{[llength $todo]}} {{
    set net [lindex $todo 0]; set todo [lrange $todo 1 end]
    if {{$net eq "NULL" || [dict exists $seen [$net getName]]}} {{ continue }}
    dict set seen [$net getName] 1
    foreach it [$net getITerms] {{
      if {{[$it isOutputSignal]}} {{ continue }}
      set inst [$it getInst]; set m [$inst getMaster]
      if {{[$m isSequential]}} {{
        set nm [$inst getName]
        if {{[string match *DFFL* [$m getName]] || [string match *_DFF_N* $nm]}} {{ continue }}
        set mt_ [[$it getMTerm] getName]
        set pin [get_pins -quiet "[string map {{[ \\[ ] \\]}} [string map {{\\ {{}}}} $nm]]/$mt_"]
        if {{![llength $pin]}} {{ set pin [get_pins -quiet "$nm/$mt_"] }}
        if {{![llength $pin]}} {{ continue }}
        set v [get_property $pin arrival_max_rise]
        if {{[string is double -strict $v]}} {{ set s [expr {{$s + $v}}]; incr k }}
      }} else {{
        foreach o [$inst getITerms] {{ if {{[$o isOutputSignal]}} {{ lappend todo [$o getNet] }} }}
      }}
    }}
  }}
  if {{$k}} {{ puts $fo "$n [expr {{$s / $k}}] $k" }}
}}
close $fo
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--base', required=True)
    ap.add_argument('--sdc', required=True)
    ap.add_argument('--env', required=True)
    ap.add_argument('--image', default='openroad/orfs:latest')
    a = ap.parse_args()
    base = sorted(glob.glob(a.base))[-1]
    db = '4_1_cts.odb' if Path(base, '4_1_cts.odb').exists() else '4_cts.odb'
    sdc = '4_cts.sdc' if Path(base, '4_cts.sdc').exists() else '3_place.sdc'
    res = {}
    with tempfile.TemporaryDirectory() as td:
        for C in ('TT', 'FF'):
            Path(td, 's.tcl').write_text(TCL.format(PLAT=PLAT, C=C, db=db, sdc=sdc))
            subprocess.run(['docker', 'run', '--rm', '-v', f'{base}:/base:ro', '-v', f'{td}:/t', a.image, 'bash', '-lc',
                            '/OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -no_init -exit /t/s.tcl'],
                           check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=7200)
            res[C] = {l.split()[0]: float(l.split()[1]) for l in Path(td, f'{C}.txt').read_text().split('\n') if l.strip()}
    assert res['TT'] and set(res['TT']) == set(res['FF']), res
    ref = {C: max(v.values()) for C, v in res.items()}
    L = ['# tap_latency.py (vm8-seam): the die balances every tap leaf to REF; source latency = REF - tap mean insertion',
         f'# TT taps {json.dumps({k: round(v, 1) for k, v in sorted(res["TT"].items())})}',
         f'# FF taps {json.dumps({k: round(v, 1) for k, v in sorted(res["FF"].items())})}',
         'if {[llength [get_libs -quiet *_FF_*]]} {']
    L += [f'  set_clock_latency -source {round(ref["FF"] - v, 1)} [get_ports -quiet {{{t}[0]}}]' for t, v in sorted(res['FF'].items())]
    L += ['} else {']
    L += [f'  set_clock_latency -source {round(ref["TT"] - v, 1)} [get_ports -quiet {{{t}[0]}}]' for t, v in sorted(res['TT'].items())]
    L += ['}']
    Path(a.sdc).write_text('\n'.join(L) + '\n')
    Path(a.env).write_text(f'FCL_REF_TT={round(ref["TT"])}\nFCL_REF_FF={round(ref["FF"])}\n')
    print(f'tap_latency: {len(res["TT"])} taps, REF TT {ref["TT"]:.1f} / FF {ref["FF"]:.1f} ps; '
          f'TT spread {min(res["TT"].values()):.1f}..{ref["TT"]:.1f}')


if __name__ == '__main__':
    main()
