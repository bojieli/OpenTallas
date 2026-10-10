#!/usr/bin/env python3
"""Run on an admitted fleet host, never on memory-pressured localhost.
Creates immutable source-pinned records; no overwrite of failure verdicts.
"""
import argparse, ast, hashlib, json, pathlib, subprocess
ROOT=pathlib.Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser();p.add_argument('--out',required=True);p.add_argument('--depth',type=int,default=512);p.add_argument('--seq-bits',type=int,default=12)
a=p.parse_args();out=pathlib.Path(a.out).resolve();out.mkdir(parents=True,exist_ok=False)
files=['rtl/hbm_accel/tu/ot_hbm_link_retry.sv','rtl/test/tb_hbm_link_retry.sv','tools/uarch_model.py','tools/hbm_link_retry_bench.py']
sha={f:hashlib.sha256((ROOT/f).read_bytes()).hexdigest() for f in files}
s=(ROOT/'tools/uarch_model.py').read_text();node=next(n for n in ast.parse(s).body if isinstance(n,ast.FunctionDef) and n.name=='hbm_link_retry_model');env={};exec(ast.get_source_segment(s,node),env)
model=env['hbm_link_retry_model'](depth=a.depth,seq_bits=a.seq_bits)
runs=[]
for name,flags,negative in [('positive',[],False),('duplicate_mutant',['-DOT_HBM_RETRY_MUT_DUPLICATE'],True)]:
 cmd=['iverilog','-g2012','-s','tb_hbm_link_retry',f'-Ptb_hbm_link_retry.TB_DEPTH={a.depth}',f'-Ptb_hbm_link_retry.TB_SW={a.seq_bits}',*flags,'-o',str(out/name),*[str(ROOT/f) for f in files[:2]]]
 build=subprocess.run(cmd,text=True,capture_output=True);(out/(name+'.build.log')).write_text(build.stdout+build.stderr)
 if build.returncode: runs.append(dict(name=name,pass_gate=False,build_exit=build.returncode));continue
 sim=subprocess.run(['vvp',str(out/name)],text=True,capture_output=True);(out/(name+'.log')).write_text(sim.stdout+sim.stderr)
 gate=(sim.returncode!=0 and 'FATAL:' in sim.stdout) if negative else (sim.returncode==0 and 'PASS_ALL' in sim.stdout)
 runs.append(dict(name=name,pass_gate=gate,simulation_exit=sim.returncode,negative_control=negative))
record=dict(source_sha256=sha,model=model,runs=runs,protocol_exactness_gate='PASS' if all(r['pass_gate'] for r in runs) else 'FAIL',qualification='STANDALONE_PROTOCOL_ONLY',physical_qualified=False,protected_sram_integrated=False,landing_credit_bridge_integrated=False)
(out/'record.json').write_text(json.dumps(record,indent=2)+'\n');print(json.dumps(record,indent=2))
raise SystemExit(0 if all(r['pass_gate'] for r in runs) else 1)
