`timescale 1ns/1ps
// Independent external stream scoreboard; no DUT memory or expected-state
// hierarchy reads. Run same-rate and both 3:4 orientations.
module tb_host_phase_fifo;
 parameter integer ASYNC=0, WP=6, RP=8, MUT=0;
 reg wc=0,rc=0,rn=0;always #(WP/2.0)wc=~wc;always #(RP/2.0)rc=~rc;
 reg[63:0]wd=0;reg wv=0;wire full,empty;wire[63:0]rd;wire ov;
 wire[63:0]observed=MUT?(rd^64'h100):rd;
 integer cyc=0,nw=0,nr=0;reg[63:0] expected[0:9999];
 if(ASYNC)begin:g_a
  wire ready,valid,unf;
  ot_async_fifo #(.WIDTH(64),.DEPTH(16)) dut(.wr_clk(wc),.wr_rst_n(rn),.wr_valid(wv),.wr_ready(ready),.wr_data(wd),.wr_overflow(ov),
   .rd_clk(rc),.rd_rst_n(rn),.rd_valid(valid),.rd_ready(1'b1),.rd_data(rd),.rd_underflow(unf));
  assign full=!ready;assign empty=!valid;
 end else begin:g_l
  wire[4:0]freed,count;
  ot_link_afifo #(.W(64),.AW(4),.RCOPY(4))dut(.wclk(wc),.wrst_n(rn),.wr(wv),.wdata(wd),.wfull(full),.wfreed(freed),.ovf(ov),
    .rclk(rc),.rrst_n(rn),.rd(!empty),.rempty(empty),.rdata(rd),.rcount(count));
 end
 initial begin #23 rn=1;end
 always @(negedge wc)if(rn)begin
  cyc=cyc+1;wv<=cyc%7==0&&cyc<3500;wd<={32'(cyc*579),32'(cyc^32'habc78353)};
  if(cyc==4000)begin
   if(nw!=nr||nr<400)$fatal(1,"PHASE_FIFO FAIL counts nw=%0d nr=%0d",nw,nr);
   $display("PHASE_FIFO PASS async=%0d WP=%0d RP=%0d writes=%0d reads=%0d",ASYNC,WP,RP,nw,nr);$finish;
  end
 end
 always @(posedge wc)if(rn&&wv&&!full)begin expected[nw]=wd;nw=nw+1;end
 always @(posedge rc)if(rn&&!empty)begin
  if(nr>=nw||observed!==expected[nr])$fatal(1,"PHASE_FIFO FAIL order nr=%0d observed=%h expected=%h",nr,observed,expected[nr]);
  nr=nr+1;
 end
endmodule
