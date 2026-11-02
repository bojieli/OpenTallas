import pathlib,json,sys,copy,hashlib,re
R=pathlib.Path('/srv/opentallas-scratch2/claude/codex-s81-reset-cache-correction-0405');F=pathlib.Path('/srv/opentallas-scratch2/claude/codex-flow-s81-source-2055');sys.path.insert(0,str(F/'src/tools/die_plan'));import schema as S,reset_tree as RT
path=F/'src/physical/die_plan/s81/plan_source39_clockset_t49.json';raw=json.load(open(path));summary=[]
for tn,key,node,oldxy,newxy in [('slice_station__t18','taps','clk_t16',[196.6712,294.8172],[197.088,294.112]),('col_h10_r0_p1__t1__cl911743eb','added_taps','clk_t28',[1126.44,980.6],[1126.432,958.496])]:
 newraw=copy.deepcopy(raw);newnode=next(t for t in newraw['partition_types'][tn]['clock'][key]if t['name']==node);assert newnode['xy']==newxy
 oldraw=copy.deepcopy(newraw);next(t for t in oldraw['partition_types'][tn]['clock'][key]if t['name']==node)['xy']=oldxy
 A=S.Plan(oldraw,path);B=S.Plan(newraw,path);assert A is not B
 a=RT.for_type(A,tn);b=RT.for_type(B,tn);O=R/tn;O.mkdir(exist_ok=True)
 for name,obj in [('old_fresh',a),('new_fresh',b)]: (O/(name+'.json')).write_text(json.dumps(obj,indent=1)+'\n')
 oldsv='\n'.join(RT.rtl_lines(a));newsv='\n'.join(RT.rtl_lines(b));ex=lambda s:re.sub(r'//[^\n]*','',s)
 row={'type':tn,'separate_fresh_Plan_objects':True,'old_relays':len(a['relays']),'new_relays':len(b['relays']),'output_count':len(a['taps']),'same_output_names':a['taps']==b['taps'],'old_release':RT.release_clocks(a),'new_release':RT.release_clocks(b),'raw_rtl_identical':oldsv==newsv,'executable_rtl_identical':ex(oldsv)==ex(newsv),'old_executable_sha256':hashlib.sha256(ex(oldsv).encode()).hexdigest(),'new_executable_sha256':hashlib.sha256(ex(newsv).encode()).hexdigest()}
 (O/'old_rtl.sv').write_text(oldsv+'\n');(O/'new_rtl.sv').write_text(newsv+'\n');(O/'report.json').write_text(json.dumps(row,indent=1)+'\n');summary.append(row);print(json.dumps(row),flush=True)
 N=len(a['taps']);mut=copy.deepcopy(b);byq={r['q']:r for r in mut['relays']};target='rst_n_t28' if 'cl911' in tn else 'rst_n_t16';leaf=byq[target];leaf['d']=byq[leaf['d']]['d'];sv=RT.relay_sv()+'\n'
 for name,t in [('old_tree',a),('new_tree',b),('mutant_tree',mut)]:
  sv+=f'module {name}(input wire clk,input wire arst_n,output wire[{N-1}:0] observations,output wire rst_o_0);\n'+'\n'.join(RT.rtl_lines(t))+'\n'+''.join(f'assign observations[{i}]=rst_n_t{i};\n'for i in range(N))+'endmodule\n'
 (O/'native_reset_trees.sv').write_text(sv)
(R/'summary.json').write_text(json.dumps(summary,indent=1)+'\n')
