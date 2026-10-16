`timescale 1ns/1ps
// Q-KVSYS PVJOIN 2026-10-16: COMPILER-CONSTANT IMAGE variant of qkd_static_kv_layer_programme (same file's logic, the
// DCAL pattern: the boot image is a compile-time constant from the link compiler, no die loader, no 10,368 table flops).
// ROOTS = the 324 boot words (stage-major, 9 roots a stage, word 0 low) that the boot-loaded module would receive at
// addresses 0..323; DIGEST / EPOCH = its addresses 324 / 325 (bound authorized programme).  Image legality (every root
// in 3..stage_end-1, run >= issue + 4, quiet after the last launch, all36 sum < 2^32) is checked by the compiler
// (tools/qwen_static_kv/layer_roots_from_link.py -> layer_programme.assemble_rows) and again at elaboration here.
// Behaviour from reset: configured one edge after reset release; every start / stage / root / metadata edge identical to
// the boot-loaded module sealed with the same image (bench tools/qwen_static_kv/layer_rom_bench.sh: cycle equivalence).
// The wrapper qkd_static_kv_layer_programme_img binds the committed image layer_programme_image.svh.
// MUT 1..3 as the boot-loaded module; MUT 4 (bench only): every stage reads the next stage's roots.
module qkd_static_kv_layer_programme_rom #(parameter integer MUT=0,parameter [36*9*32-1:0] ROOTS='0,parameter [63:0] DIGEST=64'd0,parameter [15:0] EPOCH=16'd0)(
 input wire ck,rst_n,
 input wire start,authority_valid,programme_authorized,
 input wire[15:0]programme_epoch,input wire[63:0]programme_digest,
 input wire[15:0]authority_epoch,input wire[17:0]authority_token,authority_position,
 input wire[1:0]authority_generation,
 output reg ctrl_go,kgo,vgo,attention_issue,attention_run,writer_start,link_start,
 output reg stage_start,stage_done,expected_upstream_quiet,output reg[5:0]completed_stage,
 output wire[5:0]stage,output wire[5:0]layer,
 output reg[15:0]epoch,output reg[17:0]token,position,output reg[13:0]ctx_t,
 output reg[1:0]generation,
 output reg configured,active,done,fault,output reg[7:0]fault_code,
 output reg[31:0]age,token_cycles
);
 (* keep *)reg rn;always @(posedge ck)rn<=rst_n;
 reg start_q,av_q,authorized_q;
 reg[63:0]pdigest_q;reg[15:0]pepoch_q,epoch_q;reg[17:0]token_q,pos_q;reg[1:0]gen_q;
 always @(posedge ck)begin
  pdigest_q<=programme_digest;pepoch_q<=programme_epoch;
  epoch_q<=authority_epoch;token_q<=authority_token;pos_q<=authority_position;gen_q<=authority_generation;
 end
 always @(posedge ck or negedge rn)
 if(!rn)begin start_q<=0;av_q<=0;authorized_q<=0;end
 else begin start_q<=start;av_q<=authority_valid;authorized_q<=programme_authorized;end
 reg[5:0]stage_q,index_q;
 reg[31:0]r_ctrl,r_k,r_v,r_issue,r_run,r_writer,r_link,r_quiet,r_end;
 reg load_row;
 function automatic [31:0] root(input integer st,input integer w);
  root=ROOTS[(9*st+w)*32 +: 32];
 endfunction
 // elaboration-time image check (the boot-loaded module's bad_row / seal rules)
 initial begin : img_check
  integer st,w;reg[36:0]sum;sum=0;
  for(st=0;st<36;st=st+1)begin
   for(w=0;w<8;w=w+1)if(root(st,w)<3||root(st,w)>=root(st,8))$error("layer image: stage %0d root %0d outside 3..end-1",st+1,w);
   for(w=0;w<7;w=w+1)if(root(st,7)<=root(st,w))$error("layer image: stage %0d quiet before root %0d",st+1,w);
   if({1'b0,root(st,4)}<{1'b0,root(st,3)}+33'd4)$error("layer image: stage %0d run < issue + 4",st+1);
   sum=sum+{5'b0,root(st,8)};
  end
  if(sum>37'h0ffffffff||sum==0)$error("layer image: all36 duration");
 end
 assign stage=(MUT==2)?(stage_q^6'd1):stage_q;
 assign layer=stage-6'd1;
 wire[5:0] rix=(MUT==4)?((index_q==6'd35)?6'd0:index_q+6'd1):index_q;
 always @(posedge ck)if(load_row)begin
  r_ctrl<=root(rix,0);r_k<=root(rix,1);r_v<=root(rix,2);r_issue<=root(rix,3);r_run<=root(rix,4);
  r_writer<=root(rix,5);r_link<=root(rix,6);r_quiet<=root(rix,7);r_end<=root(rix,8);
 end
 always @(posedge ck or negedge rn)begin
  if(!rn)begin
   ctrl_go<=0;kgo<=0;vgo<=0;attention_issue<=0;attention_run<=0;writer_start<=0;link_start<=0;
   stage_start<=0;stage_done<=0;expected_upstream_quiet<=0;completed_stage<=0;
   epoch<=0;token<=0;position<=0;ctx_t<=0;generation<=0;
   configured<=0;active<=0;done<=0;fault<=0;fault_code<=0;age<=0;token_cycles<=0;
   stage_q<=0;index_q<=0;load_row<=0;
  end else begin
   ctrl_go<=0;kgo<=0;vgo<=0;attention_issue<=0;attention_run<=0;writer_start<=0;link_start<=0;
   stage_start<=0;stage_done<=0;done<=0;load_row<=0;
   configured<=1;
   if(fault)active<=0;
   else begin
    if(start_q)begin
     if(!configured||active||!av_q||!authorized_q||pos_q>8191||pepoch_q!=EPOCH||pdigest_q!=DIGEST)begin fault<=1;fault_code[3]<=1;end
     else begin
      epoch<=epoch_q;token<=token_q;position<=pos_q;ctx_t<=14'(pos_q+1);generation<=gen_q;
      stage_q<=1;index_q<=0;load_row<=1;active<=1;age<=0;token_cycles<=0;stage_start<=1;expected_upstream_quiet<=0;
     end
    end
    if(active)begin
     age<=age+1'b1;token_cycles<=token_cycles+1'b1;
     if(!load_row)begin
      ctrl_go<=age==r_ctrl-1;kgo<=age==r_k-1;vgo<=age==r_v-1;
      attention_issue<=age==r_issue-1;attention_run<=age==r_run-1;
      writer_start<=age==r_writer-((MUT==1)?32'd2:32'd1);link_start<=age==r_link-1;
      if(age==r_quiet-1)expected_upstream_quiet<=1;
      if(age==r_end-1)begin
       stage_done<=1;completed_stage<=stage_q;
       if(stage_q==36)begin active<=0;done<=1;end
       else begin stage_q<=stage_q+1'b1;index_q<=index_q+1'b1;load_row<=1;age<=0;stage_start<=1;expected_upstream_quiet<=0;end
      end
     end
     if(MUT==3)ctx_t<=14'(authority_position+1);
    end
   end
  end
 end
endmodule

// The die master: the ROM variant bound to the committed link-compiled image (regenerated and compared by the bench).
`include "layer_programme_image.svh"
module qkd_static_kv_layer_programme_img #(parameter integer MUT=0)(
 input wire ck,rst_n,
 input wire start,authority_valid,programme_authorized,
 input wire[15:0]programme_epoch,input wire[63:0]programme_digest,
 input wire[15:0]authority_epoch,input wire[17:0]authority_token,authority_position,
 input wire[1:0]authority_generation,
 output wire ctrl_go,kgo,vgo,attention_issue,attention_run,writer_start,link_start,
 output wire stage_start,stage_done,expected_upstream_quiet,output wire[5:0]completed_stage,
 output wire[5:0]stage,output wire[5:0]layer,
 output wire[15:0]epoch,output wire[17:0]token,position,output wire[13:0]ctx_t,
 output wire[1:0]generation,
 output wire configured,active,done,fault,output wire[7:0]fault_code,
 output wire[31:0]age,token_cycles
);
 qkd_static_kv_layer_programme_rom #(.MUT(MUT),.ROOTS(LP_ROOTS),.DIGEST(LP_DIGEST),.EPOCH(LP_EPOCH)) u_rom(.ck(ck),.rst_n(rst_n),
  .start(start),.authority_valid(authority_valid),.programme_authorized(programme_authorized),.programme_epoch(programme_epoch),
  .programme_digest(programme_digest),.authority_epoch(authority_epoch),.authority_token(authority_token),
  .authority_position(authority_position),.authority_generation(authority_generation),.ctrl_go(ctrl_go),.kgo(kgo),.vgo(vgo),
  .attention_issue(attention_issue),.attention_run(attention_run),.writer_start(writer_start),.link_start(link_start),
  .stage_start(stage_start),.stage_done(stage_done),.expected_upstream_quiet(expected_upstream_quiet),.completed_stage(completed_stage),
  .stage(stage),.layer(layer),.epoch(epoch),.token(token),.position(position),.ctx_t(ctx_t),.generation(generation),
  .configured(configured),.active(active),.done(done),.fault(fault),.fault_code(fault_code),.age(age),.token_cycles(token_cycles));
endmodule
