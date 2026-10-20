#!/usr/bin/env python3
"""Build a source-bound pin/lattice model. This does not generate a gateable kit."""
import hashlib,json,re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
OUT=Path(__file__).resolve().parent
SRC=ROOT/'rtl/qwen_sys/static_embedding_20261014/qkd_kvs_emb_ctx_n32child.sv'
VIEW=ROOT/'physical/ref_tile/qkd_embedding_row_tx_ctx_n32c/views/qkd_embedding_row_tx_ctx_native32'
lef=(VIEW/'qkd_embedding_row_tx_ctx_native32.lef').read_text()
assert not re.search(r'^\s*SYMMETRY\b',lef,re.M),'Requires a separately reviewed symmetry change'
assert re.search(r'SIZE\s+237\.6+\s+BY\s+151\.2+\s*;',lef)
ports={}
for d,hi,lo,n in re.findall(r'^\s*(input|output)\s+wire\s*(?:\[(\d+):(\d+)\]\s*)?(\w+)',SRC.read_text(),re.M):
 ports[n]={'direction':d,'bits':list(range(int(lo),int(hi)+1)) if hi else [None]}
pins={}
def add(port,face,start,pitch=.192):
 for j,b in enumerate(ports[port]['bits']):
  name=port if b is None else f'{port}[{b}]'
  assert name not in pins
  pins[name]={'face':face,'along_um':round(start+j*pitch,6),'direction':ports[port]['direction'],'role':'proposed boundary FF; NOT placed'}
 return start+len(ports[port]['bits'])*pitch
s=100
for n in ['i_hroot_WS','i_hroot_WN']:s=add(n,'W',s)
s=200
for n in ['i_hroot_ES','i_hroot_EN']:s=add(n,'S',s)
add('i_ctx','E',10);add('d2d__emb_tx_slot','E',50);add('i_ctl','S',20)
s=260
for n in ['px_st','px_tok','px_tep','emb_fault']:s=add(n,'E',s)
add('rst_n','S',150);add('ck','S',180)
# Use actual closed child LEF output rectangles. Pin routes and FF placement remain unqualified.
rows=[]
for match in re.finditer(r'^\s*PIN\s+(emb_tx_payload\[\d+\]|emb_tx_v)\s*$(.*?)^\s*END\s+\1\s*$',lef,re.M|re.S):
 name,body=match.groups()
 rects=[tuple(map(float,x)) for x in re.findall(r'RECT\s+([-.\d]+)\s+([-.\d]+)\s+([-.\d]+)\s+([-.\d]+)\s*;',body)]
 assert rects,name
 r=rects[0];x=86.4+(r[0]+r[2])/2;y=86.4+(r[1]+r[3])/2
 pn='rowtx__'+name
 if name=='emb_tx_v':pn+='[0]'
 rows.append((y,pn,x,y))
assert len(rows)==549,len(rows)
# Snap outer E-face targets to 0.192um track grid, requiring a unique target for every bit.
used=set()
for y,n,x,cy in sorted(rows):
 k=round(y/.192)
 while k in used:k+=1
 used.add(k);py=round(k*.192,6)
 pins[n]={'face':'E','along_um':py,'direction':'output','role':'proposed boundary FF; NOT placed','child_actual_pin_center':[x,cy],'ff_target':[381.6,py],'child_to_ff_L1_um':abs(381.6-x)+abs(py-cy)}
expected={n if b is None else f'{n}[{b}]' for n,p in ports.items() for b in p['bits']}
assert set(pins)==expected,(len(pins),len(expected),set(pins)^expected)
maxwindow={};minsep={}
for face in ['W','E','S','N']:
 vals=sorted(p['along_um'] for p in pins.values() if p['face']==face)
 limit=302.4 if face in ['W','E'] else 388.8
 assert all(0<x<limit for x in vals),(face,vals)
 assert len(set(vals))==len(vals),face
 maxwindow[face]=max([sum(0<=b-a<1 for b in vals) for a in vals] or [0])
 minsep[face]=min([b-a for a,b in zip(vals,vals[1:])] or [None])
 assert maxwindow[face]<=6,(face,maxwindow[face])
obs={}
obs_text=lef.split('\n  OBS',1)[1]
for name,body in re.findall(r'LAYER\s+(\w+)\s*;(.*?)(?=LAYER|\n\s*END)',obs_text,re.S):
 rects=[tuple(map(float,x)) for x in re.findall(r'RECT\s+([-.\d]+)\s+([-.\d]+)\s+([-.\d]+)\s+([-.\d]+)\s*;',body)]
 if rects:obs[name]={'rectangles':len(rects),'bbox':[min(r[0] for r in rects),min(r[1] for r in rects),max(r[2] for r in rects),max(r[3] for r in rects)]}
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
result={'status':'SOURCE_PIN_MODEL_ONLY_NOT_GATEABLE','source_sha256':sha(SRC),'child_view_sha256':{p.name:sha(p) for p in sorted(VIEW.iterdir()) if p.is_file() and p.suffix in ['.lef','.lib','.json']},'parent_outline':[388.8,302.4],'child':{'at':[86.4,86.4],'orient':'R0','size':[237.6,151.2],'lattice_um':43.2},'routing_layer_model':{'old_parent_cap':'M5','old_analytical_capacity_assumed':'M6/M7','status':'INCOMPATIBLE_ASSUMPTIONS_NO_CAPACITY_ADMISSION','child_actual_OBS':obs,'scope':'Need actual layer directions/pitches, PG/OBS and width before choosing cap or channel; no over-the-child upper-metal capacity is currently admitted'},'parent_boundary_bits':len(pins),'face_max_pins_in_1um_window':maxwindow,'face_min_sep_um':minsep,'child_output_connections':len(rows),'max_child_output_to_proposed_FF_L1_um':max(p.get('child_to_ff_L1_um',0) for p in pins.values()),'schedule':{'new_edges_from_R0_placement':0,'inherited_native_parent_active_edges_vs_legacy_source':2,'inherited_generic_wrapper_active_edges':2,'inherited_parallel_reset_edges':6,'scope':'Wrapper input/output edges were already priced by KV-PLAN5. They are separate from native CTX+JOIN changes. Current producer/consumer first-use composition remains OPEN.'},'obligations':['No emitted kit until exact source pin FF ownership and complete connected register-stage/all-driver L1 fit405','Exact clock entry, child input arrival, linked parent/child reference TT/FF spreads<=80; prior own-R is insufficient','Real parent mapped standard area including generic wrapper FFs plus child abstract must establish fill/placement capacity','Actual upper metal directions/PG/OBS/channel access; provisional track count is not admission','Source first-use/reset/identity/full native child bench, current native census and exact shared RTL identities','Canonical PG both grids and final native PG on actual routed parent; no old MY view use'],'pins':pins}
(OUT/'source_pin_model.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({k:v for k,v in result.items() if k not in ['pins','child_view_sha256']},indent=2))
