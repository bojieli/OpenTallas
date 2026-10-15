`timescale 1ns/1ps
`default_nettype none
// Explicit typed target120 raw-control kernel:160 local-slot successor.
// Source read_row[1:0], publish_row[1:0] and expect_row[1:0] carry
// home-local slot identity; global row identity arrives in actual metadata/header.
// Twenty-one real catalogue banks; old selected120 node remains a distinct module.
// Explicit typed target120 Engram component successor. Native catalogue owns
// all source/packet/qslot/bridge/endpoint/consumer controls; no ideal control
// vector, dynamic arbitration, or normal ready path exists. Candidate q0
// SerDes neighbor chain only; pads/clock/physical qualification remains open.
module ot_hcoll_engram_chain_slot_node #(
 parameter integer NODE=0,HOME_BASE=0,NBANKS=21
)(
 input wire rst_n,clk_control,
 input wire [NBANKS-1:0] clk_mem,clk_program_capture,
 input wire clk_qcapture,clk_qoutput,input wire [7:0] clk_bridge,
 input wire [2:0] clk_rxface,input wire [4:0] clk_endpoint_tx,clk_endpoint_rx,
 input wire cfg_v,input wire [7:0] cfg_target,input wire [11:0] cfg_addr,input wire [255:0] cfg_data,
 input wire desc_v,input wire [11:0] desc_base,input wire [12:0] desc_limit,input wire [15:0] desc_loops,
 input wire launch_v,program_active,epoch_begin,input wire [7:0] epoch,input wire phy_up,
 output wire source_read_v,output wire [4:0] source_read_row,output wire [3:0] source_read_sector,
 input wire [3:0] owned_slot_valid,input wire [19:0] owned_slot_global_row,
 input wire source_response_v,source_response_present,input wire [4:0] source_response_row,input wire [3:0] source_response_sector,
 input wire source_raw_v,input wire [4:0] source_raw_row,input wire [3:0] source_raw_sector,input wire [255:0] source_raw_data,
 output wire consumer_write_v,output wire [4:0] consumer_write_row,output wire [3:0] consumer_write_sector,output wire [255:0] consumer_write_data,
 output wire consumer_read_v,output wire [4:0] consumer_read_row,output wire [3:0] consumer_read_sector,
 output wire tx_pin_v,output wire [611:0] tx_pin_frame,
 input wire rx_pin_v,input wire [611:0] rx_pin_frame,
 output wire configured,init_busy,busy,done,consumer_complete,
 output reg fault,
 output wire issued_v,output wire [255:0] issued_control
);
 localparam NPT=3,NS=10,ND=16;
 wire [255:0] ctl;wire cv,program_fault;wire [12:0] control_cycle;
 ot_hgi_coll_control256_program #(.NBANKS(NBANKS),.QID(0)) u_program(
  .clk_control(clk_control),.clk_mem(clk_mem),.clk_capture(clk_program_capture),.rst_n(rst_n),
  .cfg_v(cfg_v),.cfg_target(cfg_target),.cfg_addr(cfg_addr),.cfg_data(cfg_data),
  .desc_v(desc_v),.desc_base(desc_base),.desc_limit(desc_limit),.desc_loops(desc_loops),
  .launch_v(launch_v),.program_active(program_active),.configured(configured),.init_busy(init_busy),
  .busy(busy),.done(done),.fault(program_fault),.control_v(cv),.control(ctl),.control_cycle(control_cycle));
 assign issued_control=ctl;assign issued_v=cv;
 assign source_read_v=ctl[190];assign source_read_row=ctl[191+:5];assign source_read_sector=ctl[196+:4];
 assign consumer_read_v=ctl[228];assign consumer_read_row=ctl[229+:5];assign consumer_read_sector=ctl[234+:4];
 wire packet_v,packet_fault;wire [544:0] packet;
 if(NODE<8)begin:g_source
  ot_hcoll_engram_slot_packetizer #(.HOME(HOME_BASE+NODE),.DEST(HOME_BASE+8)) u_packet(
   .clk(clk_control),.rst_n(rst_n),.epoch_begin(epoch_begin),.owned_slot_valid(owned_slot_valid),.owned_slot_global_row(owned_slot_global_row),
   .response_v(source_response_v),.response_present(source_response_present),.response_row(source_response_row),.response_sector(source_response_sector),.raw_v(source_raw_v),.raw_row(source_raw_row),.raw_sector(source_raw_sector),.raw_data(source_raw_data),
   .expect_response_v(ctl[200]),.capture_low(ctl[201]),.publish_v(ctl[202]),.publish_slot(ctl[203+:2]),.publish_pair(ctl[208+:3]),
   .out_v(packet_v),.out_flit(packet),.fault(packet_fault));
 end else begin:g_no_source
  assign packet_v=0;assign packet=0;assign packet_fault=0;
 end
 wire endpoint_rx_v;wire [544:0] endpoint_rx_data;
 wire rx_abort,tx_abort;wire [10:0] rx_cause,tx_cause;
 wire [2:0] bridge_tx_v,face_rx_v;wire [3*545-1:0] bridge_tx_d,face_rx_d;
 if(NODE<8)begin:g_tx
  ot_hgi_coll_static_link_capture u_endpoint(.ck(clk_endpoint_tx),.rst_n(rst_n),.epoch_begin(epoch_begin),.epoch(epoch),
   .wr_v(ctl[90]),.wr_observed_v(bridge_tx_v[0]),.wr_seq(ctl[91+:16]),.wr_flit(bridge_tx_d[0+:545]),
   .rd_v(ctl[107]),.rd_seq(ctl[108+:16]),.rx_expect_v(1'b0),.rx_expect_seq(16'b0),.phy_up(phy_up),
   .tx_pin_v(tx_pin_v),.tx_pin_flit(tx_pin_frame),.rx_pin_v(1'b0),.rx_pin_flit(612'b0),.rx_v(),.rx_flit(),
   .epoch_abort(tx_abort),.retry_requested(),.fault_cause(tx_cause));
 end else begin:g_no_tx
  assign tx_pin_v=0;assign tx_pin_frame=0;assign tx_abort=0;assign tx_cause=0;
 end
 if(NODE>0)begin:g_rx
  ot_hgi_coll_static_link_capture u_endpoint(.ck(clk_endpoint_rx),.rst_n(rst_n),.epoch_begin(epoch_begin),.epoch(epoch),
   .wr_v(1'b0),.wr_observed_v(1'b0),.wr_seq(16'b0),.wr_flit(545'b0),.rd_v(1'b0),.rd_seq(16'b0),
   .rx_expect_v(ctl[124]),.rx_expect_seq(ctl[125+:16]),.phy_up(phy_up),
   .tx_pin_v(),.tx_pin_flit(),.rx_pin_v(rx_pin_v),.rx_pin_flit(rx_pin_frame),.rx_v(endpoint_rx_v),.rx_flit(endpoint_rx_data),
   .epoch_abort(rx_abort),.retry_requested(),.fault_cause(rx_cause));
 end else begin:g_no_rx
  assign endpoint_rx_v=0;assign endpoint_rx_data=0;assign rx_abort=0;assign rx_cause=0;
 end
 wire [NS-1:0] src_v;wire [NS*545-1:0] src_d;
 for(genvar s=0;s<NS;s=s+1)begin:g_source_bus
  if(s==0)begin assign src_v[s]=packet_v;assign src_d[s*545+:545]=packet;end
  else if(s==3)begin assign src_v[s]=face_rx_v[1];assign src_d[s*545+:545]=face_rx_d[545+:545];end
  else begin assign src_v[s]=0;assign src_d[s*545+:545]=0;end
 end
 wire [ND-1:0] dst_v;wire [ND*545-1:0] dst_d;wire qfault;wire [3:0] qkind;
 ot_hgi_coll_qslots #(.NPT(3),.NS(NS),.ND(ND),.SELW(4)) u_qslots(
  .clk_capture(clk_qcapture),.clk_output(clk_qoutput),.rst_n(rst_n),.src_v(src_v),.src_d(src_d),
  .capture_slot(ctl[0+:10]),.sink_slot(ctl[10+:16]),.sink_select(ctl[26+:64]),
  .dst_v(dst_v),.dst_d(dst_d),.fault(qfault),.fault_kind(qkind));
 wire [48:0] bc=ctl[141+:49];wire [7:0] bv;wire [8*545-1:0] bd;wire [15:0] bf;wire [5:0] rf;
 ot_hgi_coll_quarter_bridge #(.NPT(3)) u_bridge(.clk_output(clk_bridge),.rst_n(rst_n),
  .src_v({2'b0,dst_v[0+:3]}),.src_d({1090'b0,dst_d[0+:3*545]}),
  .expect_v(bc[0+:5]),.out_slot(bc[5+:8]),.out_select(bc[13+:24]),.out_v(bv),.out_d(bd),.fault(bf));
 assign bridge_tx_v=bv[0+:3];assign bridge_tx_d=bd[0+:3*545];
 for(genvar p=0;p<3;p=p+1)begin:g_rxface
  wire local_v;wire [544:0] local_d;
  if(p==1)begin assign local_v=endpoint_rx_v;assign local_d=endpoint_rx_data;end
  else begin assign local_v=0;assign local_d=0;end
  ot_hgi_coll_quarter_bridge_mux #(.NS(2)) u_face(.clk(clk_rxface[p]),.rst_n(rst_n),
   .src_v({bv[3+p],local_v}),.src_d({bd[(3+p)*545+:545],local_d}),
   .expect_v({bc[38+p*4],bc[37+p*4]}),.slot(bc[39+p*4]),.select(bc[40+p*4]),
   .out_v(face_rx_v[p]),.out_d(face_rx_d[p*545+:545]),.fault(rf[p*2+:2]));
 end
 wire assemble_fault;
 if(NODE==8)begin:g_consumer
  ot_hcoll_engram_slot_assembler #(.DEST(HOME_BASE+8),.HOME_BASE(HOME_BASE)) u_assemble(.clk(clk_control),.rst_n(rst_n),.epoch_begin(epoch_begin),
   .in_v(dst_v[3]),.in_flit(dst_d[3*545+:545]),.expect_v(ctl[211]),.expect_local_slot(ctl[212+:2]),.expect_pair(ctl[217+:3]),.expect_home(ctl[220+:8]),
   .write_v(consumer_write_v),.write_row(consumer_write_row),.write_sector(consumer_write_sector),.write_data(consumer_write_data),.fault(assemble_fault),.complete(consumer_complete));
 end else begin:g_no_consumer
  assign consumer_write_v=0;assign consumer_write_row=0;assign consumer_write_sector=0;assign consumer_write_data=0;assign assemble_fault=0;assign consumer_complete=0;
 end
 always @(posedge clk_control or negedge rst_n)
  if(!rst_n)fault<=0;
  else fault<=fault|program_fault|packet_fault|qfault|(|bf)|(|rf)|assemble_fault|rx_abort|tx_abort|
  (ctl[190]&&(|ctl[195:193]))|(ctl[202]&&(|ctl[207:205]))|(ctl[211]&&(|ctl[216:214]));
endmodule
`default_nettype wire
