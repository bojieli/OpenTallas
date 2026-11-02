import json,pathlib,sys,copy,hashlib
r=pathlib.Path('/srv/opentallas-scratch/claude/codex-s81-clk-t28-2340');o=r/'reset_miter';sys.path.insert(0,'/home/ubuntu/OpenTallas/tools/die_plan');import reset_tree as RT
old=json.load(open(r/'baseline_native_relays_currenttools.json'));new=json.load(open(r/'candidate_native_relays.json'));assert old['taps']==new['taps'] and len(old['taps'])==45
mut=copy.deepcopy(new);byq={x['q']:x for x in mut['relays']};leaf=byq['rst_n_t28'];leaf['d']=byq[leaf['d']]['d']
text=RT.relay_sv()+'\n'
for name,t in [('old_tree',old),('new_tree',new),('mutant_tree',mut)]:
 text+=f'module {name}(input wire clk,input wire arst_n, output wire [44:0] observations, output wire rst_o_0);\n'
 text+='\n'.join(RT.rtl_lines(t))+'\n'
 for i in range(45):text+=f'assign observations[{i}]=rst_n_t{i};\n'
 text+='endmodule\n'
(o/'native_reset_trees.sv').write_text(text)
(o/'source.json').write_text(json.dumps({'old_relay_count':len(old['relays']),'new_relay_count':len(new['relays']),'entry_stages_old':RT.entry_stages(old),'entry_stages_new':RT.entry_stages(new),'release_clocks_old':RT.release_clocks(old),'release_clocks_new':RT.release_clocks(new),'all45named_outputs':old['taps'],'native_emitter':'tools/die_plan/reset_tree.py rtl_lines','native_cell_source':'tools/die_plan/gen_rtl.py CELLS via reset_tree.relay_sv','mutant':'rst_n_t28 skips exactly one upstream native relay; all original relays retained','native_rtl_sha256':hashlib.sha256(text.encode()).hexdigest()},indent=1)+'\n')
