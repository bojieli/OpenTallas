import json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'tools/die_plan'))
import form_geometry as g
base=Path(__file__).resolve().parent
t=json.loads((base/'sd_origin_type.json').read_text())
r=g.placement_reservations(t)
for i,p in enumerate(t['reset'].get('local_taps_um',[])):r['reset_local:'+str(i)]=g.grow([*p,*p],2.16)
for q in t['clock']['landing_contract']['collector_tree']['relays']:
 p=q['xy'];r['reset_relay:'+q['name']]=g.grow([*p,*p],2.16)
macro=[17.28,54,1866.24,1026]
a=g.prepare_chain([190.56,19.98],[1876.5,180.09],t['outline_um'],[g.grow(macro,5.0)],4,site_boxes=list(r.values()),reach=405)
a['stage_roles']=['existing origin s0','existing origin s1','existing origin s2','origin pd[0]']
a['endpoint_role']='origin pd[1], selected by PAD2; unused pd[2] remains local'
a['input']='original sf/strap selected s_in -> complete START epoch/control bundle before existing s0; retain original negedge sf selection/reset phase'
a['added_boot_cycles']=2
a['added_cycles']=2
a['note']='Use existing arbitrary-PAD origin form with PADW2/PAD2; two added pd registers, +2 effective boot cycles'
a['route_macro_clearance_um']=5.0
a['source_clock_semantics']='preserve existing named receiving domains including clk_t5 source_latency -80ps; no clock relaxation'
a['reservation_count']=len(r)
a['actual_old_sites_um']={'s0':[107.136,29.43],'s1':[1868.4,125.01],'s2':[1868.4,179.82],'pd':[1868.454,181.44]}
a['proposed_pd1_um']=[1876.5,180.09]
a['sf_site_um']=[189.0,20.25]
a['padw']=2
a['selected_pad']=2
a['unused_pd2_um']=[1876.5,182.52]
a['scope']='candidate only: KV owner implements CA leaf PAD/K phase/ledger proof before adoption; no current plan mutation'
(base/'sd_origin_candidate.json').write_text(json.dumps(a,indent=2)+'\n')
print(json.dumps(a,indent=2))
