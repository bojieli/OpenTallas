`timescale 1ns/1ps
`default_nettype none
// One compiler-reserved tail home: the existing four parameter ROMs serve
// coefficient jobs and final-head gain loads at disjoint fixed-cycle slots.
// The mode is sampled on start, held through fixed completion and checked.
// No availability, completion, credits or returned commits gate issue.
module ot_s81_hcx_post_gain_native #(
 parameter integer RL=4,WL=4,MUT_POST=0,MUT_GAIN=0,PRE_FORWARD=0,MUT_PRE=0,
 parameter IMAGE="hcx_post"
)(
 input wire clk,rst_n,start,gain_mode,gain_draft,ffn,
 input wire [13:0] raw_base_row,coef_base_row,gain_base_row,
 input wire [5:0] layer_idx,
 input wire [31:0] norm_eps,
 input wire [15:0] compiled_cycles,
 output wire done,
 output wire rq_v,output wire [13:0] rq_row,
 input wire rs_v,input wire [511:0] rs_d,
 output wire wq_v,output wire [13:0] wq_row,
 output wire [15:0] wq_mask,output wire [511:0] wq_d,
 input wire wq_commit,
 // Native pending-pre layer boundary. Required when PRE_FORWARD=1.
 input wire pre_in_v,input wire [127:0] pre_in_data,
 output wire pre_out_v,output wire [127:0] pre_out_data,
 output wire fault
);
 reg active_gain,busy,join_fault;
 wire pdone,pfault,gdone,gfault,gbusy;
 wire pce,gce;wire[11:0]pa,ga;
 wire pv,gv,prv;wire[13:0]prow,grow,prrow;
 wire[15:0]pm,gm;wire[511:0]pdat,gdat,forwarded_pdat;wire pre_fault;
 wire[287:0]pq;
 wire[255:0]rd={pq[216+:64],pq[144+:64],pq[72+:64],pq[0+:64]};
 // Selection follows the commanded owner, never a runtime request arbiter.
 wire rom_ce=active_gain?gce:pce;
 wire[11:0]rom_addr=active_gain?ga:pa;
 assign rq_v=prv&&!active_gain;assign rq_row=prrow;
 assign wq_v=active_gain?gv:pv;
 assign wq_row=active_gain?grow:prow;
 assign wq_mask=active_gain?gm:pm;
 assign wq_d=active_gain?gdat:forwarded_pdat;
 assign done=active_gain?gdone:pdone;
 assign fault=join_fault|pfault|gfault|pre_fault;
 generate if(PRE_FORWARD)begin:g_pre_forward
  ot_s81_hcx_pre_forward #(.MUT_CURRENT_PRE(MUT_PRE))forwarder(
   .clk(clk),.rst_n(rst_n),.incoming_v(pre_in_v),.incoming_pre(pre_in_data),
   .start(start&&!gain_mode),.done(pdone),.coef_base_row(coef_base_row),
   .i_v(pv),.i_row(prow),.i_mask(pm),.i_data(pdat),.o_data(forwarded_pdat),
   .outgoing_v(pre_out_v),.outgoing_pre(pre_out_data),.fault(pre_fault));
 end else begin:g_legacy_pre
  assign forwarded_pdat=pdat;assign pre_out_v=1'b0;assign pre_out_data=128'd0;assign pre_fault=1'b0;
 end endgenerate
 ot_s81_hcx_post_native #(.RL(RL),.WL(WL),.MUT_POST(MUT_POST),.EXTERNAL_ROM(1))post(
  .clk(clk),.rst_n(rst_n),.start(start&&!gain_mode),.ffn(ffn),.raw_base_row(raw_base_row),.coef_base_row(coef_base_row),
  .layer_idx(layer_idx),.norm_eps(norm_eps),.compiled_cycles(compiled_cycles),.done(pdone),
  .rq_v(prv),.rq_row(prrow),.rs_v(rs_v&&!active_gain),.rs_d(rs_d),
  .wq_v(pv),.wq_row(prow),.wq_mask(pm),.wq_d(pdat),.wq_commit(wq_commit&&!active_gain),.fault(pfault),
  .param_ce(pce),.param_addr(pa),.param_data(rd));
 ot_s81_head_gain_stream #(.WL(WL),.MUT_GAIN(MUT_GAIN))gain(
  .clk(clk),.rst_n(rst_n),.start(start&&gain_mode),.draft(gain_draft),.vm_base_row(gain_base_row),
  .rom_ce(gce),.rom_addr(ga),.rom_data(rd),.wq_v(gv),.wq_row(grow),.wq_mask(gm),.wq_d(gdat),
  .wq_commit(wq_commit&&active_gain),.busy(gbusy),.done(gdone),.fault(gfault));
 generate for(genvar m=0;m<4;m=m+1)begin:g_rom
`ifndef SYNTHESIS
  ot_rom_4096x72_m8 #(.INSTANCE($sformatf("%s_p%0d",IMAGE,m)))rom(
`else
  ot_rom_4096x72_m8 rom(
`endif
   .clk(clk),.ce_in(rom_ce),.addr_in(rom_addr),.rd_out(pq[72*m+:72]));
 end endgenerate
 always@(posedge clk or negedge rst_n)begin
  if(!rst_n)begin active_gain<=0;busy<=0;join_fault<=0;end
  else begin
   if(start)begin
    active_gain<=gain_mode;busy<=1;
    if(busy||pce||gce||pv||gv)join_fault<=1;
   end
   if(done)busy<=0;
   if(busy&&gain_mode!=active_gain)join_fault<=1;
   if((pce&&gce)||(pv&&gv)||(active_gain&&(pce||pv||prv))||(!active_gain&&(gce||gv)))join_fault<=1;
  end
 end
endmodule
`default_nettype wire
