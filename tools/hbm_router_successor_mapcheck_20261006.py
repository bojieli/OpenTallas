#!/usr/bin/env python3
"""Verify actual mapped local controls and SS/FF receiver loads before placement.

Inputs must be actual mapped-netlist JSON, flattened WITHOUT optimisation in a
separate analysis copy, plus exact installed-library input pin capacitances.
This never rewrites the native mapping or invents a physical/clock closure.
"""
import argparse,collections,hashlib,json,re
from pathlib import Path
TOP='ot_hbm_router_topk_successor'
CONTROL=['x_first','c_first','x_v','c_v','x_last','c_last','finished']
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()
def check(mapped,caps,source_map):
 net=json.loads(mapped.read_text())['modules'][TOP];lib=json.loads(caps.read_text())
 controls={k:{} for k in CONTROL};bit_controls={};cells=net['cells'];rank_bits={'ge_q':set(),'valid_q':set()};rank_counts=collections.Counter()
 seq=collections.Counter();unary={};unary_cells=set()
 for name,c in cells.items():
  typ=c['type'];conn=c['connections'];n=name.replace('\\[','[').replace('\\]',']')
  if typ.startswith('DFF'):
   seq[typ]+=1
   rm=re.search(r'g_on\.g_lane\[(\d+)\]\.u_lane\.(ge_q|valid_q)\[\d+\]\$_DFF',n)
   if rm:
    rank_counts[rm[2]]+=1;rank_bits[rm[2]].add(conn.get('QN',conn.get('Q',[]))[0])
   m=re.search(r'g_on\.g_lane\[(\d+)\]\.u_lane\.(x_first|c_first|x_v|c_v|x_last|c_last|finished)\$_DFF',n)
   if m:
    lane,k=int(m[1]),m[2];assert lane not in controls[k],(k,lane)
    out=conn.get('QN',conn.get('Q',[]));assert len(out)==1 and isinstance(out[0],int),(name,conn)
    controls[k][lane]=dict(cell=name,type=typ,source_bit=out[0]);bit_controls[out[0]]=(lane,k)
  if typ.startswith(('BUF','INV')) and len(conn.get('A',[]))==len(conn.get('Y',[]))==1:
   unary.setdefault(conn['A'][0],[]).append(conn['Y'][0]);unary_cells.add(name)
 counts={k:len(v) for k,v in controls.items()}
 assert all(rank_counts[k]==len(rank_bits[k])==192 for k in rank_bits),('ACTUAL_RANK_STATE_FAIL',dict(rank_counts))
 assert all(n==32 for n in counts.values()),('ACTUAL_LOCAL_CONTROL_RETENTION_FAIL',counts)
 for k,v in controls.items():assert len({row['source_bit'] for row in v.values()})==32,k
 clock=net['ports']['clk']['bits'][0];corners={}
 for corner,library in lib.items():
  trees={}
  for k,lanes in controls.items():
   for lane,row in lanes.items():
    seen={row['source_bit']};todo=list(seen)
    while todo:
     for bit in unary.get(todo.pop(),[]):
      if bit not in seen:seen.add(bit);todo.append(bit)
    trees[(lane,k)]=seen
  fanout={key:[] for key in trees};owners_by_bit=collections.defaultdict(list)
  for key,tree in trees.items():
   for bit in tree:owners_by_bit[bit].append(key)
  clockcap=0.;clocksinks=0
  for name,c in cells.items():
   if c['type']=='$scopeinfo':continue
   assert c['type'] in library,(c['type'],name)
   for pin,bits in c['connections'].items():
    if pin not in library[c['type']]:continue
    for bit in bits:
     if bit==clock:clockcap+=library[c['type']][pin];clocksinks+=1
     if name in unary_cells:continue
     for key in owners_by_bit.get(bit,[]):fanout[key].append(dict(cell=name,pin=pin,cap_fF=library[c['type']][pin]))
  per=[]
  for (lane,k),receivers in fanout.items():
   assert receivers,('CONTROL_WITHOUT_ACTUAL_RECEIVER',lane,k)
   # A different lane receiving this data-control bit proves folding/aliasing.
   foreign=[]
   for r in receivers:
    m=re.search(r'g_lane\[(\d+)\]',r['cell'])
    if m and int(m[1])!=lane:foreign.append(r)
   assert not foreign,('CROSS_LANE_CONTROL_ALIAS',lane,k,foreign)
   per.append(dict(lane=lane,control=k,actual_cell=controls[k][lane]['cell'],library_leaf_receiver_load_fF=sum(x['cap_fF'] for x in receivers),actual_leaf_receiver_pins=len(receivers),buffer_tree_nets=len(trees[(lane,k)]),receivers=receivers))
  corners[corner]=dict(clock_connected_input_pin_cap_fF=clockcap,clock_connected_input_pins=clocksinks,root_input_cap_not_inferred=True,actual_controls=per)
 return dict(status='ACTUAL_MAPPED_LOCAL_CONTROLS_AND_LIBRARY_LOADS_PASS',top=TOP,mapped_verilog_sha256=sha(source_map),mapped_json_sha256=sha(mapped),library_caps_sha256=sha(caps),control_DFF_counts=counts,rank_DFF_counts=dict(rank_counts),sequential_cells=dict(seq),corners=corners,wire_RC_included=False,propagated_clock=False,physical_closed=False,parent_qualified=False,placement_allowed_only_after_actual_capacity_and_frame_binding=True)
if __name__=='__main__':
 a=argparse.ArgumentParser();a.add_argument('--mapped-json',type=Path,required=True);a.add_argument('--caps',type=Path,required=True);a.add_argument('--source-mapped-verilog',type=Path,required=True);a.add_argument('--out',type=Path,required=True);q=a.parse_args()
 if q.out.exists():a.error('immutable map receipt exists')
 r=check(q.mapped_json,q.caps,q.source_mapped_verilog);q.out.write_text(json.dumps(r,indent=2)+'\n');print(json.dumps({k:r[k] for k in ['status','control_DFF_counts','sequential_cells']}))
