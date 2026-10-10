`timescale 1ns/1ps
module tb_s81_control_lane #(parameter integer MUT=0, ERR=0, NEG=0);
 reg ck=0,rst=0;always #0.4166 ck=~ck;
 reg tv=0,tl=0;reg[511:0] td=0;wire tr;wire rxv,rxl;wire[511:0] rxd;reg rxr=0;
 wire av,ar;wire[552:0] ad;wire lv,ll,lr;wire[551:0] ld;
 wire fault;reg corev=0;reg inject=0;
 wire[552:0] into={ll,ld};
 ot_s81_ctrl_lane_adapter #(.ENABLE(1),.MUT(MUT)) u(.clk(ck),.rst_n(rst),
 .core_lo_v(corev),.core_lo_r(),.core_lo_d(553'd0),.core_li_v(),.core_li_r(1'b1),.core_li_d(),
 .lane_lo_v(av),.lane_lo_r(ar),.lane_lo_d(ad),.lane_li_v(lv||inject),.lane_li_r(lr),.lane_li_d(inject?{1'b1,40'd1,512'd0}:into),
 .c_tx_v(tv),.c_tx_r(tr),.c_tx_d(td),.c_tx_l(tl),.c_rx_v(rxv),.c_rx_r(rxr),.c_rx_d(rxd),.c_rx_l(rxl),.fault(fault));
 wire lf;wire[3:0] lfc;wire[31:0] tx,rx,crc,nak,replays;
 ot_dsrom_link_ct #(.FLIT_BYTES(69),.TX_STAGES(2),.RX_STAGES(3),.CREDITS(512),.SEQW(10),.CHANNEL_CYCLES(4),
 .ERR_PERIOD_FWD(ERR?97:0),.ERR_PERIOD_REV(ERR?131:0)) link(.clk(ck),.rst_n(rst),.channel_cycles(16'd4),
 .in_valid(av),.in_ready(ar),.in_data(ad[551:0]),.in_last(ad[552]),.out_valid(lv),.out_ready(lr),.out_data(ld),.out_last(ll),
 .credit_stalls(),.fault(lf),.fault_code(lfc),.st_flits_tx(tx),.st_flits_rx_ok(rx),.st_crc_err(crc),.st_naks(nak),.st_replays(replays),
 .st_timeouts(),.st_retx_flits(),.st_max_replay_occ());
 function automatic[511:0] payload(input integer i);
 for(integer j=0;j<16;j=j+1)payload[32*j+:32]=32'(i*2654435761+j*13);
 endfunction
 integer cyc=0,sent=0,got=0,errors=0,lastcy=0,firstcy=0;
 always @(posedge ck)if(rst)begin
 cyc=cyc+1;
 if(tv&&tr)sent=sent+1;
 if(rxv&&rxr)begin
  if(rxd!==payload(got)||rxl!=(got==640))errors=errors+1;
  if(got==0)firstcy=cyc;
  got=got+1;lastcy=cyc;
 end
 end
 always @(negedge ck)if(rst&&NEG==0)begin
 rxr=(cyc%11>=4);tv=(sent<641);td=payload(sent);tl=(sent==640);
 end
 initial begin
 repeat(6)@(negedge ck);rst=1;
 if(NEG)begin
  repeat(4)@(negedge ck);if(NEG==1)corev=1;else inject=1;
  @(negedge ck);corev=0;inject=0;repeat(8)@(negedge ck);
  $display("TB_S81_CONTROL_LANE neg=%0d fault=%b rx=%0d %s",NEG,fault,got,(fault&&got==0)?"PASS":"FAIL");
  if(!fault||got!=0)$fatal(1,"reserved lane malformed/collision gate");$finish;
 end
 repeat(9000)@(negedge ck);
 if(sent!=641||got!=641||fault||lf||(ERR&&crc==0)||(ERR&&replays==0))errors=errors+1;
 $display("TB_S81_CONTROL_LANE mut=%0d err=%0d native=553 payload_bits=512 sent=%0d got=%0d errors=%0d fault=%b linkfault=%b crc=%0d replays=%0d first=%0d last=%0d %s",MUT,ERR,sent,got,errors,fault,lf,crc,replays,firstcy,lastcy,errors==0?"PASS":"FAIL");
 $finish;
 end
endmodule
