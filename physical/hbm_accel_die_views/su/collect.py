#!/usr/bin/env python3
"""CLAUDE HBM-ABSTRACTS (hub): collect a finished hub route into the committed view tree.

  collect.py lane    --host H --route DIR --quarter su|sfu|hc      DIR = route_lane.sh work dir (routes/<label>)
      -> physical/hbm_accel_die_views/<q>/lane/<lane>/{<lane>.lef, <lane>_ss.lib, <lane>_ff.lib, lane.json}
  collect.py quarter --host H --route DIR --quarter su|sfu|hc      DIR = route_quarter.sh work dir (OUT/<label>)
      -> physical/hbm_accel_die_views/<q>/{hfd_<q>.lef, hfd_<q>_ss.lib, hfd_<q>_ff.lib, check.json, view.json}

Verdict rule (AGENTS sign-off): closed = routed, SS setup worst >= 0 and FF hold worst >= 0 at 833 / 60 / 25, zero DRC.
A quarter view is recorded interim-not-closed even when its route closes: it is a PHYSICAL ENVELOPE (registered die
wrapper around closed lanes, tools/hbm_hub_quarter_gen.py), not the SU / SFU / HC function."""
import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
LANE = {'su': 'ot_su12_light', 'sfu': 'ot_su12_sfu', 'hc': 'ot_dsrom_su_hcpost_lane'}


def sh(host, cmd):
    return subprocess.run(['ssh', host, cmd], capture_output=True, text=True).stdout


def fetch(host, src, dst):
    dst.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(['scp', '-q', f'{host}:{src}', str(dst)], check=True)


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def route_facts(host, d):
    exitf = dict(l.split('=') for l in sh(host, f'cat {d}/exit').split() if '=' in l)
    cs_route = json.loads(sh(host, f'cat {d}/corner_sta.json') or '{}')
    cs833 = json.loads(sh(host, f'cat {d}/corner_sta_833.json 2>/dev/null') or '{}')
    cs = cs833 if cs833.get('setup_ss') else cs_route      # sign-off at 833 when the route was over-constrained
    phys = json.loads(sh(host, f'cat {d}/physical.json') or '{}')
    chk = [c for c in ((phys.get('acceptance') or {}).get('checks') or []) if c.get('stage') == 'place_and_route']
    c0 = chk[0] if chk else {}
    ss = (cs.get('setup_ss') or {}).get('worst_slack_ps')
    ff = (cs.get('hold_ff') or {}).get('worst_slack_ps')
    rs = (cs_route.get('setup_ss') or {}).get('worst_slack_ps')
    return dict(exit=exitf, signoff='833 ps re-time (corner_sta_833.json)' if cs is cs833 else 'route SDC (corner_sta.json)',
                route_clock_ss_worst_slack_ps=rs, ss_worst_slack_ps=ss, ff_worst_hold_slack_ps=ff,
                ss_violating_d_pins=(cs.get('setup_ss') or {}).get('violating_d_pins'),
                ff_violating_d_pins=(cs.get('hold_ff') or {}).get('violating_d_pins'),
                drc_violations=None if c0.get('drc_errors') is None else int(c0['drc_errors']),
                antenna_violating_nets=c0.get('antenna_violating_nets'),
                max_slew_cap_fanout=[c0.get('max_slew_violations'), c0.get('max_cap_violations'), c0.get('max_fanout_violations')],
                source_commit=sh(host, f'cat {d}/SOURCE_COMMIT').strip(), args=sh(host, f'cat {d}/args').strip()[:400],
                acceptance=(phys.get('acceptance') or {}).get('status'))


def margin_ok(f):
    """owner margin rule 2026-10-06: SS >= +40 ps (accept line, owner UPDATE 2; design target +60), FF >= +15 ps at 833."""
    return closed(f) and f['ss_worst_slack_ps'] >= 40 and f['ff_worst_hold_slack_ps'] >= 15


def closed(f):
    return (f['exit'].get('rc') == '0' and f['ss_worst_slack_ps'] is not None and f['ss_worst_slack_ps'] >= 0
            and f['ff_worst_hold_slack_ps'] is not None and f['ff_worst_hold_slack_ps'] >= 0 and f['drc_violations'] == 0)


def lef_layers(lef):
    t = Path(lef).read_text()
    pg = {}
    for net in ('VDD', 'VSS'):
        m = re.search(rf'PIN {net}\b(.*?)END {net}', t, re.S)
        pg[net] = sorted(set(re.findall(r'LAYER (\S+) ;', m.group(1)))) if m else []
    obs = t.split('  OBS', 1)[1] if '  OBS' in t else ''
    size = re.search(r'SIZE ([\d.]+) BY ([\d.]+)', t)
    return dict(pg=pg, obs=sorted(set(re.findall(r'LAYER (\S+) ;', obs))), size=[float(size.group(1)), float(size.group(2))])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('mode', choices=['lane', 'quarter'])
    ap.add_argument('--host', required=True)
    ap.add_argument('--route', required=True)
    ap.add_argument('--quarter', required=True, choices=sorted(LANE))
    a = ap.parse_args()
    d = a.route.rstrip('/')
    f = route_facts(a.host, d)
    base = ROOT / 'physical/hbm_accel_die_views' / a.quarter
    if a.mode == 'lane':
        n = LANE[a.quarter]
        out = base / 'lane' / n
        for s in ('.lef', '_ss.lib', '_ff.lib'):
            fetch(a.host, f'{d}/view/{n}{s}', out / f'{n}{s}')
        oc = sh(a.host, f'tail -3 {d}/outcheck.txt').strip()
        rec = dict(schema='opentallas.hbm_hub_lane_view.v1', lane=n, route=f'{a.host}:{d}', closed=closed(f), margin_ok=margin_ok(f),
                   recipe='r2/r3: signals M2-M5, pins M4 left edge every track, PDN top M6 (su/route_lane.sh)',
                   interface_sdc='physical/hbm_die_abstracts_20261006/compute/ot_su12_full/interface.sdc (Carson real SU view)',
                   outcheck=oc, layers=lef_layers(out / f'{n}.lef'), **f,
                   sha256={p.name: sha(p) for p in sorted(out.glob(f'{n}*')) if p.suffix in ('.lef', '.lib')})
        (out / 'lane.json').write_text(json.dumps(rec, indent=1) + '\n')
        print(json.dumps({k: rec[k] for k in ('lane', 'closed', 'ss_worst_slack_ps', 'ff_worst_hold_slack_ps',
                                              'drc_violations', 'layers')}))
        return
    m = f'hfd_{a.quarter}'
    for s in ('.lef', '_ss.lib', '_ff.lib'):
        fetch(a.host, f'{d}/view/{m}{s}', base / f'{m}{s}')
    fetch(a.host, f'{d}/check.json', base / 'check.json')
    chk = json.loads((base / 'check.json').read_text())
    lay = lef_layers(base / f'{m}.lef')
    lane = json.loads((base / 'lane' / LANE[a.quarter] / 'lane.json').read_text())
    defects = []
    if not closed(f):
        defects.append(f"NOT CLOSED: SS worst {f['ss_worst_slack_ps']} ps / FF hold worst {f['ff_worst_hold_slack_ps']} ps "
                       f"/ DRC {f['drc_violations']}")
    if any(l in ('M8', 'M9') for l in lay['pg']['VDD'] + lay['pg']['VSS'] + lay['obs']):
        defects.append('PDN contract: M8/M9 used inside the quarter')
    if closed(f) and not margin_ok(f):
        defects.append(f"MARGIN: SS {f['ss_worst_slack_ps']} / FF {f['ff_worst_hold_slack_ps']} ps under the +40 / +15 owner accept line")
    if not lane.get('margin_ok'):
        defects.append('lane view under the +40 / +15 owner accept line (see source.lane)')
    defects.append('ENVELOPE: SU/SFU/HC function (controller, die-port protocol) not built; die bits map onto lane pins '
                   'by the generator rule (tools/hbm_hub_quarter_gen.py)')
    view = dict(schema='opentallas.hbm_die_view.v1', master=m, kind=a.quarter, status='interim-not-closed',
                lef=f'{m}.lef', lib=dict(ss=f'{m}_ss.lib', ff=f'{m}_ff.lib'),
                check={k: chk.get(k) for k in ('verdict', 'problems')},
                source=dict(route=f'{a.host}:{d}', rtl=f'physical/hbm_accel_die_views/{a.quarter}/rtl/{m}.sv',
                            lane=dict(name=LANE[a.quarter], closed=lane['closed'], route=lane['route'],
                                      ss=lane['ss_worst_slack_ps'], ff=lane['ff_worst_hold_slack_ps'],
                                      size=lane['layers']['size']),
                            closed_route=closed(f), margin_ok=margin_ok(f), **f),
                pdn_contract=dict(view_pg_layers=lay['pg'], view_obs_layers=lay['obs'],
                                  breaks_contract=any(l in ('M8', 'M9') for l in lay['pg']['VDD'] + lay['obs'])),
                defects=defects, sha256={p: sha(base / p) for p in (f'{m}.lef', f'{m}_ss.lib', f'{m}_ff.lib')})
    (base / 'view.json').write_text(json.dumps(view, indent=1) + '\n')
    print(json.dumps({k: view[k] for k in ('master', 'status', 'check', 'defects')}))


if __name__ == '__main__':
    main()
