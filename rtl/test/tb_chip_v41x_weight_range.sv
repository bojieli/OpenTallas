`timescale 1ns/1ps
// Actual behavioral W model, small allocated memory. No high-address aliasing.
module tb_chip_v41x_weight_range;
parameter W_AW=30;
reg clk=0; always #5 clk=~clk;
reg rst_n=0,w_v=0; reg[W_AW-1:0] addr=0; reg[5:0] len=1;
wire ready,oor; wire[1:0] rv; wire[511:0] data;
integer i,seen=0,cycles=0;
ot_chip_v41x_hbm3e_phy #(.NPC(2),.K_MEM(64),.W_PORT(1),.W_AW(W_AW),.NPC_W(2),.W_MEM(64),.LWIN(3)) dut(
.clk(clk),.rst_n(rst_n),.k_v(2'b0),.k_addr(56'b0),.k_len(8'b0),.k_tag(32'b0),
.k_we(2'b0),.k_wdata(512'b0),.k_wstrb(64'b0),.kr_rdy(2'b11),
.w_v(w_v),.w_rdy(ready),.w_addr(addr),.w_len(len),.w_tag(3'd3),.wr_v(rv),.wr_rdy(2'b11),.wr_data(data),.w_oor(oor));
initial begin
for(i=0;i<64;i=i+1) dut.g_w.u_w.mem[i]=256'(i+100);
repeat(3) @(negedge clk);rst_n=1;
// All these are illegal even though modulo W_MEM would access valid storage.
addr=(W_AW==30)?30'h20000003:24'h800003;w_v=1;
repeat(3) begin @(negedge clk);if(ready||!oor||dut.g_w.u_w.req_v) $fatal(1,"high address escaped");end
addr=63;len=2;
@(negedge clk);if(ready||dut.g_w.u_w.req_v) $fatal(1,"crossing burst escaped");
addr=0;len=0;
@(negedge clk);if(ready||dut.g_w.u_w.req_v) $fatal(1,"empty burst escaped");
w_v=0;rst_n=0;repeat(2) @(negedge clk);rst_n=1;
addr=63;len=1;w_v=1;
do @(posedge clk); while(!ready);
@(negedge clk);w_v=0;
wait(seen==1);
@(negedge clk);if(oor) $fatal(1,"valid last sector fault");
$display("WEIGHT_RANGE_PASS width=%0d valid_last_sector=63 rejected_high_crossing_empty=3",W_AW);$finish;
end
always @(posedge clk) begin
cycles<=cycles+1;
if(cycles>2000) $fatal(1,"timeout");
for(integer p=0;p<2;p=p+1) if(rv[p]) begin
if(data[p*256+:256]!==256'd163) $fatal(1,"wrong last-sector data");
seen<=seen+1;
end
end
endmodule
