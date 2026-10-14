#!/usr/bin/env python3
import json,re,hashlib,importlib.util,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];O=ROOT/'results/arch/hbm_native_1013/frontc_parent_1014';D=O/'bench_deps';D.mkdir(exist_ok=True)
spec=importlib.util.spec_from_file_location('smphy',ROOT/'tools/hbm_accel_smh_physical.py');mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
paths=[p for p in mod.RTL if p!='rtl/hbm_accel/sm/ot_hbm_accel_smh.sv' and not p.endswith('_bb.v')]+['rtl/hbm_accel/sm/ot_hbm_accel_int8_line.sv','rtl/lib/ot_rst_relay.sv','physical/hbm_accel_macros/ot_sram_1r1w_512x256_m1_r2c2/ot_sram_1r1w_512x256_m1_r2c2.v','physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v']
receipts=[];files=['source_literal.sv','frontc_parent.sv','frontc_tb.sv','stdcell_functional.sv']
for i,p in enumerate(paths):
 b=subprocess.check_output(['git','show','49b00f711:'+p],cwd=ROOT);name=f'{i:02d}_'+Path(p).name;(D/name).write_bytes(b);files.append('bench_deps/'+name);receipts.append(dict(source=p,source_commit='49b00f711',file='bench_deps/'+name,sha256=hashlib.sha256(b).hexdigest()))
ports=json.loads((O/'census.json').read_text())['modules']['ot_smh_frontc_native_parent']['ports']
names=['u_bc','u_is','u_xl','u_tw','u_te','u_rw','u_re','u_bw','u_be']
data={k:v for k,v in ports.items() if not k.startswith(('raw_','rst_'))}
lines=['`timescale 1ns/1ps','module tb;','reg clk=0, rst_n=0; integer cyc, j, checked=0, mismatches=0, xbeats=0, requests=0, responses=0, posted_desc=0, posted_ops=0, desc_credit=10, op_credit=10; reg mut_clk=0; reg [31:0] rnd=32\'h31415926;','reg[41:0] pending[0:1023]; integer due[0:1023]; integer wp=0,rp=0;','function automatic [31:0] next_rand(input [31:0] a); reg[31:0] b; begin b=a^(a<<13); b=b^(b>>17); next_rand=b^(b<<5);end endfunction']
for k,v in data.items():
 w=len(v['bits']);rg='' if w==1 else f'[{w-1}:0] '
 lines.append((f'reg {rg}{k}=0;' if v['direction']=='input' else f'wire {rg}g_{k},d_{k}; reg {rg}prev_{k}=0; integer activity_{k}=0;'))
g=['.clk(clk)','.rst_n(rst_n)'];d=[]
for n in names:d.extend([f'.raw_{n}('+('mut_clk?1\'b0:clk' if n=='u_xl' else 'clk')+')',f'.rst_{n}(rst_n)'])
for k,v in data.items():
 if v['direction']=='input':g.append(f'.{k}({k})');d.append(f'.{k}({k})')
 else:g.append(f'.{k}(g_{k})');d.append(f'.{k}(d_{k})')
lines += ['ot_hbm_accel_smh_front_c u_gold('+','.join(g)+');','ot_smh_frontc_native_parent u_dut('+','.join(d)+');','initial begin mut_clk=$test$plusargs("MUTCLK"); for(cyc=0;cyc<8192;cyc=cyc+1) begin','clk=0; rst_n=!(cyc<16 || (cyc>=4096 && cyc<4112));','fd_v=0; fs_v=0; fp_v=0; fq_ret=0; fr_rl=g_fo_pbz[1]; fsv=0;','if(!rst_n) begin desc_credit=10;op_credit=10;wp=0;rp=0; end else begin','desc_credit=desc_credit+g_fd_ret;op_credit=op_credit+g_fs_ret;','if(cyc%256==32 && desc_credit>0) begin fd_v=1; fd_d={32\'(posted_desc*16),24\'d16}; desc_credit=desc_credit-1; posted_desc=posted_desc+1;end','if(cyc%256==36 && op_credit>0) begin fs_v=1;fs_d={13\'d8,16\'d2,8\'d1,1\'b0,2\'d0,7\'d3};op_credit=op_credit-1;posted_ops=posted_ops+1;end','if(g_fq_v) begin if(wp-rp>=1000)$fatal(1,"request queue overflow"); pending[wp%1024]=g_fq_d;due[wp%1024]=cyc+7+(wp%5);wp=wp+1;fq_ret=1;requests=requests+1;end','if(rp<wp && due[rp%1024]<=cyc) begin fp_v=1;for(j=0;j<34;j=j+1)begin rnd=next_rand(rnd);fp_d[j*32+:32]=rnd;end fp_d[1097:1088]=pending[rp%1024][41:32];rp=rp+1;responses=responses+1;end','end','for(j=0;j<64;j=j+1)begin rnd=next_rand(rnd);fx_b[j*32+:32]=rnd;end','fx_b[2067:2048]=20\'(cyc);fx_b[2068]=rst_n&&(cyc%7<4);if(fx_b[2068])xbeats=xbeats+1;','#0.4166665;clk=1;#0.200;','if(cyc>32) begin checked=checked+1;']
for k,v in data.items():
 if v['direction']=='output':lines += [f'if(g_{k} !== d_{k}) begin mismatches=mismatches+1;if(mismatches<8)$display("FRONTC_MISMATCH cycle=%0d port={k}",cyc);end',f'if(g_{k} !== prev_{k})activity_{k}=activity_{k}+1;prev_{k}=g_{k};']
lines += ['end #0.2166665; end','$display("FRONTC_EXACT checked=%0d mismatches=%0d xbeats=%0d descriptors=%0d ops=%0d requests=%0d responses=%0d",checked,mismatches,xbeats,posted_desc,posted_ops,requests,responses);']
for k,v in data.items():
 if v['direction']=='output':lines.append(f'$display("FRONTC_ACTIVITY {k} %0d",activity_{k});')
lines += ['if(requests<8 || responses<8 || xbeats<100)$fatal(1,"frontC activity insufficient");','if(mismatches!=0)$fatal(1,"frontC literal comparison mismatch");$finish;end endmodule']
(O/'frontc_tb.sv').write_text('\n'.join(lines)+'\n');(O/'stdcell_functional.sv').write_text('module HB4xp67_ASAP7_75t_R(input wire A,output wire Y);assign Y=A;endmodule\n')
(O/'bench_sources.json').write_text(json.dumps(dict(status='FULL_NINE_REAL_CHILD_RTL_AND_REAL_GENERATED_SRAM_FUNCTIONAL_MODEL_NO_TIMING_QUALIFICATION',sources=receipts),indent=2)+'\n')
(O/'bench_build.sh').write_text('#!/bin/bash\nset -euo pipefail\ncd "$(dirname "$0")"\nV=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}\n"$V" --binary --timing -j 4 -Wno-fatal -DSYNTHESIS -DOT_SMH_FC_HIER --top-module tb --Mdir work_bench '+' '.join(files)+' > bench_build.log 2>&1\n')
(O/'bench_run.sh').write_text('#!/bin/bash\nset -euo pipefail\ncd "$(dirname "$0")"\nif [ "${1:-split}" = mut ]; then exec ./work_bench/Vtb +MUTCLK; else exec ./work_bench/Vtb; fi\n')
print('Generated full front real child+SRAM comparison, badactualRAWmapping mutant')
