#!/usr/bin/env python3
"""Run only on an admitted fleet host; preserve every source-pinned attempt."""
import argparse,hashlib,json,pathlib,subprocess
ROOT=pathlib.Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser();p.add_argument('--out',required=True)
# struct-close 2026-10-09: --cl benches ot_hbm_link_retry_pipeline_cl.sv (unguarded -cl line) in place of the default
p.add_argument('--cl',action='store_true');a=p.parse_args()
out=pathlib.Path(a.out);out.mkdir(parents=True,exist_ok=False)
sources=['rtl/common/ot_secded.sv','rtl/common/ot_secded_cols.svh',
'physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v',
*__import__('os').environ.get('OT_RETRY_REPLAY_SRC','rtl/hbm_accel/tu/link_retry_sram_20261008/ot_hbm_replay_sram.sv').split(),   # redesign-hbm: '<common>/ot_secded_dec_dp.sv <..>/ot_hbm_replay_sram_dp.sv'
'rtl/hbm_accel/tu/link_retry_pipeline_20261009/ot_hbm_link_retry_pipeline'+('_cl' if a.cl else '')+'.sv',
'rtl/hbm_accel/tu/link_retry_pipeline_20261009/tb_hbm_link_retry_pipeline.sv']
sha={s:hashlib.sha256((ROOT/s).read_bytes()).hexdigest() for s in sources};gates=[]
for name,flags,negative in [('positive',[],False),('duplicate_mutant',['-DOT_HBM_RETRY_PIPE_MUT_DUPLICATE'],True)]:
 cmd=['iverilog','-g2012','-I'+str(ROOT/'rtl/common'),'-s','tb_hbm_link_retry_pipeline',*flags,*(['-DOT_HBM_RETRY_NO_REG_POISON'] if a.cl else []),*__import__('os').environ.get('OT_RETRY_DEFS','').split(),'-o',str(out/name),*[str(ROOT/s) for s in sources if s.endswith(('.sv','.v'))]]
 b=subprocess.run(cmd,capture_output=True,text=True);(out/(name+'.build.log')).write_text(b.stdout+b.stderr)
 v=subprocess.run(['vvp',str(out/name)],capture_output=True,text=True) if b.returncode==0 else b
 (out/(name+'.log')).write_text(v.stdout+v.stderr)
 passed=b.returncode==0 and (v.returncode!=0 and 'FATAL:' in v.stdout if negative else v.returncode==0 and 'PASS_ALL' in v.stdout)
 gates.append(dict(name=name,negative_control=negative,pass_gate=passed,build_exit=b.returncode,run_exit=v.returncode))
r=dict(source_sha256=sha,gates=gates,exactness_gate='PASS' if all(g['pass_gate'] for g in gates) else 'FAIL',physical_qualified=False,die_integrated=False)
(out/'record.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2))
raise SystemExit(0 if r['exactness_gate']=='PASS' else 1)
