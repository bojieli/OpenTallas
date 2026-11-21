#!/usr/bin/env python3
"""cland_clock_contract.py (KV-PLAN-R2 11-20, FABLE-PD-KV-1840 1d): per-pin clk / fclk pin-register clock means of a SIGNED kv_cland ring master (the KV-R 11-16 form of the
kvhg1_views_1116 clock_contract.json).  The kit's own signoff session (signoff/<corner>/session.tcl, same libs, routed
6_final.odb + spef, golden SDC, source latency 0) is re-run with one census block appended before its exit:
  clk  = the signoff pin-register set (SO_CK boundary lines; checked equal to signoff.json corners.<c>.insertion_pinflops)
  fclk = flops clocked by fclk in the first-stage data fanout of the forwarded ring inputs d / t_rst_n.
Reproduces the KV-R 11-16 kvhg1_views_1116 contract of kv_cland_w1045_ns_ddbeb exactly (clk 1599 / 256.5931 ps, fclk 4249 /
617.5619 ps TT; 198.4596 / 445.8876 FF).  core_clock_contract.load reads the result (two clock pins need per-pin means).
  cland_clock_contract.py run   KIT OUT CORNER        (docker; launch through ot-run)
  cland_clock_contract.py write KIT OUT VIEWLIB_TT    -> OUT/clock_contract.json  (then copy it into the exported view)"""
import hashlib
import json
import os
import re
import shutil
import statistics
import subprocess
import sys
from pathlib import Path

BLOCK = r'''
# ---- KV-PLAN-R2 1d census (appended; the signoff session above is unchanged) ----
set mk_fwd {}
foreach p [all_registers -clock_pins] { set cl [get_property $p clocks]; if {[llength $cl] == 1 && [get_full_name [lindex $cl 0]] in $::so_fwd_clks} { dict set mk_fwd [regsub {/[^/]+$} [get_full_name $p] {}] $p } }
set mk_cone {}
if {[llength $so_fwd_in]} {
  foreach p [get_fanout -from [get_ports $so_fwd_in] -flat -endpoints_only -trace_arcs all] {
    set n [get_full_name $p]
    if {![dict exists $so_data $n]} continue
    set i [regsub {/[^/]+$} $n {}]
    if {[dict exists $mk_fwd $i]} { dict set mk_cone $i 1 }
  }
}
puts "MK_FWD_REGS [dict size $mk_fwd] CONE [dict size $mk_cone]"
dict for {i p} $mk_fwd {
  set cl [get_property $p clocks]
  set a ""
  if {$so_cf} { catch {set a [ot_cf_wire $p [lindex $cl 0]]} }
  if {$a eq ""} { catch {set a [get_property $p arrival_max_rise]} }
  if {$a eq "" || ![string is double -strict $a]} { puts "MK_FCK_ERR $i"; continue }
  puts "MK_FCK [expr {[dict exists $mk_cone $i] ? 1 : 0}] [format %.2f $a] [get_full_name [lindex $cl 0]]"
}
puts "MK_DONE 1"
'''


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def census_session(txt):
    """the signoff session with the census block inserted before its final exit (nothing else changes)"""
    lines = txt.rstrip('\n').split('\n')
    if lines[-1].strip() != 'exit':
        raise ValueError('signoff session.tcl does not end with exit')
    return '\n'.join(lines[:-1]) + '\n' + BLOCK + 'exit\n'


def run(kit, out, corner):
    kit, out = Path(kit).resolve(), Path(out).resolve()
    src = kit / 'signoff' / corner
    od = out / corner
    od.mkdir(parents=True, exist_ok=True)
    (od / 'session.tcl').write_text(census_session((src / 'session.tcl').read_text()))
    if (od / 'sdcdir').exists():
        shutil.rmtree(od / 'sdcdir')
    shutil.copytree(src / 'sdcdir', od / 'sdcdir')
    base = next((kit / 'run/results/asap7').glob('*/base'))
    img = os.environ.get('OT_ORFS_IMAGE', 'openroad/orfs:asap7lock')
    cmd = ['docker', 'run', '--rm', '--name', f'ckc_{os.getpid()}_{corner}',
           '-v', f'{base}:/base:ro', '-v', f'{od}/sdcdir:/sdc', '-v', f'{od}:/out', '-v', f'{kit}:/work:ro',
           '-v', f'{kit}/config.mk:/work/config.mk:ro', img,
           '/OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad', '-no_init', '-exit', '/out/session.tcl']
    (od / 'cmd.sh').write_text(' '.join(cmd) + '\n')
    with open(od / 'sta.log', 'w') as f:
        rc = subprocess.run(cmd, stdout=f, stderr=subprocess.STDOUT).returncode
    print(corner, 'rc', rc)
    return rc


def stats(vals):
    return dict(mean_ps=round(statistics.fmean(vals), 4), n=len(vals), min_ps=min(vals), max_ps=max(vals))


def write(kit, out, viewlib):
    kit, out = Path(kit).resolve(), Path(out).resolve()
    so = kit / 'signoff' / 'signoff.json'
    rec = json.loads(so.read_text())
    if rec.get('verdict') != 'SIGNED':
        raise ValueError(f"signoff verdict {rec.get('verdict')!r} is not SIGNED")
    ssha = sha(so)
    mod = re.search(r'\bcell\s*\(\s*"?([^"\s)]+)', Path(viewlib).read_text()).group(1)
    pins = {'clk': {}, 'fclk': {}}
    src = f'KV-PLAN-R2 11-20 STA on signed 6_final.odb+spef (signoff.json sha256 {ssha[:16]}), clock %s, corner %s'
    for corner in ('tt', 'ff'):
        log = (out / corner / 'sta.log').read_text()
        if 'MK_DONE 1' not in log or 'MK_FCK_ERR' in log:
            raise ValueError(f'{corner}: census incomplete')
        clk = [float(m[1]) for m in re.finditer(r'^SO_CK 1 (\S+) clk$', log, re.M)]
        fck = [float(m[1]) for m in re.finditer(r'^MK_FCK 1 (\S+) fclk$', log, re.M)]
        ref = rec['corners'][corner]['insertion_pinflops']
        st = stats(clk)
        if st['n'] != ref['n'] or abs(st['mean_ps'] - ref.get('mean_ps', ref.get('mean'))) > 0.05:
            raise ValueError(f'{corner}: clk census {st} != signoff insertion_pinflops {ref}')
        if not fck:
            raise ValueError(f'{corner}: empty fclk census')
        pins['clk'][corner] = dict(stats(clk), basis='pin_register_mean', source=src % ('clk', corner))
        pins['fclk'][corner] = dict(stats(fck), basis='pin_register_mean', source=src % ('fclk', corner))
    doc = {
        'schema': 'opentallas.core_clock_contract.v1', 'view_lib_sha256': sha(viewlib), 'signed': True,
        'signoff_verdict': 'SIGNED', 'signoff_source': f'{mod}/signoff.json sha256 {ssha}',
        'definition': ('Pin-to-flop clock arrival measured from the core\'s own clock port with source latency 0 on every clock '
                       '(set_clock_latency -source 0), propagated clock, extracted SPEF of the signed routed 6_final.odb; the die '
                       'tool adds the parent arrival at the pin (early core tap = parent arrival - this mean). Boundary-register '
                       'census per clock port: clk = the signoff pin-register set (flops on the data/ctl input and output cones, '
                       '== signoff.json corners.<c>.insertion_pinflops, verified n and mean equal); fclk = flops clocked by fclk '
                       'in the cone of the forwarded ring inputs d / t_rst_n (signoff excludes the forwarded clock and its ring '
                       'inputs from its own census). Same definition for both pins.'),
        'pins': pins}
    (out / 'clock_contract.json').write_text(json.dumps(doc, indent=1))
    print(json.dumps({p: {c: (v['n'], v['mean_ps']) for c, v in d.items()} for p, d in pins.items()}))
    return doc


if __name__ == '__main__':
    if sys.argv[1] == 'run':
        sys.exit(run(*sys.argv[2:5]))
    write(*sys.argv[2:5])
