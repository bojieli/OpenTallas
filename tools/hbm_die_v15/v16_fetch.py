#!/usr/bin/env python3
"""Collect finished SYNTH views of v16 die cells (H-DIE-V16CASE 2026-10-16) into VIEWS_DIR/synth/<cell>/:
<wrapper>_synth_{tt,ff}.lib, etm_worst_*.rpt, meta.json = {std_area_um2 (yosys stat -liberty, top incl. submodules),
macros {module: [count, w, h]} (counts incl. submodules from the stat hierarchy; size from the macro LEF next to its
_bb.v), host, remote}.  Finds each cell on whichever fleet host built it.

    v16_fetch.py --views VIEWS_DIR [--remote-root DIR] [--commit SHA]
"""
import argparse, json, subprocess
from pathlib import Path

HOSTS = ['ot-epyc1tb', 'ot-epyc4', 'ot-agidock128']
REMOTE_PY = r'''
import json, re, sys, os
root, src, cell, wrap = sys.argv[1:5]
d = f"{root}/syn/{cell}"
st = open(f"{d}/{cell}.stat").read()
area = float(re.search(r"Chip area for top module '[^']*': ([\d.]+)", st).group(1))
fj = json.load(open(f"{d}/{cell}.files.json"))
mods = {m['module']: m['file'] for m in fj['macros']}
hier = st.split('=== design hierarchy ===', 1)[-1]
mac = {}
for m, f in mods.items():
    c = [int(x) for x in re.findall(r'^\s+(\d+)\s+\S+\s+' + re.escape(m) + r'\s*$', hier, re.M)]
    if not c:
        continue
    lef = f"{src}/{f[:-len('_bb.v')]}.lef" if f.endswith('_bb.v') else None
    w = h = 0.0
    if lef and os.path.exists(lef):
        s = re.search(r'SIZE\s+([\d.]+)\s+BY\s+([\d.]+)', open(lef).read())
        w, h = float(s.group(1)), float(s.group(2))
    mac[m] = [max(c), w, h]
print(json.dumps(dict(std_area_um2=area, macros=mac)))
'''


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--views', required=True)
    ap.add_argument('--remote-root', default='/srv/opentallas-scratch/claude/hdie-v16case')
    ap.add_argument('--commit', default='8c3c2a340')
    a = ap.parse_args()
    V = json.loads((Path(a.views) / 'views.json').read_text())
    src = f'{a.remote_root}/src_{a.commit}'
    found = {}
    for h in HOSTS:
        out = subprocess.run(['ssh', h, f'cd {a.remote_root}/syn 2>/dev/null && ls -d */ | tr -d /'], capture_output=True,
                             text=True).stdout.split()
        for c in out:
            w = V.get(c, {}).get('wrapper')
            if not w:
                continue
            ok = subprocess.run(['ssh', h, f'test -s {a.remote_root}/syn/{c}/{w}_synth_ff.lib && echo y'],
                                capture_output=True, text=True).stdout.strip()
            if ok == 'y':
                found[c] = h
    for c, h in sorted(found.items()):
        w = V[c]['wrapper']
        dst = Path(a.views) / 'synth' / c
        dst.mkdir(parents=True, exist_ok=True)
        for f in (f'{w}_synth_tt.lib', f'{w}_synth_ff.lib', 'etm_worst_tt.rpt', 'etm_worst_ff.rpt'):
            subprocess.run(['scp', '-q', f'{h}:{a.remote_root}/syn/{c}/{f}', str(dst / f)])
        meta = subprocess.run(['ssh', h, 'python3', '-', a.remote_root, src, c, w], input=REMOTE_PY,
                              capture_output=True, text=True)
        m = json.loads(meta.stdout) if meta.returncode == 0 and meta.stdout.strip() else dict(error=meta.stderr[-400:])
        m.update(host=h, remote=f'{a.remote_root}/syn/{c}')
        (dst / 'meta.json').write_text(json.dumps(m, indent=1))
        print(c, h, m.get('std_area_um2'), len(m.get('macros', {})))
    print('FETCHED', len(found))


if __name__ == '__main__':
    main()
