#!/usr/bin/env python3
"""c5 diagnosis (2026-10-13): dump the generator's region geometry (what dsrom_s81_fulldie.where() classifies with) for a
die-iter case, so a congestion map can be classified off-host.
usage: c5diag_regions.py <src snapshot> <options.txt> <out.json>   (env as the chain: OT_S81_CTRL_GATE_WARN, OT_S81_Q_LEF)"""
import argparse, json, sys
from pathlib import Path
src, opts, out = sys.argv[1:4]
sys.path.insert(0, str(Path(src) / 'tools'))
import dsrom_s81_fulldie as S  # noqa: E402
S.apply_options(S.die_options(argparse.ArgumentParser()).parse_args(Path(opts).read_text().split()))
m = S.build()
g = m['geo']
num = lambda v: v if isinstance(v, (int, float, str)) or v is None else ([num(x) for x in v] if isinstance(v, (list, tuple)) else None)
rec = dict(die=list(S.DIE), geo={k: num(v) for k, v in g.items() if num(v) is not None}, x_vch=m['x_vch'], VCH=S.VCH,
           chh=[S.chh(t) for t in range(len(g['ch_y']))],
           regions=[dict(name=r['name'], kind=r.get('kind'), rect=list(r['rect'])) for r in m['regions']],
           phys=[dict(name=k, rect=[it.x, it.y, it.x + it.w, it.y + it.h]) for k, it in m['phys'].items()],
           links=[dict(name=it.name, rect=[it.x, it.y, it.x + it.w, it.y + it.h]) for it in m['links']])
Path(out).write_text(json.dumps(rec, indent=1) + '\n')
print('OT_REGIONS', len(rec['regions']), 'regions', rec['die'])
