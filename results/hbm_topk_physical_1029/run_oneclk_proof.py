#!/usr/bin/env python3
import argparse,json,subprocess,hashlib
from pathlib import Path
ap=argparse.ArgumentParser();ap.add_argument('repo',type=Path);ap.add_argument('packet',type=Path);ap.add_argument('out',type=Path);a=ap.parse_args();repo=a.repo.resolve();packet=a.packet.resolve();out=a.out.resolve();out.mkdir(parents=True,exist_ok=False)
r=json.load(open(packet/'oneclk_report.json'));assert r['extra_oneclk_data_or_control_cycles']==0 and r['existing_write_visibility_cycles']==2
src=(packet/'source/physical_public_only.sv').read_text();assert src.count('wire[7:0]clk_mem={8{clk}};')==1
bench=(repo/'results/hbm_topk_wpipe_1029/tb_idx_link_wpipe.sv').read_text()
bench=bench.replace('ot_hbm_idx_topk_link_static_serial_reference refdut','ot_hbm_idx_topk_link_static #(.WRITE_PIPE_STAGES(2)) refdut')
bench=bench.replace('ot_hbm_idx_topk_link_static_core #(.MUT(MUT),.WRITE_PIPE_STAGES(WPIPE)) dut(.clk(clk),.clk_mem({8{clk}}),','ot_hbm_idx_topk_link_static_physical_oneclk #(.MUT(MUT),.WRITE_PIPE_STAGES(WPIPE)) dut(.clk(clk),')
for name in ('we','wa','wd'):bench=bench.replace('refdut.'+name,'refdut.core.'+name)
for name in ('mem_we','mem_wa','mem_wd'):bench=bench.replace('dut.'+name,'dut.core.'+name)
bench=bench.replace('always @(posedge clk or negedge rst_n)begin\n  if(!rst_n)begin hw0','always @(posedge clk or negedge refdut.rst_core_n)begin\n  if(!refdut.rst_core_n)begin hw0')
bench=bench.replace('else if(clear)begin hw0','else if(refdut.clear_r)begin hw0')
bench=bench.replace('if(WPIPE==2&&(!rst_n||clear)&&dut.core.mem_we!==0)','if(WPIPE==2&&(!dut.rst_core_n||dut.clear_r)&&dut.core.mem_we!==0)')
bench=bench.replace('if(rst_n&&!clear&&WPIPE==2)','if(dut.rst_core_n&&!dut.clear_r&&WPIPE==2)')
bench=bench.replace('due[cycle+2]=1','due[cycle+4]=1')
bench=bench.replace('integer cycle=0,errors=0,','always @(clk) #1 if(dut.clk_mem!=={8{clk}}) $fatal(1,"ONECLK_WRONG_PHASE_CONTROL");\n integer cycle=0,errors=0,')
(out/'tb_public_oneclk.sv').write_text(bench)
base=[repo/'rtl/hbm_accel/index/ot_hbm_idx_topk_link_static.sv',repo/'rtl/hbm_accel/index/ot_hbm_idx_compact_tree.sv',repo/'physical/asap7_memory_macros_v2/ot_sram_1r1w_64x512_m1_r2c2/ot_sram_1r1w_64x512_m1_r2c2.v',out/'tb_public_oneclk.sv']
results=[]
for mut,clockmut in [(0,0),(1,0),(0,1)]:
 tag=f'm{mut}c{clockmut}';phy=out/('physical_'+tag+'.sv');phy.write_text(src.replace('wire[7:0]clk_mem={8{clk}};','wire[7:0]clk_mem={~clk,{7{clk}}};') if clockmut else src)
 with (out/('build_'+tag+'.log')).open('w') as fd:subprocess.run(['iverilog','-g2012','-s','tb_idx_link_wpipe','-Ptb_idx_link_wpipe.WPIPE=2',f'-Ptb_idx_link_wpipe.MUT={mut}','-o',str(out/(tag+'.vvp'))]+list(map(str,base+[phy])),stdout=fd,stderr=subprocess.STDOUT,check=True)
 p=subprocess.run(['vvp',str(out/(tag+'.vvp'))],stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True);(out/('run_'+tag+'.log')).write_text(p.stdout)
 if mut==clockmut==0:assert p.returncode==0,p.stdout
 else:assert p.returncode!=0 and ('ONECLK_WRONG_PHASE_CONTROL' if clockmut else 'dense compaction exact/miter/timeline mismatch') in p.stdout,p.stdout
 results.append(dict(tag=tag,rc=p.returncode,result='PASS' if mut==clockmut==0 else 'CONTROL_CAUGHT'))
print(json.dumps(dict(status='PUBLIC_NATIVE_ONECLK_LOCKSTEP_PASS',results=results,physical_source_sha256=r['physical_source_sha256'],source_cycles_added=0,existing_internal_SRAM_commit_edges=2,scope='Both PUBLIC native masters with existing input/output PIN stages, four compiler calendar frames/full bits/real SRAM; oneclk removes only eight same-source clock pins. Physical gen outer face shell unchanged and not a die token pass.'),indent=2))
