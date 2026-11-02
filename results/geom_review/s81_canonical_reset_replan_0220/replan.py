import json,sys,pathlib,copy
R=pathlib.Path('/srv/opentallas-scratch2/claude/codex-s81-reset-canonical-0220');sys.path.insert(0,str(R/'current/tools/die_plan'));import schema as S,reset_tree as RT,taps as T,gen_phys as G
p=json.load(open(R/'source39_approved_clk28.json'));P=S.Plan(p,path=R/'source39_approved_clk28.json');tn='col_h10_r0_p1__t1__cl574cc59d';old=json.load(open(R/'source_only_185.json'));new=RT.for_type(P,tn);(R/'canonical_tree.json').write_text(json.dumps(new,indent=1)+'\n')
obs=RT.blockages(P.types[tn]);hits=[{'q':r['q'],'xy':r['xy']} for r in new['relays'] if any(a<r['xy'][0]<c and b<r['xy'][1]<d for a,b,c,d in obs)]
report={'classification':'DISABLED_CANONICAL_RESET_PHYSICAL_REPLAN_PREP','tools':(R/'TOOLS_COMMIT').read_text().strip(),'type':tn,'source_old_relays':len(old['relays']),'canonical_new_relays':len(new['relays']),'FF_delta':len(new['relays'])-len(old['relays']),'named_outputs':len(new['taps']),'same_named_outputs':old['taps']==new['taps'],'old_release_cycles':RT.release_clocks(old),'new_release_cycles':RT.release_clocks(new),'canonical_relay_point_hits':hits,'canonical_obstacles':len(obs)}
try:
 taps=[(n,*G._snap_tap(P,x,y))for n,x,y in T.grid_explicit_sites(P,tn)];sinks=json.load(open(R/'native_data_sinks.json'))+[[float(r['xy'][0]),float(r['xy'][1]),1.]for r in new['relays']];loads,far,asg=T.assign(taps,sinks,1500,200,max_distance_um=200);report['clock_bad']=[{'name':n,'load':loads[i],'radius':far[i]}for i,(n,x,y)in enumerate(taps)if i>=16 and(not loads[i] or loads[i]>1500 or far[i]>200+1e-6)]
except Exception as e:report['clock_model_error']=str(e)
(R/'report.json').write_text(json.dumps(report,indent=1)+'\n');print(json.dumps(report))
N=len(new['taps']);assert N==45 and old['taps']==new['taps'];mut=copy.deepcopy(new);byq={r['q']:r for r in mut['relays']};leaf=byq['rst_n_t28'];leaf['d']=byq[leaf['d']]['d'];sv=RT.relay_sv()+'\n'
for name,t in [('old_tree',old),('new_tree',new),('mutant_tree',mut)]:
 sv+=f'module {name}(input wire clk,input wire arst_n,output wire [{N-1}:0] observations,output wire rst_o_0);\n'+'\n'.join(RT.rtl_lines(t))+'\n'+''.join(f'assign observations[{i}]=rst_n_t{i};\n'for i in range(N))+'endmodule\n'
(R/'native_reset_trees.sv').write_text(sv)
