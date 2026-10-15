`timescale 1ns/1ps
`default_nettype none
// Distinct paired programme family. Original ot_smh_calendar_static is unchanged.
// Both actual SRAMs read the SAME fixed PC each edge. Every original protected
// field remains checked: c7a1, PC identity, bit223 and239:234 zero. Role A0/A1
// lives INSIDE bits222:215; each plane carries215 actual calendar bits.
// Epoch-owned atomic installation: begin -> plane0/plane1 for all1024 PCs ->
// commit. Plane1 seals a pair only after that PC's plane0 committed this epoch.
// Configuration ACK is registered at actual macro write/seal/commit edge.
// No ready, repair, retry or arrival-driven action exists in execution.
module ot_smh_calendar_pair_static #(
 parameter integer W=291,TARGET=128,
 parameter integer MUT_PC=0,MUT_DATA=0,MUT_SEAL=0
)(
 input wire clk,rst_n,
 input wire cfg_begin_v,cfg_commit_v,cfg_we,
 input wire [15:0] cfg_epoch,
 input wire [10:0] cfg_addr,
 input wire [255:0] cfg_data,
 output reg cfg_ack_v,output reg [1:0] cfg_ack_kind,
 output wire [7:0] cfg_ack_target,output reg [10:0] cfg_ack_addr,
 output reg [15:0] cfg_ack_epoch,output reg [1:0] cfg_ack_resp,
 output reg ready,output reg [15:0] ready_epoch,
 input wire start_v,input wire [9:0] start_base,
 input wire [10:0] start_limit,input wire [15:0] start_loops,start_epoch,
 output reg [W-1:0] calendar,output reg calendar_v,
 output reg [31:0] ordinal,output reg active,done,fault
);
 localparam integer U0=W>215?215:W,U1=W>215?W-215:0;
 localparam [214:0] MASK0=(215'b1<<U0)-1'b1,MASK1=(215'b1<<U1)-1'b1;
 initial if(W<1||W>430||TARGET<128||TARGET>159)$fatal(1,"paired programme requires W1..430 target128..159");
 function automatic word_ok(input [255:0] word,input [9:0] address,input plane);
  reg [214:0] mask;
  begin
   mask=plane?MASK1:MASK0;
   word_ok=word[255:240]==16'hc7a1&&word[233:224]==address&&word[239:234]==0&&word[223]==0&&
     word[222:215]==(plane?8'ha1:8'ha0)&&((word[214:0]&~mask)==0);
  end
 endfunction
 reg begin_q,commit_q,we_q,start_q;
 reg [15:0] cfg_epoch_q,start_epoch_q,loops_q;
 reg [10:0] cfg_addr_q,limit_q;
 reg [9:0] base_q;
 reg [255:0] data_q;
 always @(posedge clk)begin
  cfg_epoch_q<=cfg_epoch;cfg_addr_q<=cfg_addr;data_q<=cfg_data;
  start_epoch_q<=start_epoch;loops_q<=start_loops;base_q<=start_base;limit_q<=start_limit;
 end
 always @(posedge clk or negedge rst_n)
  if(!rst_n)begin begin_q<=0;commit_q<=0;we_q<=0;start_q<=0;end
  else begin begin_q<=cfg_begin_v;commit_q<=cfg_commit_v;we_q<=cfg_we;start_q<=start_v;end
 reg [1023:0] loaded0,loaded1,sealed;
 reg install_open,epoch_valid;
 reg running;reg [9:0] pc,base;reg [10:0] limit;
 reg [15:0] loops_left;reg [31:0] issued;
 reg valid0,valid1,last0,last1,seal0,seal1;
 reg [9:0] pc0,pc1;reg [31:0] ord0,ord1;
 reg [255:0] captured0,captured1;
 wire [255:0] macro0,macro1;
 wire [429:0] pair_payload={captured1[214:0],captured0[214:0]};
 wire busy=running|valid0|valid1;
 wire cfg_any=begin_q|commit_q|we_q;
 wire cfg_unique=cfg_any&&!(begin_q&&commit_q)&&!(begin_q&&we_q)&&!(commit_q&&we_q);
 wire begin_ok=begin_q&&cfg_unique&&!start_q&&!busy&&!install_open&&!fault&&cfg_epoch_q!=0&&
   (!epoch_valid||(ready_epoch!=16'hffff&&cfg_epoch_q==ready_epoch+16'd1));
 wire write_ok=we_q&&cfg_unique&&!start_q&&!busy&&install_open&&!fault&&cfg_epoch_q==ready_epoch&&
   word_ok(data_q,cfg_addr_q[9:0],cfg_addr_q[10])&&
   (cfg_addr_q[10]?(!loaded1[cfg_addr_q[9:0]]&&(MUT_SEAL||loaded0[cfg_addr_q[9:0]])):!loaded0[cfg_addr_q[9:0]]);
 wire commit_ok=commit_q&&cfg_unique&&!start_q&&!busy&&install_open&&!fault&&cfg_epoch_q==ready_epoch&&(&sealed);
 wire start_ok=start_q&&!cfg_any&&!busy&&!install_open&&ready&&!fault&&start_epoch_q==ready_epoch&&
   limit_q>{1'b0,base_q}&&limit_q<=1024&&loops_q!=0;
 wire read_ok=valid1&&seal1&&word_ok(captured0,pc1,1'b0)&&word_ok(captured1,pc1,1'b1)&&!fault&&!cfg_any&&!start_q;
 wire final_issue=({1'b0,pc}+11'd1==limit)&&loops_left==1;
 assign cfg_ack_target=8'(TARGET);
 ot_sram_1r1w_1024x256_m2_r2c2 programme0(
  .clk(clk),.r_ce_in(running&&!fault),.r_addr_in(pc),.rd_out(macro0),
  .w_ce_in(write_ok&&!cfg_addr_q[10]),.w_addr_in(cfg_addr_q[9:0]),.wd_in(data_q),.w_mask_in({256{1'b1}}),
  .rr_en(2'b00),.rr_addr(18'd0),.cr_en(2'b00),.cr_sel(16'd0));
 ot_sram_1r1w_1024x256_m2_r2c2 programme1(
  .clk(clk),.r_ce_in(running&&!fault),.r_addr_in(pc^(MUT_PC?10'd1:10'd0)),.rd_out(macro1),
  .w_ce_in(write_ok&&cfg_addr_q[10]),.w_addr_in(cfg_addr_q[9:0]),.wd_in(data_q),.w_mask_in({256{1'b1}}),
  .rr_en(2'b00),.rr_addr(18'd0),.cr_en(2'b00),.cr_sel(16'd0));
 always @(posedge clk)begin
  captured0<=macro0;captured1<=macro1;pc0<=pc;pc1<=pc0;ord0<=issued;ord1<=ord0;
  calendar<=read_ok?(pair_payload[W-1:0]^(MUT_DATA?{{(W-1){1'b0}},1'b1}:{W{1'b0}})):{W{1'b0}};
  ordinal<=ord1;
 end
 always @(posedge clk or negedge rst_n)begin
  if(!rst_n)begin
   loaded0<=0;loaded1<=0;sealed<=0;install_open<=0;epoch_valid<=0;ready<=0;ready_epoch<=0;
   cfg_ack_v<=0;cfg_ack_kind<=0;cfg_ack_addr<=0;cfg_ack_epoch<=0;cfg_ack_resp<=0;
   running<=0;pc<=0;base<=0;limit<=0;loops_left<=0;issued<=0;
   valid0<=0;valid1<=0;last0<=0;last1<=0;seal0<=0;seal1<=0;
   calendar_v<=0;active<=0;done<=0;fault<=0;
  end else begin
   cfg_ack_v<=cfg_any;cfg_ack_kind<=begin_q?2'd1:commit_q?2'd2:2'd0;
   cfg_ack_addr<=cfg_addr_q;cfg_ack_epoch<=cfg_epoch_q;
   cfg_ack_resp<=(begin_ok||write_ok||commit_ok)?2'd0:2'd2;
   if(cfg_any&&!(begin_ok||write_ok||commit_ok))fault<=1;
   if(begin_ok)begin
    loaded0<=0;loaded1<=0;sealed<=0;install_open<=1;epoch_valid<=1;ready<=0;ready_epoch<=cfg_epoch_q;
   end
   if(write_ok)begin
    if(cfg_addr_q[10])begin loaded1[cfg_addr_q[9:0]]<=1;sealed[cfg_addr_q[9:0]]<=1;end
    else loaded0[cfg_addr_q[9:0]]<=1;
   end
   if(commit_ok)begin install_open<=0;ready<=1;end
   valid0<=running&&!fault;valid1<=valid0;last0<=running&&final_issue;last1<=last0;
   seal0<=sealed[pc];seal1<=seal0;
   calendar_v<=read_ok;done<=read_ok&&last1;active<=busy&&!fault;
   if(valid1&&!read_ok)fault<=1;
   if(start_q)begin
    if(!start_ok)fault<=1;
    else begin running<=1;pc<=base_q;base<=base_q;limit<=limit_q;loops_left<=loops_q;issued<=0;end
   end
   if(running)begin
    issued<=issued+1;
    if({1'b0,pc}+11'd1==limit)begin
     if(loops_left==1)running<=0;
     else begin pc<=base;loops_left<=loops_left-1;end
    end else pc<=pc+1;
   end
   if(fault)running<=0;
  end
 end
endmodule
`default_nettype wire
