`timescale 1ns/1ps
module tb_red;
reg ck=0;always #5 ck=~ck;reg rst_n=0;integer cycle;integer checked=0;
reg [7:0] l_ov=0;
reg [8*32-1:0] l_out=0;
reg [1:0] l_red0=0;
reg  l_redsq0=0;
reg  l_last0=0;
reg [23:0] l_raddr0=0;
wire  red_we, ref_red_we;
wire [23:0] red_addr, ref_red_addr;
wire [31:0] red_data, ref_red_data;
wire  rd_v, ref_rd_v;
wire  busy, ref_busy;
wire  fault, ref_fault;
localparam integer MUT=`MUT;
qfd_dv_s5_red dut(.ck(ck),.rst_n(rst_n),.l_ov(l_ov),.l_out(l_out),.l_red0(l_red0),.l_redsq0(l_redsq0),.l_last0(l_last0),.l_raddr0(l_raddr0),.red_we(red_we),.red_addr(red_addr),.red_data(red_data),.rd_v(rd_v),.busy(busy),.fault(fault));
red_reference refdut(.ck(ck),.rst_n(rst_n),.l_ov(l_ov),.l_out(l_out),.l_red0(l_red0),.l_redsq0(l_redsq0),.l_last0(l_last0),.l_raddr0(l_raddr0),.red_we(ref_red_we),.red_addr(ref_red_addr),.red_data(ref_red_data),.rd_v(ref_rd_v),.busy(ref_busy),.fault(ref_fault));
initial begin repeat(4) @(negedge ck);rst_n=1;
for(cycle=0;cycle<800;cycle=cycle+1) begin @(negedge ck);
l_ov=(cycle%20<16)?8'hff:0; l_last0=(cycle%20==15);l_red0=(cycle<400)?1:2;l_redsq0=(cycle>=200 && cycle<400);l_raddr0=cycle/20;
for(integer j=0;j<8;j=j+1) l_out[j*32+:32]=32'h3f000000+((cycle*8+j)<<12);
#1;end
repeat(200) @(negedge ck);if(checked<30) $fatal(1,"TOO_FEW_RESULTS %0d",checked);$display("PASS red 800 stimulus cycles");$finish;end
always @(negedge ck) if(rst_n && cycle>8) begin #2;
if((red_we !== ref_red_we)) $fatal(1,"MISMATCH red red_we cycle=%0d",cycle);
if(red_we && (red_addr !== ref_red_addr)) $fatal(1,"MISMATCH red red_addr cycle=%0d",cycle);
if(red_we && (red_data !== ref_red_data)) $fatal(1,"MISMATCH red red_data cycle=%0d",cycle);
if((rd_v !== ref_rd_v)) $fatal(1,"MISMATCH red rd_v cycle=%0d",cycle);
if((busy !== ref_busy)) $fatal(1,"MISMATCH red busy cycle=%0d",cycle);
if((fault !== ref_fault)) $fatal(1,"MISMATCH red fault cycle=%0d",cycle);
if(red_we) checked=checked+1;
end
endmodule
