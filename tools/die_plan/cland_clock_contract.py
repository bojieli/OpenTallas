#!/usr/bin/env python3
"""Per-pin clk / fclk clock contract (clock_contract.json) of a SIGNED landing-ring master view.

KV-RINGMAC-R1 11-21: committed copy of KV-PLAN-R2's d27b/hubc_tools/ck_contract.py (scratch, 11-20), which made the
clock_contract.json of the kvd23_hubc_views ring masters; gen_phys reads it through core_clock_contract (a ring master
has two clock pins, clk and fclk, so the die tool needs measured per-pin means).  Companion of cland_ring_master.py.
The kit's own signoff session (signoff/<corner>/session.tcl, same libs, routed 6_final.odb + spef, golden SDC, source
latency 0) is re-run with one census block appended before its exit:
  clk  = the signoff pin-register set (SO_CK boundary lines; checked equal to signoff.json corners.<c>.insertion_pinflops)
  fclk = flops clocked by fclk in the first-stage data fanout of the forwarded ring inputs d / t_rst_n.
  cland_clock_contract.py run   KIT OUT CORNER        (docker; launch through ot-run, --mem 8 --threads 2)
  cland_clock_contract.py write KIT OUT VIEWLIB_TT    -> OUT/clock_contract.json (copy it into the view dir)"""
import hashlib, json, os, re, shutil, statistics, subprocess, sys
from pathlib import Path

BLOCK = r'''
# ---- cland_clock_contract census (appended; the signoff session above is unchanged) ----
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


def run(kit, out, corner):
    kit, out = Path(kit).resolve(), Path(out).resolve()
    src = kit / 'signoff' / corner
    od = out / corner
    od.mkdir(parents=True, exist_ok=True)
    txt = (src / 'session.tcl').read_text()
    lines = txt.rstrip('\n').split('\n')
    assert lines[-1].strip() == 'exit', 'session.tcl does not end with exit'
    (od / 'session.tcl').write_text('\n'.join(lines[:-1]) + '\n' + BLOCK + 'exit\n')
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
    assert rec.get('verdict') == 'SIGNED', rec.get('verdict')
    ssha = sha(so)
    mod = re.search(r'\bcell\s*\(\s*"?([^"\s)]+)', Path(viewlib).read_text()).group(1)
    pins = {'clk': {}, 'fclk': {}}
    src = f'KV-PLAN-R2 11-20 STA on signed 6_final.odb+spef (signoff.json sha256 {ssha[:16]}), clock %s, corner %s'
    for corner in ('tt', 'ff'):
        log = (out / corner / 'sta.log').read_text()
        if 'MK_DONE 1' not in log or 'MK_FCK_ERR' in log:
            raise SystemExit(f'{corner}: census incomplete')
        clk = [float(m[1]) for m in re.finditer(r'^SO_CK 1 (\S+) clk$', log, re.M)]
        fck = [float(m[1]) for m in re.finditer(r'^MK_FCK 1 (\S+) fclk$', log, re.M)]
        ref = rec['corners'][corner]['insertion_pinflops']
        st = stats(clk)
        if st['n'] != ref['n'] or abs(st['mean_ps'] - ref.get('mean_ps', ref.get('mean'))) > 0.05:
            raise SystemExit(f'{corner}: clk census {st} != signoff insertion_pinflops {ref}')
        if not fck:
            raise SystemExit(f'{corner}: empty fclk census')
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


if __name__ == '__main__':
    if sys.argv[1] == 'run':
        sys.exit(run(*sys.argv[2:5]))
    write(*sys.argv[2:5])
