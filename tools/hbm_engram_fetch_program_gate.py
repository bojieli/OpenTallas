#!/usr/bin/env python3
"""Actual native target124 programme SRAM/issuer component contract gate."""
from __future__ import annotations
import argparse,hashlib,json,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
TB='''`timescale 1ps/1fs
module tb;
reg clk_control=0;always #416.667 clk_control=~clk_control;wire clk_mem=clk_control;
reg rst_n=0,cfg_v=0,desc_v=0,launch_v=0,token_v=0,token_first=0;
reg[7:0]cfg_target=124;reg[11:0]cfg_addr=0;reg[255:0]cfg_data=0;
reg[9:0]desc_base=0,desc_limit=42;reg[15:0]desc_loops=1;reg[16:0]token_cid=0;
reg[7:0]home_done=0,home_fault=0;
wire configured,init_busy,busy,done,fault,epoch_begin,hash_v,hash_first,fetch_start,instruction_v;
wire[16:0]hash_cid;wire[31:0]instruction;wire[9:0]instruction_pc;
ot_hbm_engram_fetch_program #(.MUT_OPCODE(`MUT_OPCODE),.MUT_DESC_TARGET(`MUT_DESC_TARGET)) dut(.*);
integer edge_no=0,launch_edge=-1,fetch_edge=-1,opchecks=0,epochs=0,hashes=0,fetches=0,mode=0;
reg[31:0]ops[0:41];
always @(posedge clk_control)begin:check
 integer rel;
 edge_no=edge_no+1;
 // Declared component boundary: status-only home completion at fixeddeadline.
 // Actual home controllers/SRAM are proved separately, not replaced for a fullnativeclaim.
 home_done<=0;
 if(fetch_start)begin fetch_edge=edge_no;fetches=fetches+1;end
 if(fetch_edge>=0 && edge_no==fetch_edge+18944)home_done<=8'hff;
 #2;
 if(rst_n && launch_edge>=0 && mode==0)begin
  if(fault)$fatal(1,"programmefault edge%0d",edge_no);
  rel=edge_no-launch_edge;
  if(instruction_v!==(rel>=5 && rel<47))$fatal(1,"exactprogrammefirst/lastage rel%0d",rel);
  if(instruction_v)begin
   if(instruction_pc!==10'(rel-5) || instruction!==ops[rel-5])$fatal(1,"actualmacroinstructiondata rel%0d",rel);
   opchecks=opchecks+1;
  end
  if(epoch_begin)epochs=epochs+1;
  if(hash_v)begin
   if(!hash_first || hash_cid!==17'd77)$fatal(1,"realproducerCIDcapture");
   hashes=hashes+1;
  end
  if(done && edge_no!=fetch_edge+18945)$fatal(1,"fixedkerneldone");
 end
end
task tick;begin @(posedge clk_control);#3;end endtask
initial begin
 if(!$value$plusargs("MODE=%d",mode))mode=0;
 for(integer i=0;i<42;i=i+1)ops[i]=0;
 ops[0]=1;ops[1]=2;ops[40]=3;
 repeat(3)tick;@(negedge clk_control);rst_n=1;
 // Unconfigured target ignores the unmasked globalC10 broadcast.
 launch_v=1;tick;@(negedge clk_control);launch_v=0;repeat(3)tick;
 if(fault || busy || instruction_v)$fatal(1,"unconfiguredglobalC10muststayquiet");
 for(integer w=0;w<6;w=w+1)begin
  @(negedge clk_control);cfg_v=1;cfg_addr=w;cfg_data=0;
  for(integer s=0;s<7;s=s+1)cfg_data[s*32+:32]=ops[w*7+s];
  tick;@(negedge clk_control);cfg_v=0;repeat(2)tick;
 end
 @(negedge clk_control);desc_v=1;tick;@(negedge clk_control);desc_v=0;
 repeat(mode==1?128:129)tick;
 if(mode==0)begin
  // Another configured target must not alter our descriptor, age or activation.
  @(negedge clk_control);cfg_target=120;desc_base=3;desc_limit=2;desc_loops=0;desc_v=1;tick;
  @(negedge clk_control);desc_v=0;repeat(3)tick;
  if(!configured || init_busy || fault)$fatal(1,"unrelateddescriptorchangedtarget124");
  cfg_target=124;desc_base=0;desc_limit=42;desc_loops=1;
 end
 @(negedge clk_control);launch_v=1;token_v=1;token_cid=77;token_first=1;tick;launch_edge=edge_no;
 @(negedge clk_control);launch_v=0;token_v=0;token_cid=999;token_first=0;
 if(mode==1)begin
  repeat(4)tick;if(!fault || instruction_v || busy)$fatal(1,"early129launchmustreject");
  $display("PASS early129descriptorlaunchfault");$finish;
 end
 repeat(18992)tick;
 if(fault || busy || opchecks!=42 || epochs!=1 || hashes!=1 || fetches!=1)$fatal(1,"fullprogrammecounts op%0d epoch%0d hash%0d fetch%0d busy%b",opchecks,epochs,hashes,fetches,busy);
 // Explicit actualdescriptor disable; no SRAM reset or software targetmask.
 launch_edge=-1;
 @(negedge clk_control);desc_base=0;desc_limit=0;desc_loops=0;desc_v=1;tick;
 @(negedge clk_control);desc_v=0;repeat(3)tick;
 if(configured || init_busy || fault)$fatal(1,"descriptor-disable");
 @(negedge clk_control);launch_v=1;tick;@(negedge clk_control);launch_v=0;repeat(4)tick;
 if(fault || busy || instruction_v || epoch_begin || hash_v || fetch_start)$fatal(1,"disabledC10muststayquiet");
 // The same actual catalogue can be reselected after disabling.
 @(negedge clk_control);desc_limit=42;desc_loops=1;desc_v=1;tick;
 @(negedge clk_control);desc_v=0;repeat(130)tick;
 if(!configured || init_busy || fault)$fatal(1,"retainedcataloguereactivation");
 $display("PASS target124 real128x256SRAM seven32bitops raw224 42instructions firstage5 consumer6 guard130 fixedkernel18945 CIDcapture unconfiguredC10 disableC10 reselect");$finish;
end
endmodule
'''
def run(out):
    out=Path(out);out.mkdir(parents=True,exist_ok=True);tb=out/'tb.sv';tb.write_text(TB)
    paths=['physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v','rtl/hbm_accel/engram_static_20261015/ot_hbm_engram_fetch_program.sv']
    runs=[]
    for name,mutant,desc_mutant,mode in [('baseline',0,0,0),('early_launch',0,0,1),('opcode_mutant',1,0,0),('descriptor_target_mutant',0,1,0)]:
        cp=subprocess.run(['iverilog','-g2012',f'-DMUT_OPCODE={mutant}',f'-DMUT_DESC_TARGET={desc_mutant}','-s','tb','-o',str(out/name),*[str(ROOT/p) for p in paths],str(tb)],capture_output=True,text=True)
        (out/f'{name}.build.log').write_text(cp.stdout+cp.stderr);assert cp.returncode==0,cp.stderr
        rp=subprocess.run(['vvp',str(out/name),f'+MODE={mode}'],capture_output=True,text=True)
        (out/f'{name}.run.log').write_text(rp.stdout+rp.stderr)
        assert (rp.returncode==0)==(mutant==0 and desc_mutant==0),rp.stdout+rp.stderr
        runs.append(dict(name=name,returncode=rp.returncode,output=rp.stdout.strip()))
    result=dict(schema='opentallas.hbm.engram.fetch_program.v1',status='pass',target=124,cfg_meaningful_bits=224,ops_per_word=7,op_width=32,
        native_words=128,pc_width=10,max_cycles=896,descriptor_launch_guard=130,first_instruction_age=5,first_consumer_age=6,
        fixed_kernel_done_after_fetch_consumer=18945,inactive_global_C10=True,unrelated_descriptor_isolation=True,explicit_disable_descriptor=dict(base=0,limit=0,loops=0),retained_catalogue_reselect=True,runs=runs,
        home_status_modeled=True,scope='Programme SRAM/issuer component only; actual homekernel and wholeoperation must compose, no fullnative/physical/performance claim',
        source_sha256={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in paths})
    (out/'receipt.json').write_text(json.dumps(result,indent=2)+'\n');return result
if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--out',required=True);a=ap.parse_args();print(json.dumps(run(a.out),indent=2))
