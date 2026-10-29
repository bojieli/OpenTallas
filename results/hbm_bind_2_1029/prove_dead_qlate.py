#!/usr/bin/env python3
"""HBM-BIND-2: dead-input proof (opentallas.dead_inputs.v1) for the scorer leaf u_qlate.rst_n literal tie.
ot_hdc_delay #(W=569, D=0) (QLATE=0 in ot_hbm_idx_chunk_rt_h): D==0 -> g_wire `assign q = d`, rst_n has no fanout.
Proof = Yosys (ORFS image, docker) proc+opt of the exact selected source body with the exact parameters, then
tools/die_plan/dead_inputs.dead_bits (output aliases live).  One declaration per partition type that holds a u_qlate.
usage: prove_dead_qlate.py REPO MANIFEST(asbuilt_b.json) TYPES_CSV OUT_DIR"""
import json,sys,subprocess,os,hashlib,re
from pathlib import Path
repo,man,types,out=Path(sys.argv[1]),Path(sys.argv[2]),sys.argv[3].split(','),Path(sys.argv[4])
sys.path.insert(0,str(repo/'tools/die_plan'));from dead_inputs import dead_bits,module_hash
m=json.loads(man.read_text());base=Path(m['base'])
MOD='ot_hdc_delay';PAR={'W':'569','D':'0','RESET':'0'}  # full evaluated parameter set (bind compares defaults+overrides)
sel=[f for f in m['prefer'] if (base/f).is_file() and re.search(r'^module\s+'+MOD+r'\b',(base/f).read_text(),re.M)]
assert len(sel)==1,sel;src=sel[0]
out.mkdir(parents=True,exist_ok=True)
body=re.search(r'^module\s+'+MOD+r'\b.*?^endmodule',(base/src).read_text(),re.M|re.S).group()
(out/'input.sv').write_text('`timescale 1ns/1ps\n'+body+'\n')
(out/'run.ys').write_text(f"read_verilog -sv input.sv\nchparam {' '.join(f'-set {k} {v}' for k,v in PAR.items())} {MOD}\nhierarchy -top {MOD}\nproc\nopt\nwrite_json opt.json\n")
subprocess.run(['docker','run','--rm','--memory=2g','--memory-swap=2g','-u',f'{os.getuid()}:{os.getgid()}','-v',f'{out}:{out}','-w',str(out),
  'openroad/orfs:asap7lock','/OpenROAD-flow-scripts/tools/install/yosys/bin/yosys','-q','-l','yosys.log','-s','run.ys'],check=True)
mods=json.loads((out/'opt.json').read_text())['modules'];mk=[k for k in mods if k==MOD or k.startswith('$paramod') and MOD in k];assert len(mk)==1,mk
mod=mods[mk[0]]
dead={pn:sorted(dead_bits(mod,pn)) for pn,p in mod['ports'].items() if p['direction']=='input'}
print('dead bits per input',{k:len(v) for k,v in dead.items()})
assert dead['rst_n']==[0]
ports={'rst_n':[[0,0]]}
sha=module_hash(base/src,MOD);assert sha==module_hash(repo/src,MOD) if (repo/src).is_file() else True
decl=[dict(partition_type=t,module=MOD,parameters=PAR,source=src,module_sha256=sha,method='yosys.proc.opt.no_fanout',remaining_loads=0,ports=ports) for t in types]
rec=dict(schema='opentallas.dead_inputs.v1',verdict='PASS',defines=m.get('defines',[]),dependency_modules=[],
 source_commit=subprocess.check_output(['git','-C',str(repo),'rev-parse','HEAD'],text=True).strip(),
 note='HBM-BIND-2 10-29: scorer leaf core u_qlate = ot_hdc_delay W=569 D=0 (wire); rst_n literal 1 at the parent has no fanout in the optimized module (no child cells). Per-type declarations only; no port removed, no new type.',
 declarations=decl)
(out/'proof.json').write_text(json.dumps(rec,indent=1)+'\n');print('DEAD_INPUTS_PROVED',len(decl),'declarations')
