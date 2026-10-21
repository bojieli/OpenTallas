#!/usr/bin/env python3
"""Model additional real corridors within the owner's full26000x33000 reticle.

No RTL, block outline, bus width or clock constraint changes. Begin from dM's
orientation/pgp/xload corrections. Added cuts separate both SU row pairs and
open both sides of the outer xq stacks. Exact S4 must price the new routes.
"""
import copy,json,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
base=ROOT/'results/arch/hbm_release_r16_1021/plandM'
out=Path(sys.argv[1]);out.parent.mkdir(parents=True,exist_ok=True)
step=dict(plan='R16_E_FULL_RETICLE',why='Owner10-21 drops500um margin; real SU row and outer xq corridors, no squeeze',
 bands=[dict(name='all',y0=-1e9,y1=1e9,cuts=[[3950.,129.6],[4800.,129.6],[20300.,129.6],[21170.,129.6]])],
 ycuts=[[12480.,259.2],[19980.,259.2]])
spec=out.parent/'cut_spec_eM.json';spec.write_text(json.dumps(step,indent=1)+'\n')
subprocess.run([sys.executable,str(ROOT/'tools/hbm_die_v16/d4g_channel_cuts.py'),'--spec',str(spec),
 '--grants',str(base/'grants_d4g.json'),'--plan',str(base/'compact.P.json'),'--lanes',str(base/'lanes.json'),
 '--region-map',str(base/'d4g_region_map.json'),'--out',str(out)],check=True)
cm=json.load(open(base/'coord_map.json'));cm['spec']['steps'].append(step)
cm['r16_full_reticle']=dict(by='CODEX-DIE13:40',added_step=step['plan'])
(out/'coord_map.json').write_text(json.dumps(cm,indent=1)+'\n')
g=json.load(open(out/'grants_d4g.json'));g0=json.load(open(base/'grants_d4g.json'))
policy=dict(owner='10-21~08:45',allowed_die_um=[26000.,33000.],allowed_mm2=858.,external_margin_required_um=0.,
 seal_ring='approximately0.1mm INSIDEoutline; no further guesseddimension subtraction',
 evidence='/home/ubuntu/.claude/projects/-home-ubuntu-OpenTallas/memory/owner-full-reticle-1021.md')
g['floorplan']['owner_reticle_policy']=policy
(out/'grants_d4g.json').write_text(json.dumps(g,indent=1)+'\n')
w,h=g['floorplan']['die_um'];w0,h0=g0['floorplan']['die_um']
assert max(w,h)<=33000 and min(w,h)<=26000
before={s['name']:s['outline'] for s in g0['slots'] if s.get('kind')!='die'}
after={s['name']:s['outline'] for s in g['slots'] if s.get('kind')!='die'}
assert before==after,'blockshape/inventory changed'
model=dict(status='GEOMETRY_MODEL_ONLY',policy=policy,source_base='367859fca/dM',before_die_um=[w0,h0],die_um=[w,h],
 before_mm2=w0*h0/1e6,die_mm2=w*h/1e6,area_delta_pct=100*(w*h/(w0*h0)-1),
 remaining_lattice_slack_um=[26000-w,33000-h],block_shapes_changed=0,compute_storage_inventory='unchanged',
 added_vertical_corridors=step['bands'][0]['cuts'],added_horizontal_corridors=step['ycuts'],
 static_latency='No cycle claim. ActualGEN/S4 required to price every moved source/sink and relay/landing',
 remaining='S4 hop/capacity mustPASS; exactnewSU S2 source reuse thenstrictbind/clockreset/STA/IR, no failedgeometryroute')
(out/'full_reticle_model.json').write_text(json.dumps(model,indent=1)+'\n')
print('FULL_RETICLE_MODEL',json.dumps(model))
