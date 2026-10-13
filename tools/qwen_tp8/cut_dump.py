# Build the tp8b Qwen die (die_top_lint recipe tp8b) and scan its cuts (asbuilt + CAP_MODE v3).
# usage (from repo root): python3 tools/qwen_tp8/cut_dump.py OUTDIR
import sys, json, time
from pathlib import Path
sys.path.insert(0,'tools'); sys.path.insert(0,'results/arch/qwen_tp8_1012')
import die_top_lint as D, cuts as C
out=Path(sys.argv[1]); out.mkdir(parents=True, exist_ok=True); t=time.time()
D.QWEN_RECIPE='tp8b'; D._QW.clear(); D.QSRC=None
v,m=D.load_qwen()[:2]
v.write_netlist(m,1,out/'die.v')
from qwen_rom_fulldie_b3r2 import _pin_pos
pos=_pin_pos(v,m)
json.dump(dict(insts=[dict(n=i.name,m=i.master,x=i.x,y=i.y,w=i.w,h=i.h,orient=i.orient) for i in m['insts']],
               buses=m['buses'], endpoint_pos={f'{i}.{p}':pos(i,p) for _,_,_,eps in m['buses'] for i,p in eps}),
          open(out/'physical_model.json','w'))
hops=[]
for bid,cls,bits,eps in m['buses']:
    if bid.startswith('tree_') and len(eps)==2:
        a,b=[pos(*e) for e in eps]
        hops.append(dict(bus=bid,bits=bits,endpoints=eps,manhattan_um=abs(a[0]-b[0])+abs(a[1]-b[1])))
json.dump(dict(count=len(hops),max_stage_um=max(h['manhattan_um'] for h in hops),
               over_500=[h for h in hops if h['manhattan_um']>500],
               note='Pin-centroid Manhattan distance on generatedplacement; final actualDB snap and STA required'),
          open(out/'tree_hops.json','w'),indent=1)

json.dump(dict(pad_trim=m.get('tp8_pad_trim'),pads=m.get('tp8_tree_pads'),relays=m.get('r21_relays')),open(out/'pad_placement.json','w'),indent=1)
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
# pin alignment of every die bundle (owner 2026-10-13, tools/hier_contract/pin_align.py): jog, bit order, length
pa, PA = D.pin_align_record('qwen_rom', m, v.masters(m, 1), v.port_widths(m, 1), D.real_blocks('qwen_rom', m))
json.dump(pa, open(out/'pin_align.json','w'), indent=1, default=str)
print(PA.line(pa))
if pa['verdict'] == 'FAIL' and PA.gate_mode() == 'fail': sys.exit('pin align FAIL (see pin_align.json; OT_PIN_ALIGN_GATE=warn builds anyway)')
