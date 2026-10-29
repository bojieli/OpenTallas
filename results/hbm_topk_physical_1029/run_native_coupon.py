#!/usr/bin/env python3
"""Smallest WPIPE mechanism coupon using current native caller clock expressions."""
import argparse,hashlib,json,subprocess
from pathlib import Path
ap=argparse.ArgumentParser();ap.add_argument('repo',type=Path);ap.add_argument('out',type=Path);a=ap.parse_args();repo=a.repo.resolve();o=a.out.resolve();o.mkdir(parents=True,exist_ok=False)
p=repo/'results/hbm_topk_physical_1029';r=json.load(open(p/'current_native_caller.json'))
assert r['exact_clock_bit_equality'] and r['all_port_expressions_unchanged'] and r['other_callers_unchanged']
assert r['parameter']=={'WRITE_PIPE_STAGES':2} and r['added_internal_write_visibility_cycles']==2
for f,h in r['source_files'].items():assert hashlib.sha256((repo/f).read_bytes()).hexdigest()==h,f
bench=(repo/'results/hbm_topk_wpipe_1029/tb_idx_link_wpipe.sv').read_text()
bench=bench.replace('parameter integer MUT=0,WPIPE=2;', 'parameter integer MUT=0,WPIPE=2,CMUT=0;')
needle='reg rst_n=0,clear=0,ingest_v=0,flush=0,emit_v=0;'
clockdecl='wire[0:0]hb_ckgen__pll_stream={clk};\n wire native_core_clock='+r['native_clock_expression']+';\n wire[7:0]native_mem_clocks=CMUT?{7\'d0,~clk}:'+r['native_clock_mem_expression']+';\n always @(clk) #1 if(native_mem_clocks!=={8{native_core_clock}}) $fatal(1,"NATIVE_CLOCK_ALIAS_CONTROL");\n '
bench=bench.replace(needle,clockdecl+needle)
needle='dut(.clk(clk),.clk_mem({8{clk}}),'
assert needle in bench
bench=bench.replace(needle,'dut(.clk(native_core_clock),.clk_mem(native_mem_clocks),')
(o/'tb_native.sv').write_text(bench)
files=[repo/f for f in r['source_files']]+[repo/'tools/hbm_b2/topk_tree/serial_reference.sv',repo/'physical/asap7_memory_macros_v2/ot_sram_1r1w_64x512_m1_r2c2/ot_sram_1r1w_64x512_m1_r2c2.v',o/'tb_native.sv']
results=[]
for mut,cmut in [(0,0),(4,0),(5,0),(6,0),(0,1)]:
 tag=f'm{mut}c{cmut}';v=o/(tag+'.vvp')
 cmd=['iverilog','-g2012','-s','tb_idx_link_wpipe','-Ptb_idx_link_wpipe.WPIPE=2',f'-Ptb_idx_link_wpipe.MUT={mut}',f'-Ptb_idx_link_wpipe.CMUT={cmut}','-o',str(v)]+list(map(str,files))
 with (o/('build_'+tag+'.log')).open('w') as fd:subprocess.run(cmd,stdout=fd,stderr=subprocess.STDOUT,check=True)
 rr=subprocess.run(['vvp',str(v)],stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True);(o/('run_'+tag+'.log')).write_text(rr.stdout)
 if mut==cmut==0:assert rr.returncode==0,rr.stdout
 else:
  assert rr.returncode!=0,tag
  assert ('NATIVE_CLOCK_ALIAS_CONTROL' if cmut else 'dense compaction exact/miter/timeline mismatch') in rr.stdout,rr.stdout
 results.append(dict(tag=tag,exit=rr.returncode,expectation='PASS' if mut==cmut==0 else 'CONTROL_CAUGHT'))
print(json.dumps(dict(caller_source_sha256=r['candidate_sha256'],results=results,added_internal_SRAM_visibility_edges=2,added_outer_IO_edges=0,scope='Current native caller clock aliases plus full-shape core mechanism. Existing native input/output shell unchanged by caller/source receipt; not a full die bound token pass or physical clock signoff.'),indent=2))
