`timescale 1ns/1ps
`default_nettype none
// Static successor of the host packet controller (H-NETLIST cp2, 2026-10-15).
// ot_hbm_host_packet carried the retired dynamic loader's service faces (h_* loader->host AXI-lite,
// h_dma_* host DMA slave, m_* loader memory master). In the static die the host only installs
// configuration through the static ingress (F20..F30) and reads its status; the die raises status
// packets (irq = programme complete, fault = die fault aggregate). Packet ops 03/04/91..94 of the
// dynamic loader are therefore refused (protocol_fault, sticky) instead of reaching an absent loader.
// Packet ABI of the kept ops is unchanged (byte-exact with ot_hbm_host_packet):
//   rx op01 AXI-lite write {strb[163:160], data[127:96], addr[43:32]}  -> tx op81 {resp}
//   rx op02 AXI-lite read  {addr[43:32]}                             -> tx op82 {data[127:96]}
//   tx opFF status {fault, irq} whenever either changes.
// Host-link transmit flow control lives HERE (off-die boundary, elastic by owner rule): a TXC-credit
// counter replenished by the endpoint face t_cr; f_send/f_flit is the face's t_v/t_flit (545-b flit,
// upper 33 b = reserved-zero flit header, the landing faults on nonzero).
// Pins: every input lands in an unconditional pin flop; every output is a flop Q. AXI and landing
// handshakes are evaluated on mirrored pin copies (own valid/ready delayed one edge) and ready/valid
// are pulsed at most every other edge, so the registered views can never double-transfer.
module ot_hbm_host_packet_static #(parameter integer TXC=32, parameter integer MUT=0)(
 input wire clk,rst_n,
 // host landing FIFO (rx)
 input wire rx_valid,input wire [511:0] rx_packet,output reg rx_ready,
 // endpoint face (tx), credit returned by the face
 output reg f_send,output reg [544:0] f_flit,input wire t_cr,
 // AXI-lite master toward ot_hbm_host_static_ingress
 output reg s_awvalid,input wire s_awready,output reg [11:0] s_awaddr,
 output reg s_wvalid,input wire s_wready,output reg [31:0] s_wdata,output reg [3:0] s_wstrb,
 input wire s_bvalid,input wire [1:0] s_bresp,output reg s_bready,
 output reg s_arvalid,input wire s_arready,output reg [11:0] s_araddr,
 input wire s_rvalid,output reg s_rready,input wire [31:0] s_rdata,
 // die status (ot_hbm_status_join)
 input wire irq,fault,
 output reg protocol_fault
);
 // ---------------- pin flops
 reg rv_p,awr_p,wr_p,arr_p,bv_p,rvv_p,cr_p,irq_p,flt_p;
 reg [511:0] rp_p;reg [1:0] br_p;reg [31:0] rd_p;
 always @(posedge clk)begin rp_p<=rx_packet;br_p<=s_bresp;rd_p<=s_rdata;end
 always @(posedge clk or negedge rst_n)
  if(!rst_n)begin rv_p<=0;awr_p<=0;wr_p<=0;arr_p<=0;bv_p<=0;rvv_p<=0;cr_p<=0;irq_p<=0;flt_p<=0;end
  else begin rv_p<=rx_valid;awr_p<=s_awready;wr_p<=s_wready;arr_p<=s_arready;bv_p<=s_bvalid;rvv_p<=s_rvalid;
   cr_p<=t_cr;irq_p<=irq;flt_p<=fault;end
 // mirrors of own outputs as the peer sampled them
 reg rxr_m,awv_m,wv_m,arv_m,brd_m,rrd_m;
 always @(posedge clk or negedge rst_n)
  if(!rst_n)begin rxr_m<=0;awv_m<=0;wv_m<=0;arv_m<=0;brd_m<=0;rrd_m<=0;end
  else begin rxr_m<=rx_ready;awv_m<=s_awvalid;wv_m<=s_wvalid;arv_m<=s_arvalid;brd_m<=s_bready;rrd_m<=s_rready;end
 wire rx_take=rv_p&&rxr_m, aw_hs=awr_p&&awv_m, w_hs=wr_p&&wv_m, ar_hs=arr_p&&arv_m;
 wire b_hs=bv_p&&brd_m, r_hs=rvv_p&&rrd_m;
 // ---------------- state
 reg buf_v;reg [511:0] buf_p;
 reg sbw,sbr,sb_resp,sr_resp,status_pending;
 reg [15:0] sb_id,sr_id;reg [1:0] s_write_resp,last_status;reg [31:0] s_read_data;
 reg [$clog2(TXC+1)-1:0] credits;
 wire [7:0] op=buf_p[7:0];
 wire [15:0] tid=buf_p[31:16];
 wire malformed=buf_p[15:8]!=8'd1 || buf_p[511:171]!=341'd0;
 function automatic [511:0] packet(input [7:0] code,input [15:0] id,input [63:0] data,input [1:0] resp);
 begin packet={341'd0,1'b1,resp,8'd0,data,64'd0,id,8'd1,code};end endfunction
 always @(posedge clk or negedge rst_n)begin
 if(!rst_n)begin
  rx_ready<=0;f_send<=0;f_flit<=0;protocol_fault<=0;buf_v<=0;
  sbw<=0;sbr<=0;sb_resp<=0;sr_resp<=0;status_pending<=0;last_status<=0;s_write_resp<=0;s_read_data<=0;
  sb_id<=0;sr_id<=0;credits<=TXC[$clog2(TXC+1)-1:0];
  s_awvalid<=0;s_wvalid<=0;s_bready<=0;s_arvalid<=0;s_rready<=0;s_awaddr<=0;s_wdata<=0;s_wstrb<=0;s_araddr<=0;
 end else begin
  // landing handshake: ready pulsed at most every other edge, only into an empty buffer
  rx_ready<=!rx_ready&&!buf_v&&!rx_take;
  if(rx_take)begin buf_v<=1;buf_p<=rp_p;end
  if({flt_p,irq_p}!=last_status)begin status_pending<=1;last_status<={flt_p,irq_p};end
  if(aw_hs)s_awvalid<=0;
  if(w_hs)s_wvalid<=0;
  if(ar_hs)s_arvalid<=0;
  if(b_hs)begin s_bready<=0;sb_resp<=1;s_write_resp<=MUT==3?2'd0:br_p;if(br_p!=0)protocol_fault<=1;end
  if(r_hs)begin s_rready<=0;sr_resp<=1;s_read_data<=rd_p;end
  // one buffered request at a time; a request waits only for its own AXI direction to retire
  if(buf_v)begin
   if(malformed)begin protocol_fault<=1;buf_v<=0;end
   else case(op)
    8'h01:if(!sbw)begin
     buf_v<=0;
     if(buf_p[95:44]!=0||buf_p[159:128]!=0||buf_p[167:164]!=0)protocol_fault<=1;
     else begin sbw<=1;sb_id<=tid;s_awvalid<=1;s_awaddr<=buf_p[43:32];s_wvalid<=1;
      s_wdata<=buf_p[127:96]^(MUT==1?32'd1:32'd0);s_wstrb<=buf_p[163:160];s_bready<=1;end
    end
    8'h02:if(!sbr)begin
     buf_v<=0;
     if(buf_p[95:44]!=0)protocol_fault<=1;
     else begin sbr<=1;sr_id<=tid;s_arvalid<=1;s_araddr<=buf_p[43:32];s_rready<=1;end
    end
    default:begin protocol_fault<=1;buf_v<=0;end   // dynamic-loader ops 03/04/91..94 and unknown ops
   endcase
  end
  // transmit: one flit per edge while link credit remains (host-link flow control, off-die boundary)
  f_send<=0;
  if(credits!=0 && (sb_resp||sr_resp||status_pending))begin
   f_send<=1;
   if(sb_resp)begin f_flit<={33'd0,packet(8'h81,sb_id,64'd0,s_write_resp)};sb_resp<=0;sbw<=0;end
   else if(sr_resp)begin f_flit<={33'd0,packet(8'h82,sr_id,{32'd0,s_read_data},2'd0)};sr_resp<=0;sbr<=0;end
   else begin f_flit<={33'd0,packet(8'hff,16'd0,{62'd0,last_status},2'd0)};status_pending<=0;end
  end
  credits<=credits+(cr_p?1'b1:1'b0)-((credits!=0 && (sb_resp||sr_resp||status_pending) && MUT!=2)?1'b1:1'b0);
 end
 end
endmodule
`default_nettype wire
