from pathlib import Path
import json,gzip,collections,sys,importlib.util,math,hashlib,types
r=Path(__file__).resolve().parent;case=r.parent/'recip_place_pg_canary_prep_1102';d=json.loads(gzip.decompress((r/'CURRENT_ODB_STATIC.json.gz').read_bytes()));p=json.loads(gzip.decompress((case/'final_read/PLACE_INVENTORY.json.gz').read_bytes()));cells=p['instances'];seq=d['sequential'];loads=collections.defaultdict(list);drivers=collections.defaultdict(list)
for name,inst in cells.items():
 for pin,role,io,net in inst['signal_iterms']:
  if role=='CLOCK' or not net:continue
  if io=='INPUT':loads[net].append((name,pin))
  elif io=='OUTPUT':drivers[net].append((name,pin))
def isbuf(n):return cells[n]['master'].startswith(('BUFx','INVx'))
def trace(net,direction):
 pending=[(net,[])];seen=set();found=[];bad=[]
 while pending:
  net,path=pending.pop()
  if net in seen:bad.append({'reason':'cycle_or_reconvergence','net':net,'path':path});continue
  seen.add(net);terms=loads[net] if direction=='INPUT' else drivers[net]
  if not terms:bad.append({'reason':'no_terminal','net':net,'path':path});continue
  if direction=='OUTPUT' and len(terms)!=1:bad.append({'reason':'multiple_drivers','net':net,'terms':terms});continue
  for n,pin in terms:
   if n in seq:
    if (direction=='INPUT' and pin!='D') or (direction=='OUTPUT' and seq[n]['pins'][pin]['direction']!='OUTPUT'):bad.append({'reason':'wrong_FF_terminal','instance':n,'pin':pin})
    else:found.append({'instance':n,'pin':pin,'path':path,'master':seq[n]['master']})
   elif isbuf(n):
    want='OUTPUT' if direction=='INPUT' else 'INPUT';nxt=[t for t in cells[n]['signal_iterms'] if t[2]==want]
    if len(nxt)!=1:bad.append({'reason':'buffer_terminal_count','instance':n})
    else:pending.append((nxt[0][3],path+[[n,pin,nxt[0][0]]]))
   else:bad.append({'reason':'combinational_before_boundary_FF','instance':n,'master':cells[n]['master'],'pin':pin})
 return found,bad
rows=[];errors=[]
for name,port in d['ports'].items():
 if name in ['clk','rst_n'] or port['role'] in ('POWER','GROUND'):continue
 found,bad=trace(port['net'],port['direction']);targets={(x['instance'],x['pin']) for x in found}
 if bad or len(targets)!=1:errors.append({'port':name,'targets':found,'errors':bad});continue
 target=found[0];i=seq[target['instance']];cx=(i['box'][0]+i['box'][2])/2;cy=(i['box'][1]+i['box'][3])/2;xy=i['pins'][target['pin']]['xy'];points=[((z['box'][0]+z['box'][2])/2,(z['box'][1]+z['box'][3])/2) for g in port['BPin_groups'] for z in g];target.update(port=name,direction=port['direction'],pin_points=points,register_center=[cx,cy],register_pin_xy=xy,center_manhattan_um=max(abs(x-cx)+abs(y-cy) for x,y in points),terminal_manhattan_um=max(abs(x-xy[0])+abs(y-xy[1]) for x,y in points));rows.append(target)
# Existing geometry evaluator supplies limits and identical area-bin calculation.
file=Path('/home/ubuntu/OpenTallas/tools/autopilot/geom_rules.py');spec=importlib.util.spec_from_file_location('GR',file);G=importlib.util.module_from_spec(spec);spec.loader.exec_module(G)
vals=sorted(x['center_manhattan_um'] for x in rows);centres=[((x['box'][0]+x['box'][2])/2,(x['box'][1]+x['box'][3])/2,n) for n,x in seq.items()];r2r=max(max(x+y for x,y,n in centres)-min(x+y for x,y,n in centres),max(x-y for x,y,n in centres)-min(x-y for x,y,n in centres));clockport=d['ports']['clk'];z=clockport['BPin_groups'][0][0]['box'];root=((z[0]+z[2])/2,(z[1]+z[3])/2);reach=[(abs(x['pins']['CLK']['xy'][0]-root[0])+abs(x['pins']['CLK']['xy'][1]-root[1]),n) for n,x in seq.items()];all_inside=all(0<=x['box'][0]<=x['box'][2]<=216 and 0<=x['box'][1]<=x['box'][3]<=138.24 for x in seq.values());typed={}
for idx,(n,x) in enumerate(cells.items()):
 m=p['masters'][x['master']];kind='M' if m['block'] else 'P' if 'WELLTAP' in m['type'] or 'SPACER' in m['type'] else 'S' if n in seq else 'B' if isbuf(n) else 'K';typed[idx]=(kind,x['master'],*x['box'],'')
area=G.area_metrics(types.SimpleNamespace(die=d['outline'],cells=typed));out={'status':'PASS_BOUNDARY_AND_ALL_PAIR_GEOMETRY' if not errors and len(rows)==67 and len({x['instance'] for x in rows})==67 and G.q(vals,.9)<=G.PINREG_P90 and max(vals)<=G.PINREG_HARD and r2r<=G.R2R_MAX else 'FAIL_GEOMETRY_REVIEW_REQUIRED','saved_ODB_sha256':d['saved_ODB_sha256'],'boundary':{'mapped_data_bits':len(rows),'dedicated_registers':len({x['instance'] for x in rows}),'explicit_role_exemptions':['clk','rst_n'],'errors':errors,'p90_center_manhattan_um':G.q(vals,.9),'max_center_manhattan_um':max(vals),'max_actual_D_Q_pin_manhattan_um':max(x['terminal_manhattan_um'] for x in rows),'declared_p90_limit_um':G.PINREG_P90,'declared_hard_max_um':G.PINREG_HARD,'measurement':'Conservative maximum over every physical BPin rectangle centre to actual mapped register cell centre; D/Q-centroid distances separately retained','mapping':rows},'R2R':{'all8994_sequential_boxes_contained':all_inside,'universal_outline_Manhattan_bound_um':216+138.24,'exact_all_pair_centres_max_Manhattan_um':r2r,'limit_um':G.R2R_MAX,'scope':'All register endpoint pairs covered geometrically; not routed length or timing'},'area':area,'current_clock':{'root_port':'clk','root_xy':root,'sink_count':len(seq),'sink_nets':dict(collections.Counter(x['pins']['CLK']['net'] for x in seq.values())),'max_preCTS_root_to_sink_Manhattan_um':max(reach)[0],'worst_preCTS_sink':max(reach)[1],'actual_preCTS_generated_taps':0,'generation':'Native ORFS cts.tcl clock_tree_synthesis creates a fresh tree from these current sinks; no old tap graph or old clustering reused','clock_reach_status':'PRE_CTS_TREE_NOT_GENERATED; raw root reach is not a completed clock-tree PASS'},'x31_BPin_groups':len(d['ports']['x[31]']['BPin_groups']),'x31_rectangles':sum(map(len,d['ports']['x[31]']['BPin_groups'])),'geom_rules_source':str(file),'geom_rules_sha256':hashlib.sha256(file.read_bytes()).hexdigest(),'no_solver_STA_CTS':True}
(r/'TYPED_GEOMETRY.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps({k:out[k] for k in ['status','R2R','area','current_clock','x31_BPin_groups','x31_rectangles']},indent=2));print('BOUNDARY',len(rows),'errors',len(errors),'p90',G.q(vals,.9),'max',max(vals))
