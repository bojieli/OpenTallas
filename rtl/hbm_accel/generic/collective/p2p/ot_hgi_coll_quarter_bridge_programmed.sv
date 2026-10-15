`timescale 1ns/1ps
`default_nettype none
// Actual bridge and RX faces controlled exclusively by native SRAM catalogue.
// Quarter QID and NPT are physical identity. All clocks same logical edge,
// independently supplied at phi-R. No exposed ideal per-cycle control port.
module ot_hgi_coll_quarter_bridge_programmed #(
 parameter [1:0] QID=2'd0,
 parameter integer NBANKS=2,NPT=(QID==0?3:2),NS=NPT+2,ND=2*NPT+2,SW=$clog2(NS),
 parameter integer MUT_DATA=0,MUT_WRAP=0
)(
 input wire rst_n,clk_program,input wire [NBANKS-1:0] clk_mem,
 input wire [ND-1:0] clk_bridge,input wire [NPT-1:0] clk_rx,
 input wire cfg_v,input wire [7:0] cfg_target,input wire [11:0] cfg_addr,input wire [255:0] cfg_data,
 input wire desc_v,input wire [11:0] desc_base,input wire [12:0] desc_limit,input wire [15:0] desc_loops,
 input wire launch_v,program_active,
 input wire [NPT-1:0] local_tx_v,input wire [NPT*545-1:0] local_tx_d,
 input wire cw_in_v,ccw_in_v,input wire [544:0] cw_in_d,ccw_in_d,
 input wire [NPT-1:0] phy_rx_v,input wire [NPT*545-1:0] phy_rx_d,
 output wire [NPT-1:0] phy_tx_v,local_rx_v,
 output wire [NPT*545-1:0] phy_tx_d,local_rx_d,
 output wire cw_out_v,ccw_out_v,output wire [544:0] cw_out_d,ccw_out_d,
 output wire configured,init_busy,busy,done,program_fault,
 output reg fault
);
 initial if(NPT!=(QID==0?3:2))$fatal(1,"physicalbridge QID/NPT mismatch");
 wire cv;wire [48:0] control;wire [12:0] control_cycle;
 ot_hgi_coll_bridge_program #(.NBANKS(NBANKS),.QID(QID),.MUT_DATA(MUT_DATA),.MUT_WRAP(MUT_WRAP)) u_program(
  .clk_control(clk_program),.clk_mem(clk_mem),.rst_n(rst_n),
  .cfg_v(cfg_v),.cfg_target(cfg_target),.cfg_addr(cfg_addr),.cfg_data(cfg_data),
  .desc_v(desc_v),.desc_base(desc_base),.desc_limit(desc_limit),.desc_loops(desc_loops),
  .launch_v(launch_v),.program_active(program_active),.configured(configured),.init_busy(init_busy),
  .busy(busy),.done(done),.fault(program_fault),.control_v(cv),.control(control),.control_cycle(control_cycle));
 wire [ND-1:0] bridge_v;wire [ND*545-1:0] bridge_d;wire [ND*2-1:0] bridge_fault;
 wire [NPT*2-1:0] rx_fault;
 ot_hgi_coll_quarter_bridge #(.NPT(NPT)) u_bridge(.clk_output(clk_bridge),.rst_n(rst_n),
  .src_v({ccw_in_v,cw_in_v,local_tx_v}),.src_d({ccw_in_d,cw_in_d,local_tx_d}),
  .expect_v(control[0+:NS]),.out_slot(control[NS+:ND]),.out_select(control[NS+ND+:ND*SW]),
  .out_v(bridge_v),.out_d(bridge_d),.fault(bridge_fault));
 for(genvar p=0;p<NPT;p=p+1)begin:g_rx
  localparam B=NS+ND+ND*SW+p*4;
  ot_hgi_coll_quarter_bridge_mux #(.NS(2)) u_face(.clk(clk_rx[p]),.rst_n(rst_n),
   .src_v({bridge_v[NPT+p],phy_rx_v[p]}),.src_d({bridge_d[(NPT+p)*545+:545],phy_rx_d[p*545+:545]}),
   .expect_v({control[B+1],control[B]}),.slot(control[B+2]),.select(control[B+3]),
   .out_v(local_rx_v[p]),.out_d(local_rx_d[p*545+:545]),.fault(rx_fault[p*2+:2]));
 end
 assign phy_tx_v=bridge_v[0+:NPT];assign phy_tx_d=bridge_d[0+:NPT*545];
 assign cw_out_v=bridge_v[2*NPT];assign cw_out_d=bridge_d[2*NPT*545+:545];
 assign ccw_out_v=bridge_v[2*NPT+1];assign ccw_out_d=bridge_d[(2*NPT+1)*545+:545];
 always @(posedge clk_program or negedge rst_n)
  if(!rst_n)fault<=0;
  else fault<=fault | program_fault | (|bridge_fault) | (|rx_fault);
endmodule
`default_nettype wire
