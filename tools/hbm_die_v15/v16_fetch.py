#!/usr/bin/env python3
"""Collect finished SYNTH views of v16 die cells (H-DIE-V16CASE 2026-10-16) into VIEWS_DIR/synth/<cell>/:
<wrapper>_synth_{tt,ff}.lib, etm_worst_*.rpt, meta.json = {std_area_um2 (yosys stat -liberty, top incl. submodules),
macros {module: [count, w, h]} (counts incl. submodules from the stat hierarchy; size from the macro LEF next to its
_bb.v), host, remote}.  Finds each cell on whichever fleet host built it.

    v16_fetch.py --views VIEWS_DIR [--remote-root DIR] [--commit SHA]
"""
import argparse, hashlib, json, subprocess
from pathlib import Path

HOSTS = ['ot-epyc4', 'ot-agidock128']   # ot-epyc1tb retired 10-16 (its reusable views were copied to ot-epyc4)
REMOTE_PY = r'''
import hashlib, json, re, sys, os, shlex
root, src, cell, wrap = sys.argv[1:5]
d = f"{root}/syn/{cell}"
ys = open(f"{d}/{cell}.ys").read()
tops = re.findall(r'^hierarchy -check -top (\S+)\s*$', ys, re.M)
if tops != [wrap]:
    raise ValueError(f"Wrong synthesized top: {tops}; expected parameter wrapper {wrap}")
inputs = sorted({shlex.split(l)[-1] for l in ys.splitlines() if l.startswith('read_verilog ')})
input_hashes = {p: hashlib.sha256(open(f'{src}/{p}', 'rb').read()).hexdigest() for p in inputs}
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
print(json.dumps(dict(std_area_um2=area, macros=mac, actual_top=tops[0], source_file_sha256=input_hashes,
                     synthesis_script_sha256=hashlib.sha256(ys.encode()).hexdigest())))
'''


def check_sources(meta, commit, views):
    """Verify remote source bytes against the declared Git snapshot and exact wrapper."""
    hashes = meta['source_file_sha256']
    paths = [p for p in hashes if not p.startswith('v16w/')]
    data = subprocess.run(['git', '-C', str(Path(__file__).resolve().parents[2]), 'cat-file', '--batch'],
                          input=''.join(f'{commit}:{p}\n' for p in paths).encode(), capture_output=True, check=True).stdout
    offset = 0
    for p in paths:
        end = data.index(b'\n', offset)
        header = data[offset:end].split()
        if len(header) != 3 or header[1] != b'blob':
            raise ValueError(f'Source absent from {commit}: {p}')
        size = int(header[2]); blob = data[end + 1:end + 1 + size]; offset = end + 2 + size
        if hashlib.sha256(blob).hexdigest() != hashes[p]:
            raise ValueError(f'Source differs from {commit}: {p}')
    for p in hashes:
        if p.startswith('v16w/'):
            local = Path(views) / 'wrap' / Path(p).name
            if hashlib.sha256(local.read_bytes()).hexdigest() != hashes[p]:
                raise ValueError(f'Parameter wrapper mismatch: {p}')


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--views', required=True)
    ap.add_argument('--remote-root', default='/srv/opentallas-scratch/claude/hdie-v16case')
    ap.add_argument('--commit', default='8c3c2a340')
    ap.add_argument('cells', nargs='*', help='only these cells (a same-named older build with other ports/params/source must not be fetched)')
    a = ap.parse_args()
    V = json.loads((Path(a.views) / 'views.json').read_text())
    src = f'{a.remote_root}/src_{a.commit}'
    found = {}
    for h in HOSTS:
        out = subprocess.run(['ssh', h, f'cd {a.remote_root}/syn 2>/dev/null && ls -d */ | tr -d /'], capture_output=True,
                             text=True).stdout.split()
        for c in out:
            w = V.get(c, {}).get('wrapper')
            if not w or (a.cells and c not in a.cells):
                continue
            ok = subprocess.run(['ssh', h, f'test -s {a.remote_root}/syn/{c}/{w}_synth_ff.lib && '
                                f'grep -qx OT_ETM_DONE_ff {a.remote_root}/syn/{c}/etm.log && echo y'],
                                capture_output=True, text=True).stdout.strip()
            if ok == 'y':
                found[c] = h
    for c, h in sorted(found.items()):
        w = V[c]['wrapper']
        meta = subprocess.run(['ssh', h, 'python3', '-', a.remote_root, src, c, w], input=REMOTE_PY,
                              capture_output=True, text=True)
        if meta.returncode:
            raise ValueError(f'Cannot admit {c}: {meta.stderr[-1000:]}')
        m = json.loads(meta.stdout)
        check_sources(m, a.commit, a.views)
        dst = Path(a.views) / 'synth' / c
        dst.mkdir(parents=True, exist_ok=True)
        files = (f'{w}_synth_tt.lib', f'{w}_synth_ff.lib', 'etm_worst_tt.rpt', 'etm_worst_ff.rpt')
        # Large Liberty tables compress well. Copy a cell in one checked transfer;
        # a failed transfer must not publish a receipt for incomplete views.
        subprocess.run(['rsync', '-az', *[f'{h}:{a.remote_root}/syn/{c}/{f}' for f in files], str(dst) + '/'],
                       check=True)
        m.update(host=h, remote=f'{a.remote_root}/syn/{c}', declared_source_snapshot=a.commit,
                 consumed_file_sha256={f: hashlib.sha256((dst / f).read_bytes()).hexdigest() for f in files})
        (dst / 'meta.json').write_text(json.dumps(m, indent=1))
        print(c, h, m.get('std_area_um2'), len(m.get('macros', {})))
    print('FETCHED', len(found))


if __name__ == '__main__':
    main()
