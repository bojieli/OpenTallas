#!/usr/bin/env python3
"""HBM die: GUIDED detail route of one REPRESENTATIVE REGION of the full-die global-routed database (OWNER STEER
2026-10-07 (6): no flat full-die DRT; regions with DRT convergence, DRC and the GRT-vs-DRT correlation as the error bar).

2026-10-08: the projected-pin crop (every cut net's pin at its outside-terminal centroid, one point per edge) failed the
region GRT on r25 (GRT-0031 stacked pins -> GRT-0080 'Invalid pin placement' for hub/attn/chain; ioedge: no net with
two terminals -> GRT-0094).  This is the Qwen guided-window cut (tools/qwen_die_region_guided.py, which this tool
copies into the region dir and runs unchanged inside the container): kept instances = centre inside the window,
region box grown to them, overlapping removed instances become obstructions, every net leaving the window gets its
boundary pin where ITS full-die global route crosses the window edge, on that guide's layer, on a free unblocked
track; the die guides are clipped to the window and kept, so DRT follows the full-die global route.

Correlation (the error bar of the die timing, which is on GRT parasitics):
  * wire length per net: the clipped die-GRT guides (wl_grt.csv) vs the detail route (wl_drt.csv);
  * slack per endpoint, OPTION B corners (TT setup, FF hold, SS setup sensitivity) with the die's clock context
    (relay_clock_context.json, tools/hbm_die_relay_sta.py constraints): GRT parasitics vs RCX on the routed region.
    Guides cannot feed estimate_parasitics (GRT-0008), so the GRT side re-runs global_route on the cut region (same
    layers / adjustments as the die GRT) -- the same estimator the die STA uses.  No hold pads in the region STA
    (they cancel in the GRT - RCX delta).

  python3 tools/hbm_die_region_drt.py stage --case <relay case dir> --name hub --window x0 y0 x1 y1
      -> <case>/regiong_<name>/start_region.sh   (run on the host; mounts the case read-only at /case)
  python3 tools/hbm_die_region_drt.py compare --dir <case>/regiong_<name>   -> compare.json
"""
import argparse
import json
import os
import re
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import hbm_die_relay_sta as hrs          # noqa: E402
import qwen_die_region_guided as qg      # noqa: E402

CORNERS = (('tt', 'max'), ('ff', 'min'), ('ss', 'max'))


def sta_tcl(case, para):
    full = (case / 'run_grt_sta.tcl').read_text()
    libs = '\n'.join(l.replace('/work/', '/case/') for l in full.splitlines()
                     if l.startswith(('define_corners', 'read_liberty')))
    ctx = json.loads((case / 'relay_clock_context.json').read_text())
    sinks = dict(ctx['view_sinks'], **ctx['relay_sinks'])
    if para == 'grt':
        load = '''step load { read_db /work/region.odb }
source /OpenROAD-flow-scripts/flow/platforms/asap7/setRC.tcl
set_routing_layers -signal M4-M9 -clock M4-M9
set_global_routing_layer_adjustment M4-M5 0.30
set_global_routing_layer_adjustment M6-M9 0.146
step grt { global_route -congestion_iterations 30 -allow_congestion -congestion_report_file /work/region_grt_congestion.rpt }
step wl_rgrt { report_wire_length -net * -global_route -file /work/wl_region_grt.csv }
step est { estimate_parasitics -global_routing }
'''
    else:
        load = 'step load { read_db /work/routed.odb }\nstep spef { read_spef /work/routed.spef }\n'
    body = []
    for c, k in CORNERS:
        body.append(hrs.constraints(sinks, c))
        body.append(f'''step sta_{c} {{
  set f [open /work/slack_{para}_{c}.txt w]
  foreach pe [find_timing_paths -path_delay {k} -corner {c} -group_path_count 200000 -endpoint_path_count 1 -unique_paths_to_endpoint] {{
    puts $f "[get_full_name [get_property $pe endpoint]] [get_property $pe slack]" }}
  close $f
  puts "OT_STA para={para} corner={c} wns_ns=[sta::worst_slack -{k}] tns_ns=[sta::total_negative_slack -{k}]"
}}
''')
    return qg.HEAD + 'step libs {\n' + libs + '\n}\n' + load + ''.join(body) + 'puts OT_STA_DONE\n'


def stage(a):
    case = Path(a.case).resolve()
    d = case / f'regiong_{a.name}'
    d.mkdir(parents=True, exist_ok=True)
    (d / 'region.json').write_text(json.dumps({'win': a.window, 'name': a.name, 'ckpt': str(case / 'ckpt_grt.odb')}))
    (d / 'qwen_die_region_guided.py').write_text(Path(qg.__file__).read_text())
    (d / 'drt.tcl').write_text(qg.drt_tcl(a.threads, a.drt_iters))
    for p in ('grt', 'rcx'):
        (d / f'sta_{p}.tcl').write_text(sta_tcl(case, p))
    img = '${IMAGE:-openroad/orfs:asap7lock}'
    run = (f'docker run --rm --name dieev_hbm_rg_{a.name}_$1 --memory={a.mem}g -v $D:/work -v {case}:/case:ro -w /work {img} '
           'bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; /usr/bin/time -v openroad -threads $2 -no_init '
           '-exit /work/$1.tcl > /work/$1.log 2>&1; rc=\\$?; chmod -R a+rwX /work; exit \\$rc"')
    (d / 'start_region.sh').write_text(f'''#!/bin/bash
# HBM guided region {a.name}: cut from the full-die GRT checkpoint -> DRT on the clipped die guides -> RCX
#   -> STA TT/FF/SS on region-GRT and on RCX parasitics -> compare.json (tools/hbm_die_region_drt.py compare)
set -u
D=$(cd $(dirname $0) && pwd); cd $D
say() {{ echo "$(date '+%F %T %Z') $*" >> $D/STATUS.log; }}
run() {{ {run}; echo $? > $D/$1.exit; }}
ln -f {case}/ckpt_grt.odb ckpt_grt.odb 2>/dev/null || cp -f {case}/ckpt_grt.odb ckpt_grt.odb
docker run --rm --name dieev_hbm_rg_{a.name}_cut --memory={a.mem}g -e QDR_IN=/work/ckpt_grt.odb -e QDR_OUT=/work/region.odb \\
  -e QDR_REGION_JSON=/work/region.json -v $D:/work -w /work {img} \\
  bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; /usr/bin/time -v openroad -python -exit /work/qwen_die_region_guided.py > /work/cut.log 2>&1; rc=\\$?; chmod -R a+rwX /work; exit \\$rc"
rc=$?; rm -f ckpt_grt.odb
say "cut rc=$rc $(grep -E '^QDR (region|pins)' cut.log | tr '\\n' ' ' | cut -c1-600)"
[ $rc = 0 ] || exit 1
run sta_grt 8 &
run drt {a.threads}
say "drt rc=$(cat drt.exit) $(grep -E 'OT_STEP_FAIL|OT_TIME step=drt|Number of violations|OT_FLOW_DONE' drt.log | tail -4 | tr '\\n' ' ')"
wait
grep -q "OT_STEP_FAIL drt" drt.log || {{ [ -s routed.spef ] && run sta_rcx 8; }}
say "sta: $(grep -h OT_STA sta_grt.log sta_rcx.log 2>/dev/null | tr '\\n' ' ')"
python3 {Path(__file__).resolve() if a.tool_path is None else a.tool_path} compare --dir $D > compare.out 2>&1
say "compare: $(tail -1 compare.out)"
''')
    os.chmod(d / 'start_region.sh', 0o755)
    print(d)


def read_wl(p):
    out = {}
    if not p.exists():
        return out
    for ln in p.read_text().splitlines():      # report_wire_length -file: 'grt: <net> <wl_um> <pins>'
        f = ln.split()
        if len(f) < 4 or not f[0].endswith(':'):
            continue
        try:
            out[f[1]] = float(f[2])
        except ValueError:
            continue
    return out


def read_slack(p):
    out = {}
    if p.exists():
        for ln in p.read_text().splitlines():
            e, s = ln.rsplit(' ', 1)
            try:
                out[e] = float(s) * 1000.0
            except ValueError:
                pass
    return out


def q(v, f):
    v = sorted(v)
    return v[min(len(v) - 1, int(f * len(v)))] if v else None


def compare(a):
    d = Path(a.dir)
    r = {'region': d.name}
    if (d / 'region.odb.json').exists():
        j = json.loads((d / 'region.odb.json').read_text())
        r.update(region_um=j['region_um'], area_mm2=j['area_mm2'], kept_instances=j['kept_instances'],
                 pins_guides=j['pins_guides'])
    g, t = read_wl(d / 'wl_grt.csv'), read_wl(d / 'wl_drt.csv')
    common = [n for n in g if n in t and g[n] > 0]
    if common:
        ratio = [t[n] / g[n] for n in common]
        r['wirelength'] = dict(nets=len(common), grt_um=round(sum(g[n] for n in common), 1),
                               drt_um=round(sum(t[n] for n in common), 1),
                               total_ratio=round(sum(t[n] for n in common) / sum(g[n] for n in common), 4),
                               per_net_ratio_p50=round(statistics.median(ratio), 4),
                               per_net_ratio_p95=round(q(ratio, 0.95), 4), per_net_ratio_max=round(max(ratio), 4))
    log = (d / 'drt.log').read_text(errors='replace') if (d / 'drt.log').exists() else ''
    viol = re.findall(r'Number of violations = (\d+)', log)
    r['drt'] = dict(iterations_logged=len(viol), violations_by_iter=[int(v) for v in viol][-8:],
                    final_violations=int(viol[-1]) if viol else None, done='OT_FLOW_DONE' in log)
    r['slack_ps'] = {}
    for c, _ in CORNERS:
        sg, sr = read_slack(d / f'slack_grt_{c}.txt'), read_slack(d / f'slack_rcx_{c}.txt')
        ce = [e for e in sg if e in sr]
        if not ce:
            continue
        dl = [sr[e] - sg[e] for e in ce]
        r['slack_ps'][c] = dict(endpoints=len(ce), wns_grt=round(min(sg[e] for e in ce), 1),
                                wns_rcx=round(min(sr[e] for e in ce), 1),
                                delta_rcx_minus_grt_p05=round(q(dl, 0.05), 1), delta_p50=round(statistics.median(dl), 1),
                                delta_p95=round(q(dl, 0.95), 1), delta_min=round(min(dl), 1), delta_max=round(max(dl), 1))
    (d / 'compare.json').write_text(json.dumps(r, indent=1))
    print(json.dumps({k: v for k, v in r.items() if k in ('region', 'wirelength', 'drt', 'slack_ps')}))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest='cmd', required=True)
    s = sub.add_parser('stage')
    s.add_argument('--case', required=True)
    s.add_argument('--name', required=True)
    s.add_argument('--window', nargs=4, type=float, required=True)
    s.add_argument('--threads', type=int, default=12)
    s.add_argument('--mem', type=int, default=150)
    s.add_argument('--drt-iters', type=int, default=64)
    s.add_argument('--tool-path', help='path of this tool on the run host (default: this file)')
    c = sub.add_parser('compare')
    c.add_argument('--dir', required=True)
    a = ap.parse_args()
    stage(a) if a.cmd == 'stage' else compare(a)


if __name__ == '__main__':
    main()
