#!/usr/bin/env python3
"""Fleet-only independent-state convergence of kept GRP s6c copies.
SRAM outputs are shared arbitrary per-instance values; no SRAM/reset/data assumptions.
The theorem covers replicated FF outputs after reset, not full RTL equivalence.
"""
import argparse,gzip,hashlib,importlib.util,json,re,subprocess,sys
from pathlib import Path
ap=argparse.ArgumentParser();ap.add_argument('--root',required=True);ap.add_argument('--out',required=True);ap.add_argument('--negative-only',action='store_true');a=ap.parse_args()
b=Path(a.root).resolve();out=Path(a.out).resolve();out.mkdir(parents=True,exist_ok=True)
sp=importlib.util.spec_from_file_location('tl',b/'tools/textbook_lint.py');m=importlib.util.module_from_spec(sp);sys.modules['tl']=m;sp.loader.exec_module(m)
coupon=b/'results/rtl/qwen_kv_die/canonical_seq_coupon_1020/formal_compatible'
# Shared arbitrary macro outputs preserve correlation of copies reading the same SRAM port.
macros=[]
for n in ['ot_sram_1r1w_4x32_m1_p192_grp_rsp','ot_sram_1r1w_128x256_m1_r2c2_p192_mir']:
 p=b/'physical/asap7_memory_macros'/n/(n+'_bb.v');s=p.read_text().replace('(* blackbox *)','');s=s.replace('endmodule','  (* anyseq *) reg '+('[31:0]' if '4x32' in n else '[255:0]')+' arbitrary_rd;\n  assign rd_out = arbitrary_rd;\nendmodule');macros.append(s)
(out/'sram_shared_anyseq.v').write_text('\n'.join(macros))
results=[]
for top in ['qkd_kvs_grp_s6c','qkd_kvs_grp_h_s6c']:
 rd=b/'results/rtl/qwen_kv_die/kvs_grp_s6_1020';rec=json.loads((rd/(top+'.json')).read_text());raw=gzip.decompress((rd/'inputs'/(top+'.input.mapped.v.gz')).read_bytes());assert hashlib.sha256(raw).hexdigest()==rec['source_sha256']
 mods=m.parse_verilog(raw.decode());g,ot=m.flatten(mods,None);ga=m.build(g,None);ports=mods[ot];eq=[]
 for r in rec['copied_cells']:
  if r['kind']!='ff':continue
  for pn,bs in g.cells[r['cell']][2].items():
   if ga['pin_dir'][r['cell']][pn]!='out':continue
   for x in bs:
    for j in range(1,r['copies']):eq.append('(n%d_c0 == n%d_c%d)'%(x,x,j))
 src=(b/'rtl/qwen_sys/static_kv_die_20261017'/(top+'.sv')).read_text();assert hashlib.sha256(src.encode()).hexdigest()==rec['generated_sha256'];src=src.replace('module '+top+' (','module '+top+' (eq_copies,',1).replace(');',');\n output wire eq_copies;\n assign eq_copies = '+' & '.join(eq)+';',1)
 decl=[];conn=['.eq_copies(eq_copies)']
 for p in ports.ports:
  if ports.dirs[p]!='input':continue
  w='' if p not in ports.widths else '[%d:%d] '%ports.widths[p];decl.append('input wire '+w+p);conn.append('.'+p+'('+p+')')
 src+='\nmodule proof('+','.join(decl+['output wire eq_copies'])+');\n'+top+' u('+','.join(conn)+');\nendmodule\n';sv=out/(top+'.sv');sv.write_text(src)
 for mutant in ([1] if a.negative_only else [0,1]):
  # Invert D of one actual retained clone; equality must fail after reset release.
  active_sv=sv
  mutated_cell=None
  if mutant:
   target=next(r for r in rec['copied_cells'] if r['kind']=='ff');mutated_cell='u%d_c1'%target['cell']
   pattern=r'('+re.escape(mutated_cell)+r' \(.*?\.D\()([^()]+)(\))'
   changed,count=re.subn(pattern,lambda z:z[1]+'~('+z[2]+')'+z[3],src,count=1);assert count==1
   active_sv=out/(top+'.mutant.sv');active_sv.write_text(changed)
  prefix=out/(top+('.positive' if not mutant else '.negative'))
  cmds=['read_verilog '+str(coupon/'library_model_pdk.v'),'read_verilog -overwrite '+str(coupon/'canonical_ASR_normalized.v'),'read_verilog -overwrite '+str(coupon/'canonical_DFF_normalized.v'),'read_verilog '+str(out/'sram_shared_anyseq.v'),'read_verilog '+str(active_sv),'hierarchy -check -top proof','setattr -mod -unset keep_hierarchy','setattr -unset keep','flatten','proc','opt_expr','opt_clean','write_json '+str(prefix)+'.pre.json','async2sync','clk2fflogic','opt_clean']
  sat='sat -seq 32 -prove eq_copies '+str(1)+' -prove-skip 11 -set rst_n 0 -set hrst_n 0 -verify'
  for t in range(1,33):sat+=' -set-at %d ck %d -set-at %d hck %d'%(t,t%2,t,(t//2)%2)
  for t in range(13,33):sat+=' -set-at %d rst_n 1 -set-at %d hrst_n 1'%(t,t)
  cmds.append(sat);ys=Path(str(prefix)+'.ys');ys.write_text('\n'.join(cmds)+'\n')
  with Path(str(prefix)+'.log').open('w') as h:rc=subprocess.run([str(Path.home()/'.local/opentallas-tools/yosys-0.68/bin/yosys'),'-s',str(ys)],stdout=h,stderr=subprocess.STDOUT).returncode
  log=Path(str(prefix)+'.log').read_text();state=json.loads(Path(str(prefix)+'.pre.json').read_text())['modules']['proof'];init={n:v['attributes']['init'] for n,v in state['netnames'].items() if 'init' in v.get('attributes',{})};seq=[(n,c['type']) for n,c in state['cells'].items() if 'dff' in c['type'].lower() or c['type']=='$ff'];assert not init
  ok=(rc==0 and 'SUCCESS!' in log) if not mutant else (rc!=0 and 'proof did fail' in log)
  r=dict(top=top,mutant=mutant,mutated_cell=mutated_cell,rc=rc,expected=ok,equalities=len(eq),sequential_instances=len(seq),state_init_attributes=init,source_sha256=rec['source_sha256'],mapped_sha256=rec['generated_sha256'],macro_contract='independent shared anyseq output each instance/time; no storage assumptions',no_opt_merge=True,no_unknown_cells_allowed=True)
  Path(str(prefix)+'.summary.json').write_text(json.dumps(r,indent=1)+'\n');results.append(r);print(json.dumps(r),flush=True)
  if not ok:raise SystemExit(1)
(out/'summary.json').write_text(json.dumps(results,indent=1)+'\n')
