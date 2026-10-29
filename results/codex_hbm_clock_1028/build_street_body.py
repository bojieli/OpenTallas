import sys,json,hashlib,time
from pathlib import Path
R0=Path(__file__).parent
R=R0/'street_body'
R.mkdir(exist_ok=True)
sys.path.insert(0,str(R0/'tools/die_plan'))
import die_trial as D
D.DME_WORKERS=8
import adaptive_detour_v2 as adaptive_detour,fast_tap_clear,body_sites
body_contract=body_sites.install(D)
fast_tap_clear.install(D.S)
adaptive_stats=adaptive_detour.install(D)
oldtree=R0/'street_body/NO_PRIOR_TAPS.json'
if oldtree.exists():
 old=json.loads(oldtree.read_text())
 D.clock_taps=lambda P:[(t['part'],t['tap'],*t['xy']) for t in old['taps']]
 print('REUSE same C25b generated tap list',len(old['taps']),flush=True)
cal={'leg':[11.034201,0.169972,0.000058,7.001714],'tap':[0.03644737,0.00013425],'basis':'HBM trial2b routed TT early legs LSQ, CLK-MODEL-SWEEP-1; tap fit TT routed3274legs RMS1.89ps'}
(R/'stage_cal.json').write_text(json.dumps(cal,indent=1))
D.load_stage_cal(R/'stage_cal.json')
P=D.S.Plan(D.S.load(sys.argv[1]),Path(sys.argv[1]))
reg=json.load(open('/srv/opentallas-scratch2/claude/die-hbm-9/c21_part_region.json'))['part_region']
# C23 split PHY_N W/C/E copies PHY_N region; same local source, phase only estimate.
for p in P.parts:
 if p.startswith('PHY_N') and p not in reg:reg[p]=reg.get('PHY_N','T060')
prior=json.loads((R0/'corrected/meta.json').read_text())['site_legal']['balance']['region_dme']
snake_regions={k for k,v in prior.items() if v['spread']>120}|{'T019','T003'}
print('ZERO SKEW DME regions',sorted(snake_regions),flush=True)
print('BUILD START',time.time(),flush=True)
_orig_taps=D.clock_taps
def taps_logged(P):
 print('TAPS START',time.time(),flush=True)
 v=_orig_taps(P)
 print('TAPS DONE',len(v),time.time(),flush=True)
 return v
D.clock_taps=taps_logged
_orig_attach=D.attach_region_dme
def attach_logged(*args,**kwargs):
 print('DME START',time.time(),flush=True)
 v=_orig_attach(*args,**kwargs)
 print('DME DONE',time.time(),flush=True)
 return v
D.attach_region_dme=attach_logged
nd,segs,legs,meta=D.clock_kit(P,R/'clock',200,180,site_legal=True,site_slide=True,regions=reg,tree_form='link_htree',tree_opts={'feed':'/srv/opentallas-scratch2/claude/die-hbm-9/c21_feed.json'},clock_rc='1x',region_dme='delay',region_dme_snake=snake_regions,region_dme_early=1.0,region_dme_early_ff=0.8639019524013111,region_dme_early_mode='merge',clock_cell='inv2',cell_paths=True)
(R/'adaptive_stats.json').write_text(json.dumps(adaptive_stats,indent=1))
(R/'meta.json').write_text(json.dumps(meta,indent=1))
(R/'body_contract.json').write_text(json.dumps(body_contract,indent=1))
print('BUILD DONE cells',meta['site_legal']['cells'],'wire_um',meta['wire_um'],flush=True)
