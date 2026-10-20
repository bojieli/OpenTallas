#!/usr/bin/env python3
"""Turn an EQUIVALENT kv_leaf_lec.py result into a frozen parameter receipt for kv_expand strict bind (OWNER 10-20 09:05).

The receipt keeps the schema kv_expand_parameters.preserve() checks (opentallas.native_parameter_profile.v1, identity,
parameters, native_qualified=true) and records qualification='standard_lec' with the LEC evidence: the bind gate
needs only that an equivalence of the exact parameters on the exact view exists.  Refuses unless the LEC is EQUIVALENT,
every LEC source byte equals the worktree's, the selected view's TT/FF Liberty equal the closed job's recorded view, and
(when given) the parameter-mutant control came out NOT_EQUIVALENT or failed elaboration on the RTL parameter trap.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))
import kv_expand_parameters as EP  # noqa: E402


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--root', required=True)
    ap.add_argument('--lec', required=True)
    ap.add_argument('--control', help='parameter-mutant control lec json (expect fail)')
    ap.add_argument('--module', required=True, help='RTL module the die instantiates')
    ap.add_argument('--rtl', required=True)
    ap.add_argument('--view', required=True)
    ap.add_argument('--closed-job', required=True)
    ap.add_argument('--closed-commit', required=True)
    ap.add_argument('--record-libs', required=True, help='JSON {tt: sha, ff: sha} of the closed job record/views libs')
    ap.add_argument('--out', required=True, help='receipts dir (results/arch/<lane>/receipts)')
    a = ap.parse_args(argv)
    root, out = Path(a.root).resolve(), Path(a.out)
    r = json.loads(Path(a.lec).read_text())
    if r.get('verdict') != 'EQUIVALENT' or r.get('expect') != 'pass':
        sys.exit(f'{a.module}: LEC verdict {r.get("verdict")}: no receipt')
    if r['module'] != a.module:
        sys.exit(f'LEC module {r["module"]} != {a.module}')
    stale = [s for s, h in r['sources'].items() if not (root / s).is_file() or sha(root / s) != h]
    if stale:
        sys.exit(f'{a.module}: LEC sources differ from the worktree: {stale}')
    vd = root / a.view
    libs = json.loads(a.record_libs)
    for c in ('tt', 'ff'):
        if sha(vd / f'{vd.name}_{c}.lib') != libs[c]:
            sys.exit(f'{a.module}: view {c} liberty != closed job record ({a.closed_job})')
    ctl = None
    if a.control:
        c = json.loads(Path(a.control).read_text())
        trap = c.get('verdict') == 'ERROR' and 'gold elaboration failed' in c.get('error', '') and \
            ('requires' in c['error'] or 'trap' in c['error'])
        if not (c.get('verdict') == 'NOT_EQUIVALENT' or trap):
            sys.exit(f'{a.module}: parameter control {c.get("parameters")} gave {c.get("verdict")} (must fail)')
        ctl = dict(parameters=c['parameters'], verdict=c['verdict'] if not trap else 'ELABORATION_TRAP',
                   cex_frame=c.get('cex_frame'), file=Path(a.control).name, sha256=sha(a.control))
    ident = EP.artifact_identity(root, a.view, a.rtl)
    rec = dict(schema='opentallas.native_parameter_profile.v1', module=a.module, identity=ident,
               parameters=r['parameters'], native_qualified=True, qualification='standard_lec',
               evidence=dict(method='standard sequential LEC: ' + r['engine']['tool'] +
                             f"; reset held {r['reset']['cycles']} edges then every output compared every cycle; "
                             'all registers power up 0 on both sides (datapath unreset); hard macros cut',
                             closed_job=a.closed_job, closed_commit=a.closed_commit, gate_sha256=r['gate_sha256'],
                             view_tie='view TT/FF liberty bytes == the closed job liberty (record/views or closed_archive final)', record_libs=libs,
                             wrapper=r.get('wrapper'), sources=r['sources'], aig=r.get('aig'),
                             abc_log_sha256=r['engine']['abc_log_sha256'], abc_cmd=r['engine'].get('abc_cmd'), aig_sha256=r['aig_sha256'],
                             lec=Path(a.lec).name, lec_sha256=sha(a.lec), control=ctl))
    rp = out / 'receipts' / f'{a.module}.json'
    rp.parent.mkdir(parents=True, exist_ok=True)
    rp.write_text(json.dumps(rec, indent=1, sort_keys=True) + '\n')
    pf = out / 'profiles.json'
    prof = json.loads(pf.read_text()) if pf.is_file() else {}
    prof[a.module] = dict(parameters=r['parameters'], identity=ident,
                          frozen_receipt=dict(path=str(rp.resolve().relative_to(root)), sha256=sha(rp)))
    pf.write_text(json.dumps(prof, indent=1, sort_keys=True) + '\n')
    print(f'receipt {rp} ({a.module} {r["parameters"]})')


if __name__ == '__main__':
    main()
