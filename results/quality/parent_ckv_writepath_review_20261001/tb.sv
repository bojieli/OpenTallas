`timescale 1ns/1ps
module tb; reg clk=0; always #5 clk=~clk; reg rst_n=0; reg [3:0] cv=0,cwe=0; wire [3:0] iv,iw,ir,id,ov,ow,orr,od; wire fault;
ot_chip_v41x_kv_reqmux dut0(.w_v('0),.w_addr('0),.w_len('0),.w_tag('0),.w_we('0),.w_wdata('0),.w_wstrb('0),.w_srdy('0),.c_v(cv),.c_rdy(ir),.c_addr('0),.c_len('0),.c_tag('0),.c_we(cwe),.c_wdata('0),.c_wstrb('0),.c_wr_done(id),.c_srdy('0),.m_v(iv),.m_rdy(4'hf),.m_we(iw),.m_wr_done(4'hf),.s_v('0),.s_tag('0),.s_beat('0),.s_data('0));
ot_chip_v41x_kv_rope_reqmux dut1(.clk(clk),.w_v('0),.w_addr('0),.w_len('0),.w_tag('0),.w_we('0),.w_wdata('0),.w_wstrb('0),.w_srdy('0),.c_v(cv),.c_rdy(orr),.c_addr('0),.c_len('0),.c_tag('0),.c_we(cwe),.c_wdata('0),.c_wstrb('0),.c_wr_done(od),.c_srdy('0),.p_v('0),.p_addr('0),.p_len('0),.p_tag('0),.p_we('0),.p_wdata('0),.p_wstrb('0),.p_srdy('0),.m_v(ov),.m_rdy(4'hf),.m_we(ow),.m_wr_done(4'hf),.s_v('0),.s_tag('0),.s_beat('0),.s_data('0),.fault(fault),.rst_n(rst_n));
initial begin
 #2; rst_n=0; #10; rst_n=1; cv=1; cwe=0; #1;
 $display("read ov=%b ow=%b ready=%b fault=%b",ov,ow,orr,fault); if(ov!==1 || ow!==0 || orr!==1 || fault!==0) $fatal(1,"read positive failed");
 cwe=1; #1;
 if(iv!==1 || iw!==0 || id!==0) $fatal(1,"inner write-block witness changed");
 if(ov!==0 || orr!==0 || od!==0) $fatal(1,"outer write-block witness changed");
 @(posedge clk); #1; if(fault!==1) $fatal(1,"write did not fault");
 $display("PASS_READ_POSITIVE_WRITE_BLOCKED_INNER_NO_WE_NO_DONE_OUTER_NO_ACCEPT_FAULT"); $finish;
 end endmodule
