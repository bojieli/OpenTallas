`timescale 1ns/1ps
`default_nettype none
// H-NETLIST/vmsm 2026-10-15: the die home of the HBM stack fault glue (G-ENG-STACK-FAULT).  At die level the service
// engine is flattened into 32 controller leaves ot_hbm_svc_pc_ctrl_leaf per quadrant; the channel-pair command check
// (ca_fault: both PCs of channel c issue a row command on the same edge -- the shared CA bus of
// ot_hbm_svc_native_sector_pipeline_leaves) and the fault OR of that parent had no tile.  One leaf per quadrant:
//   hbm_clk side : row_v[31:0] (tap of each ctl.row_v, the controller's registered PHY command valid), pc_fault[31:0],
//                  owner_fault[31:0] -> pin registers -> sticky ca / pc / owner bits;
//   stream_clk   : svg_fault[7:0] (ot_hbm_svc_sm_group.fault), share_fault[7:0] (ot_hbm_svc_vm_kshare.fault),
//                  del_fault[7:0] (ot_hbm_svc_vmdel_lane.fault), cal_fault (fill calendar) -> pin registers -> sticky
//                  (svg_fault is the group's feed||issuer OR across its hbm/stream domains: one extra synchroniser flop);
//   the hbm sticky bits enter the stream domain through two synchroniser flops (sticky levels: no handshake needed).
// Outputs (stream_clk, registers): fault (any), status[6:0] = {cal, del, share, svg, owner, pc, ca}.  The ca check sees
// row_v one edge after the controller (pin register), same pair rule as the parent.  MUT=1 checks pairs (2c, 2c+2).
module ot_hbm_svc_stack_fault #(parameter integer MUT=0) (
 input wire hbm_clk,hbm_rst_n,stream_clk,stream_rst_n,
 input wire[31:0]row_v,pc_fault,owner_fault,
 input wire[7:0]svg_fault,share_fault,del_fault,input wire cal_fault,
 output reg fault,output reg[6:0]status
);
 reg[31:0]rv_q,pf_q,of_q;reg ca,pc,ow;
 always @(posedge hbm_clk or negedge hbm_rst_n)begin
  if(!hbm_rst_n)begin rv_q<=0;pf_q<=0;of_q<=0;ca<=0;pc<=0;ow<=0;end
  else begin
   rv_q<=row_v;pf_q<=pc_fault;of_q<=owner_fault;
   for(integer c=0;c<16;c=c+1)
    if(rv_q[2*c]&&rv_q[(MUT==1)?((2*c+2)%32):(2*c+1)])ca<=1;
   if(|pf_q)pc<=1;
   if(|of_q)ow<=1;
  end
 end
 reg[7:0]sg_q,sg_q2,sh_q,dl_q;reg cl_q;reg[2:0]h1,h2;reg sg,sh,dl,cl;
 always @(posedge stream_clk or negedge stream_rst_n)begin
  if(!stream_rst_n)begin sg_q<=0;sg_q2<=0;sh_q<=0;dl_q<=0;cl_q<=0;h1<=0;h2<=0;sg<=0;sh<=0;dl<=0;cl<=0;fault<=0;status<=0;end
  else begin
   sg_q<=svg_fault;sg_q2<=sg_q;sh_q<=share_fault;dl_q<=del_fault;cl_q<=cal_fault;
   h1<={ow,pc,ca};h2<=h1;
   if(|sg_q2)sg<=1;if(|sh_q)sh<=1;if(|dl_q)dl<=1;if(cl_q)cl<=1;
   status<={cl,dl,sh,sg,h2};
   fault<=cl||dl||sh||sg||(|h2);
  end
 end
endmodule
`default_nettype wire
