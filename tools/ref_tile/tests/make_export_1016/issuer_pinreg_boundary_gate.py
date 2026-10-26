#!/usr/bin/env python3
"""Actual Yosys pin-register wrapper + actual128-row c8/c10 RTL clock/status proof.

Run on the fleet through ot-run. No cells are mapped here; the production Tcl
hook generates the same outer boundary wrapper used by route synthesis. Only
the original top module's identifier changes to its generated core identifier.
"""
from pathlib import Path
import argparse,hashlib,importlib.util,json,os,re,shutil,subprocess,sys
ROOT=Path(__file__).resolve().parents[2]
def digest(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def run(cmd,**kw):return subprocess.run(cmd,check=True,**kw)
def main():
 a=argparse.ArgumentParser();a.add_argument('out');a.add_argument('--hook');a.add_argument('--writer',help='read-only production config writer candidate');a.add_argument('--old-wrapper');a.add_argument('--serial-wrapper',help='actual historical Make-corrupted serial data wrapper negative control');a.add_argument('--bind-existing',help='byte-bind Make/Yosys outputs to an already completed functional proof');a.add_argument('--kind',choices=['c8','c10','all'],default='all');a=a.parse_args()
 out=Path(a.out).resolve();out.mkdir(parents=True,exist_ok=True)
 hook=Path(a.hook).resolve()if a.hook else ROOT/'physical/common_flow/ot_pin_regs.tcl'
 yosys=os.environ.get('YOSYS')or str(Path.home()/'.local/opentallas-tools/yosys-0.68/bin/yosys')
 if not Path(yosys).is_file():yosys=shutil.which('yosys')
 if not yosys:raise RuntimeError('actual Yosys required')
 sources={};receipt={'hook':str(hook),'hook_sha256':digest(hook),'qualified':False,'scope':'actual generated boundary + actual sourceRTL simulation; physicalphase/route/productionconsumer still unqualified','tops':{}}
 for kind,stem in [('c8','s81fill2_sseq_c8'),('c10','s81issuer_c10_localtree')]:
  if a.kind!='all'and a.kind!=kind:continue
  spec=json.loads((ROOT/'tools/ref_tile/specs_s81_fill2'/f'{stem}.json').read_text());top=spec['top'];d=out/kind;d.mkdir(exist_ok=True)
  kit=ROOT/'physical/ref_tile'/spec['name']/'kit.env'
  # Let bash parse the actual generated array, then pass each literal value
  # through subprocess's environment without a second shell evaluation.
  q=run(['bash','-c','set -e; source "$1"; printf "%s\\0" "${EXTRA[@]}"','bash',str(kit)],stdout=subprocess.PIPE).stdout.decode().split('\0')
  env=os.environ.copy();env.update(DESIGN_NAME=top,RESULTS_DIR=str(d))
  for i,word in enumerate(q[:-1]):
   if word=='--orfs-var'and '='in q[i+1]:
    k,v=q[i+1].split('=',1)
    if k.startswith('OT_PIN_REGS'):env[k]=v
  # Exercise the physical flow's actual config writer AND GNU Make export.
  # The kit-only environment misses Make expansion of regexp anchors such as $|.
  sys.path.insert(0,str(ROOT/'tools'))
  writer=Path(a.writer).resolve()if a.writer else ROOT/'tools/run_abi3_physical.py'
  module_spec=importlib.util.spec_from_file_location('issuer_actual_physical_writer',writer)
  physical=importlib.util.module_from_spec(module_spec);module_spec.loader.exec_module(physical)
  pin_env={k:v for k,v in env.items()if k.startswith('OT_PIN_REGS')}
  config=physical.orfs_config_lines('issuer_boundary',dict(top=top,sources=spec['sources'],parameters={}),
      'asap7',dict(corner_env='WC',extra_config=pin_env),50,0.5,memory_max_bits=65536)
  makefile=d/'boundary_config.mk'
  dump=d/'dump_make_env.py'
  dump.write_text('import json,os; print(json.dumps({k:v for k,v in os.environ.items() if k.startswith("OT_PIN_REGS")}))\n')
  makefile.write_text('\n'.join(config)+'\n.PHONY: boundary_env\nboundary_env:\n\t@'+sys.executable+' '+str(dump)+'\n')
  make_out=run(['make','--no-print-directory','-s','-f',str(makefile),'boundary_env'],stdout=subprocess.PIPE).stdout
  actual_env=json.loads(make_out)
  (d/'make_env.json').write_text(json.dumps(actual_env,indent=2)+'\n')
  if actual_env!=pin_env:raise RuntimeError('actual GNU Make boundary environment differs from literal kit: '+repr(dict(expected=pin_env,actual=actual_env)))
  env.update(actual_env)
  wanted_clocks=set(spec['clock_ports'])|{spec['clock_port']}
  if set(env.get('OT_PIN_REGS_CLOCK','').split(','))!=wanted_clocks:raise RuntimeError('generated clock roles differ from literal declarations')
  if set(env.get('OT_PIN_REGS_RESET_PORTS','').split(','))!=set(spec['reset_ports']):raise RuntimeError('generated reset roles differ from literal declarations')
  src=[ROOT/p for p in spec['sources']];sources.update({str(p.relative_to(ROOT)):digest(p)for p in src})
  script=d/'generate.tcl';script.write_text('yosys read_verilog -sv -DSYNTHESIS '+' '.join(map(str,src))+'\nsource {'+str(hook)+'}\n')
  with (d/'yosys.log').open('w')as f:run([yosys,'-Q','-T','-c',str(script)],env=env,stdout=f,stderr=subprocess.STDOUT)
  table=(d/'ot_pin_regs.tsv').read_text();rows={}
  for l in table.splitlines()[1:]:
   v=l.split('\t');rows[v[0]]=dict(direction=v[1],width=int(v[2]),cycles=int(v[3]),why=v[4])
  for n in ['ck','ckv','rst','rsv']:
   if rows[n]['cycles']!=0 or rows[n]['why']!=('clock'if n in wanted_clocks else'reset'):raise RuntimeError('actual transformed clock/reset not direct: '+n)
  for n in ['f_ks','f_pw','t_kd','t_st']+(['f_pq_pw']if kind=='c10'else[]):
   if rows[n]['cycles']!=0:raise RuntimeError('serial data got wrong-domain pin register: '+n)
  direct=set(wanted_clocks)|set(spec['reset_ports'])|{'f_ks','f_pw','t_kd','t_st'}|({'f_pq_pw'}if kind=='c10'else set())
  for n,row in rows.items():
   if n not in direct and row['direction']!='inout' and (row['cycles']!=1 or row['why']!='pin register'):raise RuntimeError('real ck data boundary lost pin stage: '+n)
  if a.bind_existing:
   previous=Path(a.bind_existing).resolve()/kind
   for filename in ['ot_pin_regs_wrapper.v','ot_pin_regs.tsv']:
    if digest(d/filename)!=digest(previous/filename):raise RuntimeError('actual Make/Yosys output differs from completed functional proof: '+kind+'/'+filename)
   receipt.setdefault('completed_functional_binding',{})[kind]=str(previous)
  else:
   top_src=next(p for p in src if re.search(r'\bmodule\s+'+top+r'\b',p.read_text()))
   renamed=re.sub(r'(\bmodule\s+)'+top+r'\b',r'\g<1>'+top+'__ot_pr_core',top_src.read_text(),count=1)
   (d/'actual_core.sv').write_text(renamed)
   actual_src=[p if p!=top_src else d/'actual_core.sv'for p in src]
   tb=ROOT/'rtl/dsrom_sys/s81_static_control/test/tb_s81_issuer_pinreg_boundary.sv'
   compile_cmd=['iverilog','-g2012']+(['-DS81_STATUS_C8']if kind=='c8'else[])+['-s','tb_s81_issuer_pinreg_boundary','-o',str(d/'sim')]
   compile_src=list(map(str,actual_src))+[str(d/'ot_pin_regs_wrapper.v'),str(tb)]
   run(compile_cmd+compile_src)
   sys.path.insert(0,str(ROOT/'tools/s81_static_control'))
   from program import encode_program
   p=encode_program([dict(engine=0,arg=0x102938,issue=0,done=5),dict(engine=12,arg=0xfa0312,issue=1,done=6),dict(engine=14,arg=0,issue=6,done=0),dict(engine=15,arg=0,issue=7,done=0)],0,0)
   (d/'status.hex').write_text(''.join(f"{x['word']:09x}\n"for x in p['writes']))
   for mode in [0,1]:
    with (d/f'mode{mode}.log').open('w')as f:run(['vvp','-n',str(d/'sim'),f'+mode={mode}'],cwd=d,stdout=f,stderr=subprocess.STDOUT)
    print((d/f'mode{mode}.log').read_text().strip(),flush=True)
   if kind=='c8'and a.old_wrapper:
    old=Path(a.old_wrapper).resolve();run(compile_cmd[:-1]+[str(d/'old_mutant')]+list(map(str,actual_src))+[str(old),str(tb)])
    with (d/'old_registered_clock_reset_mutant.log').open('w')as f:r=subprocess.run(['vvp','-n',str(d/'old_mutant'),'+mode=0'],cwd=d,stdout=f,stderr=subprocess.STDOUT)
    if r.returncode==0 or 'serial clock/reset was data registered'not in(d/'old_registered_clock_reset_mutant.log').read_text():raise RuntimeError('actual historical clock/reset mutant escaped')
    receipt['old_wrapper_sha256']=digest(old)
   if kind=='c8'and a.serial_wrapper:
    old=Path(a.serial_wrapper).resolve();run(compile_cmd[:-1]+[str(d/'make_serial_mutant')]+list(map(str,actual_src))+[str(old),str(tb)])
    with (d/'make_serial_mutant.log').open('w')as f:r=subprocess.run(['vvp','-n',str(d/'make_serial_mutant'),'+mode=0'],cwd=d,stdout=f,stderr=subprocess.STDOUT)
    if r.returncode==0 or 'status fault edge 17 expected 211'not in(d/'make_serial_mutant.log').read_text():raise RuntimeError('actual historical Make/serial-data mutant escaped expected fault-phase witness')
    receipt['make_serial_wrapper_sha256']=digest(old)
  receipt['tops'][kind]={'top':top,'NOPS':128,'STAGE':0,'kit_sha256':digest(kit),'config_writer_sha256':digest(writer),'make_config_sha256':digest(makefile),'make_env_sha256':digest(d/'make_env.json'),'wrapper_sha256':digest(d/'ot_pin_regs_wrapper.v'),'table_sha256':digest(d/'ot_pin_regs.tsv'),'role_env':{k:v for k,v in env.items()if k.startswith('OT_PIN_REGS')},'rows':rows}
 receipt['proof_script_sha256']=digest(Path(__file__));receipt['source_sha256']=sources;receipt['bench_sha256']=digest(ROOT/'rtl/dsrom_sys/s81_static_control/test/tb_s81_issuer_pinreg_boundary.sv')
 (out/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
 print('ISSUER_PINREG_BOUNDARY PASS '+('Make/Yosys byte-binding to completed actual128 functional proof'if a.bind_existing else'actual128-row c8/c10 wrappers, exact clocks/reset release, +1ck dataIO and fixed fault observation'),flush=True)
if __name__=='__main__':main()
