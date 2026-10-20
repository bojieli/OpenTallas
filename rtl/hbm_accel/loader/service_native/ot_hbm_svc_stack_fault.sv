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
//   the hbm sticky bits enter the stream domain through one ot_hbm_svc_fault_cdc each (HBMA-SVC 10-17, was two flops).
// Outputs (stream_clk, registers): fault (any), status[6:0] = {cal, del, share, svg, owner, pc, ca}.  The ca check sees
// row_v one edge after the controller (pin register), same pair rule as the parent.  MUT=1 checks pairs (2c, 2c+2).
// OWN_W (H-NETLIST 1815, PC H8 adoption): owner fault bits per controller (H8 ot_hbm_svc_pc_ctrl_leaf_cfg_h8 exports six
// registered sticky classes owner_fault_split[5:0]); the sticky owner bit is the OR of all of them.  OWN_W=1 is the
// original module exactly.
// NPC / NG / ND (RTL-BUILD-HBM/stk 2026-10-18, d4g plan (b) per-quadrant stack fault; defaults 32 / 8 / 8 = the per-stack
// module exactly): NPC controllers (row_v / pc_fault / owner_fault), NG SM groups (svg_fault / share_fault), ND delivery
// lanes (del_fault).  The d4g quadrant instance sfault_<q> is NPC 16 (its PCs 16q'..16q'+15: channel pairs (2c, 2c+1)
// never straddle the W/E halves), NG 4 (its svg / vmks leaves), ND 8 (its vmdel_<q>0..7), cal_fault = its fill calendar.
// MUT=1 with NPC 16 checks pairs (2c, (2c+2) mod 16).  MUT=2 drops the owner class crossing (bench mutant).
module ot_hbm_svc_stack_fault #(parameter integer MUT=0, parameter integer OWN_W=1,
                                parameter integer NPC=32, parameter integer NG=8, parameter integer ND=8) (
 input wire hbm_clk,hbm_rst_n,stream_clk,stream_rst_n,
 input wire[NPC-1:0]row_v,pc_fault,input wire[NPC*OWN_W-1:0]owner_fault,
 input wire[NG-1:0]svg_fault,share_fault,input wire[ND-1:0]del_fault,input wire cal_fault,
 output reg fault,output reg[6:0]status
);
 // HBMA-SVC 2026-10-17 (native CDC rule, async_gray_fifo profile; owner regional reset): every hbm -> stream crossing
 // goes through the audited Gray FIFO (ot_hbm_svc_fault_cdc, one per sticky class) instead of the former ad hoc two-flop
 // level synchroniser h1/h2; each reset pin lands on ONE reviewed reset conditioner (ot_reset_sync, assert async,
 // release synchronous) and only the sticky / status flops clear from it; the pin flops are data (no reset).  Status
 // values are unchanged (sticky); detection latency of ca/pc/owner grows from 2 stream edges to the FIFO online +
 // synchroniser latency (fault path only, no production timing).  MUT=2 (bench): the owner class crossing is dropped.
 // HBM-KITS-B/SFAULT 2026-10-18: merge e37520d6c kept the NPC/NG/ND header of 1ad261112 but dropped this CDC body
 // (ca_s/pc_s/ow_s undeclared, h1/h2 dead); restored here on the parameterised ports.
 wire hrst,srst;
 ot_reset_sync u_hrst(.clk(hbm_clk),.async_rst_n(hbm_rst_n),.sync_rst_n(hrst));
 ot_reset_sync u_srst(.clk(stream_clk),.async_rst_n(stream_rst_n),.sync_rst_n(srst));
 reg[NPC-1:0]rv_q,pf_q;reg[NPC*OWN_W-1:0]of_q;reg ca,pc,ow;
 always @(posedge hbm_clk)begin rv_q<=row_v;pf_q<=pc_fault;of_q<=owner_fault;end
 always @(posedge hbm_clk or negedge hrst)begin
  if(!hrst)begin ca<=0;pc<=0;ow<=0;end
  else begin
   for(integer c=0;c<NPC/2;c=c+1)
    if(rv_q[2*c]&&rv_q[(MUT==1)?((2*c+2)%NPC):(2*c+1)])ca<=1;
   if(|pf_q)pc<=1;
   if(|of_q)ow<=1;
  end
 end
 wire ca_s,pc_s,ow_s;
 ot_hbm_svc_fault_cdc u_ca(.wr_clk(hbm_clk),.wr_rst_n(hrst),.rd_clk(stream_clk),.rd_rst_n(srst),.src_fault(ca),
  .dst_fault(ca_s),.wr_overflow(),.rd_underflow());
 ot_hbm_svc_fault_cdc u_pc(.wr_clk(hbm_clk),.wr_rst_n(hrst),.rd_clk(stream_clk),.rd_rst_n(srst),.src_fault(pc),
  .dst_fault(pc_s),.wr_overflow(),.rd_underflow());
 ot_hbm_svc_fault_cdc u_ow(.wr_clk(hbm_clk),.wr_rst_n(hrst),.rd_clk(stream_clk),.rd_rst_n(srst),.src_fault((MUT==2)?1'b0:ow),
  .dst_fault(ow_s),.wr_overflow(),.rd_underflow());
 reg[NG-1:0]sg_q,sg_q2,sh_q;reg[ND-1:0]dl_q;reg cl_q;reg sg,sh,dl,cl;
 always @(posedge stream_clk)begin sg_q<=svg_fault;sg_q2<=sg_q;sh_q<=share_fault;dl_q<=del_fault;cl_q<=cal_fault;end
 always @(posedge stream_clk or negedge srst)begin
  if(!srst)begin sg<=0;sh<=0;dl<=0;cl<=0;fault<=0;status<=0;end
  else begin
   if(|sg_q2)sg<=1;if(|sh_q)sh<=1;if(|dl_q)dl<=1;if(cl_q)cl<=1;
   status<={cl,dl,sh,sg,ow_s,pc_s,ca_s};
   fault<=cl||dl||sh||sg||ow_s||pc_s||ca_s;
  end
 end
endmodule
`default_nettype wire
