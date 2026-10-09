#!/usr/bin/env python3
"""Real-macro protected replay gates. Execute only on an admitted fleet host."""
import argparse,hashlib,json,pathlib,subprocess
ROOT=pathlib.Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser();p.add_argument('--out',required=True);a=p.parse_args()
out=pathlib.Path(a.out).resolve();out.mkdir(parents=True,exist_ok=False)
sources=['rtl/common/ot_secded.sv','rtl/common/ot_secded_cols.svh',
 'physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v',
 'rtl/hbm_accel/tu/link_retry_sram_20261008/ot_hbm_replay_sram.sv',
 'rtl/hbm_accel/tu/link_retry_sram_20261008/ot_hbm_link_retry_sram.sv',
 'rtl/hbm_accel/tu/link_retry_sram_20261008/tb_hbm_replay_sram.sv',
 'rtl/hbm_accel/tu/link_retry_sram_20261008/tb_hbm_link_retry_sram.sv']
sha={s:hashlib.sha256((ROOT/s).read_bytes()).hexdigest() for s in sources};results=[]
for name,top,flags,neg in [
 ('store','tb_hbm_replay_sram',[],False),
 ('store_mutant','tb_hbm_replay_sram',['-Ptb_hbm_replay_sram.TB_MUT=1'],True),
 ('retry','tb_hbm_link_retry_sram',[],False),
 ('retry_mutant','tb_hbm_link_retry_sram',['-DOT_HBM_RETRY_MUT_DUPLICATE'],True)]:
 cmd=['iverilog','-g2012','-I'+str(ROOT/'rtl/common'),'-s',top,*flags,'-o',str(out/name),*[str(ROOT/s) for s in sources if s.endswith('.sv') or s.endswith('.v')]]
 b=subprocess.run(cmd,capture_output=True,text=True);(out/(name+'.build.log')).write_text(b.stdout+b.stderr)
 if b.returncode:r=dict(name=name,pass_gate=False,build_exit=b.returncode)
 else:
  v=subprocess.run(['vvp',str(out/name)],capture_output=True,text=True);(out/(name+'.log')).write_text(v.stdout+v.stderr)
  passed=v.returncode!=0 and 'FATAL:' in v.stdout if neg else v.returncode==0 and 'PASS_ALL' in v.stdout
  r=dict(name=name,negative_control=neg,pass_gate=passed,simulation_exit=v.returncode)
 results.append(r)
record=dict(source_sha256=sha,gates=results,exactness_gate='PASS' if all(r['pass_gate'] for r in results) else 'FAIL',qualification='REAL_MACRO_INTERFACE_STANDALONE',physical_qualified=False,die_integrated=False)
(out/'record.json').write_text(json.dumps(record,indent=2)+'\n');print(json.dumps(record,indent=2));raise SystemExit(0 if all(r['pass_gate'] for r in results) else 1)
