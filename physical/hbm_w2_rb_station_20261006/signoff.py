#!/usr/bin/env python3
"""Sign off one routed rb station at 833.333 ps with the measured insertion.

Pass 1 measures the routed clk_sm insertion L (min/max over the block's flops)
on the final ODB + RCX SPEF. Pass 2 regenerates the receiver clock-root
contract SDC (make_sdc.py) at 833.333 ps with L = measured max (setup) and
measured min (hold side of the budget), then reports SS setup and FF hold,
split reg2reg / in2reg / reg2out. Accept: SS >= +40 ps, FF >= +15 ps.
"""
import argparse, json, re, subprocess, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
TCL = r"""
set P /OpenROAD-flow-scripts/flow/platforms/asap7
foreach f [lsort [glob $P/lib/NLDM/*_RVT_$::env(LIBC)_*.lib*]] { read_liberty $f }
read_db $::env(ODB)
read_sdc $::env(SDC)
read_spef $::env(SPEF)
set_propagated_clock [all_clocks]
puts "LATBEGIN"
if {[catch {report_clock_latency -clock clk_sm -digits 2} m]} {puts "NOLAT $m"}
puts "LATEND"
foreach {tag from to} {reg2reg all_registers all_registers in2reg all_inputs all_registers reg2out all_registers all_outputs} {
  foreach d {max min} {
    set paths [find_timing_paths -path_delay $d -from [$from] -to [$to] -group_path_count 1]
    if {[llength $paths]} {puts "SLACK $tag $d [format %.2f [get_property [lindex $paths 0] slack]]"} else {puts "SLACK $tag $d none"}
  }
}
puts "WORST max [format %.2f [sta::worst_slack -max]]"
puts "WORST min [format %.2f [sta::worst_slack -min]]"
puts "TNS max [format %.2f [sta::total_negative_slack -max]]"
report_checks -path_delay $::env(DELAY) -group_path_count 1 -format full_clock_expanded -digits 2
"""


def sta(case, odb, sdc, spef, libc, delay):
    (case/'tk_signoff.tcl').write_text(TCL)
    rel = lambda q: '/work/'+str(Path(q).relative_to(case))
    cmd = ['docker', 'run', '--rm', '-v', f'{case}:/work', '-e', f'LIBC={libc}', '-e', f'ODB={rel(odb)}',
           '-e', f'SDC={rel(sdc)}', '-e', f'SPEF={rel(spef)}', '-e', f'DELAY={delay}', 'openroad/orfs:asap7lock',
           'bash', '-lc', 'source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; openroad -exit -no_splash /work/tk_signoff.tcl']
    p = subprocess.run(cmd, capture_output=True, text=True)
    return p.stdout+p.stderr


def parse(log):
    out = dict(slack={}, worst={})
    for m in re.finditer(r'^SLACK (\S+) (max|min) (\S+)', log, re.M):
        out['slack'][f'{m[1]}_{m[2]}'] = None if m[3] == 'none' else float(m[3])
    for m in re.finditer(r'^WORST (max|min) (\S+)', log, re.M):
        out['worst'][m[1]] = float(m[2])
    lat = log.split('LATBEGIN', 1)[-1].split('LATEND', 1)[0]
    m = re.search(r'rise -> rise.*?^\s*(-?\d+\.\d+)\s+(-?\d+\.\d+) latency$', lat, re.S | re.M)
    out['latency_rise'] = [float(m[1]), float(m[2])] if m else None
    return out


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--run', type=Path, required=True); a = ap.parse_args()
    run = a.run.resolve()
    odb = next(run.rglob('results/asap7/*/base/6_final.odb'))
    res = odb.parent; spef = res/'6_final.spef'; case = next(p for p in odb.parents if (p/'config.mk').is_file())
    sdc0 = case/'station.sdc'
    log1 = sta(case, odb, sdc0, spef, 'SS', 'max'); p1 = parse(log1)
    (run/'signoff_pass1_SS.log').write_text(log1)
    log1f = sta(case, odb, sdc0, spef, 'FF', 'min'); p1f = parse(log1f)
    (run/'signoff_pass1_FF.log').write_text(log1f)
    ss_lat, ff_lat = p1['latency_rise'], p1f['latency_rise']
    if not ss_lat or not ff_lat:
        raise SystemExit('no clock latency measured; see signoff_pass1_*.log')
    result = dict(route_sdc=str(sdc0), measured_insertion_SS=ss_lat, measured_insertion_FF=ff_lat)
    sdc = case/'signoff.sdc'
    subprocess.run([sys.executable, str(HERE/'make_sdc.py'), '--period-ps', '833.333', '--l-max', f'{ss_lat[1]:.2f}',
                    '--l-min', f'{ss_lat[0]:.2f}', '--l-ff-min', f'{ff_lat[0]:.2f}', '--out', str(sdc)],
                   check=True, capture_output=True)
    for corner, delay in (('SS', 'max'), ('FF', 'min')):
        log = sta(case, odb, sdc, spef, corner, delay)
        (run/f'signoff_{corner}.log').write_text(log)
        result[corner] = parse(log)
    ss = result['SS']['worst'].get('max'); ff = result['FF']['worst'].get('min')
    result['accept'] = dict(SS_setup_ps=ss, FF_hold_ps=ff, SS_ok=ss is not None and ss >= 40, FF_ok=ff is not None and ff >= 15)
    (run/'signoff.json').write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps(result['accept']))


if __name__ == '__main__':
    main()
