`timescale 1ns/1fs
// Off-die HOST peer for the S81 type-2 key-store/start frame. No DUT forces.
// Same 1104-bit frame/parity law as tb_s81sl_lep_host, with the selected
// 544-bit SerDes PMA interface rather than the older 513-bit UCIe interface.
module ot_tb_s81_native_ks_peer (
 input wire clk,rst_n,send,input wire[52:0]ks,
 input wire[543:0]pma_from_die0,pma_from_die1,
 input wire pma_die_tck0,pma_die_tck1,
 output wire[543:0]pma_to_die0,pma_to_die1,
 output wire queued,accepted,output wire[5:0]fault
);
 reg pending=0,sent0=0,sent1=0;
 reg[1103:0]frame=0;
 wire r0,r1;wire[511:0]tx0,tx1,rx0,rx1;wire[1:0]st0,st1;
 wire iv0,iv1;wire[552:0]id0,id1;wire tck0,tck1;
 wire[2:0]f0,f1;
 assign queued=pending;assign accepted=sent0&&sent1;assign fault={f1,f0};
 always @(posedge clk or negedge rst_n)begin
  if(!rst_n)begin pending<=0;sent0<=0;sent1<=0;frame<=0;end
  else begin
   if(send)begin
    if(pending)$fatal(1,"native KS peer accepts one mission request");
    frame<=({1051'd0,ks}<<4)|(1104'd2<<1);pending<=1;
   end
   if(pending&&!sent0&&r0)sent0<=1;
   if(pending&&!sent1&&r1)sent1<=1;
  end
 end
 dsfd_coll_lane_e l0(.ck(clk),.rs(rst_n),.chb(1'b0),.rx({st0[0],st0[1],rx0,rst_n}),.tx(tx0),.tf(),
  .lo_v(pending&&!sent0),.lo_r(r0),.lo_d({1'b0,frame[551:0]}),.li_v(iv0),.li_r(1'b1),.li_d(id0),.flt(f0));
 dsfd_coll_lane_e l1(.ck(clk),.rs(rst_n),.chb(1'b0),.rx({st1[0],st1[1],rx1,rst_n}),.tx(tx1),.tf(),
  .lo_v(pending&&!sent1),.lo_r(r1),.lo_d({1'b0,frame[1103:552]}),.li_v(iv1),.li_r(1'b1),.li_d(id1),.flt(f1));
 ot_pdie_serdes_col #(.PMA_LAT(4),.TXL(2)) p0(.clk(clk),.rst(rst_n),.tx(tx0),.rx(rx0),.st(st0),
  .pma_tx(pma_to_die0),.pma_tck(tck0),.pma_rx(pma_from_die0),.pma_rck(pma_die_tck0));
 ot_pdie_serdes_col #(.PMA_LAT(4),.TXL(2)) p1(.clk(clk),.rst(rst_n),.tx(tx1),.rx(rx1),.st(st1),
  .pma_tx(pma_to_die1),.pma_tck(tck1),.pma_rx(pma_from_die1),.pma_rck(pma_die_tck1));
endmodule
