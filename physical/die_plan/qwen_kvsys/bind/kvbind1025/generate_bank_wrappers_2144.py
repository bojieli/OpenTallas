import sys,pathlib
sys.path.insert(0,'tools');import die_port_bind as D
p=pathlib.Path('physical/die_plan/qwen_kvsys/bind/kv45/group_r2c_native.sv');mods={m.name:m for m in D.parse_modules(p.read_text(),str(p))}
for name in ['qkd_kvs_grp_r2c','qkd_kvs_grp_h_r2c']:
 m=mods[name];new=name+'_r8pos';decl=[]
 for pn in m.order:
  direction,ranges=m.ports[pn];dim=''.join(f'[{a}:{b}]' for a,b in ranges);decl.append(f'    {direction} wire {dim} {pn}')
 ps='' if not m.params else ' #(\n'+',\n'.join('    parameter '+k+' = '+str(v) for k,v in m.params.items())+'\n)'
 text='`timescale 1ns/1ps\n// Uniform same-ABI position-selected R8 landing bank, no new pins.\nmodule '+new+ps+' (\n'+',\n'.join(decl)+'\n);\n'
 text+='    wire [17:0] r8_tok;\n    wire [15:0] r8_epoch;\n'
 text+='    (* keep_hierarchy = 1 *) kv_pc_r8_position_bank u_position_bank (.clk(ck), .stack_id(slg__cfg_stack), .group_id(slg__cfg_group),\n        .tok_i(x__tok), .epoch_i(x__tep), .tok_o(r8_tok), .epoch_o(r8_epoch));\n'
 forward='' if not m.params else ' #('+', '.join('.'+k+'('+k+')' for k in m.params)+')'
 ports=[f'        .{pn}('+('r8_tok' if pn=='x__tok' else 'r8_epoch' if pn=='x__tep' else pn)+')' for pn in m.order]
 text+='    '+name+forward+' u_native (\n'+',\n'.join(ports)+'\n    );\nendmodule\n'
 pathlib.Path('rtl/qwen_sys/kv_pc_r8_positionbank_1025/'+new+'.sv').write_text(text)
 print(name,len(m.ports),m.params)
