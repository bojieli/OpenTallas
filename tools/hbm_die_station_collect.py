#!/usr/bin/env python3
"""Collect routed station views (CLAUDE HBM-ABSTRACTS stations) into physical/hbm_accel_die_views/stations/<master>/:
LEF + SS/FF ETM + view.json (schema opentallas.hbm_die_view.v1).  Reads each route dir over ssh (host:dir/label).

  collect --route HOST:DIR --master M [--label L]
"""
import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VIEWS = ROOT / 'physical/hbm_accel_die_views/stations'
PACKING = ('every forwarded segment port of fc = (base, nd, nu): data bits [0, base) in the generator DIRECTION MODEL '
           'directions, then nd downstream forwarded clocks [base, base+nd), then nu upstream forwarded clocks '
           '[base+nd, base+nd+nu); downstream data bits in ascending index cut in slices of 512, slice k clocked by '
           'base+k; upstream data likewise by base+nd+k; data captured on the falling edge of the received forwarded '
           'clock, every launch on the rising edge of the forwarded clock it sends; station maps data bit i to data bit '
           'i (role maps: gath b = {a2, a, t1, t0} from bit 0 (t0 [0,270), t1 [270,540), a [540,1080), a2 [1080,2160)); '
           'cdist leaves of 103 b: a leaves 0-3 = taps t0-t3, a leaves 4-7 = b leaves 0-3; SM request launch: a[43] '
           '(req_ready) driven 1, b[43] driven 0); rst active low')


def sh(host, cmd):
    return subprocess.run(['ssh', host, cmd], capture_output=True, text=True).stdout


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--route', required=True, help='HOST:ROUTE_DIR (the route_view.sh label dir)')
    ap.add_argument('--master', required=True)
    ap.add_argument('--bench', default='', help='bench check summary (pos/neg) for the record')
    a = ap.parse_args()
    host, rd = a.route.split(':', 1)
    m = a.master
    d = VIEWS / m
    ex = sh(host, f'cat {rd}/exit')
    cs = json.loads(sh(host, f'cat {rd}/corner_sta.json') or '{}')
    ck = json.loads(sh(host, f'cat {rd}/check.json') or '{}')
    phys = json.loads(sh(host, f'cat {rd}/physical.json') or '{}')
    commit = sh(host, f'cat {rd}/SOURCE_COMMIT').strip()
    args = sh(host, f'cat {rd}/args').strip()
    ss = cs.get('setup_ss', {}).get('worst_slack_ps')
    ff = cs.get('hold_ff', {}).get('worst_slack_ps')
    drc = None
    try:
        drc = phys['results']['route']['drc'] if 'results' in phys else None
    except Exception:  # noqa: BLE001
        pass
    if drc is None:
        txt = json.dumps(phys)
        import re
        mm = re.search(r'"drc": (\d+)', txt)
        drc = int(mm.group(1)) if mm else None
    for f in (f'{m}.lef', f'{m}_ss.lib', f'{m}_ff.lib'):
        subprocess.run(['scp', '-q', f'{host}:{rd}/view/{f}', str(d / f)], check=True)
    closed = (ss is not None and ff is not None and ss >= 0 and ff >= 0 and drc == 0 and ck.get('verdict') == 'MATCH'
              and 'rc=0' in ex)
    view = dict(schema='opentallas.hbm_die_view.v1', master=m, kind='stations',
                status='closed' if closed else 'interim-not-closed',
                lef=f'{m}.lef', lib=dict(ss=f'{m}_ss.lib', ff=f'{m}_ff.lib'),
                check=dict(verdict=ck.get('verdict'), positions=ck.get('positions'), problems=ck.get('problems'),
                           obs_layers=ck.get('obs_layers'), pg_pins=ck.get('pg_pins')),
                source=dict(route=f'{host}:{rd}', SOURCE_COMMIT=commit, args=args, exit=ex.split(),
                            ss_setup_ps=ss, ff_hold_ps=ff, drc=drc, closes_signoff=cs.get('closes_signoff'),
                            rtl=f'physical/hbm_accel_die_views/stations/{m}/{m}.sv',
                            sdc=f'physical/hbm_accel_die_views/stations/{m}/{m}.sdc',
                            generator='tools/hbm_die_station_gen.py'),
                bench=a.bench, size_um=ck.get('size_view'), packing=PACKING,
                sha256={f: sha(d / f) for f in (f'{m}.lef', f'{m}_ss.lib', f'{m}_ff.lib')}, defects=[])
    old = d / 'view.json'
    if old.exists():
        view['defects'] = json.loads(old.read_text()).get('defects', [])
    old.write_text(json.dumps(view, indent=1) + '\n')
    print(json.dumps(dict(master=m, status=view['status'], ss=ss, ff=ff, drc=drc, check=ck.get('verdict'))))


if __name__ == '__main__':
    sys.exit(main())
