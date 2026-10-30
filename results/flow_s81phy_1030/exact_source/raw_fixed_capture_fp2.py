"""Literal proposed noninverting DATA repeater model, with actual mapped source inversion.
No RTL generation, inferred repair, physical qualification or extra cycles.
"""
import json,sys,math
from pathlib import Path
R=Path(__file__).parent;sys.path.insert(0,str(R/'tool_snapshot/tools/die_plan'))
from die_clock_128 import _bilin
LIB=json.load(open(R/'stage_lib.json'))['corners']
def data(c,length,inslew,pol,kind='start',fanout=1,spacing=80,local_um=1.0,native=False):
 lib=LIB[c]['cells'];source='INVx1_ASAP7_75t_R' if kind=='start' else 'INVx3_ASAP7_75t_R';buf='BUFx8_ASAP7_75t_R';end='DFFHQNx1_ASAP7_75t_R' if native else 'DFFLQNx1_ASAP7_75t_R';n=max(1,math.ceil(length/spacing));q='fall' if pol=='rise' else 'rise';slew=inslew;total=0.;mx=0.;receipts=[]
 # Source INV drives one dedicated first buffer per outgoing edge; raw kept
 # BUF2 receiver is an additional genuine mapped local load, not imaginary.
 own=lib[buf]['cap_ff']*fanout+(lib['BUFx2_ASAP7_75t_R']['cap_ff'] if kind=='raw' else 0.)
 steps=[('DFFHQNx1_ASAP7_75t_R',local_um,lib[source]['cap_ff'],pol), (source,fanout*3.0,own,q)]
 steps += [(buf,length/n,lib[end if i==n-1 else buf]['cap_ff'],q) for i in range(n)]
 for cell,wire,cap,p in steps:
  cw=wire*.187*1.7;rw=wire*.0125096;el=rw*(cw/2+cap)
  d=_bilin(lib[cell]['cell_'+p],slew,cw+cap);s=_bilin(lib[cell][p+'_transition'],slew,cw+cap)
  total+=d+el;slew=math.hypot(s,2.2*el);mx=max(mx,slew);receipts.append(dict(master=cell,wire_um=wire,load_ff=cw+cap,delay_ps=d+el,slew_ps=slew))
 return total,mx,receipts

import count_align_plan as CA
v=json.load(open(R/'exact_actual_buffered_ca_fp2.json')); em=json.load(open(R/'edge_map0.json'));checks=[]
for q in v['start_checks']:
 native=q['path'] in {z['path'] for z in json.load(open(R/'native_emit_contract_fp2.json'))['stages'] if z['kind']=='native_origin'}
 if native:continue
 ivs=[];fivs=[];cs={}
 for c,z in q['details'].items():
  vals=[data(c,z['wire_um'],s,p,'raw',fanout=4,spacing=100,native=not em[q['path']]) for s in [5,80] for p in ['rise','fall']]
  dl=min(x[0] for x in vals)*.95;dh=max(x[0] for x in vals)*1.1011
  cl=z['phase_ps'][0]+z['data_ps'][1];ch=z['phase_ps'][1]+z['data_ps'][0]
  fl=z['fall_phase_ps'][0]+z['data_ps'][1];fh=z['fall_phase_ps'][1]+z['data_ps'][0]
  ivs.append([cl-dh,ch-dl]);fivs.append([fl-dh,fh-dl]);cs[c]=dict(raw_data_ps=[dl,dh],max_slew_ps=max(x[1] for x in vals))
 e=dict(lo=min(x[0] for x in ivs),hi=max(x[1] for x in ivs),fall_lo=min(x[0] for x in fivs),fall_hi=max(x[1] for x in fivs),d_ps=0.)
 # FALL sampling boundary is shifted by833/2; ca_pair_interval fall gives edge arrival component only.
 # Evaluate existing fixed capture choice, rather than select a new raw edge.
 lo,hi=(e['fall_lo'],e['fall_hi']) if em[q['path']] else (e['lo'],e['hi'])
 if em[q['path']]:lo+=416.5;hi+=416.5
 # Integer sample counts are unambiguous only if the entire interval remains
 # farther than canonical104.125ps from every833ps sampling boundary.
 dist=min(abs(lo-round(lo/833)*833),abs(hi-round(hi/833)*833))
 clean=math.floor((lo-104.125)/833)==math.floor((hi+104.125)/833)
 checks.append(dict(path=q['path'],fixed_edge='fall' if em[q['path']] else 'rise',interval_ps=[lo,hi],boundary_distance_ps=dist,clean=clean,corners=cs))
out=dict(scope='Proposed RAW DATA recipe with actual INV3+keptBUF2 load; conservativefourfanout, SAME fixed START capture edge; nativeglobalreset excluded unchanged. PureNLDM/CA MODEL ONLY',count=len(checks),all_clean=all(q['clean'] for q in checks),min_distance_ps=min(q['boundary_distance_ps'] for q in checks),max_slew_ps=max(z['max_slew_ps'] for q in checks for z in q['corners'].values()),checks=checks,build_allowed=False)
(R/'raw_fixed_capture_fp2.json').write_text(json.dumps(out,indent=1)+'\n');print({k:v for k,v in out.items() if k!='checks'})
