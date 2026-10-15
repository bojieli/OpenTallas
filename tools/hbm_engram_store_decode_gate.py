#!/usr/bin/env python3
"""Actual mapped SRAM+eight-scale decoder check on source-pinned external rows."""
from __future__ import annotations
import argparse,hashlib,json,subprocess,shutil
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def bench():
    return '''`timescale 1ns/1ps
module tb;
reg clk=0;always #5 clk=~clk;
reg rst_n=0,epoch_begin=0,write_v=0,read_v=0;reg[4:0]write_row=0,read_row=0;
reg[3:0]write_sector=0,read_sector=0;reg[255:0]write_data=0;
wire raw_v;wire[4:0]raw_row;wire[3:0]raw_sector;wire[255:0]raw_data;
wire out_v,fault;wire[4:0]out_row;wire[2:0]out_block;wire[511:0]out_data;
ot_hbm_engram_row_store_decode #(.MUT_SCALE(`MUT_SCALE)) dut(.*);
reg[255:0]external_sector[0:431];reg[511:0]expected[0:383];
reg[10000:0]due=0,raw_due=0;integer raw_word[0:10000];integer due_row[0:10000],due_block[0:10000],due_word[0:10000];
integer edge_no=0,checks=0,raw_checks=0,layer=0,r,s,idx;reg expect_fault=0;
always @(posedge clk)begin
 edge_no=edge_no+1;
 #2;
 if(rst_n)begin
  if(fault && !expect_fault)$fatal(1,"store/scale fault");
  if(raw_v!==raw_due[edge_no])$fatal(1,"raw response calendar");
  if(raw_due[edge_no])begin
   if(raw_data!==external_sector[raw_word[edge_no]] || raw_row!==(raw_word[edge_no]%216)/9 || raw_sector!==raw_word[edge_no]%9)$fatal(1,"raw response identity/data");
   raw_checks=raw_checks+1;
  end
  if(out_v!==due[edge_no])$fatal(1,"exactreadcalendar edge%0d v%b want%b",edge_no,out_v,due[edge_no]);
  if(due[edge_no])begin
   if(out_row!==due_row[edge_no] || out_block!==due_block[edge_no] || out_data!==expected[due_word[edge_no]])
    $fatal(1,"actual SRAM/decode mismatch edge%0d row%0d block%0d",edge_no,out_row,out_block);
   checks=checks+1;
  end
 end
end
task tick;begin @(posedge clk);#3;end endtask
initial begin
 $readmemh("external_hbm_sectors.hex",external_sector);$readmemh("expected_bf16.hex",expected);
 repeat(3)tick;@(negedge clk);rst_n=1;
 for(layer=0;layer<2;layer=layer+1)begin
  @(negedge clk);epoch_begin=1;write_v=0;read_v=0;tick;@(negedge clk);epoch_begin=0;
  for(r=0;r<24;r=r+1)for(s=0;s<9;s=s+1)begin
   @(negedge clk);write_v=1;write_row=r;write_sector=s;write_data=external_sector[layer*216+r*9+s];tick;
  end
  @(negedge clk);write_v=0;repeat(4)tick;
  // Actual scale sector8 first, then all8code sectors; continuous reservedreads.
  for(r=0;r<24;r=r+1)for(idx=0;idx<9;idx=idx+1)begin
   s=(idx==0)?8:idx-1;
   @(negedge clk);read_v=1;read_row=r;read_sector=s;
   raw_due[edge_no+4]=1;raw_word[edge_no+4]=layer*216+r*9+s;
   if(s!=8)begin due[edge_no+4]=1;due_row[edge_no+4]=r;due_block[edge_no+4]=s;due_word[edge_no+4]=layer*192+r*8+s;end
   tick;
  end
  @(negedge clk);read_v=0;repeat(5)tick;
 end
 if(checks!=384 || raw_checks!=432)$fatal(1,"full48rowoutputcount");
 @(negedge clk);epoch_begin=1;tick;@(negedge clk);epoch_begin=0;read_v=1;read_row=0;read_sector=8;expect_fault=1;
 tick;if(!fault)$fatal(1,"unwritten retained oldepoch must fault");
 @(negedge clk);read_v=0;rst_n=0;tick;
 $display("PASS actual2macros SRAM source48rows 384blocks 12288BF16 eight-scales raw432 epochreuse unwrittenfault exactreadage3");$finish;
end
endmodule
'''

def run(out,inputs):
    out=Path(out);out.mkdir(parents=True,exist_ok=True);inputs=Path(inputs)
    binding=json.loads((inputs/'receipt.json').read_text())
    for name in ['external_hbm_sectors.hex','expected_bf16.hex']:
        raw=(inputs/name).read_bytes();assert hashlib.sha256(raw).hexdigest()==binding['data_sha256'][name]
        (out/name).write_bytes(raw)
    tb=out/'tb.sv';tb.write_text(bench())
    paths=['physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v',
        'rtl/hdc/v41/ot_hdc_engram_tables_shipped_pkg.sv','rtl/hdc/v41/ot_hdc_engram_gather.sv',
        'rtl/hbm_accel/engram_static_20261015/ot_hbm_engram_row_store_decode.sv']
    runs=[]
    for name,mutant in [('baseline',0),('reuse_scale0',1)]:
        cp=subprocess.run(['iverilog','-g2012',f'-DMUT_SCALE={mutant}','-s','tb','-o',str((out/name).resolve()),*[str(ROOT/p) for p in paths],str(tb)],capture_output=True,text=True)
        (out/f'{name}.build.log').write_text(cp.stdout+cp.stderr);assert cp.returncode==0,cp.stderr
        rp=subprocess.run(['vvp',str((out/name).resolve())],cwd=out,capture_output=True,text=True)
        (out/f'{name}.run.log').write_text(rp.stdout+rp.stderr)
        assert (rp.returncode==0)==(mutant==0),rp.stdout+rp.stderr
        runs.append(dict(name=name,returncode=rp.returncode,output=rp.stdout.strip()))
    receipt=dict(schema='opentallas.hbm.engram.store_decode.v1',status='pass',actual_rows=48,bf16_elements=12288,
        actual_macros=2,epochs=2,raw_sectors=432,epoch_reuse_without_global_reset=True,unwritten_old_epoch_fault=True,read_latency_edges=3,source_binding=binding['data_sha256'],runs=runs,
        scope='Actual288B source rows -> actual128x256 SRAM macros -> real per32-code UE8M0/E4M3 decode, externalstimulus at write face',
        dma_coll_hash_join_qualified=False,physical_qualified=False,
        source_sha256={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in paths})
    (out/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n');return receipt
if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--out',required=True);ap.add_argument('--inputs',required=True);a=ap.parse_args();print(json.dumps(run(a.out,a.inputs),indent=2))
