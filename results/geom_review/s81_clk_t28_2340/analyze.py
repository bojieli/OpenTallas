import json,sys,pathlib,copy,hashlib
r=pathlib.Path('/srv/opentallas-scratch/claude/codex-s81-clk-t28-2340');sys.path.insert(0,'/home/ubuntu/OpenTallas/tools/die_plan');import schema as S,gen_phys as G,taps as T
from placement_obstacles import placement_boxes
p=json.load(open(r/'plan_source39_deadrefreshed.json'));tn='col_h10_r0_p1__t1__cl574cc59d';d=json.load(open(r/'clk_t28_failure_census.json'));P=S.Plan(p);typ=P.types[tn];assigned=[q for q in d['sink_rows'] if q['tap']=='clk_t28'];uv=lambda q:(q['x']+q['y'],q['x']-q['y']);us,vs=zip(*[uv(q) for q in assigned]);R=200
intersection={'u':[max(us)-R,min(us)+R],'v':[max(vs)-R,min(vs)+R],'exact_minimum_radius_um':max(max(us)-min(us),max(vs)-min(vs))/2}
old=next(t for t in typ['clock']['added_taps'] if t['name']=='clk_t28')['xy'];new=list(G._snap_tap(P,1126.44,958.5));assert new==[1126.432,958.496]
boxes=placement_boxes(typ,halo=S.TAP_CLEAR_UM);point_hits=[n for n,b in boxes.items() if b[0]<new[0]<b[2] and b[1]<new[1]<b[3]];assert not point_hits
# Native BUFx24 body (largest current clock driver), centred at new point; no extra halo beyond canonical8.64.
body=[new[0]-.81,new[1]-.135,new[0]+.81,new[1]+.135];body_hits=[n for n,b in boxes.items() if body[0]<b[2] and body[2]>b[0] and body[1]<b[3] and body[3]>b[1]];assert not body_hits
u,v=sum(new),new[0]-new[1];assert intersection['u'][0]<=u<=intersection['u'][1] and intersection['v'][0]<=v<=intersection['v'][1]
sinks=[(q['x'],q['y'],q['weight']) for q in d['sink_rows']];baseline=[(q['name'],q['x'],q['y']) for q in d['taps']];candidate=[(n,*new) if n=='clk_t28' else(n,x,y) for n,x,y in baseline]
load,far,asg=T.assign(candidate,sinks,1500,200,max_distance_um=200);bad=[{'tap':n,'load':load[i],'radius':far[i]} for i,(n,x,y) in enumerate(candidate) if (i>=16 and(not load[i] or load[i]>1500 or far[i]>200+1e-6))];assert not bad,bad
oldasg=[next(i for i,t in enumerate(d['taps']) if t['name']==q['tap']) for q in d['sink_rows']]
orig_typ=copy.deepcopy(typ)
for t in typ['clock']['added_taps']:
 if t['name']=='clk_t28':t['xy']=new
# Native canonical geometry check, all40 nodes and all87 reuse/body/halo obstacles.
actual=T.grid_explicit_sites(P,tn);assert len(actual)==40;assert [x[0] for x in actual]==[x[0] for x in baseline]
consumed=[(n,*G._snap_tap(P,x,y)) for n,x,y in actual];cload,cfar,casg=T.assign(consumed,sinks,1500,200,max_distance_um=200)
cbad=[{'tap':n,'load':cload[i],'radius':cfar[i]} for i,(n,x,y) in enumerate(consumed) if i>=16 and(not cload[i] or cload[i]>1500 or cfar[i]>200+1e-6)];assert not cbad,cbad
report={'status':'MODEL_PASS_FOR_SOURCE_CLOCK_EVENT','type':tn,'tap':'clk_t28','old_xy_um':old,'new_xy_um':new,'source_plan_sha256':hashlib.sha256((r/'plan_source39_deadrefreshed.json').read_bytes()).hexdigest(),'source_census_sha256':hashlib.sha256((r/'clk_t28_failure_census.json').read_bytes()).hexdigest(),'assigned_sink_count':len(assigned),'all_sink_rows':len(sinks),'l1_feasible_intersection_at_200':intersection,'canonical_obstacles_with8_64halo':len(boxes),'point_or_driver_body_obstacle_hits':point_hits+body_hits,'nominal_BUFx24_body_um':body,'consumed_pin_is_same_as_declaration':new==list(G._snap_tap(P,*new)),'unchanged_clock_nodes':39,'clock_node_count':40,'added_source_FF':0,'added_edges':0,'added_cycles':0,'changed_sink_nearest_assignment':sum(a!=b for a,b in zip(oldasg,asg)),'tap28_load_radius_raw':[load[28],far[28]],'tap28_load_radius_consumed':[cload[28],cfar[28]],'all_added_taps_pass':not bad and not cbad,'all_taps':[{'name':n,'xy_um':[x,y],'load':load[i],'radius_um':far[i],'consumed_load':cload[i],'consumed_radius_um':cfar[i]} for i,(n,x,y) in enumerate(candidate)],'obstacles':[{'name':n,'rect_um':list(b)} for n,b in boxes.items()],'current_assigned_sink_rows':assigned,'reset_relay_count_before':len(d['reset_relays']),'reset_after_recompute':'pending exact native RT/sink model check; original edges/count must remain'}
(r/'repair_model.json').write_text(json.dumps(report,indent=1)+'\n');(r/'plan_candidate.json').write_text(json.dumps(p,separators=(',',':'))+'\n');print({k:v for k,v in report.items() if k not in ['all_taps','obstacles','current_assigned_sink_rows']})
