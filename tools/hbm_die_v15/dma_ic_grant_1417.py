#!/usr/bin/env python3
"""New source-specific diagnostic DMA leaves from actual immutable LEF bit rectangles."""
import hashlib,json,re,subprocess,tempfile,sys,copy
from pathlib import Path
R=Path(__file__).resolve().parents[2];sys.path.insert(0,str(R/'tools'));import hbm_die_views as V
REF='c3d44471d';source='rtl/hbm_accel/generic/peers/static/ot_hgi_dma_back_static_vp4_ic.sv';data=subprocess.check_output(['git','show',REF+':'+source],cwd=R)
items=[('bank','ot_hgi_dma_back_landing_bank_ic','native_bank_nl1','ot_hgi_dma_back_landing_bank'),('controller','ot_hgi_dma_back_static_vp4_controller_ic','controller','ot_hgi_dma_back_static_vp4_controller')];masters={}
for kind,top,folder,oldtop in items:
 f=Path('/home/ubuntu/artifacts/hbm-dma-native-1417')/folder/'record/views'/oldtop/(oldtop+'.lef');s=f.read_text();w,h=map(float,re.search(r'SIZE\s+(\S+) BY (\S+) ;',s).groups());pins=[]
 for name,direction,layer,rect in re.findall(r'  PIN (\S+)\s+DIRECTION (\S+) ;.*?LAYER (\S+) ;\s+RECT\s+([^;]+);',s,re.S):
  if direction not in ('INPUT','OUTPUT'):continue
  x0,y0,x1,y1=map(float,rect.split());x=(x0+x1)/2;y=(y0+y1)/2
  face='W' if x0==0 else 'E' if abs(x1-w)<1e-6 else 'S' if y0==0 else 'N' if abs(y1-h)<1e-6 else None
  assert face,(name,rect);pins.append(dict(name=name,direction=direction,face=face,layer=layer,centre_um=[round(x,6),round(y,6)],offset=round(y if face in 'WE' else x,6),rect_um=[x0,y0,x1,y1],offset_pending_view=False))
 with tempfile.TemporaryDirectory() as td:
  tf=Path(td)/'ic.sv';tf.write_bytes(data);ports=V.L.parse_module(str(tf),top)['ports']
 expected={f'{n}[{i}]' if width>1 else n for n,(_,width) in ports.items() for i in range(width)};assert expected=={p['name'] for p in pins},(top,len(expected),len(pins),expected-{p['name'] for p in pins})
 masters[kind]=dict(cell=top,source=source,source_sha256=hashlib.sha256(data).hexdigest(),source_prerequisite=REF,outline=dict(w=w,h=h),pins=pins,assigned_pin_file=str(f),assigned_pin_file_sha256=hashlib.sha256(f.read_bytes()).hexdigest(),pin_provenance='NEW diagnostic assignment of literal per-bit rectangles measured in immutable old-source routed LEF; actual IC ODB must match. This does not inherit old source timing or physical qualification.',mapped_area_um2=None,mapped_FF=None,clock_entry=dict(port='clk',face=next(p['face'] for p in pins if p['name']=='clk'),offset=next(p['offset'] for p in pins if p['name']=='clk'),delivery='Related same-phase entry phi minus independently measured insertion R; no ideal internal clock or inherited qualification.'))
slots=[]
for b in range(8):slots.append(dict(masters['bank'],name=f'dma_bank_ic{b}_diagnostic',parent='dma_ic_461p2x305p68_PLANNING_ONLY',origin=dict(x=(b%3)*160.4,y=(b//3)*108.56,orient='R0')))
slots.append(dict(masters['controller'],name='dma_controller_ic_diagnostic',parent='dma_ic_461p2x305p68_PLANNING_ONLY',origin=dict(x=320.8+(140.4-75.6)/2,y=217.12+(88.56-75.6)/2,orient='R0'),params=dict(STK=0,QID=0,STACK_BYTES=22500000000,MUT=0)))
for i,a in enumerate(slots):
 for b in slots[i+1:]:assert a['origin']['x']+a['outline']['w']<=b['origin']['x'] or b['origin']['x']+b['outline']['w']<=a['origin']['x'] or a['origin']['y']+a['outline']['h']<=b['origin']['y'] or b['origin']['y']+b['outline']['h']<=a['origin']['y']
out=dict(schema='opentallas.hier_contract.v1',die='hbm_v15',version=5,clock_period_ps=833.333,slots=slots,diagnostic_only=True,qualification=False,canonical_die_contract_mutated=False,production_binding_adopted=False,parent_candidate_outline_um=dict(w=461.2,h=305.68),current_parent_outline_um=dict(w=432,h=360.72),parent_home='UNASSIGNED: candidate width exceeds current parent by29.2um; no current parent footprint or incident pin/clock/PG qualification adopted',native_contract=dict(launch_ps_max=220,capture_ps_max=190,spread_ps_max=80,TT_setup='>=0',FF_hold='>=0',DRC=0,SS='sensitivity only'),source_cost=dict(bank_added_declared_FF=272,controller_added_declared_FF=23,SRAM_edge_delta=1,VM_issue_lead_delta=1,read_prefetch_lead_edges=2),scope='NEW diagnostic exact-bit leaf grant, not inherited historical child adoption. Source MAIN/MIRROR proof and compiler early command contract required. Eight independent bank roots plus controller root. Parent all incident transport, clocks and current-die placement OPEN.')
p=R/'results/arch/hbm_die_v15/dma_ic_grants_1417.json';p.write_text(json.dumps(out,indent=1)+'\n');print(json.dumps({'masters':{k:len(v['pins']) for k,v in masters.items()},'slots':len(slots),'qualified':False}))
