# Build the tp8b Qwen die (die_top_lint recipe tp8b) and scan its cuts (asbuilt + CAP_MODE v3).
# usage (from repo root): python3 tools/qwen_tp8/cut_dump.py OUTDIR
import sys, json, time
from pathlib import Path
sys.path.insert(0,'tools'); sys.path.insert(0,'results/arch/qwen_tp8_1012')
import die_top_lint as D, cuts as C
out=Path(sys.argv[1]); out.mkdir(parents=True, exist_ok=True); t=time.time()
D.QWEN_RECIPE='tp8b'; D._QW.clear(); D.QSRC=None
m=D.load_qwen()[1]
ins=[dict(n=i.name, m=getattr(i,'master',''), x=i.x, y=i.y, w=i.w, h=i.h) for i in m['insts']]
json.dump(dict(insts=ins, buses=[(b,c,bits,[e[0] for e in eps]) for b,c,bits,eps in m['buses']]), open(out/'rom_tp8b.json','w'))
r_=m.get('r21_relays',{}); print('relays', r_.get('relays'), 'repaired', r_.get('repaired'), 'unrepaired', len(r_.get('unrepaired',[])), 'off_plan', r_.get('off_plan'), 'feedback', r_.get('feedback'))
print('built', round(time.time()-t), 'die', m['die'].get('w'), m['die'].get('h'), 'pads', json.dumps(m.get('tp8_tree_pads'))[:200])
A=C.Net(out/'rom_tp8b.json'); R=C.rom_cuts(A)
json.dump(R, open(out/'tp8b_cuts.json','w'), indent=1)
print('row', R['row_H_max']['util'], 'spine', R['spine_V_max']['util'], 'col', R['col_V_max']['util'])
for r in R['fine'][:6]: print('fine', r)
C.CAP_MODE='v3'; A=C.Net(out/'rom_tp8b.json'); R=C.rom_cuts(A)
json.dump(R, open(out/'tp8b_cuts_v3.json','w'), indent=1)
print('V3 row', R['row_H_max']['util'], 'spine', R['spine_V_max']['util'], 'col', R['col_V_max']['util'])
for r in R['fine'][:6]: print('V3 fine', r)
