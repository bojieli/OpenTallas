`timescale 1ps/1ps
module tb_svg_fifo_sram;
 parameter integer MUT=0, WP=512, RP=417, PHASE=17;
 reg wr_clk=0,rd_clk=0,rst_n=0;always #(WP)wr_clk=~wr_clk;
 initial begin #(PHASE);forever #(RP)rd_clk=~rd_clk;end
 reg wr_valid=0,rd_ready=0;reg[284:0]wr_data=0;
 wire w0,w1,v0,v1,ov0,ov1,un0,un1;wire[284:0]d0,d1;
 integer wc=0,rc=0,tx=0,rx=0,errors=0,first_fail=0,resets=0;
 ot_hbm_svc_async_fifo #(.WIDTH(285),.DEPTH(8)) ref_fifo(.wr_clk(wr_clk),.wr_rst_n(rst_n),.wr_valid(wr_valid),.wr_ready(w0),.wr_data(wr_data),.wr_overflow(ov0),.rd_clk(rd_clk),.rd_rst_n(rst_n),.rd_valid(v0),.rd_ready(rd_ready),.rd_data(d0),.rd_underflow(un0));
 ot_hbm_svc_async_fifo_sram285 #(.MUT(MUT)) dut(.wr_clk(wr_clk),.wr_rst_n(rst_n),.wr_valid(wr_valid),.wr_ready(w1),.wr_data(wr_data),.wr_overflow(ov1),.rd_clk(rd_clk),.rd_rst_n(rst_n),.rd_valid(v1),.rd_ready(rd_ready),.rd_data(d1),.rd_underflow(un1));
 function automatic[284:0]pattern(input integer n);begin pattern={29'(n^32'h5a5a5a5a),32'(n),32'(~n),32'(n*17),32'(n^32'hdeadbeef),32'(n+99),32'(n*31),32'(n^32'h12345678),32'(n+32'h55aa55aa)};end endfunction
 always @(negedge wr_clk)begin wc=wc+1;wr_valid=rst_n&&w0&&(wc%7!=0);wr_data=pattern(tx);end
 always @(posedge wr_clk)begin
  if(rst_n&&w0&&wr_valid)tx=tx+1;
  #1;if(w0!==w1||ov0!==ov1)errors=errors+1;
 end
 always @(negedge rd_clk)begin rc=rc+1;rd_ready=rst_n&&v0&&(rc%11<8)&&!(rc%401<55);end
 always @(posedge rd_clk)begin
  if(rst_n&&v0&&rd_ready)begin
   rx=rx+1;
   if(d0!==d1)begin errors=errors+1;if(first_fail<5)begin first_fail=first_fail+1;$display("MISMATCH rc=%0d old=%h new=%h",rc,d0,d1);end end
  end
  #1;if(v0!==v1||un0!==un1)errors=errors+1;
 end
 task reset_once;begin rst_n=0;resets=resets+1;repeat(6)@(negedge wr_clk);rst_n=1;end endtask
 initial begin
  reset_once();repeat(901)@(negedge rd_clk);reset_once();
  repeat(2003)@(negedge rd_clk);reset_once();repeat(3007)@(negedge rd_clk);
  if(rx<1000||tx<1000)errors=errors+1;
  $display("SVG_FIFO_SRAM %s mut=%0d wp=%0d rp=%0d phase=%0d errors=%0d tx=%0d rx=%0d resets=%0d",errors==0?"PASS":"FAIL",MUT,WP,RP,PHASE,errors,tx,rx,resets);
  if(errors)$fatal(1,"macro FIFO mismatch");$finish;
 end
endmodule
