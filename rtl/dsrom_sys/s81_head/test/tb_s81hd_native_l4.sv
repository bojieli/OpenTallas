`timescale 1ns/1ps
// Exact full B return plus actual timed-reset and explicit-GO start mechanism.
// HEADB4: GO has one pin register (go_q): the DUT accepts GO one edge later, so the
// gold core gets GO and the x schedule one cycle later; output alignment is unchanged.
module tb_s81hd_native_l4;
  reg clk=0;always #5 clk=~clk;
  reg rst_n=0,go=0,ref_go=0;reg [255:0] x=0;
  wire nv,nf;wire [31:0] nd;
  ot_s81hd_elemB_l4_native #(.INSTANCE("new")) dut (
      .clk(clk),.rst_n(rst_n),.go(go),.x(x),.o_v(nv),.o_d(nd),.fault(nf));
  wire rv,rf;wire [31:0] rd;
  gold_ot_s81hd_elem #(.LV(6),.PAD(2),.JOIN(0),.ROWS(128),.CUT(9'h1ff),.SPLIT9(1),
      .FADD_L4(1),.IOREG(1),.SAFE(1),.INSTANCE("gold")) ref_core (
      .clk(clk),.rst_n(rst_n),.go(ref_go),.x(x),.row0(17'd0),.b_v(1'b0),.b_d(32'd0),
      .o_v(rv),.o_d(rd),.fault(rf),.l_v(),.l_d(),.head_v(),.head_d(),.head_row(),
      .done(),.best_row(),.best_bits(),.best_key());
  reg rvo=0,rfo=0;reg [31:0] rdo;
  always @(posedge clk) begin rvo<=rv;rfo<=rf;rdo<=rd;end
  task edge_sample;begin @(posedge clk);#1;end endtask
  function automatic [15:0] activation(input integer logical_word,lane);
    integer k;
    begin k=((logical_word%64)+64)%64;
      activation=16'h3c80 | 16'((k*13+lane*7)%128);
      if((k+lane)%5==0) activation[15]=1'b1;
    end
  endfunction
  integer cyc,j,rows=0,first=-1,last=-1;
  initial begin
    repeat(5) edge_sample();
    @(negedge clk);rst_n=1;
    edge_sample();if(dut.ready!==1'b0) $fatal(1,"READY early first release edge");
    @(negedge clk);go=1;
    edge_sample();if(dut.ready!==1'b1) $fatal(1,"READY late second release edge");
    @(negedge clk);go=0;
    // The one-edge-early GO must fault and must not start a scan.
    for(cyc=0;cyc<8500;cyc=cyc+1) begin
      edge_sample();
      if(nv) $fatal(1,"EARLY_GO_ACCEPTED cycle=%0d",cyc);
      if(cyc==0 && nf) $fatal(1,"EARLY_GO fault before go_q edge");
      if(cyc>0 && !nf) $fatal(1,"EARLY_GO did not fault");
    end
    @(negedge clk);rst_n=0;
    edge_sample();if(dut.ready!==1'b1) $fatal(1,"RESET assertion bypassed registered delivery");
    edge_sample();if(dut.ready!==1'b0 || nv || nf) $fatal(1,"RESET controls not clear second edge");
    repeat(3) edge_sample();
    @(negedge clk);rst_n=1;
    edge_sample();if(dut.ready) $fatal(1,"second release early");
    edge_sample();if(!dut.ready) $fatal(1,"second release late");
    @(negedge clk);
    for(cyc=0;cyc<9000;cyc=cyc+1) begin
      go=(cyc==0);ref_go=(cyc==1);
      for(j=0;j<16;j=j+1) x[16*j+:16]=activation(cyc-6-4*(j%8),j);
      @(negedge clk);
      if(nf || rfo || nv!==rvo || (nv && nd!==rdo))
        $fatal(1,"NATIVE_DIFF cycle=%0d valid=%b/%b data=%h/%h fault=%b/%b",cyc,nv,rvo,nd,rdo,nf,rfo);
      if(nv) begin
        if(first<0) first=cyc;
        if(last>=0 && cyc-last!=64) $fatal(1,"native cadence");
        last=cyc;rows=rows+1;
      end
    end
    if(rows!=128 || first!=146 || last!=8274) $fatal(1,"COUNTS rows=%0d first=%0d last=%0d",rows,first,last);
    $display("PASS native_rows=%0d cadence=64 first=%0d last=%0d reset_assert=2 release_ready=2 GO_accept=4 early_GO_fault_drop=PASS",rows,first,last);
    $finish;
  end
endmodule
