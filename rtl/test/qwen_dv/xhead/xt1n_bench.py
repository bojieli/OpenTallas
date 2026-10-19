#!/usr/bin/env python3
"""QW-DIEFIX-NFAR XT1n bench driver (tb_xt1n.sv): the N side of dvs_W5 -- near band-2 cluster c16_W5_2 (cid 2) and the FAR
cluster c16_W5_3 (cid 3) behind it.  Events are XT1's (xt1_bench.gen: same hr / XPF / x beats, slice hr layout).
Check: near words (RS lines = c16_W5_2.rs) vs gold cid 2, far words (RSO lines = c16_W5_2.rs_o, the far cluster's rs fed
through) vs gold cid 3, each with xt1_bench.check (k = kc-1 word per (r, j), count rounds x k x 8).

  xt1n_bench.py check --gold-near G2 --gold-far G3 --log LOG --mode M [--lead L --gap G]  -> RESULT XT1N line + JSON
"""
from __future__ import annotations

import argparse
import contextlib
import io
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import xt1_bench as X        # noqa: E402


def split(log):
    near, far = [], []
    for ln in Path(log).read_text().split('\n'):
        p = ln.split()
        if len(p) < 2:
            continue
        if p[1] == 'RS':
            near.append(ln)
        elif p[1] == 'RSO':
            far.append(' '.join([p[0], 'RS'] + p[2:]))
        elif p[1] == 'FAULT' and p[2] == 'far_cluster':
            far.append(ln)
        elif p[1] == 'FAULT' and p[2] == 'near_cluster':
            near.append(ln)
        else:
            near.append(ln); far.append(ln)
    out = {}
    for k, v in (('near', near), ('far', far)):
        q = Path(f'{log}.{k}'); q.write_text('\n'.join(v) + '\n'); out[k] = q
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('cmd', choices=('check',))
    ap.add_argument('--gold-near', required=True)
    ap.add_argument('--gold-far', required=True)
    ap.add_argument('--log', required=True)
    ap.add_argument('--mode', default='nominal')
    ap.add_argument('--lead', type=int, default=8)
    ap.add_argument('--gap', type=int, default=4)
    a = ap.parse_args()
    logs = split(a.log)
    res, vs = {}, []
    for side, g in (('near', a.gold_near), ('far', a.gold_far)):
        b = argparse.Namespace(log=str(logs[side]), mode=a.mode, lead=a.lead, gap=a.gap)
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            v = X.check(b, json.loads(Path(g).read_text()))
        vs.append(v)
        res[side] = json.loads(Path(str(logs[side]) + '.result.json').read_text())
        print(f'[{side}] ' + buf.getvalue().rstrip().replace('RESULT XT1', 'XT1'))
    v = 'PASS' if all(x == 'PASS' for x in vs) else 'FAIL'
    Path(a.log + '.xt1n.json').write_text(json.dumps(dict(verdict=v, mode=a.mode, lead=a.lead, gap=a.gap, **res), indent=1))
    print(f'RESULT XT1N {v} mode={a.mode} near={res["near"]["exact"]} far={res["far"]["exact"]}')
    sys.exit(0 if v == 'PASS' else 1)


if __name__ == '__main__':
    main()
