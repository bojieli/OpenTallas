#!/usr/bin/env python3
"""Actual RTL + golden gate and two distinct synthesizable negative controls."""
import hashlib,json,pathlib,subprocess,tempfile,time
ROOT=pathlib.Path(__file__).resolve().parents[2]
OUT=ROOT/'results/rtl/s81_static_hc_1014';OUT.mkdir(parents=True,exist_ok=True)
RTL='rtl/dsrom_sys/s81_static_hc/'
common=['rtl/ot_fp32_rne_pkg.sv','rtl/hdc/ot_hdc_prefix.sv',
 'rtl/dsrom_sys/s81_ph/ot_s81ph_fp32_add_rne_preexp.sv',RTL+'s81_static_hc_reduce.sv',RTL+'s81_static_hc_assemble.sv']
bench=RTL+'test/tb_s81_static_hc.sv';faultbench=RTL+'test/tb_s81_static_hc_faults.sv'
inputs=common+[bench,faultbench,'tools/s81_static_hc/check.py']
result={'scope':'source component only; no native slot, timing or token-rate qualification',
 'source_sha256':{p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in inputs},'runs':{}}
with tempfile.TemporaryDirectory(prefix='s81-static-hc-') as tmp:
 for mut in (0,1,2):
  binary=str(pathlib.Path(tmp)/f'hc{mut}')
  subprocess.run(['iverilog','-g2012','-s','tb_s81_static_hc',f'-Ptb_s81_static_hc.MUT={mut}','-o',binary]+common+[bench],cwd=ROOT,check=True,capture_output=True,text=True)
  started=time.monotonic();run=subprocess.run(['vvp',binary],cwd=ROOT,capture_output=True,text=True)
  log=run.stdout+run.stderr;(OUT/f'mut{mut}.log').write_text(log)
  expected=('PASS static HC' in log and run.returncode==0) if mut==0 else (run.returncode!=0 and ('word mismatch' if mut==1 else 'row mismatch') in log)
  result['runs'][str(mut)]={'returncode':run.returncode,'expected_verdict':expected,'runtime_seconds':round(time.monotonic()-started,3)}
  if not expected: raise RuntimeError(log)
 binary=str(pathlib.Path(tmp)/'faults')
 subprocess.run(['iverilog','-g2012','-s','tb_s81_static_hc_faults','-o',binary,RTL+'s81_static_hc_assemble.sv',faultbench],cwd=ROOT,check=True,capture_output=True,text=True)
 run=subprocess.run(['vvp',binary],cwd=ROOT,capture_output=True,text=True)
 (OUT/'faults.log').write_text(run.stdout+run.stderr)
 result['runs']['faults']={'returncode':run.returncode,'expected_verdict':run.returncode==0 and 'PASS assembler' in run.stdout}
 if not result['runs']['faults']['expected_verdict']:raise RuntimeError(run.stdout+run.stderr)
result.update(verdict='PASS_SOURCE_ONLY',exact_words=832,production_words=320,production_rows_8192bits=20,
 word_sample_edge_to_output_edge=17,word_pipeline_register_stages=18,earliest_last_word_sample_edge_to_row_edge=19,
 production_cadence_cycles=[4,4,8],production_transport_records_per_16cycles=3,
 arithmetic_mutant='actual inner tree changed to (p0+p2)+(p1+p3)',assembly_mutant='actual destination word index xor1')
(OUT/'verdict.json').write_text(json.dumps(result,indent=2,sort_keys=True)+'\n')
print(json.dumps(result,indent=2,sort_keys=True))
