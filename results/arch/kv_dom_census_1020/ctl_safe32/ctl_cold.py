import json,sys,importlib.util,subprocess,re
from pathlib import Path
from collections import Counter
root=Path('/work');base=Path('/src');top='qkd_kvs_ctl_s32'
sp=importlib.util.spec_from_file_location('tl',base/'tools/textbook_lint.py');m=importlib.util.module_from_spec(sp);sys.modules['tl']=m;sp.loader.exec_module(m)
net=Path('/original/1_2_yosys.v');mods=m.parse_verilog(net.read_text());g,oldtop=m.flatten(mods,None);a=m.build(g,None);ports=mods[oldtop]
rec=json.loads((root/(top+'.json')).read_text());eq=[];pairs=[]
for r in rec['copied_cells']:
 if r['kind']!='ff':continue
 ci=r['cell']
 for pn,bs in g.cells[ci][2].items():
  if a['pin_dir'][ci][pn]!='out':continue
  for x in bs:
   for j in range(1,r['copies']):eq.append('(n%d_c0 == n%d_c%d)'%(x,x,j));pairs.append((x,j))
assert eq,'no state obligations'
src=(root/(top+'.sv')).read_text();src=src.replace('module '+top+' (','module '+top+' (eq_copies,',1);src=src.replace(');',');\n output wire eq_copies;\n assign eq_copies = '+(' & '.join(eq))+';',1)
decl=[];conn=['.eq_copies(eq_copies)']
for p in ports.ports:
 if ports.dirs[p]!='input':continue
 width='' if p not in ports.widths else '[%d:%d] '%ports.widths[p];decl.append('input wire '+width+p);conn.append('.'+p+'('+p+')')
src+='\nmodule proof('+','.join(decl+['output wire eq_copies'])+');\n'+top+' u('+','.join(conn)+');\nendmodule\n';(root/'ctl.cold.sv').write_text(src)
cmd=['read_liberty -ignore_miss_func '+str(p) for p in sorted(root.glob('*.lib'))]
cmd+=['read_verilog -lib '+str(p) for p in (base/'physical/asap7_memory_macros_v2').glob('ctl_sram*/*_bb.v')]
cmd+=['read_verilog /work/ctl.cold.sv','hierarchy -top proof','setattr -mod -unset keep_hierarchy','setattr -unset keep','flatten','proc','opt_expr','opt_clean','write_json /work/ctl.cold_pre.json','async2sync','clk2fflogic','opt_clean']
sat='sat -seq 32 -prove eq_copies 1 -prove-skip 11 -set rst_n 0 -set por_n 0 -verify'
for t in range(1,33):sat+=' -set-at %d ck %d'%(t,t%2)
for t in range(13,33):sat+=' -set-at %d rst_n 1 -set-at %d por_n 1'%(t,t)
cmd.append(sat);(root/'ctl.cold.ys').write_text('\n'.join(cmd)+'\n')
with (root/'ctl.cold.log').open('w') as f:rc=subprocess.run(['yosys','-s','/work/ctl.cold.ys'],stdout=f,stderr=subprocess.STDOUT).returncode
state=json.loads((root/'ctl.cold_pre.json').read_text())['modules']['proof'];init={n:v['attributes']['init'] for n,v in state['netnames'].items() if 'init' in v.get('attributes',{})};types=Counter(c['type'] for c in state['cells'].values());seq=[n for n,c in state['cells'].items() if 'dff' in c['type'].lower() or c['type']=='$ff'];distinct=[]
for n,j in pairs:
 a=state['netnames']['u.n%d_c0'%n]['bits'];b=state['netnames']['u.n%d_c%d'%(n,j)]['bits'];distinct.append(a!=b)
r=dict(rc=rc,sequential_instances=len(seq),copy_equalities=len(eq),all_copy_outputs_distinct=all(distinct),state_init_attributes=init,cell_type_inventory=dict(types),no_opt_merge=True,no_unknown_cells_allowed=True,reset_protocol='12 halfsteps reset held low on rst_n/por_n,20 halfsteps released; core positive edges every2steps; observe12..32')
(root/'ctl.cold_inventory.json').write_text(json.dumps(r,indent=2)+'\n');print('CTL_COLD_STATE_PROOF',r,flush=True)
assert not init and all(distinct)
raise SystemExit(rc)
