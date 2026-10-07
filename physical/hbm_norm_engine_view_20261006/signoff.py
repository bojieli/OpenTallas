#!/usr/bin/env python3
"""Sign off one routed norm view: SS setup / FF hold at 833.333 ps with the MEASURED insertion (two passes, as
the W2 station signoff). Prints {"ss_ps","ff_ps","drc"} (closure-loop metrics_cmd)."""
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
if {[catch {report_clock_latency -clock clk -digits 2} m]} {puts "NOLAT $m"}
puts "LATEND"
foreach {tag from to} {reg2reg all_registers all_registers in2reg all_inputs all_registers reg2out all_registers all_outputs} {
  foreach d {max min} {
    set paths [find_timing_paths -path_delay $d -from [$from] -to [$to] -group_path_count 1]
    if {[llength $paths]} {puts "SLACK $tag $d [format %.2f [get_property [lindex $paths 0] slack]]"} else {puts "SLACK $tag $d none"}
  }
}
puts "WORST max [format %.2f [sta::worst_slack -max]]"
puts "WORST min [format %.2f [sta::worst_slack -min]]"
report_checks -path_delay $::env(DELAY) -group_path_count 3 -format full_clock_expanded -digits 2
"""
def sta(case, odb, sdc, spef, libc, delay):
    (case/'nev_signoff.tcl').write_text(TCL)
    rel = lambda q: '/work/'+str(Path(q).relative_to(case))
    cmd = ['docker', 'run', '--rm', '-v', f'{case}:/work', '-e', f'LIBC={libc}', '-e', f'ODB={rel(odb)}', '-e', f'SDC={rel(sdc)}',
           '-e', f'SPEF={rel(spef)}', '-e', f'DELAY={delay}', 'openroad/orfs:asap7lock', 'bash', '-lc',
           'source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; openroad -exit -no_splash /work/nev_signoff.tcl']
    p = subprocess.run(cmd, capture_output=True, text=True); return p.stdout+p.stderr
def parse(log):
    o = dict(slack={}, worst={})
    for m in re.finditer(r'^SLACK (\S+) (max|min) (\S+)', log, re.M): o['slack'][f'{m[1]}_{m[2]}'] = None if m[3] == 'none' else float(m[3])
    for m in re.finditer(r'^WORST (max|min) (\S+)', log, re.M): o['worst'][m[1]] = float(m[2])
    lat = log.split('LATBEGIN', 1)[-1].split('LATEND', 1)[0]
    m = re.search(r'rise -> rise.*?^\s*(-?\d+\.\d+)\s+(-?\d+\.\d+) latency$', lat, re.S | re.M)
    o['latency_rise'] = [float(m[1]), float(m[2])] if m else None
    return o
def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--run', type=Path, required=True); a = ap.parse_args()
    run = a.run.resolve(); odb = next(run.rglob('results/asap7/*/base/6_final.odb')); res = odb.parent
    spef = res/'6_final.spef'; case = next(p for p in odb.parents if (p/'config.mk').is_file()) if any((p/'config.mk').is_file() for p in odb.parents) else run/'work'
    sdc0 = next(run.rglob('results/asap7/*/base/6_final.sdc'))
    # the sta container mounts `case`; keep everything under it
    case = run/'work'
    l1 = sta(case, odb, sdc0, spef, 'SS', 'max'); p1 = parse(l1); l1f = sta(case, odb, sdc0, spef, 'FF', 'min'); p1f = parse(l1f)
    if not p1['latency_rise'] or not p1f['latency_rise']: raise SystemExit('no clock latency measured')
    ss, ff = p1['latency_rise'], p1f['latency_rise']
    sdc = case/'signoff.sdc'
    subprocess.run([sys.executable, str(HERE/'make_sdc.py'), '--signoff', '--l-ss-max', f'{ss[1]:.2f}', '--l-ss-min', f'{ss[0]:.2f}',
                    '--l-ff-min', f'{ff[0]:.2f}', '--l-ff-max', f'{ff[1]:.2f}', '--out', str(sdc)], check=True, capture_output=True)
    out = dict(measured_SS=ss, measured_FF=ff)
    for corner, delay in (('SS', 'max'), ('FF', 'min')):
        log = sta(case, odb, sdc, spef, corner, delay); (run/f'signoff_{corner}.log').write_text(log); out[corner] = parse(log)
    drc = None
    for f in run.rglob('5_2_route.json'):
        d = json.load(open(f)); drc = d.get('detailedroute__route__drc_errors', drc)
    m = dict(ss_ps=out['SS']['worst'].get('max'), ff_ps=out['FF']['worst'].get('min'), drc=drc)
    (run/'signoff.json').write_text(json.dumps(dict(out, metrics=m), indent=2)+'\n'); print(json.dumps(m))
if __name__ == '__main__': main()
# bump
