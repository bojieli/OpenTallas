#!/usr/bin/env python3
"""H-DIE-R8b 2026-10-17: which SYNTH cells of a v16 view plan can reuse an existing synthesis (same cell name, the
same wrapper text and every recorded source file byte-identical to this checkout) and which must be synthesised.
A cell name alone is not enough: parameter variants are renumbered when the netlist changes (ot_hbm_fault_leaf__pvK
after the LG fold), so a stale ETM with the right name would bind the wrong parameters.

    synth_reuse_r8b.py --views VPLAN --metas DIR_OF_<cell>/meta.json --root CHECKOUT --out reuse.json
prints 'SYNTH <cells...>' (the cells to run) and writes reuse.json {reuse: [...], synth: {cell: reason}}.
"""
import argparse
import hashlib
import json
from pathlib import Path


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main():
    ap = argparse.ArgumentParser()
    for k in ('--views', '--metas', '--root', '--out'):
        ap.add_argument(k, required=True)
    ap.add_argument('--prev', help='previous run view plan: a cell it bound as SYNTH with the SAME wrapper text is reused '
                    'as that run did (keeps its admission, incl. --diagnostic-param-alias views); new / changed cells synthesise')
    a = ap.parse_args()
    V = json.loads((Path(a.views) / 'views.json').read_text())
    root = Path(a.root)
    reuse, synth = [], {}
    for cell, v in sorted(V.items()):
        if v['kind'] != 'SYNTH':
            continue
        mp = Path(a.metas) / cell / 'meta.json'
        if not mp.is_file():
            synth[cell] = 'no prior synthesis'; continue
        m = json.loads(mp.read_text())
        if a.prev:
            pv = json.loads((Path(a.prev) / 'views.json').read_text()).get(cell)
            pw = Path(a.prev) / 'wrap' / f"{v['wrapper']}.sv"
            nw = Path(a.views) / 'wrap' / f"{v['wrapper']}.sv"
            if not (pv and pv['kind'] == 'SYNTH' and pw.is_file() and pw.read_bytes() == nw.read_bytes()):
                synth[cell] = 'new cell or wrapper differs from the previous run'; continue
            # A previous wrapper proves only the parameter binding.  Its implementation can change while the
            # wrapper remains byte-identical (GEN2e reused old split2/split3 timing after RTL changes).
            # Always validate the immutable source inventory below as well.
        srcs = m.get('source_file_sha256') or {}
        wkey = f"v16w/{v['wrapper']}.sv"
        wnew = Path(a.views) / 'wrap' / f"{v['wrapper']}.sv"
        why = None
        if not srcs:
            why = 'prior synthesis has no immutable source inventory'
        elif srcs.get(wkey) != sha(wnew):
            why = 'wrapper (parameters) changed'
        else:
            for f, h in srcs.items():
                if f.startswith('v16w/'):
                    continue
                p = root / f
                if not p.is_file():
                    why = f'source gone: {f}'; break
                if sha(p) != h:
                    why = f'source changed: {f}'; break
        if why:
            synth[cell] = why
        else:
            reuse.append(cell)
    Path(a.out).write_text(json.dumps(dict(reuse=reuse, synth=synth), indent=1))
    for c, w in synth.items():
        print('NEED', c, '|', w)
    print('REUSE', len(reuse), 'SYNTH', len(synth))
    print('SYNTH ' + ' '.join(synth))


if __name__ == '__main__':
    main()
