from pathlib import Path
import json,math,copy,collections,re,types,importlib.util
p=Path('/home/ubuntu/coord/tmp/codex-xrt-compact-alt-0445');src=Path('/home/ubuntu/coord/tmp/codex-xrt-compact-0414');old=json.loads((src/'source/pins.json').read_text());event=json.loads((src/'disabled_event.json').read_text());parents=json.loads((src/'parent_occurrences.json').read_text());rt=json.loads((src/'source/native_rows_taps.json').read_text());W,H=207.36,194.4;groups=collections.defaultdict(list);new=[]
for q in old:
 if q['bus']!='clk':groups[q['face']].append(q)
for face,items in groups.items():
 axis='y' if face in 'WE' else 'x';dim=H if face in 'WE' else W;items.sort(key=lambda q:q[axis]);prev=-1
 m2=sorted({round(row*.27+phase,6) for row in range(int(H/.27)+1) for phase in [.045,.081,.117,.153,.189,.225] if 4.32<=row*.27+phase<=H-4.32})
 for i,q in enumerate(items):
  ly=('M2' if i%2 else 'M4') if face in 'WE' else q['layer'];goal=4.32+(dim-8.64)*(i+.5)/len(items)
  if ly=='M2':t=min(m2,key=lambda x:abs(x-goal))
  else:pitch=.036 if ly=='M3' else .048;off=.009 if ly=='M3' else .012;t=off+round((goal-off)/pitch)*pitch
  assert t>prev+1e-6,(face,i,t,prev);prev=t
  q={k:v for k,v in q.items() if k not in ['native_rects','x','y']};q['layer']=ly
  q.update(x=round(.0315 if face=='W' and ly=='M2' else .042 if face=='W' else W-.0315 if face=='E' and ly=='M2' else W-.042 if face=='E' else t,6),y=round(.0315 if ly=='M3' and face=='S' else .042 if face=='S' else H-.0315 if ly=='M3' and face=='N' else H-.042 if face=='N' else t,6));new.append(q)
new.append(dict(bus='clk',bit=None,face='C',layer='M5',x=103.692,y=97.2,shape_um=[.048,.48]))
name=lambda q:q['bus']+(f"[{q['bit']}]" if q['bit'] is not None else '')
assert len(new)==len(old)==7563 and {name(q) for q in new}=={name(q) for q in old}
old_by={name(q):q for q in old};new_by={name(q):q for q in new};changed=[]
for q in new:
 n=name(q);oq=old_by[n]
 if q['layer']!=oq['layer']:changed.append(dict(name=n,old_layer=oq['layer'],new_layer=q['layer'],face=q['face']))
 if n!='clk':assert q['face']==oq['face']
for f,a in groups.items():
 axis='y' if f in 'WE' else 'x';assert [name(q) for q in a]==[name(q) for q in sorted([q for q in new if q['face']==f],key=lambda q:q[axis])]
sp=importlib.util.spec_from_file_location('G','/home/ubuntu/OpenTallas/tools/autopilot/geom_rules.py');G=importlib.util.module_from_spec(sp);sp.loader.exec_module(G);actual=G.Design('/home/ubuntu/coord/tmp/codex-s81-xrt-l4-2235/xrt/current_geom.tsv');nativemap={q['name']:q for q in actual.pins}
for q in new:q['io']=nativemap[name(q)]['io'];q['sig']=nativemap[name(q)]['sig']
assert set(nativemap)=={name(q) for q in new}|{'VDD','VSS'}
pincheck=G.pin_metrics(types.SimpleNamespace(die=(0,0,W,H),pins=[dict(name=name(q),sig=q['sig'],layer=q['layer'],x=q['x'],y=q['y']) for q in new]),re.compile('^strap_'))
assert pincheck['pin_peak_layer_max']<=6,pincheck
# Same-layer physical pitch and pin-rectangle spacing, checked independently of density.
spacing={}
for f in 'WENS':
 for ly in ['M2','M3','M4','M5']:
  a=sorted([q['y'] if f in 'WE' else q['x'] for q in new if q['face']==f and q['layer']==ly]);
  if len(a)<2:continue
  delta=min(y-x for x,y in zip(a,a[1:]));assert delta>=(.036 if ly in ['M2','M3'] else .048)-1e-6
  spacing[f+'/'+ly]=dict(pins=len(a),minimum_pitch_um=round(delta,6),peak_pins_per_um_10um=pincheck['pin_peak_layer'][f+'/'+ly],peak_window=pincheck['pin_peak_layer_win'][f+'/'+ly])
clock=[103.692-.024,97.2-.24,103.692+.024,97.2+.24];bay=[102.06,96.12,104.004,98.28]
inter=lambda a,b:a[0]<b[2]-1e-9 and a[2]>b[0]+1e-9 and a[1]<b[3]-1e-9 and a[3]>b[1]+1e-9
pg=json.loads((p/'actual_PG_alt_bay.json').read_text());hits=[z for z in pg['region_pg_shapes'] if z['layer'] in ['M3','M4','M5'] and inter(z['rect_um'],bay)];assert not hits;assert pg['unknown_count']==0
thits=[x for x in rt['taps'] if inter([x['x'],x['y'],x['x']+.108,x['y']+.270],bay)];assert not thits
m2rails=[z for z in pg['region_pg_shapes'] if z['layer']=='M2' and inter(z['rect_um'],bay)]
# IO signal stubs are <=0.084um deep; unchanged PG is confined to core+actual enclosures.
via_max=max(abs(v/1000) for rs in pg['via_shapes'].values() for ly,r in rs for v in r)
assert via_max<.2;edge_clearance=4.32-via_max-.084;assert edge_clearance>4
for x in parents:
 c=x['hard_core'];n=copy.deepcopy(c);n.update(outline_um=[W,H],origin_um=[round(c['origin_um'][0]+51.84,6),round(c['origin_um'][1]+99.36,6)],activation=False);x['disabled_proposed_hard_core']=n;x['origin_rule']='old+[51.84,99.36]um, both4.32multiples; retain oldbox sidegaps51.84/51.84/99.36/101.52; orientation/track_offset unchanged'
 x['proposed_parent_type_clock_entry_um']=[round(n['origin_um'][0]+103.692+c.get('track_offset_um',[0,0])[0],6),round(n['origin_um'][1]+97.2+c.get('track_offset_um',[0,0])[1],6)]
event.update(status='DISABLED_ALTERNATIVE_REVIEW_ONLY',enabled=False,outline_um=[W,H],core_um=[4.32,4.32,W-4.32,H-4.32],outline_manhattan_upper_bound_um=W+H,disabled_parent_origin_shift_um=[51.84,99.36],same_face_layer_except_clock=False,explicit_layer_event='W/E alternating physical-order bits M4/M2 (unchanged actual allowedM2-M5 routing); clock M4E→M5C. N/S layers unchanged.',same_port_identity_and_bit_order=True,preliminary_core_utilization_pct=100*event['native_bbox_area_um2']/((W-8.64)*(H-8.64)),clock_entry=dict(port='clk',layer='M5',xy_um=[103.692,97.2],shape_um=[.048,.48],driver_bay_um=bay,driver_bay_status='planned and old-native PG/TAP clear; NEW normalFP actualmaster/row/TAP/PG qualification mandatory'),pin_density_exact_sliding_10um=pincheck,capacity=spacing,layer_changes=changed,pg=dict(basis='Native retainedDEF whole-design counts and exact explicit via RECTs, oldactual proposedbay PG geometry, unchanged PDN/coremargin analyticaledgeclearance; NEWnormalFP PG not yet built',native_source_sha256=pg['source_sha256'],unknown_native_patterns=pg['unknown_count'],native_counts=pg['counts'],actual_via_max_extent_um=via_max,analytical_signal_stub_edge_PG_clearance_lower_bound_um=edge_clearance,driver_bay_M3_M4_M5_obstructions=hits,driver_bay_M2_followpin_shapes=len(m2rails),M2_bay_note='Ordinary PG followpin rails are present under row-based cell sites; not incorrectly treated as emptyPG. Signal clock entry/trunks M5/M3/M4 avoid upperPG.',TAP_bay_conflicts=thits,M2_IO_track_phases_um=[.045,.081,.117,.153,.189,.225],M2_IO_boundary_rail_phase_excluded=True,postFP_native_all_master_PG_audit_required=True),row_tap_prep=dict(retained_native_rows=len(rt['rows']),retained_native_TAPs=len(rt['taps']),new_core_site_columns=3680,new_core_rows=688,site_um=[.054,.270],new_native_inventory_required=True),release_holds=['Explicit ROOT alternative footprint+M2data/M5clock+all14parent-pin event review before ONE normalFP','all native newPG/ROW/TAP/access/congestion/clock and subsequent actualLOOK gates remain; no production/adoption/count','Old216x172.8 unchanged-layer report remains preserved HOLD; this alternative does not alter its verdict'])
for n,d in [('disabled_event.json',event),('proposed_signal_pins.json',sorted(new,key=name)),('parent_occurrences.json',parents),('pin_density.json',pincheck),('layer_changes.json',changed)]: (p/n).write_text(json.dumps(d,indent=2))
print(json.dumps({'outline':[W,H],'upper_bound':W+H,'changed_layers':len(changed),'density':pincheck['pin_peak_layer'],'spacing':spacing,'upperPGbay':len(hits),'M2PG_followpin_shapes':len(m2rails),'TAPbay':len(thits),'preliminary_util':event['preliminary_core_utilization_pct']},indent=2))
