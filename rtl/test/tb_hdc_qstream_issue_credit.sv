`timescale 1ns/1ps
// Directed boundary-state test; full numeric stalled QE is a separate gate.
module tb_hdc_qstream_issue_credit;
reg clk=0;always #5 clk=~clk;
reg rst_n=0,re=0;wire ready;
ot_hdc_qstream #(.ALLOW_QE_STALL(1),.LWIN(3),.LA(2)) dut(
.clk(clk),.rst_n(rst_n),.cfg_base(24'b0),.cfg_lbase(12'b0),.cfg_lead(16'd1),.cfg_rate(16'd0),
.tok_start(1'b0),.pos(16'd1),.l_q(128'b0),.vi_q(32'b0),.wrel_v(1'b0),.qd_v(1'b0),.qd_nb(8'b0),.qd_tiles(16'b0),
.qr_re(re),.qr_issue_ready(ready),.qr_addr(24'b0),.win_q(4352'b0),.hq_rdy(1'b0),.hq_room(8'b0),
.hr_v(8'b0),.hr_tag(24'b0),.hr_beat(40'b0),.hr_data(2048'b0));
initial begin
repeat(2) @(negedge clk);rst_n=1;
force dut.cp=1;force dut.cons=0;force dut.of_cnt=1;force dut.of_rp=0;force dut.c_i=0;
dut.of_n[0]=2;
#1;if(!ready) $fatal(1,"complete first word not issuable");
re=1;#1;if(ready) $fatal(1,"single credit double issued");
force dut.cp=2;#1;if(!ready) $fatal(1,"second word not issuable");
dut.of_n[0]=1;#1;if(ready) $fatal(1,"credit passed absent next descriptor");
force dut.of_cnt=2;#1;if(!ready) $fatal(1,"next descriptor blocked");
force dut.fault=1;#1;if(ready) $fatal(1,"fault still ready");
$display("QSTREAM_ISSUE_CREDIT_PASS");$finish;
end
endmodule
