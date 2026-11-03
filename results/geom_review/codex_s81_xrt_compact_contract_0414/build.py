import json,math,hashlib,collections,subprocess
from pathlib import Path
p=Path('/home/ubuntu/coord/tmp/codex-xrt-compact-0414');s=p/'source'
read=lambda n:json.loads((s/n).read_text())
a=read('pins.json');plan=read('current_plan.json');conns=read('current_core_conns.json');pg=read('old_actual_PG_in_new_outline.json')
W,H=216.,172.8;new=[];groups=collections.defaultdict(list)
for q in a:
 if q['bus']=='clk':continue
 groups[q['face']].append(q)
for face,items in groups.items():
 dim=H if face in 'WE' else W;axis='y' if face in 'WE' else 'x';items=sorted(items,key=lambda q:q[axis]);prev=-1
 for i,q in enumerate(items):
  ly=q['layer'];pitch=.036 if ly=='M3' else .048;offset=.009 if ly=='M3' else .012
  goal=4.32+(dim-8.64)*(i+.5)/len(items)
  t=offset+round((goal-offset)/pitch)*pitch
  if t<prev+.035999:t=offset+math.ceil((prev+.036-offset)/pitch)*pitch
  assert t<=dim-4.32,(face,t)
  prev=t;r={k:v for k,v in q.items() if k not in ['native_rects','x','y']}
  r.update(x=round(.042 if face=='W' else W-.042 if face=='E' else t,6),y=round(.0315 if ly=='M3' and face=='S' else .042 if face=='S' else H-.0315 if ly=='M3' and face=='N' else H-.042 if face=='N' else t,6))
  r['event']='compact_footprint_data_reset_repack';new.append(r)
new.append(dict(bus='clk',bit=None,layer='M5',x=108.012,y=86.4,face='INTERIOR',shape_um=[.048,.48],event='explicit_required_M5_centre_entry'))
name=lambda q:q['bus']+(f"[{q['bit']}]" if q['bit'] is not None else '')
assert len(new)==len(a)==7563 and {name(x) for x in a}=={name(x) for x in new}
old_by={name(x):x for x in a};new_by={name(x):x for x in new}
for face,items in groups.items():
 ax='y' if face in 'WE' else 'x';assert [name(x) for x in sorted(items,key=lambda q:q[ax])]==[name(x) for x in sorted([q for q in new if q['face']==face],key=lambda q:q[ax])]
for q in new:
 if q['bus']=='clk':continue
 old=old_by[name(q)];assert old['face']==q['face'] and old['layer']==q['layer']
# The new normal PDN does not exist yet. Project only the retained rule and actual
# native via-enclosure lattice into the reduced core, excluding obsolete outer PG.
core=[4.32,4.32,W-4.32,H-4.32];projected=[]
for z in pg['region_pg_shapes']:
 r=z['rect_um']
 if z['kind']=='stripe':
  r=[max(r[0],core[0]-.06),max(r[1],core[1]-.06),min(r[2],core[2]+.06),min(r[3],core[3]+.06)]
 elif not(core[0]<= (r[0]+r[2])/2<=core[2] and core[1]<=(r[1]+r[3])/2<=core[3]):continue
 if r[0]>=r[2] or r[1]>=r[3]:continue
 projected.append(dict(z,rect_um=r))
def overlaps(r,b):return r[0]<b[2]-1e-9 and r[2]>b[0]+1e-9 and r[1]<b[3]-1e-9 and r[3]>b[1]+1e-9
bay=[106.38,85.32,109.62,87.48]
bay_hits=[z for z in projected if overlaps(z['rect_um'],bay)]
assert not bay_hits
clock=[108.012-.024,86.4-.24,108.012+.024,86.4+.24]
assert not [z for z in projected if z['layer']=='M5' and overlaps(z['rect_um'],clock)]
edge_shapes=[]
for q in new:
 if q['bus']=='clk':continue
 ly=q['layer'];x,y=q['x'],q['y'];w,h=((.084,.024) if ly=='M4' else (.018,.063) if ly=='M3' else (.024,.084));edge_shapes.append((name(q),ly,[x-w/2,y-h/2,x+w/2,y+h/2]))
# All projected M3-M5 PG lies >=4.26um from die edges; edge stubs <=.084um deep.
edge_pg=[z for z in projected if z['rect_um'][0]<.084 or z['rect_um'][2]>W-.084 or z['rect_um'][1]<.084 or z['rect_um'][3]>H-.084]
assert not edge_pg
capacity={}
for face in 'WENS':
 for ly in ['M3','M4','M5']:
  items=[q for q in new if q['face']==face and q['layer']==ly]
  if not items:continue
  ax='y' if face in 'WE' else 'x';coord=sorted(q[ax] for q in items);pitch=.036 if ly=='M3' else .048
  capacity[face+'/'+ly]=dict(pins=len(items),track_pitch_um=pitch,min_same_layer_spacing_um=round(min(b-a for a,b in zip(coord,coord[1:])),6),usable_tangent_um=(H if face in 'WE' else W)-8.64)
parents=[]
for typ,t in plan['partition_types'].items():
 for c in t.get('hard_cores',[]):
  if c.get('module')!='ot_s81sl_xrt1':continue
  occ=[x for x in plan['partitions'] if x['type']==typ]
  refs={k:v for k,v in conns.get(typ,{}).items() if k==c['inst'] or 'core:'+c['inst'] in str(v)}
  parents.append(dict(type=typ,parent_outline_um=t['outline_um'],hard_core=c,die_occurrences=occ,core_conn_references=refs,required_future_event=['child outline and pins_file replacement','all parent child-pin coordinates / M5 interior clock target regenerated from same table','real child view and measured parent timing/clock contract refreshed','hard-core bounding-box/residual-space/clock/reset/PG gates rerun; no old proof or latency transfer']))
event=dict(schema='opentallas.disabled_physical_contract_event.v1',enabled=False,status='PREP_REVIEW_ONLY_NO_CAD',module='ot_s81sl_xrt1',top_params={'FOREG':0},source_rtl_changed=False,frequency_mhz=1200.4801920768308,period_ps=833,added_cycles=0,old_outline_um=[311.04,395.28],outline_um=[W,H],core_um=core,all_BTerm_count=7565,signal_BTerm_count=7563,pg_BTerms=['VDD','VSS'],port_identity='All exact old signal names/bits retained; PG names retained by unchanged standard PDN',same_face_layer_except_clock=True,bus_and_global_face_pin_order_preserved=True,clock_entry=dict(port='clk',layer='M5',xy_um=[108.012,86.4],shape_um=[.048,.48],old=dict(layer='M4',face='E',xy_um=[310.998,196.572]),driver_bay_um=bay,driver_bay_status='planned preGPL reserve; native new ROW/TAP/PG and exact entry-cell legality mandatory after normal FP; not empty-TAP assertion'),native_timing_cell_count=98537,native_bbox_area_um2=14221.259999999998,preliminary_core_utilization_pct=100*14221.26/((W-8.64)*(H-8.64)),utilization_caveat='preliminary actual old timing-cell area/new core only; new TAP/clock cells/fill/congestion not priced',outline_manhattan_upper_bound_um=W+H,old_actual_reach=dict(captures=19224,max_um=683.29,captures_gt405=1152,comb_loops=0),current_timing_references_only=dict(TT_pinreg_mean_ps=370.67,FF_pinreg_mean_ps=305.53,transfer_allowed=False),pg=dict(basis='Retained actual DEF widths/explicit via RECTs plus unchanged PDN rule and reduced CORE boundary. Analytical projection, not native new-stage PG proof.',native_source_sha256=pg['source_sha256'],unknown_native_patterns=pg['unknown_count'],native_counts=pg['counts'],native_shapes_in_new_outline=len(pg['region_pg_shapes']),projected_shapes=len(projected),driver_bay_M3_M4_M5_obstructions=bay_hits,edge_signal_stub_PG_obstructions=edge_pg,standard_rule_unchanged=True,postFP_native_all_master_PG_audit_required=True),capacity=capacity,parent_type_count=len(parents),parent_occurrence_count=sum(len(x['die_occurrences']) for x in parents),canonical_parent_commit=subprocess.check_output(['git','-C','/srv/opentallas-scratch/claude/wt/codex-s81-nearmiss-2036','rev-parse','origin/main'],text=True).strip(),canonical_plan_sha256=hashlib.sha256((s/'current_plan.json').read_bytes()).hexdigest(),source_identities={n:hashlib.sha256((s/n).read_bytes()).hexdigest() for n in ['config.mk','freeze.json','pins.json','constraint.sdc','pdn.tcl','make_tracks.tcl']},release_holds=['ROOT review and footprint/clock/pin-event scope before normal FP','no GEN/FP/PLACE/route dispatched or activated','no new mapped FF count, physical PG/row/tap/clock/route/signoff/proof claim'])
(p/'disabled_event.json').write_text(json.dumps(event,indent=2));(p/'proposed_signal_pins.json').write_text(json.dumps(sorted(new,key=name),indent=2));(p/'parent_occurrences.json').write_text(json.dumps(parents,indent=2));(p/'projected_PG_bay.json').write_text(json.dumps([z for z in projected if z['rect_um'][0]<114 and z['rect_um'][2]>102 and z['rect_um'][1]<92 and z['rect_um'][3]>80],indent=2));print(json.dumps({'capacity':capacity,'parent_types':len(parents),'parent_occurrences':sum(len(x['die_occurrences']) for x in parents),'PG_bay_hits':len(bay_hits),'projected_shapes':len(projected)},indent=2))
