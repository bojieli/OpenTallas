#!/usr/bin/env python3
"""face_ck_latency.py (hgi-1010/d4, 2026-10-10): measured option-1 source latency of the ot_hcoll_port face clock taps.

The die clock plan delivers each face tap leaf (ckf: RX pin flops, bottom face; ckt: TX pin flops, right face) so that
its pin flops arrive at the SAME insertion as the block's interior registers.  The block STA models that with
    set_clock_latency -source (REF - tap) [get_ports <tap>]
REF = the mean clock arrival of the sequential sinks of the interior tree (clk; SRAM macros excluded), tap = the mean
arrival of the sequential sinks of that tap's own in-block tree, both measured on the job's CALIBRATE CTS database
with every tap's provisional source latency removed.  Both TT (route / setup) and FF (hold) are measured: the TT values
go into the route constraint (--route-sdc, appended before the IO SDC), the FF values into the FF post-SDC (--ff-sdc:
the given io_vclk_ff file followed by the FF tap latencies; read by the MM hold scene and corner_sta's FF run).  A
negative difference is clamped to 0 (the die only adds delay) and reported.  Precedent: vm/vcut8/tap_latency.py.

    face_ck_latency.py --base '<calibrate ORFS results base glob>' --ff-io <io_vclk_ff_*.sdc>
                       --route-sdc OUT.sdc --ff-sdc OUT_FF.sdc --json OUT.json [--image openroad/orfs:latest]
"""
import argparse, glob, json, subprocess, sys, tempfile
from pathlib import Path

PLAT = "/OpenROAD-flow-scripts/flow/platforms/asap7"
TAPS = ("ckf", "ckt")
TCL = r"""
foreach l [glob {PLAT}/lib/NLDM/*RVT_{C}*] {{ read_liberty $l }}
read_db /base/{db}
read_sdc /base/{sdc}
source {PLAT}/setRC.tcl
estimate_parasitics -placement
set_propagated_clock [all_clocks]
foreach t {{{taps}}} {{ if {{[llength [get_ports -quiet $t]]}} {{ set_clock_latency -source 0 [get_ports $t] }} }}
set fo [open /t/{C}.txt w]
set blk [ord::get_db_block]
foreach root {{clk {taps}}} {{
  set bt [$blk findBTerm $root]
  if {{$bt eq "NULL"}} {{ continue }}
  # walk the clock tree: through buffers / inverters only, to the sequential clock pins (SRAM macros are not followed)
  set todo [list [$bt getNet]]; set seen [dict create]; set s 0.0; set k 0; set mn 1e9; set mx -1e9
  while {{[llength $todo]}} {{
    set net [lindex $todo 0]; set todo [lrange $todo 1 end]
    if {{$net eq "NULL" || [dict exists $seen [$net getName]]}} {{ continue }}
    dict set seen [$net getName] 1
    foreach it [$net getITerms] {{
      if {{[$it isOutputSignal]}} {{ continue }}
      set inst [$it getInst]; set m [$inst getMaster]
      if {{[$m isBlock]}} {{ continue }}
      if {{[$m isSequential]}} {{
        set pin [sta::find_pin "[$inst getName]/[[$it getMTerm] getName]"]
        if {{$pin eq "NULL" || $pin eq ""}} {{ continue }}
        set v [sta::pin_property $pin arrival_max_rise]
        if {{[string is double -strict $v]}} {{ set s [expr {{$s + $v}}]; incr k; if {{$v < $mn}} {{set mn $v}}; if {{$v > $mx}} {{set mx $v}} }}
      }} elseif {{[regexp {{^(BUF|INV|HB|CKINV)}} [$m getName]]}} {{
        foreach o [$inst getITerms] {{ if {{[$o isOutputSignal]}} {{ lappend todo [$o getNet] }} }}
      }}
    }}
  }}
  if {{$k}} {{ puts $fo "$root [expr {{$s / $k}}] $k $mn $mx" }}
}}
close $fo
"""


def measure(base, db, sdc, image, C, log_dir):
    with tempfile.TemporaryDirectory() as td:
        Path(td, 's.tcl').write_text(TCL.format(PLAT=PLAT, C=C, db=db, sdc=sdc, taps=' '.join(TAPS)))
        log = Path(log_dir, f'face_ck_latency_{C}.log')
        with open(log, 'w') as out:
            r = subprocess.run(['docker', 'run', '--rm', '-v', f'{base}:/base:ro', '-v', f'{td}:/t', image, 'bash', '-lc',
                                '/OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -no_init -exit /t/s.tcl'],
                               stdout=out, stderr=subprocess.STDOUT)
        if r.returncode or not Path(td, f'{C}.txt').exists():
            sys.stderr.write(log.read_text()[-4000:])
            raise RuntimeError(f'OpenROAD {C} face-tap measurement exited {r.returncode}; log {log}')
        rows = {}
        for line in Path(td, f'{C}.txt').read_text().splitlines():
            n, mean, k, mn, mx = line.split()
            rows[n] = dict(mean=float(mean), sinks=int(k), min=float(mn), max=float(mx))
        return rows


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--base', required=True)
    ap.add_argument('--ff-io', required=True, help='the io_vclk_ff_<min>_<max>.sdc this FF post-SDC extends')
    ap.add_argument('--route-sdc', required=True)
    ap.add_argument('--ff-sdc', required=True)
    ap.add_argument('--json', required=True)
    ap.add_argument('--image', default='openroad/orfs:latest')
    a = ap.parse_args()
    bases = sorted(glob.glob(a.base))
    if len(bases) != 1:
        ap.error(f'expected one calibrate database for {a.base!r}; found {bases}')
    base = bases[0]
    db = '4_1_cts.odb' if Path(base, '4_1_cts.odb').exists() else '4_cts.odb'
    sdc = '4_cts.sdc' if Path(base, '4_cts.sdc').exists() else '3_place.sdc'
    for name in (db, sdc):
        if not Path(base, name).is_file():
            ap.error(f'calibrate artifact missing: {Path(base, name)}')
    log_dir = Path(a.json).resolve().parent
    log_dir.mkdir(parents=True, exist_ok=True)
    res = {C: measure(base, db, sdc, a.image, C, log_dir) for C in ('TT', 'FF')}
    lat = {}
    for C, rows in res.items():
        if 'clk' not in rows:
            raise SystemExit(f'face_ck_latency: no interior (clk) sinks measured at {C}: {rows}')
        lat[C] = {t: round(max(0.0, rows['clk']['mean'] - rows[t]['mean']), 1) for t in TAPS if t in rows}
    taps = sorted(lat['TT'])
    if not taps or set(lat['TT']) != set(lat['FF']):
        raise SystemExit(f'face_ck_latency: tap sets differ / empty: {lat}')
    head = ['# face_ck_latency.py (hgi-1010/d4): option-1 source latency = interior (clk) mean insertion - tap tree mean,',
            f'# measured on {base}/{db}',
            '# TT ' + json.dumps({k: {x: round(y, 1) for x, y in v.items() if x != 'sinks'} | {'sinks': v['sinks']}
                                   for k, v in res['TT'].items()}),
            '# FF ' + json.dumps({k: {x: round(y, 1) for x, y in v.items() if x != 'sinks'} | {'sinks': v['sinks']}
                                   for k, v in res['FF'].items()})]
    route = head + ['set ot_fc_per [get_property [get_clocks core_clk] period]',
                    f'create_clock -name core_clk -period $ot_fc_per [get_ports {{clk {" ".join(taps)}}}]']
    route += [f'set_clock_latency -source {lat["TT"][t]} [get_ports {t}]' for t in taps]
    Path(a.route_sdc).write_text('\n'.join(route) + '\n')
    ff = Path(a.ff_io).read_text().rstrip('\n').split('\n') + head[:1] + \
        [f'set_clock_latency -source {lat["FF"][t]} [get_ports {t}]' for t in taps]
    Path(a.ff_sdc).write_text('\n'.join(ff) + '\n')
    Path(a.json).write_text(json.dumps(dict(schema='opentallas.hcoll_face_ck_latency.v1', base=base, db=db, sdc=sdc,
                                            measured=res, source_latency_ps=lat), indent=1) + '\n')
    print(f'face_ck_latency: TT {lat["TT"]} FF {lat["FF"]} (interior TT {res["TT"]["clk"]["mean"]:.1f} / '
          f'FF {res["FF"]["clk"]["mean"]:.1f} ps)')


if __name__ == '__main__':
    main()
