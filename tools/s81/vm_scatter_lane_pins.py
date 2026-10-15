#!/usr/bin/env python3
"""Assign actual scatter-lane signals; source ABI must match, no routing claim."""
import argparse,hashlib,json,math,sys
from pathlib import Path
R=Path(__file__).resolve().parents[2];sys.path.insert(0,str(R/'tools'))
import die_port_bind as D
W=H=172.8
FIELDS_IN=[('i_v',1),('i_we',1),('i_row',14),('i_mask',4),('i_data',128),('i_tag',8)]
FIELDS_OUT=[('o_v',1),('o_we',1),('o_addr',9),('o_mask',4),('o_data',128),('o_tag',8)]


def sites(n):
 # Actual ASAP7 M5 tracks; PG stripe keepout matches existing pinplan recipe.
 out=[]
 for k in range(4000):
  x=round(.012+.048*k,3);phase=x%5.4
  if x<2.16 or x>W-2.16 or .18<=phase<=.74:continue
  if not out or x-out[-1]>=.096-1e-6:out.append(x)
 assert len(out)>=n,(len(out),n)
 return [out[min(len(out)-1,int((i+.5)*len(out)/n))] for i in range(n)]


def main():
 global H
 ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--source',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);ap.add_argument('--master',choices=['dsfd_vm_static_scatter_lane','dsfd_vm_static_scatter_b8_out'],default='dsfd_vm_static_scatter_lane');ap.add_argument('--height',type=float,default=172.8);a=ap.parse_args();H=a.height
 module=next(m for m in D.parse_modules(a.source.read_text(),str(a.source)) if m.name==a.master);env=module.env({'DW':128,'LANE':0})
 widths={n:dict(direction=d,bits=module.width(n,env)) for n,(d,_) in module.ports.items()}
 expected={n:dict(direction='input',bits=w*8) for n,w in FIELDS_IN};expected.update({n:dict(direction='output',bits=w*8) for n,w in FIELDS_OUT});expected.update(ck=dict(direction='input',bits=1),rst_n=dict(direction='input',bits=1),fault=dict(direction='output',bits=1))
 assert widths==expected,(widths,expected)
 records={};pins={n:[] for n in widths};table=[]
 for face,fields in [('N',FIELDS_IN),('S',FIELDS_OUT)]:
  ordered=[(name,w*k+i) for k in range(8) for name,w in fields for i in range(w)]
  for (name,bit),x in zip(ordered,sites(len(ordered))):
   pins[name].append((bit,face,'M5',x));table.append((name,bit,face,'M5',x))
 for name,delta in [('ck',-.9),('rst_n',0),('fault',.9)]:
  y=round(.012+.048*round((H/2+delta-.012)/.048),3)
  pins[name].append((0,'W','M4',y));table.append((name,None,'W','M4',y))
 ports={n:dict(bits=widths[n]['bits'],direction=widths[n]['direction'],uniform=False,per_bit=[[face,L,pos,.192] for _,face,L,pos in sorted(pp)]) for n,pp in pins.items()}
 for n,pp in pins.items():assert sorted(q[0] for q in pp)==list(range(widths[n]['bits'])),n
 txt=['# SOURCE-BOUND scatter lane pin option:172.8square; native route/clock proof still required']
 seen=set()
 for n,bit,face,L,pos in table:
  key=(face,L,pos);assert key not in seen;seen.add(key)
  port=n if bit is None else f'{n}[{bit}]';x,y=(pos,H if face=='N' else 0) if face in ['N','S'] else (0,pos)
  txt.append(f'place_pin -pin_name {{{port}}} -layer {L} -location {{{x:.3f} {y:.3f}}} -pin_size {{'+('.024 .192' if L=='M5' else '.192 .024')+'} -force_to_die_boundary')
 checks={}
 for face in ['N','S']:
  vv=sorted(q[4] for q in table if q[2]==face);span=vv[-1]-vv[0]
  assert min(b-a for a,b in zip(vv,vv[1:]))>=.096-1e-6
  checks[face]=dict(bits=len(vv),span_um=span,min_spacing_um=min(b-a for a,b in zip(vv,vv[1:])),one_layer_raw_wire_track_share=len(vv)/(W/.048),native_096_slot_share=len(vv)/(W/.096))
 a.out.mkdir(parents=True,exist_ok=True);(a.out/(a.master+'.tcl')).write_text('\n'.join(txt)+'\n')
 report=dict(schema='opentallas.s81.assigned_pins.v1',master=module.name,case='actual_source_registered_scatter_option_unadopted',outline_um=[W,H],ports=ports,clock_entries={'stream':['ck']},reset_entries=['rst_n'],source_sha256=hashlib.sha256(a.source.read_bytes()).hexdigest(),source=str(a.source),port_bits=sum(q['bits'] for q in widths.values()),checks=checks,
  mapping=('LANE=l:inputrecord k is oldglobal input8*l+k; outputrecord k is oldglobalbankl+4*k' if a.master.endswith('_lane') else 'BANK_BASE=8*g:recordk is bankBANK_BASE+k; separate actual156bitcaptureleaf owns first existingstage, thisleaf owns secondstage'),
  scope='EXACT_SOURCE_PORT_PINS_AND_LOCAL_FACE_CAPACITY_ONLY',open=['Actualflop-to-pin CTS/TT/FF/DRC/nativeviews','Distribution to all four bridge groups requires uniform registered hops and compiler cycle accounting','Global clock/reset phi-R source delivery and sourceprogramfunctional/mutant proofs','Pair/bundle cut capacity including all throughtraffic; localraw trackshare is not aggregatecut proof'])
 (a.out/(a.master+'.json')).write_text(json.dumps(report,indent=1)+'\n');print(json.dumps(dict(port_bits=report['port_bits'],checks=checks,source_sha256=report['source_sha256'])))
if __name__=='__main__':main()
