#!/usr/bin/env python3
"""Minimum full-width receive-slot mechanism gate, preserving every attempt."""
import argparse, hashlib, json, pathlib, subprocess
ROOT=pathlib.Path(__file__).resolve().parents[1]
a=argparse.ArgumentParser();a.add_argument('--out',required=True);args=a.parse_args()
out=pathlib.Path(args.out);out.mkdir(parents=True,exist_ok=False)
sources=['rtl/common/ot_secded.sv','rtl/common/ot_secded_cols.svh',
'physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v',
'rtl/common/ot_secded_dec_dp.sv',
'rtl/hbm_accel/tu/link_retry_sram_20261008/ot_hbm_replay_sram_dp.sv',
'rtl/hbm_accel/tu/link_retry_pipeline_20261009/ot_hbm_link_retry_pipeline_cl.sv',
'rtl/hbm_accel/tu/link_retry_pipeline_20261009/tb_hbm_retry_rx_slot.sv']
gates=[]
for name, flags, negative in [('legacy',[],False),('slot',['-DOT_RETRY_RX_SLOT_SAMPLE'],False),
 ('occupied_slot_mutant',['-DOT_RETRY_RX_SLOT_SAMPLE','-DOT_RETRY_MUT_RX_SLOT_HOLD'],True)]:
 cmd=['iverilog','-g2012','-I'+str(ROOT/'rtl/common'),'-s','tb_hbm_retry_rx_slot',*flags,
 '-o',str(out/name),*[str(ROOT/s) for s in sources if s.endswith(('.sv','.v'))]]
 b=subprocess.run(cmd,capture_output=True,text=True);(out/(name+'.build.log')).write_text(b.stdout+b.stderr)
 v=subprocess.run(['vvp',str(out/name)],capture_output=True,text=True) if b.returncode==0 else b
 (out/(name+'.log')).write_text(v.stdout+v.stderr)
 ok=b.returncode==0 and (v.returncode!=0 and 'occupied-slot payload changed' in v.stdout if negative else v.returncode==0 and 'PASS_ALL RX_SLOT 100 records' in v.stdout)
 gates.append(dict(name=name,negative_control=negative,pass_gate=ok,build_exit=b.returncode,run_exit=v.returncode))
r=dict(source_sha256={s:hashlib.sha256((ROOT/s).read_bytes()).hexdigest() for s in sources},gates=gates,
 exactness_gate='PASS' if all(g['pass_gate'] for g in gates) else 'FAIL',physical_qualified=False)
(out/'record.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2))
if r['exactness_gate']=='PASS':print('RX_SLOT PASS 100 records, 800 hostile held edges, legacy and slot positive plus occupied-slot negative')
raise SystemExit(0 if r['exactness_gate']=='PASS' else 1)
