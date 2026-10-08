// Full width native ingress mechanism. No-ready PHY is retained in landing64.
// Each physical arrival MUST have a pre-existing end-to-end reservation.
// Fatal faults quarantine the transaction; physical purge/recovery is required.
module ot_hbm_collective_protected_ingress #(parameter integer ENABLE=0)(
 input wire clk,rst_n,pclk,prst_n,
 input wire cold_link_start,input wire [23:0] link_epoch,
 input wire ph_rx_v,input wire [544:0] ph_rx_flit,
 output wire grant_valid,input wire grant_ready,output wire [71:0] grant_word,
 input wire ack_valid,output wire ack_ready,input wire [71:0] ack_word,
 output wire out_v,input wire out_r,output wire [544:0] out_d,
 output wire final_retire,quiet_core,quiet_phy,fault,
 output wire [8:0] landing_count,receive_count
);
 generate if(!ENABLE)begin:g_off
  assign grant_valid=0;assign grant_word=0;assign ack_ready=0;
  assign out_v=0;assign out_d=0;assign final_retire=0;
  assign quiet_core=0;assign quiet_phy=0;assign fault=0;
  assign landing_count=0;assign receive_count=0;
 end else begin:g_on
  wire landing_ready,landing_valid,landing_fault,cdc_in_ready;
  wire [544:0] landing_data;
  wire cdc_valid,cdc_wempty,cdc_rempty,cdc_fault,flight_ready;
  wire [544:0] cdc_data;
  wire flight_valid,flight_quiet,flight_fault,receive_ready;
  wire [544:0] flight_data;
  wire receive_valid,receive_fault,retire_ready,credit_fault;
  wire raw_grant_valid,raw_ack_ready;
  assign fault=landing_fault|cdc_fault|flight_fault|receive_fault|credit_fault;
  ot_hbm_collective_packet_fifo #(.ENABLE(1),.DEPTH(64)) u_landing(
   .clk(pclk),.rst_n(prst_n),.push(ph_rx_v&&!fault),.din(ph_rx_flit),.ready(landing_ready),
   .pop(landing_valid&&cdc_in_ready&&!fault),.valid(landing_valid),.dout(landing_data),
   .fault(landing_fault),.count(landing_count));
  ot_hbm_collective_protected_cdc_refill #(.ENABLE(1),.W(545),.AW(6)) u_cdc(
   .wclk(pclk),.wrst_n(prst_n),.in_v(landing_valid&&!fault),.in_r(cdc_in_ready),.in_d(landing_data),
   .rclk(clk),.rrst_n(rst_n),.out_v(cdc_valid),.out_r(flight_ready&&!fault),.out_d(cdc_data),
   .wempty(cdc_wempty),.rempty(cdc_rempty),.fault(cdc_fault));
  ot_hbm_collective_protected_flight #(.ENABLE(1),.W(545),.D(14)) u_flight(
   .clk(clk),.rst_n(rst_n),.in_v(cdc_valid&&!fault),.in_r(flight_ready),.in_d(cdc_data),
   .out_v(flight_valid),.out_r(receive_ready&&!fault),.out_d(flight_data),.quiet(flight_quiet),.fault(flight_fault));
  ot_hbm_collective_packet_fifo #(.ENABLE(1),.DEPTH(256)) u_receive(
   .clk(clk),.rst_n(rst_n),.push(flight_valid&&receive_ready&&!fault),.din(flight_data),.ready(receive_ready),
   .pop(final_retire),.valid(receive_valid),.dout(out_d),.fault(receive_fault),.count(receive_count));
  assign out_v=receive_valid&&retire_ready&&!fault;
  assign final_retire=out_v&&out_r;
  ot_hbm_credit_rx #(.ENABLE(1)) u_credit(
   .clk(clk),.rst_n(rst_n),.cold_link_start(cold_link_start),.link_epoch(link_epoch),
   .final_retire(final_retire),.final_retire_ready(retire_ready),
   .grant_valid(raw_grant_valid),.grant_ready(grant_ready&&!fault),.grant_word(grant_word),
   .ack_valid(ack_valid&&!fault),.ack_ready(raw_ack_ready),.ack_word(ack_word),.fault(credit_fault));
  assign grant_valid=raw_grant_valid&&!fault;
  assign ack_ready=raw_ack_ready&&!fault;
  // Local-domain predicates only; lifecycle owner synchronizes/ANDs both.
  // Credit control transport empty is a separate lifecycle obligation.
  assign quiet_phy=!fault&&landing_count==0&&cdc_wempty&&!ph_rx_v;
  assign quiet_core=!fault&&cdc_rempty&&flight_quiet&&receive_count==0&&!final_retire;
 end endgenerate
endmodule
