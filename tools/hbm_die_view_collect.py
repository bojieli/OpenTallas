#!/usr/bin/env python3
"""Collect a routed die view (route_view.sh output dir on a remote host) into physical/hbm_accel_die_views/<kind>/:
<master>.lef, <master>_ss.lib, <master>_ff.lib, corner_sta.json, check.json and view.json (opentallas.hbm_die_view.v1).

    python3 tools/hbm_die_view_collect.py --host ot-epyc1tb --route /srv/.../routes/b1_pd55 --kind barrier \
        --master hfd_barrier --status closed [--defect TEXT ...] [--note TEXT]
"""
import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--host', required=True)
    ap.add_argument('--route', required=True)
    ap.add_argument('--kind', required=True)
    ap.add_argument('--master', required=True)
    ap.add_argument('--status', required=True, choices=['closed', 'interim-not-closed'])
    ap.add_argument('--defect', action='append', default=[])
    ap.add_argument('--note', default='')
    ap.add_argument('--bench', default='')
    ap.add_argument('--margin', action='store_true', help='require SS >= +15 / FF >= +15 ps (owner 18:15 PT 2026-10-06, lowered from +40)')
    a = ap.parse_args()
    out = ROOT / 'physical/hbm_accel_die_views' / a.kind
    out.mkdir(parents=True, exist_ok=True)
    r, m = a.route, a.master
    files = [f'{r}/view/{m}.lef', f'{r}/view/{m}_ss.lib', f'{r}/view/{m}_ff.lib', f'{r}/corner_sta.json',
             f'{r}/check.json', f'{r}/SOURCE_COMMIT', f'{r}/args']
    subprocess.run(['scp', '-q'] + [f'{a.host}:{f}' for f in files] + [str(out)], check=True)
    met = subprocess.run(['ssh', a.host, f"python3 -c \"import json;d=json.load(open('{r}/physical.json'));"
                          f"m=d['place_and_route']['metrics'];g=d['design'];print(json.dumps(dict(status=d.get('status'),"
                          f"drc=g.get('drc'),antenna=g.get('antenna'),cell_um2=m.get('standard_cell_area_um2'),"
                          f"seq_um2=m.get('sequential_area_um2'),core_um2=m.get('core_area_um2'),"
                          f"macro_um2=m.get('macro_area_um2'))))\""],
                         capture_output=True, text=True, check=True).stdout
    met = json.loads(met)
    cs = json.loads((out / 'corner_sta.json').read_text())
    ck = json.loads((out / 'check.json').read_text())
    src = (out / 'SOURCE_COMMIT').read_text().strip()
    (out / 'SOURCE_COMMIT').unlink()
    args = (out / 'args').read_text().strip()
    (out / 'args').unlink()
    (out / f'route_args_{Path(r).name}.txt').write_text(args + '\n')
    ss, ff = cs['setup_ss']['worst_slack_ps'], cs['hold_ff']['worst_slack_ps']
    # owner rule 2026-10-06 UPDATE 2: a new block view closes at SS setup >= +40 ps (design target +60) and FF hold >= +15 ps
    closes = bool(cs.get('closes_signoff')) and met.get('drc') == 0 and (not a.margin or (ss >= 15 and ff >= 15))
    if a.status == 'closed' and not closes:
        sys.exit(f'refusing status closed: SS {ss} FF {ff} drc {met.get("drc")}')
    wrap = ROOT / 'physical/hbm_accel_die_views' / a.kind / 'rtl' / f'{m}_wrap.json'
    view = dict(schema='opentallas.hbm_die_view.v1', master=m, kind=a.kind, status=a.status,
                lef=f'{m}.lef', lib=dict(ss=f'{m}_ss.lib', ff=f'{m}_ff.lib'),
                files_sha256={f: sha(out / f) for f in (f'{m}.lef', f'{m}_ss.lib', f'{m}_ff.lib')},
                check=dict(verdict=ck['verdict'], positions=ck['positions'], problems=ck['problems'],
                           obs_above_generator=ck['obs_above_generator'], pg_pins=ck['pg_pins'],
                           gen_pins=ck['gen_pins'], view_pins=ck['view_pins']),
                size_um=ck['size_gen'],
                source=dict(route=r, host=a.host, SOURCE_COMMIT=src, ss_setup_ps=ss, ff_hold_ps=ff,
                            closes_signoff_SS60_FF25=closes, clock_period_ns=0.833, **met),
                wrapper=json.loads(wrap.read_text()) if wrap.exists() else None,
                bench=a.bench, note=a.note, defects=a.defect)
    (out / 'view.json').write_text(json.dumps(view, indent=1) + '\n')
    print(json.dumps(dict(master=m, status=a.status, ss=ss, ff=ff, check=ck['verdict'], drc=met.get('drc'))))


if __name__ == '__main__':
    main()
