#!/usr/bin/env python3
"""Measured N remaining windows: physical SVG/XQ/SFU and injection corridors."""
import hashlib,json,shutil,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];base=ROOT/'results/arch/hbm_release_r16_1021/plannM'
out=Path(sys.argv[1]);out.mkdir(parents=True,exist_ok=True)
manifest=Path(sys.argv[2]);report=Path(sys.argv[3]);actual=json.load(open(manifest))['placement'];failure=json.load(open(report))
assert (failure['hop_violations'],failure['capacity']['forced'],failure['capacity']['windows']['over_1'])==(30,205,13)
for f in base.iterdir():
 if f.is_file() and f.name not in ['plan.png','report.json']:shutil.copyfile(f,out/f.name)
g=json.load(open(out/'grants_d4g.json'));p=json.load(open(out/'compact.P.json'));slots={s['name']:s for s in g['slots']};sm=dict(x.split('=') for x in (out/'slot_map.txt').read_text().strip().split(','));moves={};grids=[]
def home(n,x,y,w=None,h=None):
 a=actual[n];sn=sm.get(n,n)
 if sn not in slots:
  sn='corridor_'+n;sl=dict(name=sn,cell=a['m'],kind='tile',parent='die',outline=dict(w=a['w'],h=a['h']),origin=dict(x=x,y=y,orient=a['o']),pins=[],pin_status='FACES_ONLY',notes='Exact current source/body explicit delivery corridor; no CLOSED/source promotion')
  g['slots'].append(sl);slots[sn]=sl;sm[n]=sn
 else:slots[sn]['origin'].update(x=x,y=y)
 moves[n]=dict(a,x=x,y=y,w=a['w'] if w is None else w,h=a['h'] if h is None else h)
for r in range(8):
 for q in ['SW','NW']:
  n=f'svg_{q}{r}';a=actual[n];s=slots[sm[n]];w=round(a['w']+129.6,6);h=a['h'];x=round(a['x']-64.8,6)
  assert abs((w-345.6)*(h-216)-(a['w']-216)*(a['h']-216))<.001
  home(n,x,a['y'],w,h);s['outline']=dict(w=w,h=h)
  cx,cy=round((w-345.6)/2,6),round((h-216)/2,6)
  s['reserved_channels']=[dict(kind='feedthrough_relay_column',x_um=[cx,round(cx+345.6,6)],y_um=[0,h],owner='die',master_keepout='hard placement + M5/M6 route'),dict(kind='feedthrough_relay_row',x_um=[0,w],y_um=[cy,round(cy+216,6)],owner='die',master_keepout='hard placement + M5/M6 route')]
  s['notes']='Die-owned future physical geometry obligation776.304x646.92/345.6x216cross; exact same4solidquadrants/usablearea. SYNTH reservation only, no473or646view alias. Hardened body must implement actual matching keepouts.'
  grids.append(dict(instance=n,old=[a['w'],a['h']],new=[w,h],old_usable=(a['w']-216)*(h-216),new_usable=(w-345.6)*(h-216)))
  xc=f'xc_{q}{r}';vm=f'vmks_{q}{r}'
  home(xc,round(actual[xc]['x']-64.8,6),round(a['y']+108,6))
  home(vm,round(actual[vm]['x']+64.8,6),round(a['y']+453.6,6))
for n,x,y in [('fs_SW',9363.6,2073.6),('fs_NE',15120.,30952.8),('fs_SE',15120.,1998.),('sfault_SE',15055.2,2049.6),('refcfg_SW',9200.4,2073.6),('sfault_SW',9276.,2073.6),('refcfg_NW',9200.4,30866.4),('sfault_NW',9276.,30866.4),('wbc_SE',15260.4,1414.8),('wbc_SW',10702.8,1414.8)]:home(n,x,y)
for q in ['SE','NE']:
 y=actual[f'xq_{q}_p1_bfq0']['y'];dy=-432 if q=='SE' else 432
 for r in range(4):home(f'xq_{q}_p1_bfq{r}',[20888.928,21688.128][r%2],round(y+(r//2)*dy,6))
 n=f'xq_{q}_p1_eg';home(n,round(actual[n]['x']+306.72,6),round(actual[n]['y']+(172.8 if q=='SE' else -172.8),6))
home('sfucore_NE',round(actual['sfucore_NE']['x']-86.4,6),actual['sfucore_NE']['y'])
for q in ['SW','SE','NW','NE']:
 n='cij_'+q;home(n,round(actual[n]['x']+(-86.4 if q in ['SW','NW'] else 86.4),6),actual[n]['y'])
assert len(moves)==73
new=dict(actual,**moves);checks=[];generated=set()
for n,a in moves.items():
 bad=[];rehome=[]
 for k,b in new.items():
  if k==n:continue
  dx=min(a['x']+a['w'],b['x']+b['w'])-max(a['x'],b['x']);dy=min(a['y']+a['h'],b['y']+b['h'])-max(a['y'],b['y'])
  if dx>.001 and dy>.001:
   if n=='sfucore_NE' and k.startswith('sfr_NE') and b['rule'].startswith('relay chain '):rehome.append(k);generated.add(k)
   else:bad.append(k)
 assert not bad,(n,bad)
 if not n.startswith('svg_'):assert (a['m'],a['w'],a['h'],a['o'])==tuple(actual[n][k] for k in ['m','w','h','o'])
 checks.append(dict(instance=n,before=actual[n],after=a,fixed_body_overlaps=bad,old_generated_SFR_contacts_require_actual_GEN_replan=rehome))
model=dict(status='PHYSICAL_GEOMETRY_MODEL_NOT_CAPACITY_OR_FULL_PLACEMENT_PASS',base_source='017b32285/N',input_sha256={str(f):hashlib.sha256(f.read_bytes()).hexdigest() for f in [manifest,report]},actual_failure=dict(hops=30,forced=205,windows=13,dominant=failure['capacity']['windows']['worst'][:5]),die_um=g['floorplan']['die_um'],placement_checks=checks,SVG_future_physical_obligation=grids,usable_area_delta=0,generated_SFR_old_coordinates_not_reused=sorted(generated),SFU_NE_gap_um=dict(old=222.912,new=309.312),cij='All4 exact216x432 injectionjoin bodies moveoutward86.4 fromCOLL. Westjoins moveW toopenEface; Eastjoins moveE (Efacealreadyopen, Wsidepreviouslyabutted). Same master/source/ports/clocks, no HIDXsource/clock alias.',source='Same74 exactS2 inputs/actualH/fullreticle; HC4359 mapping candidate not adopted; currentHC23/24 remains',rtl_changes=0,guard_changes=0,cycle_credit=0,WBK='Oldbody only; c9 source/native/actualarea qualification separate',required='StrictactualGEN rehomes generatedSFR and validates every placement/pin, P/Q, S4 capacity; no failedgeometry route; actualnext source/newview must satisfy reservedcross obligation')
model['future_unadopted_qcore_obligation']=dict(source='4dd9 plus frozen10 overlays',new_body_um=[302.4,280.8],current_body_um=[actual['sucore_NE']['w'],actual['sucore_NE']['h']],status='ONE route approved/publisherguard pending, NOT CLOSED. Preserve current N qcore source/params; future compatible CLOSED source/body/clock upgrade needs explicit new homes/GEN, never alias old slot.')
g['floorplan']['r16o_corridors']=model
g['floorplan']['selected_geometry_model']='r16o_corridors; corridor_model.json (other copied model JSONs are historical lineage only)'
for fn,d in [('grants_d4g.json',g),('compact.P.json',p),('corridor_model.json',model)]: (out/fn).write_text(json.dumps(d,indent=1)+'\n')
(out/'slot_map.txt').write_text(','.join(k+'='+v for k,v in sorted(sm.items()))+'\n')
print('CORRIDOR_MODEL73 fixed_non_generated0overlap; actualSFRreplan',len(generated),'GENmandatory; no usablearea reduction')
