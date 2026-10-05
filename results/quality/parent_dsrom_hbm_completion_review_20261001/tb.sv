`timescale 1ns/1ps
module tb;
reg clk=0;always #0.5 clk=~clk;reg rst_n=0,v=0;wire ready,done;
ot_hdc_v41x_idx_hbm #(.NPC(1),.AW(8),.MEM_WORDS(16),.MEM_MODE(0),.QD(4),.RQD(4),.RW(4),.REFPB(0)) dut(.clk(clk),.rst_n(rst_n),.req_v(v),.req_rdy(ready),.req_addr(8'd0),.req_len(4'd1),.req_tag(16'd0),.req_we(1'b1),.req_wdata(256'h1234),.req_wstrb(32'hffffffff),.wr_done(done),.rsp_rdy(1'b1));
initial begin
 repeat(3) @(negedge clk);rst_n=1;v=1;
 @(posedge clk);while(!ready) @(posedge clk);@(negedge clk);v=0;
 repeat(1000) begin @(posedge clk);#0.001;if(done) begin
 if(dut.mem[0]!==256'h1234) $fatal(1,"write data absent at done");
 if(dut.now>=dut.h_tcol[0]+dut.CWL_PS+dut.BURST_PS) $fatal(1,"legacy early completion no longer reproduced");
 $display("PASS_LEGACY_COLUMN_COMPLETION now_ps=%0d column_ps=%0d required_burst_complete_ps=%0d",dut.now,dut.h_tcol[0],dut.h_tcol[0]+dut.CWL_PS+dut.BURST_PS);$finish;
 end end $fatal(1,"write timeout");end
endmodule
