`timescale 1ns/1ps
`default_nettype none
// HEAD-RTL-2: fixed-date host frame arbitration. The real HBC stage supplies
// context_valid and stripped local_ring; this block never invents admission.
// The physical and HBC fault paths return a STATUS frame to the controller.
// An overlapping arrival is a schedule fault, never a stall or hidden drop.
module ot_s81hd_host_frame_mux #(parameter integer MUT=0)(
 input wire ck,rst_n,context_valid,
 input wire host0_v,host1_v,input wire[552:0]host0_d,host1_d,
 input wire[1103:0]local_ring,input wire[16:0]source_fault,
 input wire ctl_v,input wire[552:0]ctl_d,
 output wire[1103:0]from_prev,
 output wire ctl_rx_v,output wire[552:0]ctl_rx_d,
 output wire[1:0]lane_tx_v,output wire[1105:0]lane_tx_d,
 output reg[16:0]fault
);
 wire hf=host0_v&&host0_d[552]&&host0_d[3:0]==7;
 assign from_prev={571'd0,host0_d[527:16],8'd0,4'd0,5'd1,3'd6,hf};
 wire fw=local_ring[0]&&local_ring[3:1]==6;
 wire cs=host1_v&&host1_d[552]&&host1_d[3:0]==6;
 wire cfg=cs&&(context_valid||MUT==1);
 wire result=ctl_v&&ctl_d[552]&&ctl_d[3:0]==9;
 wire status=ctl_v&&ctl_d[552]&&ctl_d[3:0]==8;
 reg[16:0]reported;
 reg[1:0]rx_gap;
 wire status_due=(|(fault&~reported))&&rx_gap==0&&!fw&&!cfg;
 wire rx_request=fw||cfg||status_due;
 wire[552:0]forward_frame={1'b1,24'd0,local_ring[532:21],8'd0,2'd0,2'd0,4'd7};
 wire[552:0]fault_frame={1'b1,519'd0,fault,12'd0,4'd8};
 assign ctl_rx_v=rx_request&&rx_gap==0;
 assign ctl_rx_d=fw?forward_frame:cfg?host1_d:fault_frame;
 assign lane_tx_v={status,result};
 assign lane_tx_d={ctl_d,ctl_d};
 wire[16:0]events=source_fault|{
  10'd0,(ctl_v&&!result&&!status),(rx_request&&rx_gap!=0),
  (fw&&cfg),(cs&&!context_valid),
  (host1_v&&!cs),(host0_v&&!hf),1'b0};
 always@(posedge ck or negedge rst_n)begin
  if(!rst_n)begin fault<=0;reported<=0;rx_gap<=0;end
  else begin
   fault<=fault|(MUT==2?17'd0:events);
   if(ctl_rx_v)rx_gap<=2;else if(rx_gap!=0)rx_gap<=rx_gap-1'b1;
   if(ctl_rx_v&&status_due)reported<=fault;
  end
 end
endmodule

// Actual hd_host provider: two existing stacked safe8 lanes, HBC1 loader/book
// and the unchanged 553-bit/three-beat host276 transport. Compiled boot dates
// and clock identity remain explicit parameters, unadmitted by default.
module ot_s81hd_host_ep_core #(
 parameter[1:0]CH_B=2'b11,
 parameter integer LOCAL_STAGE=255,LOCAL_RANK=4,PHASE_BOUND=0,
 parameter integer MUT=0,
 parameter[63:0]CLOCK_RESET_ID=0,
 parameter[47:0]BOOT_HEADER_EDGE=48'hffffffffffff,
 parameter[47:0]BOOT_COMMIT_EDGE=48'hffffffffffff
)(
 input wire ck,rst_n,start_i,
 input wire[513:0]coll_i0,coll_i1,
 output wire[511:0]coll_o0,coll_o1,
 input wire[276:0]h_tx_i,output wire[275:0]h_rx_o
);
 // The job-active bit is a real partition input; land it at the face before
 // it reaches the HBC loader. START is already the wrapper's local START tap.
 (* keep="true",face_keep="true" *)reg job_active_pin;
 always@(posedge ck or negedge rst_n)if(!rst_n)job_active_pin<=0;else job_active_pin<=h_tx_i[276];
 wire[1:0]lv,txv;wire[1105:0]ld,txd;wire[3:0]lf0,lf1;
 ot_s81hd_mesh_lane u_lane0(.ck(ck),.rst_n(rst_n),.chb(CH_B[0]),
  .rx(coll_i0),.tx(coll_o0),.tx_v(txv[0]),.tx_d(txd[552:0]),
  .rx_v(lv[0]),.rx_d(ld[552:0]),.flt(lf0));
 ot_s81hd_mesh_lane u_lane1(.ck(ck),.rst_n(rst_n),.chb(CH_B[1]),
  .rx(coll_i1),.tx(coll_o1),.tx_v(txv[1]),.tx_d(txd[1105:553]),
  .rx_v(lv[1]),.rx_d(ld[1105:553]),.flt(lf1));
 wire cv,crxf,ctxv;wire[552:0]cd,rxframe;wire rxv,crtxf;
 ot_s81hd_host276_rx u_ctl_rx(.ck(ck),.rn(rst_n),.lane(h_tx_i[275:0]),.v(cv),.frame(cd),.fault(crxf));
 ot_s81hd_host276_tx u_ctl_tx(.ck(ck),.rn(rst_n),.v(rxv),.frame(rxframe),.lane(h_rx_o),.fault(crtxf));
 wire[1103:0]from_prev,to_local,next_ro;
 // RX_ONLY=1 omits the layer return TX: the head owns no layer-return producer.
 // The live ctl frames remain visible to the diagnostic pass-through output;
 // status/return inputs are unused by this explicit receive-only parameter.
 wire[1103:0]local_ro={571'd0,cd[527:16],8'd0,4'd0,5'd1,3'd6,cv};
 wire[3:0]return_fault;wire[11:0]hbc_stage_fault;wire[7:0]hbc_fault;
 wire[514:0]f_host;wire[52:0]ks;wire[2:0]ks_slot;wire[5:0]arm_mask;wire arm_commit;
 wire[47:0]receiver_edge,boot_edge;
 dsdv_hostb_stage_hbc #(.ENABLE(1),.LOCAL_STAGE(LOCAL_STAGE),.LOCAL_RANK(LOCAL_RANK),
  .PHASE_BOUND(PHASE_BOUND),.RETURN_LOCAL(0),.RX_ONLY(1),.CLOCK_RESET_ID(CLOCK_RESET_ID),
  .BOOT_HEADER_EDGE(BOOT_HEADER_EDGE),.BOOT_COMMIT_EDGE(BOOT_COMMIT_EDGE))u_hbc(
  .ck(ck),.rst_n(rst_n),.job_active(job_active_pin),.starter_armed(start_i),
  .from_prev(from_prev),.local_ro(local_ro),.return_ro(local_ro),
  .status_t_host({11'd0,job_active_pin,65'd0}),.status_t_kd(cd[69:16]),
  .return_fault(return_fault),.to_local(to_local),.next_ro(next_ro),
  .f_host(f_host),.ks_descriptor(ks),.ks_slot(ks_slot),.arm_mask(arm_mask),
  .arm_commit(arm_commit),.fault(hbc_stage_fault),.context_valid(ctxv),
  .receiver_edge(receiver_edge),.boot_edge(boot_edge),.hbc_fault(hbc_fault));
 // A head endpoint has no HBE/KS consumer; receiving one is a contract fault.
 // Live HBC stripping and validation still happen before configuration passes.
 wire[16:0]source_fault={
  (f_host[0]||arm_commit||ks[52]),
  (|return_fault),(|hbc_stage_fault),(|hbc_fault),crtxf,crxf,
  3'd0,lf1,lf0};
 wire[16:0]host_fault;
 ot_s81hd_host_frame_mux #(.MUT(MUT))u_mux(.ck(ck),.rst_n(rst_n),.context_valid(ctxv),
  .host0_v(lv[0]),.host1_v(lv[1]),.host0_d(ld[552:0]),.host1_d(ld[1105:553]),
  .local_ring(to_local),.source_fault(source_fault),.ctl_v(cv),.ctl_d(cd),
  .from_prev(from_prev),.ctl_rx_v(rxv),.ctl_rx_d(rxframe),
  .lane_tx_v(txv),.lane_tx_d(txd),.fault(host_fault));
endmodule
`default_nettype wire
