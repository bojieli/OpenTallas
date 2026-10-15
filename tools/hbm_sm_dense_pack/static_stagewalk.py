#!/usr/bin/env python3
"""Place actual six-edge staticnorth graph; candidatehardleafdimensions, no timingclaim."""
import json,pathlib,re,hashlib,collections
R=pathlib.Path('/home/ubuntu/wt/hbm-smcompact-1014');O=pathlib.Path('results/hbm_sm_dense_pack');W,H=25.92,43.2
left=2843.76;col=[left+20+i*(W+20)for i in range(7)]
# col0 northrowW, col1 reservedcontrol21.6, col2..5 data, col6 northrowE.
# Keep controlcolumn same25.92width for explicitslack and regularpitch.
roots=[];D={}
for s in range(8):
 for stage,j,y in [('wl1',4+s%2,10+63.2*(s//2)),('wm2',2+s%2,10+63.2*(s//2)),('w0_3',2+s%2,350+63.2*(s//2)),('fx4',4+s%2,350+63.2*(s//2)),('Wa4',2+s%2,602.8+63.2*(s//2)),('Ea4',4+s%2,602.8+63.2*(s//2)),('Wm5',2+s%2,855.6+63.2*(s//2)),('Em5',4+s%2,855.6+63.2*(s//2)),('Wo6',2+s%2,1108.4+63.2*(s//2)),('Eo6',4+s%2,1108.4+63.2*(s//2))]:
  b=dict(name=f'{stage}_{s}',stage=stage,slice=s,x=col[j],y=y,w=W,h=H,bits=256,real_clock_roots=1,status='NEW_PURE_FF_MASTER_NEEDS_PHYSICAL_GATE');roots.append(b);D[(stage,s)]=b
for arm,j in [('W',0),('E',6)]:
 for stage,y in [(1,350),(2,750)]:
  b=dict(name=f'row0{arm}{stage}',x=col[j],y=y,w=W,h=103.68,bits=818,real_clock_roots=1,status='NEW_PURE_FF_MASTER_NEEDS_PHYSICAL_GATE');roots.append(b);D[(arm,stage)]=b
for i,b in enumerate(roots):
 for a in roots[:i]:
  gap=max(a['x']-b['x']-b['w'],b['x']-a['x']-a['w'],a['y']-b['y']-b['h'],b['y']-a['y']-a['h']);assert gap>=20-1e-5,(b['name'],a['name'],gap)
edges=[]
def add(name,a,b):
 edges.append(dict(net=name,source=a,destination=b,manhattan=abs(a[0]-b[0])+abs(a[1]-b[1])))
def pin(b,bit,out=False):return [b['x']+(b['w']if out else 0),b['y']+(9.36 if b['bits']==256 else 12.624)+.096*bit]
for s in range(8):
 for a,b in [('wl1','wm2'),('wm2','w0_3'),('w0_3','fx4'),('w0_3','Wa4'),('w0_3','Ea4'),('Wa4','Wm5'),('Ea4','Em5'),('Wm5','Wo6'),('Em5','Eo6')]:
  for bit in range(256):add(f'{a}_{s}[{bit}]->{b}',pin(D[(a,s)],bit,True),pin(D[(b,s)],bit))
gap=7*W+6*20+40;east=left+gap;upper=342.4+609.92+80
rin_slots=sorted([(80+.128*i,'M6')for i in range(500)]+[(80+.16*i,'M8')for i in range(500)])[:818]
for arm,x in [('W',left),('E',east)]:
 for bit in range(2048):add(f'{arm}o6[{bit}]->upperbin',pin(D[(arm+'o6',bit//256)],bit%256,True),[x,upper+140+.16*bit])
 for bit in range(818):
  add(f'row0{arm}1[{bit}]->2',pin(D[(arm,1)],bit,True),pin(D[(arm,2)],bit))
  add(f'row0{arm}2[{bit}]->upperrin',[*pin(D[(arm,2)],bit,True)],[x,upper+rin_slots[bit][0]])
# ActualXL inherited fx_b andfo_row0 pins, R0 atproposedserviceorigin.
xl=R/'results/arch/hbm_native_1013/sm/inherited_views/ot_hbm_accel_smh_fc_xl/ot_hbm_accel_smh_fc_xl.lef';t=xl.read_text();P={}
for n,b in re.findall(r'  PIN (\S+)\n(.*?)  END \S+\n',t,re.S):
 m=re.search(r'RECT\s+(\S+) (\S+) (\S+) (\S+)',b)
 if m:
  x0,y0,x1,y1=map(float,m.groups());P[n]=[2880+(x0+x1)/2,10+(y0+y1)/2]
for bit in range(2048):add(f'fx4[{bit}]->XL',pin(D[('fx4',bit//256)],bit%256,True),P[f'fx_b[{bit}]'])
for arm in ['W','E']:
 for bit in range(818):add(f'XLrow0[{bit}]->{arm}1',P[f'fo_row0[{bit}]'],pin(D[(arm,1)],bit))
by=collections.defaultdict(list)
for e in edges:by[e['net'].split('[')[0]].append(e['manhattan'])
maxima={k:max(v)for k,v in by.items()};assert max(maxima.values())<500,max(maxima.items(),key=lambda a:a[1])
smw=5707.52+gap-20;smh=1652.24
out={'verdict':'STAGEWALK84_ROOT_GEOMETRY_AND_PAYLOAD_PINREACH_PASS_NEW_MASTERS_UNQUALIFIED','existing_north_cycles':6,'added_north_cycles':0,'data256_roots':80,'row818_north_roots':4,'roots':roots,'connections':edges,'maximum_external_um':max(maxima.values()),'maxima_by_source':maxima,'central_gap_um':gap,'control_column_reserved':[col[1],0,W,1652.24],'service_strip_um':322.4,'interband_gap_um':80,'upper_band_y':upper,'SM_field_price_only':{'width_um':smw,'height_um':smh,'area_mm2':smw*smh/1e6,'all32_mm2':smw*smh*32/1e6},'actualXL_PIN_source':str(xl.relative_to(R)),'actualXL_PIN_sha256':hashlib.sha256(xl.read_bytes()).hexdigest(),'limits':['84rootoutlinesnew,25.92wide256/818 pureFFmasters needactualCTS/holdgate.','Programme/feed/results/control and4southrowroots not placed; sourcecontrolcolumn reserved butnocountorqualificationinferred.','Sevenlegacyfrontmastersnotpackedhere: lower-strip actualpinprobe failsXL/XR/PB witholdfaces.','ProposedXLorigin2880,10 mayconflictlegacyfrontplacements; onlyactualpinreach to/fromnorthgraphproven.','818upperrin endpoints are explicit two-trackM6/M8 proposedtilePORTslots; sourcebitordering andclockcalendar stillneedintegration.','EveryactualD/Qinternalreach,PG/clockcuts,TTsetup FFhold DRC0 remainopen.']}
(O/'static_stagewalk.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps({k:out[k]for k in ['verdict','maximum_external_um','central_gap_um','SM_field_price_only']},indent=2))
