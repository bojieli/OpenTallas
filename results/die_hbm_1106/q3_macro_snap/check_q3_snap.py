from pathlib import Path
import importlib.util,json,hashlib
here=Path(__file__).resolve().parent;repo=here.parents[2]
gen=repo/'physical/die_plan/hbm_arch_cores/gen_core_kit_hbm.py'
spec=importlib.util.spec_from_file_location('q3gen',gen);g=importlib.util.module_from_spec(spec);spec.loader.exec_module(g)
recipes=g.load_recipes();key='ot_hfd_coll_q3_edge_link';rec=recipes[key]
assert g.recipe_core_macros_mode(None,rec,key)=='auto'
assert g.recipe_core_macros_mode('off',rec,key)=='off'
assert g.recipe_core_macros_mode('auto',{},'other')=='auto'
assert g.recipe_core_macros_mode(None,{},'other')=='off'
for k,r in recipes.items():
 if k!=key:assert g.recipe_core_macros_mode(None,r,k)=='off',k
try:g.recipe_core_macros_mode(None,{'core_macros':'invalid'},'bad')
except SystemExit:pass
else:raise AssertionError('invalid recipe accepted')
pdir=repo/'physical/die_plan/hbm/plan_of_record/d44v'
placements,source=g.core_macros_placement(pdir/'core_macros.json',key,rec['macros'])
tracks=(here/'inputs/q3_actual_tracks.tcl').read_text();lef=(here/'inputs/q3_actual_macro.lef').read_text()
outline=(276.48,336.96)
fixed,moves=g.snap_macro_placement(placements,tracks,lambda _:lef,outline)
assert len(moves)==4 and all(m['dx_nm']==0 and m['dy_nm']==12 for m in moves),moves
w,h,rects=g.lef_signal_pins(lef,rec['macros'][0]);assert len(rects)==298
assert {r[0] for r in rects}=={'M4'}
def bad(rows):
 count=0;offsets=g.kit_track_offsets(tracks)
 for p in rows:
  x,y=map(g._nm,p['xy_um'])
  for layer,*rect in rects:
   x0,y0,x1,y1=g._oriented(rect,p.get('orient','R0'),w,h)
   direction,pitch,width=g.TECH_TRACK_LAYERS[layer]
   lo,hi=(x+x0,x+x1) if direction=='V' else (y+y0,y+y1)
   count+=not g._on_track(lo,hi,width,pitch,offsets[layer])
 return count
wrong=[dict(p,xy_um=[p['xy_um'][0],p['xy_um'][1]+0.024]) for p in placements]
assert bad(placements)==1192 and bad(fixed)==0 and bad(wrong)==1192
_,default_moves=g.snap_macro_placement(placements,'',lambda _:lef,outline)
assert default_moves==[],default_moves
report=dict(source='existing canonical factory/table with actual failed-kit tracks and LEF',resolution_cases=5,unrelated_recipes_off=len(recipes)-1,signal_rectangles_per_macro=len(rects),before_offtrack=bad(placements),after_offtrack=bad(fixed),wrong24nm_offtrack=bad(wrong),moves=moves,placements=fixed,lef_sha256=hashlib.sha256(lef.encode()).hexdigest(),tracks_sha256=hashlib.sha256(tracks.encode()).hexdigest(),extra_data_cycles=0)
(here/'canonical_snap_actual.json').write_text(json.dumps(report,indent=1)+'\n')
print(json.dumps({k:v for k,v in report.items() if k not in ('placements','moves')},sort_keys=True))
print('CANONICAL_Q3_SNAP PASS: X unchanged; Y+12nm; CLI override retained; ordinary PA/route gates pending')
