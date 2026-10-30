from pathlib import Path
import json,hashlib
b=Path('/srv/opentallas-scratch2/claude/codex-collft-ff4-0336');t='coll_ft__cla4a25d77';k=b/'gen'/t/t;a=json.load(open(b/'anchors_nf40lowtap.json'))
assert len(a['anchors'])==11645 and len(a['protected'])==54
old=(k/'nf40low_anchors.tcl').read_text();functions='proc nf_name'+old.split('proc nf_name',1)[1]
assert 'NF occupied reserved footprint before GPL' in functions and 'setPlacementStatus PLACED' in functions
lines=['# FF4 PLACE-only: complete post-PRE_GLOBAL FF2 ODB non-target FIRM/LOCKED/COVER and hardblock census.', 'set nf_anchors {}','set nf_protected {}']
for q in a['anchors']:
 x,y=q['origin_um'];nm='{'+q['name'].replace('\\','')+'}'
 lines.append(f'dict set nf_anchors {nm} [list {x} {y} {q["reserved_width_um"]}]')
for q in a['protected']:
 x,y=q['origin_um'];nm='{'+q['name'].replace('\\','')+'}'
 lines.append(f'dict set nf_protected {nm} [list {x} {y}]')
(k/'nf40low_anchors.tcl').write_text('\n'.join(lines)+'\n'+functions)
p=json.load(open(b/'plan/plan_collft_nf40lowtap.json'))
for n in a['stats']:p['partition_types'][t]['clock']['landing_contract']['bands'][n]['ring_place']='ff'
pp=b/'plan/plan_collft_ff4.json';pp.write_text(json.dumps(p,indent=1)+'\n');(k/'PLAN_SHA').write_text(hashlib.sha256(pp.read_bytes()).hexdigest()+'\n')
identity={}
for f in (b/'native_source/rtl').glob('*.sv'):
 q=k/'rtl'/f.name;identity['rtl/'+f.name]=hashlib.sha256(f.read_bytes()).hexdigest();assert f.read_bytes()==q.read_bytes(),f
for n in ['constraint.sdc','pins.json','land_slots.json']:
 f=b/'native_source'/n;assert f.read_bytes()==(k/n).read_bytes(),n
 identity[n]=hashlib.sha256(f.read_bytes()).hexdigest()
assert json.load(open(k/'lec/lec.json'))['verdict']=='EQUIVALENT'
assert len(list((k/'run/results').glob('**/3_2_place_iop.odb')))==1
assert not list((k/'run/results').glob('**/3_3_place_gp.odb'))
fixed={}
for line in (b/'census/fixed_sites.tsv').read_text().splitlines():
 fs=line.split('\t');fixed[fs[0].replace('\\','')]=fs
for q in a['protected']:
 fs=fixed[q['name'].replace('\\','')];assert abs(float(fs[3])-q['origin_um'][0])<.001 and abs(float(fs[4])-q['origin_um'][1])<.001,q
receipt={'scope':'PLACE-only physical candidate; no route authority. Original138START/reset, pinmax163.26, clocks remain HOLD.', 'anchors':11645,'protected':54,'fixed_census_records':len(fixed),'excluded_only_moving_anchors':11645,'hardblocks':0,'outline_um':[786.24,993.6],'reserved_fraction':.4,'rtl_sdc_pin_identity':identity,'native_equivalence':'FF2 native21356/21356, exact RTL and pins/SDC/land_slots byteidentical','native_source':'intel1:/srv/opentallas-scratch2/claude/codex-collft-0336/gen_nf40low_ff2/coll_ft__cla4a25d77/coll_ft__cla4a25d77','render_review':'Personally viewed planned_ff4.png PASS-COND for isolated PLACE only; pinp9025.26, unreg0, collapse0; old-comb col_v3.624 is not routed prediction.'}
(k/'physical_resume.json').write_text(json.dumps(receipt,indent=1)+'\n');(b/'review.json').write_text(json.dumps(receipt,indent=1)+'\n')
print('FF4_SOURCE_READY',len(identity),'identical artifacts',len(fixed),'fixedrecords')
