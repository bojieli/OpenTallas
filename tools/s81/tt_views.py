#!/usr/bin/env python3
"""TT timing models for hardened views (CLAUDE S81-DIE, 2026-10-07; owner option B: die setup at TT, hold at FF, SS as
sensitivity).  For every committed view that carries an SS/FF extraction (export_ss.tcl + abstract.json written by
tools/hbm_fmax_attn_abstract.py) and no <name>_tt.lib, the TT model is extracted the same way from the SAME routed
6_final odb / sdc / spef on the host that holds the route: export_tt.tcl = export_ss.tcl with the ASAP7 RVT TT NLDM
libraries (and the TT libs of any macro views it reads), library <name>_tt, no LEF rewrite.

  tt_views.py plan [--match REGEX] [--extra name=orfs_dir:view_dir ...] --out plan.json   (probes hosts over ssh)
  tt_views.py emit --plan plan.json --host H --dir REMOTE_DIR                           -> run_tt_<host>.sh on stdout
  tt_views.py collect --plan plan.json --host H --dir REMOTE_DIR                        copies <name>_tt.lib back
"""
import argparse
import json
import re
import shlex
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HOSTS = ['ot-epyc3', 'ot-epyc1tb', 'ot-epyc2', 'ot-pve1', 'ot-agidock128']


def tt_tcl(ss, name):
    t = re.sub(r'_(RVT|LVT|SLVT)_SS_', r'_\1_TT_', ss)     # multi-Vt views (OT_MULTI_VT) read LVT / SLVT libs too
    t = re.sub(r'(read_liberty \S+)_ss\.lib', r'\1_tt.lib', t)
    t = t.replace(f'-library_name {name}_ss /out/{name}_ss.lib', f'-library_name {name}_tt /out/{name}_tt.lib')
    t = re.sub(r'^write_abstract_lef .*\n', '', t, flags=re.M)
    assert f'{name}_tt.lib' in t and '_SS_' not in t, name
    return t


def targets(match):
    out = []
    for ex in sorted(ROOT.glob('**/export_ss.tcl')):
        d = ex.parent
        if '.git' in d.parts or (match and not re.search(match, str(d.relative_to(ROOT)))):
            continue
        ab = d / 'abstract.json'
        if not ab.exists():
            continue
        a = json.loads(ab.read_text())
        name = a['name']
        if (d / f'{name}_tt.lib').exists():
            continue
        mounts = []
        cmd = (a.get('corners', {}).get('ss') or {}).get('command') or []
        for i, c in enumerate(cmd):
            if c == '-v' and re.search(r':/mv\d+(:ro)?$', cmd[i + 1]):
                mounts.append(cmd[i + 1])
        out.append(dict(view=str(d.relative_to(ROOT)), name=name, orfs_dir=a['orfs_dir'], mounts=mounts,
                        tcl=tt_tcl(ex.read_text(), name)))
    return out


def probe(ts):
    for h in HOSTS:
        todo = [t for t in ts if not t.get('host')]
        if not todo:
            break
        chk = ' ; '.join(f'ls {shlex.quote(t["orfs_dir"])}/results/asap7/*/base/6_final.spef >/dev/null 2>&1 '
                         f'&& echo Y{i} || true' for i, t in enumerate(todo))
        r = subprocess.run(['ssh', '-o', 'ConnectTimeout=10', h, chk], capture_output=True, text=True)
        for m in re.findall(r'Y(\d+)', r.stdout):
            todo[int(m)]['host'] = h


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('mode', choices=['plan', 'emit', 'collect'])
    ap.add_argument('--match', default='')
    ap.add_argument('--out', type=Path)
    ap.add_argument('--plan', type=Path)
    ap.add_argument('--host')
    ap.add_argument('--dir')
    a = ap.parse_args()
    if a.mode == 'plan':
        ts = targets(a.match)
        probe(ts)
        a.out.write_text(json.dumps(ts, indent=1) + '\n')
        by = {}
        for t in ts:
            by.setdefault(t.get('host', 'MISSING'), []).append(t['name'])
        print(json.dumps({h: len(v) for h, v in by.items()}), json.dumps(by.get('MISSING', [])))
        return
    ts = [t for t in json.loads(a.plan.read_text()) if t.get('host') == a.host]
    if a.mode == 'emit':
        L = ['#!/bin/bash', f'# TT view extraction on {a.host} (tools/s81/tt_views.py, CLAUDE S81-DIE)', 'set -u',
             f'D={a.dir}', 'mkdir -p $D']
        for t in ts:
            o = f'$D/{t["name"]}'
            L.append(f'mkdir -p {o} && cat > {o}/export_tt.tcl <<\'TCL\'\n{t["tcl"]}TCL')
            mv = ' '.join(f'-v {m}' for m in t['mounts'])
            L.append(f'( docker run --rm --cpus=2 -v {t["orfs_dir"]}:/in:ro -v {o}:/out {mv} openroad/orfs:latest '
                     f'/OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -no_init -exit /out/export_tt.tcl '
                     f'> {o}/export_tt.log 2>&1; echo $? > {o}/rc ) &')
            L.append('while [ $(jobs -r | wc -l) -ge 8 ]; do sleep 5; done')
        L += ['wait', 'echo TT_DONE']
        print('\n'.join(L))
        return
    for t in ts:
        dst = ROOT / t['view']
        r = subprocess.run(['scp', '-q', f'{a.host}:{a.dir}/{t["name"]}/{t["name"]}_tt.lib',
                            f'{a.host}:{a.dir}/{t["name"]}/export_tt.log', str(dst) + '/'], capture_output=True, text=True)
        (dst / 'export_tt.tcl').write_text(t['tcl'])
        ok = (dst / f'{t["name"]}_tt.lib').exists()
        print(t['name'], 'OK' if ok else 'FAIL ' + r.stderr.strip()[:200])


if __name__ == '__main__':
    main()
