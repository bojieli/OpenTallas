#!/usr/bin/env python3
"""Model-only QCOLL partition budget. Fail closed on unknown pin/logic ownership."""
import argparse,hashlib,json,math,re
from pathlib import Path
A=argparse.ArgumentParser();A.add_argument('--root',default='.');A.add_argument('--die',required=True);A.add_argument('--out',required=True);a=A.parse_args();r=Path(a.root)
s=json.loads((r/'physical/ref_tile/qfd_io_collective_s4/spec.json').read_text());d=json.loads(Path(a.die).read_text());inst={i['n']:i for i in d['insts']};master=d['masters'];blocks=[]
for x in s['children']+s['macros']:
 le=next((r/x['view']).glob('*.lef'));z=re.search(r'SIZE\s+([\d.]+)\s+BY\s+([\d.]+)',le.read_text());ww,hh=map(float,z.groups());blocks.append(dict(name=x['inst'],kind='fold' if 'fold' in x['view'] else 'sram',x=x['at'][0],y=x['at'][1],w=ww,h=hh,orient=x['orient']))
leaves=[]
def leaf(n,ff,x,y,w,h,face='WE'):
 # Reserve5.4um at each faceend for clock/reset/control access.
 L=h if face=='WE' else w;leaves.append(dict(name=n,ff=ff,x=x,y=y,w=w,h=h,data_face=face,conservative_two_track_pin_cut=ff*.096/(L-10.8),root=n+'_ck',extra_data_edges=0,abi='candidate_only_source_logic_partition_required'))
leaf('input',547,345.6,928.8,129.6,21.6,'SN')
for q,xx in enumerate([43.2,194.4,529.2,680.4]):
 leaf('outq'+str(q),138 if q==0 else 132,xx,885.6,129.6,64.8,'SN');z=leaves[-1];z['data_face']='W/E/S inputs,N output';z['data_input_bits']=768;z['data_output_bits']=128;z['control_input_allowance']=20;z['input_face_bits']={'W':256,'E':256,'S':256};z['conservative_two_track_pin_cut']=256*.096/(64.8-10.8);z['abi']='phase3localoutput128 complete6wayreduce/gatherdatamux,PK/tfv/tfoFF,outputcapture;metadataquarter0only;exactfinalsourceABIrequired'

for n,y,ff in [('srr0',43.2,547),('sx0',183.6,547),('drr',324,515),('ur',464.4,515),('dpr',604.8,547),('up',745.2,547)]:leaf(n,ff,820.8,y,21.6,129.6)
for n,y in [('srr2',194.4),('sx2',334.8),('srr1',475.2),('sx1',615.6)]:leaf(n,547,21.6,y,21.6,129.6)
for q,y in enumerate([75.6,291.6,507.6,723.6]):leaf('lohi'+str(q),258,540,y,43.2,64.8)
for q,y in enumerate([151.2,367.2,583.2,799.2]):leaf('pf'+str(q),130,540,y,32.4,43.2)
leaf('xr',512,291.6,399.6,21.6,129.6)
for q,y in enumerate([75.6,291.6,615.6,756]):leaf('tbc'+str(q),219 if q<3 else 218,291.6,y,43.2,64.8)
leaf('tab',220,540,221.4,43.2,64.8);leaf('tef',165,540,437.4,43.2,54);leaf('tde',72,540,653.4,32.4,32.4);leaf('controller',200,291.6,550.8,43.2,54)
for q,y in enumerate([43.2,259.2,475.2,691.2]):leaf('xfselect'+str(q),16,54,y,21.6,21.6)
leaf('pringselector',20,540,199.8,21.6,21.6);leaf('rringselector',20,540,702,21.6,21.6)
root_order=['input','up','dpr','sx0','sx1','sx2','srr0','srr1','srr2','xr','ur','drr','outq0']+['lohi'+str(q)for q in range(4)]+['pf'+str(q)for q in range(4)]+['tbc'+str(q)for q in range(4)]+['tab','tde','tef']+['xfselect'+str(q)for q in range(4)]+['pringselector','rringselector','outq1','outq2','outq3']
for z in leaves:z['root']='clk'if z['name']=='controller'else'clk_local['+str(root_order.index(z['name']))+']'
allb=blocks+leaves;over=[]
for k,x in enumerate(allb):
 for y in allb[k+1:]:
  if min(x['x']+x['w'],y['x']+y['w'])>max(x['x'],y['x'])+1e-6 and min(x['y']+x['h'],y['y']+y['h'])>max(x['y'],y['y'])+1e-6:over.append([x['name'],y['name']])
def pins(i,p):
 ii=inst[i];mm=master[ii['m']];rr=[]
 for z in mm['pins']:
  base=z['name'].split('[')[0]
  if base!=p:continue
  box=z['rect'];xx=(box[0]+box[2])/2;yy=(box[1]+box[3])/2;o=ii['o']
  if o in ['MY','R180']:xx=ii['w']-xx
  if o in ['MX','R180']:yy=ii['h']-yy
  ix=re.search(r'\[(\d+)\]',z['name']);rr.append((int(ix[1])if ix else 0,ii['x']+xx,ii['y']+yy))
 return sorted(rr)
inc=[]
for b in d['buses']:
 if not any(e[0]=='io_collective'for e in b['e']):continue
 eps=[(e,pins(*e))for e in b['e']];miss=[e for e,ps in eps if not ps];mx=0;bad=0;checked=0
 if not miss:
  for e,ps in eps[1:]:
   src=eps[0][1]
   if len(src)!=len(ps)and len(src)!=1 and len(ps)!=1:miss.append(['cardinality',len(src),len(ps)]);continue
   for k in range(max(len(src),len(ps))):
    p=src[min(k,len(src)-1)];q=ps[min(k,len(ps)-1)];v=abs(p[1]-q[1])+abs(p[2]-q[2]);mx=max(mx,v);bad+=v>500;checked+=1
 inc.append(dict(name=b['b'],declared_bits=b['n'],endpoints=b['e'],checked_pin_pairs=checked,missing=miss,max_manhattan_um=mx,over500=bad,min_500um_segments=math.ceil(mx/500),scope='logicalendpoint lowerbound; existing physicalrelay map and calendar required before violation/adoption claim'))
# Existing source-derived coarsespatial graph is diagnostic only: exact newleaf ABI ispending.
import sys;sys.path.insert(0,str(r/'tools'));import qwen_coll_static_cut as C
cuts=[dict(axis=k,pos=p,bits=b,capacity=c,ratio=u)for k,p,b,c,u in C.analyse(s)]
internal=[]
lm={x['name']:x for x in leaves}
for name in ['srr0','srr1','srr2']:
 z=lm[name]
 for q,y in enumerate([43.2,259.2,475.2,691.2]):
  sx=z['x'] if z['x']>432 else z['x']+z['w'];sy=z['y']+z['h']/2;tx=86.4;ty=y+90.72;length=abs(sx-tx)+abs(sy-ty)
  internal.append(dict(name=name+' to XF'+str(q)+' selector',bits=128,source_candidate_face_um=[sx,sy],fold_source_face_um=[tx,ty],centroid_manhattan_um=length,horizontal_lower_bound_um=abs(sx-tx),requires_extra_physical_stage_or_relayout=abs(sx-tx)>500,exact_allbit_ABI_pending=True))
clock=[]
for m in s['macros']:
 z=next(x for x in blocks if x['name']==m['inst']);local=[z['x']+.012,z['y']+.780];rng=s['pin_ranges'][m['clock_entry']['port']];entry=[sum(rng)/2,s['outline']['h']];clock.append(dict(macro=m['inst'],macro_clock_um=local,current_N_entry_um=entry,current_wire_manhattan_um=abs(entry[0]-local[0])+abs(entry[1]-local[1]),proposed_local_entry_um=local,proposed_entry_is_not_current_parent_face_grant=True))
local_clocks=[]
for z in leaves:
 yy=z['y']+.108+.048*round((z['h']/2-.108)/.048);local_clocks.append(dict(root=z['root'],inst=z['name'],xy_um=[z['x']+.096,(z['y']+90.732 if z['name'].startswith('xfselect')else yy)],face='W',status='newmasterclockfaceREQUEST_only',measured_insertion_ps=None))
for z in blocks:
 if z['kind']=='fold':local_clocks.append(dict(root=z['name']+'_ck',inst=z['name'],xy_um=[z['x']+(82.692 if z['orient']=='MY'else 98.748),z['y']+181.398],face='N',status='existingclosedLEFclockpin_localentryREQUEST',measured_insertion_ps='existingviewinsertion_tobind'))
for z in clock:local_clocks.append(dict(root=z['macro']+'_ck',inst=z['macro'],xy_um=z['macro_clock_um'],face='W',status='actualSRAMLEFclockpin_localentryREQUEST',measured_insertion_ps='rawLibertyreference'))
C.OBS['leaf']={'M3','M4','M5'};bb=C.blocks_of(s)+[(z['name'],'leaf',z['x'],z['y'],z['w'],z['h'])for z in leaves];ff=C.flows(s);newcuts=[]
for axis,L,spans,tr in [('x',s['outline']['h'],sorted({v for z in bb for v in [z[2],z[2]+z[4]]}),C.TR_H),('y',s['outline']['w'],sorted({v for z in bb for v in [z[3],z[3]+z[5]]}),C.TR_V)]:
 spans=sorted(set(spans)|{pt[0 if axis=='x'else 1]for _,_,p,q in ff for pt in [p,q]})
 for pos in [(.5*(a+b))for a,b in zip(spans,spans[1:])]:
  k=0 if axis=='x'else 1;demand=sum(b for _,b,p,q in ff if min(p[k],q[k])<pos<max(p[k],q[k]));cap=sum(C.free_span(bb,lay,pos,axis,L)*t for lay,t in tr.items());newcuts.append(dict(axis=axis,pos=pos,bits=demand,capacity=cap,ratio=demand/cap if cap else 999))
basefine=[];baseblocks=C.blocks_of(s)
for axis,L,tr in [('x',s['outline']['h'],C.TR_H),('y',s['outline']['w'],C.TR_V)]:
 k=0 if axis=='x'else 1;spans=sorted({v for z in baseblocks for v in ([z[2],z[2]+z[4]]if axis=='x'else[z[3],z[3]+z[5]])}|{p[k]for _,_,a,b in ff for p in[a,b]})
 for pos in[(a+b)/2 for a,b in zip(spans,spans[1:])]:
  demand=sum(b for _,b,p,q in ff if min(p[k],q[k])<pos<max(p[k],q[k]));cap=sum(C.free_span(baseblocks,lay,pos,axis,L)*t for lay,t in tr.items());basefine.append(dict(axis=axis,pos=pos,bits=demand,capacity=cap,ratio=demand/cap if cap else 999))
report=dict(schema='opentallas.qcoll.physical_partition_model.v1',qualified=False,adopted=False,scope='Planning budget only;38root inventory per sourceowner newot_coll_tp8_local_roots candidate, not final pinABI; no route and no RTL edits',outer_frame=inst['io_collective'],die_sha256=hashlib.sha256(Path(a.die).read_bytes()).hexdigest(),inner_frame=s['outline'],existing_blocks=blocks,candidate_leaves=leaves,leaf_count=len(leaves),leaf_FF_total=sum(x['ff']for x in leaves),candidate_leaf_area_um2=sum(x['w']*x['h']for x in leaves),existing_block_area_um2=sum(x['w']*x['h']for x in blocks),overlaps=over,leaf_pin_budget_max=max(x['conservative_two_track_pin_cut']for x in leaves),baseline_endpoint_complete_cuts=basefine,baseline_endpoint_complete_worst_cut=max(basefine,key=lambda x:x['ratio']),baseline_coarse_cuts=cuts,baseline_coarse_worst_cut=max(cuts,key=lambda x:x['ratio']),local_clock_entry_requests=local_clocks,proposed_obstacle_coarse_worst_cut=max(newcuts,key=lambda x:x['ratio']),proposed_obstacle_cuts=newcuts,external_incidents=inc,internal_critical_incidents=internal,SRAM_clock_geometry=clock,blockers=['Exact sourceleaf pinABI and muxlogic ownership not final. Genericcapture-only partition leaves xsrc,lo/hi,w_d,rf_d combinationalselection inparent; cannot call wires-only.','E sr0face864 toXF Wface86.4 is777.6um horizontal alone; facecapturetoall4quarterrows also crosses648um spread. Baseline noaddededge partition isnot allincident<=500.','All9current NfaceSRAMclockentries arefar from actualWmacroclockpins; localinteriorentry proposal requires actual topdown hierarchicalclockpin grant or relayout.','Outer4157.976frame includes productiongearbox/faces/relays but has no source-current hardchild home map; internalouterincidentcontinuity cannot be qualified from outerpins alone.','Baseline cutanalysis is coarse existing sourcegraph, not exact proposedleafbitgraph; PG/OBS-aware fullproposed cuts remainrequired.','SourceFF counts differ actualexistingmapped census; candidatecontroller200 is onlymodel allowance, not qualifiedmapped bound.'])
phase_counts={};phase_bad=[]
for z in s['children']+s['macros']:
 text=next((r/z['view']).glob('*.lef')).read_text();ww,hh=map(float,re.search(r'SIZE\s+([\d.]+)\s+BY\s+([\d.]+)',text).groups())
 for pm in re.finditer(r'\bPIN\s+(\S+)\s+(.*?)\n\s*END\s+\1(?:\n|$)',text,re.S):
  name,body=pm.groups()
  if name in ['VDD','VSS']:continue
  for lm in re.finditer(r'LAYER\s+(M[45])\s*;\s*RECT\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)',body):
   lay=lm[1];x0,y0,x1,y1=map(float,lm.groups()[1:]);xx=(x0+x1)/2;yy=(y0+y1)/2
   if z['orient']=='MY':xx=ww-xx
   xx+=z['at'][0]+13633.92;yy+=z['at'][1]+324;val=yy if lay=='M4'else xx;err=abs((val-.012)/.048-round((val-.012)/.048))*.048;phase_counts[lay]=phase_counts.get(lay,0)+1
   if err>1e-5:phase_bad.append(dict(inst=z['inst'],pin=name,layer=lay,error_um=err))
report['actual_closed_view_signal_phase']={'origin_um':[13633.92,324],'scope':'ALL17existingchildLEF M4/M5signalrectcenters includingclocks,actualMYtransform;PG/otherlayersnotincluded','counts':phase_counts,'bad':phase_bad,'pass':not phase_bad}
report['candidate_inner_origin_request']={'offset_in_outer_um':[1641.6,302.4],'absolute_um':[13633.92,324.0],'source':'compute lead explicit candidate request; not grantedadoption','orientation':'R0','phase_preserves_048um_tracks':True}
report['global_clock_entry_requests']=[dict(z,global_xy_um=[z['xy_um'][0]+13633.92,z['xy_um'][1]+324.0])for z in local_clocks]
report['global_child_home_requests']=[dict(z,global_at_um=[z['x']+13633.92,z['y']+324.0])for z in blocks+leaves]
Path(a.out).write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:report[k]for k in ['leaf_count','leaf_FF_total','candidate_leaf_area_um2','overlaps','leaf_pin_budget_max','baseline_coarse_worst_cut']}));print('external_missing',sum(bool(x['missing'])for x in inc),'external_over500',sum(x['over500']for x in inc))
