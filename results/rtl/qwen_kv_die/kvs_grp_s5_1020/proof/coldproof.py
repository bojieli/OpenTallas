import json,sys,importlib.util,subprocess
from pathlib import Path
root=Path('/work');base=Path('/src')
tool=base/'tools/textbook_lint.py';sp=importlib.util.spec_from_file_location('tl',tool);m=importlib.util.module_from_spec(sp);sys.modules['tl']=m;sp.loader.exec_module(m)
records=json.loads((root/'original_census.json').read_text())
for key,top in [('qkd_kvs_grp_s3a-20261019-220148','qkd_kvs_grp_s5'),('qkd_kvs_grp_h_s4b-20261019-221603','qkd_kvs_grp_h_s5')]:
 original=Path('/originals')/key/'routes/gate/work/orfs/results/asap7'
 net=next(original.glob('*/base/1_2_yosys.v'));mods=m.parse_verilog(net.read_text());g,oldtop=m.flatten(mods,None);a=m.build(g,None);ports=mods[oldtop]
 rec=json.loads((root/(top+'.json')).read_text());eq=[]
 for r in rec['copied_cells']:
  if r['kind']!='ff':continue
  ci=r['cell']
  for pn,bs in g.cells[ci][2].items():
   if a['pin_dir'][ci][pn]!='out':continue
   for x in bs:
    for j in range(1,r['copies']):eq.append('(n%d_c0 == n%d_c%d)'%(x,x,j))
 src=(root/(top+'.sv')).read_text();src=src.replace('module '+top+' (','module '+top+' (eq_s5copies,',1);src=src.replace(');',');\n  output wire eq_s5copies;\n  assign eq_s5copies = '+(' & '.join(eq))+';',1)
 decl=[];conn=['.eq_s5copies(eq_s5copies)']
 for p in ports.ports:
  if ports.dirs[p]!='input':continue
  width='' if p not in ports.widths else '[%d:%d] '%ports.widths[p];decl.append('input wire '+width+p);conn.append('.'+p+'('+p+')')
 src+='\nmodule proof('+','.join(decl+['output wire eq_s5copies'])+');\n'+top+' u('+','.join(conn)+');\nendmodule\n';(root/(top+'.cold.sv')).write_text(src)
 reads=['read_liberty -ignore_miss_func '+str(p) for p in sorted(root.glob('*.lib'))]
 cmds=reads+['read_verilog -lib /src/physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2_p192_mir/ot_sram_1r1w_128x256_m1_r2c2_p192_mir_bb.v','read_verilog /work/'+top+'.cold.sv','hierarchy -top proof','setattr -mod -unset keep_hierarchy','setattr -unset keep','flatten','proc','opt_expr','opt_clean','write_json /work/'+top+'.cold_pre.json','async2sync','clk2fflogic','opt_clean']
 sat='sat -seq 32 -prove eq_s5copies 1 -prove-skip 11 -set rst_n 0 -set hrst_n 0 -verify'
 for t in range(1,33):sat+=' -set-at %d ck %d -set-at %d hck %d'%(t,t%2,t,(t//2)%2)
 
 for t in range(13,33):sat+=' -set-at %d rst_n 1 -set-at %d hrst_n 1'%(t,t)
 cmds.append(sat);(root/(top+'.cold.ys')).write_text('\n'.join(cmds)+'\n')
 with (root/(top+'.cold.log')).open('w') as h:rc=subprocess.run(['yosys','-s',str(root/(top+'.cold.ys'))],stdout=h,stderr=subprocess.STDOUT).returncode

 state=json.loads((root/(top+'.cold_pre.json')).read_text())['modules']['proof'];init={n:d['attributes']['init'] for n,d in state['netnames'].items() if 'init' in d.get('attributes',{})};seq=[(n,c['type']) for n,c in state['cells'].items() if 'dff' in c['type'].lower() or c['type']=='$ff'];(root/(top+'.cold_state_inventory.json')).write_text(json.dumps(dict(sequential_instances=len(seq),state_init_attributes=init,no_opt_merge=True,no_unknown_cells_allowed=True,copy_equalities=len(eq),sequential_cell_names=seq),indent=1)+'\n')
 print(top,'COLDPROOF',rc,'independent state; reset12steps then release20; copies equal t12..32',flush=True)
 if rc:raise SystemExit(rc)
