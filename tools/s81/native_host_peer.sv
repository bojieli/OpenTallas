`timescale 1ns/1fs
// Off-die HOST-plane peer. One complete frame remains stable until both real
// lane handshakes finish. Credits and receive backpressure are never bypassed.
module ot_tb_s81_native_host_peer #(parameter integer WIRE_PROFILE_BAD=0)(
 input wire clk,rst_n,
 input wire host_send,input wire[514:0]host_word,output wire host_ready,output reg host_accepted,
 input wire ks_send,input wire[52:0]ks_word,output reg ks_accepted,
 input wire[543:0]pma_from_die0,pma_from_die1,input wire pma_die_tck0,pma_die_tck1,
 output wire[543:0]pma_to_die0,pma_to_die1,
 output reg[76:0]remote_host_status,output reg remote_host_valid,output wire[6:0]fault
);
 reg pending=0,sent0=0,sent1=0,frame_parity=0,next_parity=0,ks_wait=0;
 reg[1103:0]frame=0;reg[52:0]ks_hold=0;
 integer rx_frames=0;reg rxfull0=0,rxfull1=0,parity_fault=0;reg[552:0]rxhold0=0,rxhold1=0;
 wire r0,r1,iv0,iv1;wire[552:0]id0,id1;wire[511:0]tx0,tx1,rx0,rx1;
 wire[1:0]st0,st1;wire[2:0]f0,f1;wire tck0,tck1;
 assign host_ready=!pending&&!ks_wait;
 assign fault={parity_fault,f1,f0};
 always @(posedge clk or negedge rst_n)begin
  if(!rst_n)begin
   pending<=0;sent0<=0;sent1<=0;frame<=0;frame_parity<=0;next_parity<=0;
   ks_wait<=0;ks_hold<=0;host_accepted<=0;ks_accepted<=0;
   rx_frames<=0;rxfull0<=0;rxfull1<=0;rxhold0<=0;rxhold1<=0;parity_fault<=0;
   remote_host_status<=0;remote_host_valid<=0;
  end else begin
   host_accepted<=0;ks_accepted<=0;remote_host_valid<=0;
   if(host_send&&ks_send)$fatal(1,"native peer simultaneous HOST and KS requests");
   if(ks_send)begin
    if(ks_wait)$fatal(1,"native peer KS queue overflow");
    ks_hold<=ks_word;ks_wait<=1;
   end
   if(!pending)begin
    if(ks_wait)begin
     frame<=({1051'd0,ks_hold}<<4)|(1104'd2<<1);ks_wait<=0;ks_accepted<=1;
     pending<=1;sent0<=0;sent1<=0;frame_parity<=next_parity;next_parity<=~next_parity;
    end else if(host_send)begin
     if(host_word[0]!==1'b1)$fatal(1,"native peer rejects invalid HOST word");
     frame<=({590'd0,host_word[514:1]}<<4)|(1104'd1<<1);host_accepted<=1;
     pending<=1;sent0<=0;sent1<=0;frame_parity<=next_parity;next_parity<=~next_parity;
    end
   end else begin
    if(host_send)$fatal(1,"native peer HOST request ignored backpressure");
    if(!sent0&&r0)sent0<=1;
    if(!sent1&&r1)sent1<=1;
    if(sent0&&sent1)pending<=0;
   end
   if(iv0&&!rxfull0)begin rxhold0<=id0;rxfull0<=1;end
   if(iv1&&!rxfull1)begin rxhold1<=id1;rxfull1<=1;end
   if(rxfull0&&rxfull1)begin
    rx_frames<=rx_frames+1;
    if(rx_frames<16)$display("NATIVE_HOST_PEER_RX frame=%0d kind=%0d parity=%b header=%h",rx_frames+1,rxhold0[3:1],rxhold0[552],rxhold0[15:0]);
    if(rxhold0[552]!==rxhold1[552])begin
     parity_fault<=1;$fatal(1,"native peer RX parity mismatch %b/%b",rxhold0[552],rxhold1[552]);
    end
    if(!rxhold0[0]&&rxhold0[3:1]==3'd3)begin
     remote_host_status<=rxhold0[4+:77];remote_host_valid<=1;
    end
    rxfull0<=0;rxfull1<=0;
   end
  end
 end
 dsfd_coll_lane_e #(.GFMT(WIRE_PROFILE_BAD?0:1),.EPPIPE(WIRE_PROFILE_BAD?-1:2),.LCR(0),.CH_BOARD(700)) l0(.ck(clk),.rs(rst_n),.chb(WIRE_PROFILE_BAD?1'b0:1'b1),.rx({st0[0],st0[1],rx0,rst_n}),.tx(tx0),.tf(),
  .lo_v(pending&&!sent0),.lo_r(r0),.lo_d({frame_parity,frame[551:0]}),.li_v(iv0),.li_r(!rxfull0),.li_d(id0),.flt(f0));
 dsfd_coll_lane_e #(.GFMT(WIRE_PROFILE_BAD?0:1),.EPPIPE(WIRE_PROFILE_BAD?-1:2),.LCR(0),.CH_BOARD(700)) l1(.ck(clk),.rs(rst_n),.chb(WIRE_PROFILE_BAD?1'b0:1'b1),.rx({st1[0],st1[1],rx1,rst_n}),.tx(tx1),.tf(),
  .lo_v(pending&&!sent1),.lo_r(r1),.lo_d({frame_parity,frame[1103:552]}),.li_v(iv1),.li_r(!rxfull1),.li_d(id1),.flt(f1));
 ot_pdie_serdes_col #(.PMA_LAT(4),.TXL(2)) p0(.clk(clk),.rst(rst_n),.tx(tx0),.rx(rx0),.st(st0),
  .pma_tx(pma_to_die0),.pma_tck(tck0),.pma_rx(pma_from_die0),.pma_rck(pma_die_tck0));
 ot_pdie_serdes_col #(.PMA_LAT(4),.TXL(2)) p1(.clk(clk),.rst(rst_n),.tx(tx1),.rx(rx1),.st(st1),
  .pma_tx(pma_to_die1),.pma_tck(tck1),.pma_rx(pma_from_die1),.pma_rck(pma_die_tck1));
endmodule
