import json,sys,pathlib,copy,hashlib
R=pathlib.Path('/srv/opentallas-scratch2/claude/codex-s81-cl911-t28-0212');F=pathlib.Path('/srv/opentallas-scratch2/claude/codex-flow-s81-source-2055');sys.path.insert(0,str(F/'src/tools/die_plan'))
import schema as S,gen_phys as G,taps as T,reset_tree as RT
import importlib.util
sp=importlib.util.spec_from_file_location('canonical_obstacles',R/'canonical_placement_obstacles.py');cm=importlib.util.module_from_spec(sp);sp.loader.exec_module(cm);placement_boxes=cm.placement_boxes
p=json.load(open(F/'src/physical/die_plan/s81/plan_source39_deadrefreshed_clk28.json'));P=S.Plan(p);tn='col_h10_r0_p1__t1__cl911743eb';d=json.load(open(R/'native_census.json'));typ=P.types[tn];oldtree=RT.for_type(P,tn);assert json.loads(json.dumps(oldtree))==d['reset_tree'];oldrt=oldtree['relays'];assert d['sinks'][-len(oldrt):]==[[float(r['xy'][0]),float(r['xy'][1]),1.] for r in oldrt]
new=[1126.432,958.496];assert list(G._snap_tap(P,*new))==new
boxes=placement_boxes(typ,halo=S.TAP_CLEAR_UM);body=[new[0]-.81,new[1]-.135,new[0]+.81,new[1]+.135];assert not[n for n,b in boxes.items() if body[0]<b[2] and body[2]>b[0] and body[1]<b[3] and body[3]>b[1]]
node=next(x for x in typ['clock']['added_taps'] if x['name']=='clk_t28');assert node['xy']==[1126.44,980.6];node['xy']=new
newtree=RT.for_type(P,tn);newrt=newtree['relays'];assert oldtree['taps']==newtree['taps'];sinks=d['sinks'][:-len(oldrt)]+[[float(r['xy'][0]),float(r['xy'][1]),1.] for r in newrt]
taps=T.grid_explicit_sites(P,tn);taps=[(n,*G._snap_tap(P,x,y)) for n,x,y in taps];load,far,asg=T.assign(taps,sinks,1500,200,max_distance_um=200);bad=[(n,load[i],far[i]) for i,(n,x,y) in enumerate(taps) if i>=16 and(not load[i] or load[i]>1500 or far[i]>200+1e-6)];assert not bad,bad
report={'type':tn,'old_xy':[1126.44,980.6],'new_xy':new,'tap_count':len(taps),'obstacles':len(boxes),'old_reset_relays':len(oldrt),'new_reset_relays':len(newrt),'output_count':len(oldtree['taps']),'old_release':RT.release_clocks(oldtree),'new_release':RT.release_clocks(newtree),'tap28_load_radius':[load[28],far[28]],'sink_count_old':len(d['sinks']),'sink_count_new':len(sinks),'all_added_taps_pass':not bad,'added_reset_FF':len(newrt)-len(oldrt),'bound_native_contract':bool(RT.bound_native_contract(P,tn))}
for name,t in [('old_reset',oldtree),('new_reset',newtree),('model',report)]: (R/(name+'.json')).write_text(json.dumps(t,indent=1)+'\n')
N=len(oldtree['taps']);mut=copy.deepcopy(newtree);byq={r['q']:r for r in mut['relays']};leaf=byq['rst_n_t28'];leaf['d']=byq[leaf['d']]['d'];sv=RT.relay_sv()+'\n'
for name,t in [('old_tree',oldtree),('new_tree',newtree),('mutant_tree',mut)]:
 sv+=f'module {name}(input wire clk,input wire arst_n, output wire [{N-1}:0] observations, output wire rst_o_0);\n'+'\n'.join(RT.rtl_lines(t))+'\n'+''.join(f'assign observations[{i}]=rst_n_t{i};\n' for i in range(N))+'endmodule\n'
(R/'native_reset_trees.sv').write_text(sv);(R/'plan_candidate.json').write_text(json.dumps(p,separators=(',',':'))+'\n');print(json.dumps(report))
