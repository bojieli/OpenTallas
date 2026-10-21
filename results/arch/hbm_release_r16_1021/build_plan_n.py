#!/usr/bin/env python3
"""Actual M failure: separate XQ queues and keep SVG relay crosses available."""
import hashlib,json,shutil,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
base=ROOT/'results/arch/hbm_release_r16_1021/planmM';out=Path(sys.argv[1]);out.mkdir(parents=True,exist_ok=True)
manifest=Path(sys.argv[2]);report=Path(sys.argv[3]);actual=json.load(open(manifest))['placement'];failure=json.load(open(report))
assert (failure['hop_violations'],failure['capacity']['forced'],failure['capacity']['windows']['over_1'])==(27,224,17)
for f in base.iterdir():
 if f.is_file() and f.name not in ['plan.png','report.json']:shutil.copyfile(f,out/f.name)
g=json.load(open(out/'grants_d4g.json'));p=json.load(open(out/'compact.P.json'));slots={s['name']:s for s in g['slots']}
sm=dict(x.split('=') for x in (out/'slot_map.txt').read_text().strip().split(','));moves={}
def home(n,x,y):
 a=actual[n];sn=sm.get(n,n)
 if sn not in slots:
  sn='side_'+n
  sl=dict(name=sn,cell=a['m'],kind='tile',parent='die',outline=dict(w=a['w'],h=a['h']),origin=dict(x=x,y=y,orient=a['o']),pins=[],pin_status='FACES_ONLY',notes='Exact existing source and actual body; explicit home outside die relay cross; no physical closure promotion.')
  g['slots'].append(sl);slots[sn]=sl;sm[n]=sn
 else:slots[sn]['origin'].update(x=x,y=y)
 moves[n]=dict(a,x=x,y=y)
for i in range(8):
 for q in ['SW','NW']:
  svg=actual[f'svg_{q}{i}'];box=p[f'pc_{q}{i}']
  # Extra 10.8um on the left avoids the two actual WBC fixed leaves.
  for pref,x in [('xc_',box['x']+15.12),('vmks_',svg['x']+svg['w']+32.4)]:
   home(f'{pref}{q}{i}',round(round(x/.216)*.216,3),round(svg['y']+216,3))
for i in range(8):home(f'vmdel_SW{i}',[12101.4,12403.8][i%2],round(11415.6+151.2*(i//2),3))
for q in ['SW','NW']:
 y=actual[f'xq_{q}_p0_bfq0']['y'];dy=-432 if q=='SW' else 432
 for i in range(4):home(f'xq_{q}_p0_bfq{i}',[3920.4,4719.6][i%2],round(y+(i//2)*dy,6))
 eg=f'xq_{q}_p0_eg';home(eg,actual[eg]['x'],round(actual[eg]['y']+(172.8 if q=='SW' else -172.8),6))
assert len(moves)==50
new=dict(actual,**moves);checks=[]
for n,a in moves.items():
 bad=[]
 for k,b in new.items():
  if k==n:continue
  dx=min(a['x']+a['w'],b['x']+b['w'])-max(a['x'],b['x']);dy=min(a['y']+a['h'],b['y']+b['h'])-max(a['y'],b['y'])
  if dx>.001 and dy>.001:bad.append(k)
 assert not bad,(n,bad)
 assert (a['m'],a['w'],a['h'],a['o'])==tuple(actual[n][k] for k in ['m','w','h','o'])
 checks.append(dict(instance=n,before=actual[n],after=a,actual_box_overlaps=bad))
reuse=Path('/home/ubuntu/artifacts/hdie-d4/codex_ucie_colh_bind_1021/reuse.json');rr=json.load(open(reuse));assert len(rr['reuse'])==74 and not rr['synth']
model=dict(status='SOURCE_PINNED_GEOMETRY_MODEL_NOT_CAPACITY_PASS',base_source='73500aaf0/M',die_um=g['floorplan']['die_um'],input_receipts={str(f):hashlib.sha256(f.read_bytes()).hexdigest() for f in [manifest,report,reuse]},actual_failure=dict(hops=27,forced=224,windows=17,dominant=failure['capacity']['windows']['worst'][:6]),placement_checks=checks,XQ='Four unchanged CLOSED-body queue leaves form2x2 in each actual1500umSM gap; exact egress moves172.8 along same corridor. All additional wire/station depth must be repriced.',SVG='32 actualXC/VMKS bodies side-homed outside exact216cross; same SVG four solid quadrants/usablearea',VMDEL='All8 actual257.04x108 bodies4rows2cols; actualall8equal-age full/pcbad graph, no mask/fanout weakening',source='Same74 exactSYNTH reuse and actualH view; RTL/params/ports unchanged',rtl_changes=0,cycle_credit=0,guard_changes=0,WBK='Current oldbody only; c9 native/functional/measuredarea separate; neveralias',qualification='ActualGEN/PQ/S4 required; noS5route unless strictcapacityPASS; externalclock startup/calendar remainsOPEN')
g['floorplan']['r16n_side_xq']=model
for fn,d in [('grants_d4g.json',g),('compact.P.json',p),('side_xq_model.json',model)]: (out/fn).write_text(json.dumps(d,indent=1)+'\n')
(out/'slot_map.txt').write_text(','.join(k+'='+v for k,v in sorted(sm.items()))+'\n')
print('SIDE_XQ_MODEL50 exactbodies0overlaps; REUSE74/SYNTH0; actualGEN/S4pending')
