`timescale 1ns/1ps
module tb;
reg clk=0; reg rst_n=0;
integer cyc,bitn,errors=0; reg [31:0] rng=32'h75319bad; integer mutant;
initial begin mutant=$test$plusargs("mutant"); end
reg [759:0] ci0;
wire [245:0] got0_c_o, ref0_c_o;
wire [113:0] got0_ctl_o, ref0_ctl_o;
wire [34:0] got0_sc_o, ref0_sc_o;
wire [56:0] got0_stm_o, ref0_stm_o;
qfd_qc_su_lane_w_c0 dut0 (.clk(clk), .rst_n(rst_n), .c_i(ci0), .c_o(got0_c_o), .ctl_o(got0_ctl_o), .sc_o(got0_sc_o), .stm_o(got0_stm_o));
ref_0 golden0 (.clk(clk), .rst_n(rst_n), .c_i(ci0), .c_o(ref0_c_o), .ctl_o(ref0_ctl_o), .sc_o(ref0_sc_o), .stm_o(ref0_stm_o));
reg [759:0] ci1;
wire [113:0] got1_ctl_o, ref1_ctl_o;
wire [0:0] got1_sc_o, ref1_sc_o;
wire [56:0] got1_stm_o, ref1_stm_o;
wire [218:0] got1_c_o, ref1_c_o;
qfd_qc_su_lane_w_c1 dut1 (.clk(clk), .rst_n(rst_n), .c_i(ci1), .ctl_o(got1_ctl_o), .sc_o(got1_sc_o), .stm_o(got1_stm_o), .c_o(got1_c_o));
ref_1 golden1 (.clk(clk), .rst_n(rst_n), .c_i(ci1), .ctl_o(ref1_ctl_o), .sc_o(ref1_sc_o), .stm_o(ref1_stm_o), .c_o(ref1_c_o));
initial begin
for (cyc=0;cyc<4096;cyc=cyc+1) begin
rst_n=(cyc>=16);
for(bitn=0;bitn<760;bitn=bitn+1) begin rng=(rng>>1)^(-(rng&1)&32'hd0000001); ci0[bitn]=rng[0]; end
for(bitn=0;bitn<760;bitn=bitn+1) begin rng=(rng>>1)^(-(rng&1)&32'hd0000001); ci1[bitn]=rng[0]; end
#5; clk=1; #1;
if(cyc>64) begin
if ((got0_c_o ^ ((mutant && cyc==100) ? 246'd1 : 246'd0)) !== ref0_c_o) begin $display("MISMATCH class0 c_o cycle%0d",cyc);errors=errors+1;end
if (got0_ctl_o !== ref0_ctl_o) begin $display("MISMATCH class0 ctl_o cycle%0d",cyc);errors=errors+1;end
if (got0_sc_o !== ref0_sc_o) begin $display("MISMATCH class0 sc_o cycle%0d",cyc);errors=errors+1;end
if (got0_stm_o !== ref0_stm_o) begin $display("MISMATCH class0 stm_o cycle%0d",cyc);errors=errors+1;end
if (got1_ctl_o !== ref1_ctl_o) begin $display("MISMATCH class1 ctl_o cycle%0d",cyc);errors=errors+1;end
if (got1_sc_o !== ref1_sc_o) begin $display("MISMATCH class1 sc_o cycle%0d",cyc);errors=errors+1;end
if (got1_stm_o !== ref1_stm_o) begin $display("MISMATCH class1 stm_o cycle%0d",cyc);errors=errors+1;end
if (got1_c_o !== ref1_c_o) begin $display("MISMATCH class1 c_o cycle%0d",cyc);errors=errors+1;end
end
#4;clk=0;
end
if(errors) $fatal(1,"SU_LANE_MITER FAIL errors=%0d",errors);
$display("SU_LANE_MITER PASS classes=2 E/W_equivalent=2 cycles=4096");$finish;
end
endmodule
