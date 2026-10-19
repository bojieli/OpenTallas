#!/usr/bin/env python3
"""Compile actual net bit ranges into split hard-child endpoint buses.

Geometry-only connectivity preparation. Does not emit a parent kit or clocks.
"""
import argparse,json,hashlib
from pathlib import Path
from qc_safe_graph import extract,ROOT
p=argparse.ArgumentParser();p.add_argument('--out',required=True);a=p.parse_args();g=extract();assert not g['unresolved']
base=Path('results/arch/qwen_cluster_1017/q_cluster16')
assets={};pinsets={}
for width in [257,258]:
 for h in 'wr':
  path=base/('safe_child_257_attempt6' if width==257 else 'safe_child_attempt6')/f'native_pins_{h}{width if width==257 else ""}.json'
  d=json.loads((ROOT/path).read_text());master=f'qfd_c_land_{h}{width}_narrow';pinsets[master]=d['pins'];assets[master]=dict(path=str(path),sha256=hashlib.sha256((ROOT/path).read_bytes()).hexdigest(),signal_clock_pins=d['signal_clock_pins'])
for width in [514,516]:
 path=base/'station_child_attempt1'/f'native_pins_stn{width}.json';d=json.loads((ROOT/path).read_text());master=f'qfd_c_stn{width}_safe';pinsets[master]=d['pins'];assets[master]=dict(path=str(path),sha256=hashlib.sha256((ROOT/path).read_bytes()).hexdigest(),signal_clock_pins=d['signal_clock_pins'])
def split(n):return g['nodes'].get(n,{}).get('kind')in ['qfd_c_land_w','qfd_c_land_r']
def endpoint(n,net,lo,hi,output):
 if n not in g['nodes']:
  v=g['ports'][n];return dict(inst=v.get('tile','BOUNDARY'),port=(n.rsplit('_',2)[0] if v['kind']=='tile_port' else n),range=[lo,hi],native_pin_snapshot=None,scope='actual A0/boundary pin geometry still required')
 v=g['nodes'][n];kind=v['kind'];ps=v['ports']
 if split(n):
  half='w'if kind.endswith('_w')else'r';H=int(ps['W'])//2;part=lo//H;assert hi//H==part
  return dict(inst=n+f'_p{part}',port='o'if output else'i',range=[lo%H,hi%H],master=f'qfd_c_land_{half}{H}_narrow',clock_port='ck',clock_domain=v['region'])
 if 'xstn'in kind:
  port=('tap_d'if net==ps['tap_d']else'a_d')if output else'b_d';return dict(inst=n,port=port,range=[lo,hi],master=kind+'_safe_UNQUALIFIED',native_pin_snapshot=None,clock_domain=v['region'],scope='xstn safe RTL/control/native geometry not yet qualified')
 width=int(ps.get('W',v['bits']));assert width in [514,516],(n,width)
 return dict(inst=n,port='q'if output else'd',range=[lo,hi],master=f'qfd_c_stn{width}_safe',clock_port='ck',clock_domain=v['region'])
bindings=[]
for e in g['edges']:
 src,dst=e['src'],e['dst'];bits=e['bits']
 if e['kind']=='bank':
  W=int(g['nodes'][src]['ports']['W']);H=W//2;assert bits==4*W
  for part in [0,1]:
   for side in ['w','e']:
    # The two physical faces contain slots0/1 and2/3 respectively. The
    # full logical bank interleaves lower/upper sibling data within each slot.
    segments=[dict(logical=[slot*W+part*H,slot*W+(part+1)*H-1],physical=[(slot%2)*H,(slot%2+1)*H-1])for slot in ([0,1]if side=='w'else[2,3])]
    bindings.append(dict(net=e['net'],kind='bank_data',bits=2*H,logical_segments=segments,src=dict(inst=src+f'_p{part}',port='bank_'+side,master=f'qfd_c_land_w{H}_narrow'),dst=dict(inst=dst+f'_p{part}',port='bank_'+side,master=f'qfd_c_land_r{H}_narrow'),ordinary_timing=True,proposed_bank_window=True,window_status='enumerated diagnostic only; actual native phase/reserve and Tcl dispatch unapproved'))
   bindings.append(dict(net=e['net']+'_written_p'+str(part),kind='written_flags',bits=44,src=dict(inst=src+f'_p{part}',port='vld',range=[0,43],master=f'qfd_c_land_w{H}_narrow'),dst=dict(inst=dst+f'_p{part}',port='vld',range=[0,43],master=f'qfd_c_land_r{H}_narrow'),ordinary_timing=True,window_status='NO data-window exemption'))
 else:
  cuts={0,bits}
  for n in [src,dst]:
   if split(n):cuts.add(int(g['nodes'][n]['ports']['W'])//2)
  cuts=sorted(cuts)
  for lo,upper in zip(cuts,cuts[1:]):
   hi=upper-1;bindings.append(dict(net=e['net'],kind='ordinary_data',bits=upper-lo,logical_range=[lo,hi],src=endpoint(src,e['net'],lo,hi,True),dst=endpoint(dst,e['net'],lo,hi,False),ordinary_timing=True))
checked=0;unqualified=[]
for binding in bindings:
 for side,direction in [('src','OUTPUT'),('dst','INPUT')]:
  ep=binding[side];master=ep.get('master')
  if master not in pinsets:unqualified.append(dict(net=binding['net'],side=side,endpoint=ep));continue
  lo,hi=ep.get('range',[0,binding['bits']-1])
  for bit in range(lo,hi+1):
   name=ep['port']+f'[{bit}]';assert name in pinsets[master],(master,name)
   assert pinsets[master][name]['direction']==direction,(master,name,direction)
   checked+=1
out=dict(schema='opentallas.cb16.safe_endpoint_plan.v1',diagnostic_only=True,source=g['source'],logical_data_edges=len(g['edges']),logical_bank_edges=sum(e['kind']=='bank'for e in g['edges']),physical_bus_bindings=len(bindings),bank_data_bits=sum(v['bits']for v in bindings if v['kind']=='bank_data'),written_flag_bits=sum(v['bits']for v in bindings if v['kind']=='written_flags'),native_pin_references_checked=checked,unqualified_endpoints=unqualified,native_pin_assets=assets,bindings=bindings,release_ready=False,blockers=['requires CP legal placement plus actual pin-to-pin obstacle-avoiding405um route checks','A0/boundary and xstn safe pin snapshots still missing','clock roots/native phase compensation and local hold paths not composed','written flags explicitly ordinary timing, not bank-data window','reset/epoch/compiler fullfabric result not yet adopted'])
Path(a.out).write_text(json.dumps(out,indent=1)+'\n');print('SAFE_ENDPOINT_PLAN',len(bindings),'buses',out['bank_data_bits'],'bankbits',out['written_flag_bits'],'writtenflags')
