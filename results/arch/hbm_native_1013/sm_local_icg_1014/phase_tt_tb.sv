module tb;
timeunit 1ps; timeprecision 1fs;
integer pulses=0; integer enable_checks=0;
integer mismatches=0; integer checked=0;
reg clk;
reg rst_n;
reg cgi;
wire g_cgo;
wire s_cgo;
reg [17:0] xs_a1;
reg [9:0] xs_g1;
reg [13:0] xs_a2;
reg [9:0] xs_g2;
reg [1635:0] rin;
reg [2068:0] bin;
wire [1635:0] g_rout;
wire [1635:0] s_rout;
wire [2068:0] g_bout;
wire [2068:0] s_bout;
reg [99:0] gin;
wire [199:0] g_gout;
wire [199:0] s_gout;

split_eg u_split(.clk(clk),.rst_n(rst_n),.cgi(cgi),.cgo(s_cgo),.xs_a1(xs_a1),.xs_g1(xs_g1),.xs_a2(xs_a2),.xs_g2(xs_g2),.rin(rin),.bin(bin),.rout(s_rout),.bout(s_bout),.gin(gin),.gout(s_gout),.clk_child_0(phase_raw_0),.clk_child_1(phase_raw_1),.clk_child_2(phase_raw_2),.clk_child_3(phase_raw_3),.clk_child_4(phase_raw_4),.clk_child_5(phase_raw_5),.clk_child_6(phase_raw_6),.clk_child_7(phase_raw_7),.clk_child_8(phase_raw_8),.clk_child_9(phase_raw_9),.clk_child_10(phase_raw_10),.clk_child_11(phase_raw_11));
reg phase_raw_0=0; wire reference_gclk_0;
initial begin #(1167.272435); forever begin phase_raw_0=1; #416.6665; phase_raw_0=0; #416.6665; end end
ICGx1_ASAP7_75t_R reference_0(.CLK(phase_raw_0),.ENA(u_split.u_own.cut_8870),.SE(1'b0),.GCLK(reference_gclk_0));
always @(phase_raw_0,reference_gclk_0,u_split.u_own.local_gclk_0) begin #0.001; if(checked>32 && reference_gclk_0 !== u_split.u_own.local_gclk_0) $fatal(1,"phase tt child0 mirrored original8870 pulse differs"); end
always @(posedge u_split.u_own.local_gclk_0) if(checked>32) pulses=pulses+1;
reg phase_raw_1=0; wire reference_gclk_1;
initial begin #(1174.427228); forever begin phase_raw_1=1; #416.6665; phase_raw_1=0; #416.6665; end end
ICGx1_ASAP7_75t_R reference_1(.CLK(phase_raw_1),.ENA(u_split.u_own.cut_8870),.SE(1'b0),.GCLK(reference_gclk_1));
always @(phase_raw_1,reference_gclk_1,u_split.u_own.local_gclk_1) begin #0.001; if(checked>32 && reference_gclk_1 !== u_split.u_own.local_gclk_1) $fatal(1,"phase tt child1 mirrored original8870 pulse differs"); end
always @(posedge u_split.u_own.local_gclk_1) if(checked>32) pulses=pulses+1;
reg phase_raw_2=0; wire reference_gclk_2;
initial begin #(1174.427228); forever begin phase_raw_2=1; #416.6665; phase_raw_2=0; #416.6665; end end
ICGx1_ASAP7_75t_R reference_2(.CLK(phase_raw_2),.ENA(u_split.u_own.cut_8870),.SE(1'b0),.GCLK(reference_gclk_2));
always @(phase_raw_2,reference_gclk_2,u_split.u_own.local_gclk_2) begin #0.001; if(checked>32 && reference_gclk_2 !== u_split.u_own.local_gclk_2) $fatal(1,"phase tt child2 mirrored original8870 pulse differs"); end
always @(posedge u_split.u_own.local_gclk_2) if(checked>32) pulses=pulses+1;
reg phase_raw_3=0; wire reference_gclk_3;
initial begin #(1169.485697); forever begin phase_raw_3=1; #416.6665; phase_raw_3=0; #416.6665; end end
ICGx1_ASAP7_75t_R reference_3(.CLK(phase_raw_3),.ENA(u_split.u_own.cut_8870),.SE(1'b0),.GCLK(reference_gclk_3));
always @(phase_raw_3,reference_gclk_3,u_split.u_own.local_gclk_3) begin #0.001; if(checked>32 && reference_gclk_3 !== u_split.u_own.local_gclk_3) $fatal(1,"phase tt child3 mirrored original8870 pulse differs"); end
always @(posedge u_split.u_own.local_gclk_3) if(checked>32) pulses=pulses+1;
reg phase_raw_4=0; wire reference_gclk_4;
initial begin #(1001.829719); forever begin phase_raw_4=1; #416.6665; phase_raw_4=0; #416.6665; end end
ICGx1_ASAP7_75t_R reference_4(.CLK(phase_raw_4),.ENA(u_split.u_own.cut_8870),.SE(1'b0),.GCLK(reference_gclk_4));
always @(phase_raw_4,reference_gclk_4,u_split.u_own.local_gclk_4) begin #0.001; if(checked>32 && reference_gclk_4 !== u_split.u_own.local_gclk_4) $fatal(1,"phase tt child4 mirrored original8870 pulse differs"); end
always @(posedge u_split.u_own.local_gclk_4) if(checked>32) pulses=pulses+1;
reg phase_raw_5=0; wire reference_gclk_5;
initial begin #(1167.272435); forever begin phase_raw_5=1; #416.6665; phase_raw_5=0; #416.6665; end end
ICGx1_ASAP7_75t_R reference_5(.CLK(phase_raw_5),.ENA(u_split.u_own.cut_8870),.SE(1'b0),.GCLK(reference_gclk_5));
always @(phase_raw_5,reference_gclk_5,u_split.u_own.local_gclk_5) begin #0.001; if(checked>32 && reference_gclk_5 !== u_split.u_own.local_gclk_5) $fatal(1,"phase tt child5 mirrored original8870 pulse differs"); end
always @(posedge u_split.u_own.local_gclk_5) if(checked>32) pulses=pulses+1;
reg phase_raw_6=0; wire reference_gclk_6;
initial begin #(1174.427228); forever begin phase_raw_6=1; #416.6665; phase_raw_6=0; #416.6665; end end
ICGx1_ASAP7_75t_R reference_6(.CLK(phase_raw_6),.ENA(u_split.u_own.cut_8870),.SE(1'b0),.GCLK(reference_gclk_6));
always @(phase_raw_6,reference_gclk_6,u_split.u_own.local_gclk_6) begin #0.001; if(checked>32 && reference_gclk_6 !== u_split.u_own.local_gclk_6) $fatal(1,"phase tt child6 mirrored original8870 pulse differs"); end
always @(posedge u_split.u_own.local_gclk_6) if(checked>32) pulses=pulses+1;
reg phase_raw_7=0; wire reference_gclk_7;
initial begin #(1174.427228); forever begin phase_raw_7=1; #416.6665; phase_raw_7=0; #416.6665; end end
ICGx1_ASAP7_75t_R reference_7(.CLK(phase_raw_7),.ENA(u_split.u_own.cut_8870),.SE(1'b0),.GCLK(reference_gclk_7));
always @(phase_raw_7,reference_gclk_7,u_split.u_own.local_gclk_7) begin #0.001; if(checked>32 && reference_gclk_7 !== u_split.u_own.local_gclk_7) $fatal(1,"phase tt child7 mirrored original8870 pulse differs"); end
always @(posedge u_split.u_own.local_gclk_7) if(checked>32) pulses=pulses+1;
reg phase_raw_8=0; wire reference_gclk_8;
initial begin #(1169.485697); forever begin phase_raw_8=1; #416.6665; phase_raw_8=0; #416.6665; end end
ICGx1_ASAP7_75t_R reference_8(.CLK(phase_raw_8),.ENA(u_split.u_own.cut_8870),.SE(1'b0),.GCLK(reference_gclk_8));
always @(phase_raw_8,reference_gclk_8,u_split.u_own.local_gclk_8) begin #0.001; if(checked>32 && reference_gclk_8 !== u_split.u_own.local_gclk_8) $fatal(1,"phase tt child8 mirrored original8870 pulse differs"); end
always @(posedge u_split.u_own.local_gclk_8) if(checked>32) pulses=pulses+1;
reg phase_raw_9=0; wire reference_gclk_9;
initial begin #(1001.829719); forever begin phase_raw_9=1; #416.6665; phase_raw_9=0; #416.6665; end end
ICGx1_ASAP7_75t_R reference_9(.CLK(phase_raw_9),.ENA(u_split.u_own.cut_8870),.SE(1'b0),.GCLK(reference_gclk_9));
always @(phase_raw_9,reference_gclk_9,u_split.u_own.local_gclk_9) begin #0.001; if(checked>32 && reference_gclk_9 !== u_split.u_own.local_gclk_9) $fatal(1,"phase tt child9 mirrored original8870 pulse differs"); end
always @(posedge u_split.u_own.local_gclk_9) if(checked>32) pulses=pulses+1;
reg phase_raw_10=0; wire reference_gclk_10;
initial begin #(976.585019); forever begin phase_raw_10=1; #416.6665; phase_raw_10=0; #416.6665; end end
ICGx1_ASAP7_75t_R reference_10(.CLK(phase_raw_10),.ENA(u_split.u_own.cut_8870),.SE(1'b0),.GCLK(reference_gclk_10));
always @(phase_raw_10,reference_gclk_10,u_split.u_own.local_gclk_10) begin #0.001; if(checked>32 && reference_gclk_10 !== u_split.u_own.local_gclk_10) $fatal(1,"phase tt child10 mirrored original8870 pulse differs"); end
always @(posedge u_split.u_own.local_gclk_10) if(checked>32) pulses=pulses+1;
reg phase_raw_11=0; wire reference_gclk_11;
initial begin #(917.766650); forever begin phase_raw_11=1; #416.6665; phase_raw_11=0; #416.6665; end end
ICGx1_ASAP7_75t_R reference_11(.CLK(phase_raw_11),.ENA(u_split.u_own.cut_8870),.SE(1'b0),.GCLK(reference_gclk_11));
always @(phase_raw_11,reference_gclk_11,u_split.u_own.local_gclk_11) begin #0.001; if(checked>32 && reference_gclk_11 !== u_split.u_own.local_gclk_11) $fatal(1,"phase tt child11 mirrored original8870 pulse differs"); end
always @(posedge u_split.u_own.local_gclk_11) if(checked>32) pulses=pulses+1;
initial begin
clk=0;
for (integer cycle=0; cycle<4128;cycle=cycle+1) begin
for(integer bitbase=0;bitbase<1;bitbase=bitbase+1) cgi=$urandom_range(0,1);
for(integer bitbase=0;bitbase<18;bitbase=bitbase+1) xs_a1[bitbase]=$urandom_range(0,1);
for(integer bitbase=0;bitbase<10;bitbase=bitbase+1) xs_g1[bitbase]=$urandom_range(0,1);
for(integer bitbase=0;bitbase<14;bitbase=bitbase+1) xs_a2[bitbase]=$urandom_range(0,1);
for(integer bitbase=0;bitbase<10;bitbase=bitbase+1) xs_g2[bitbase]=$urandom_range(0,1);
for(integer bitbase=0;bitbase<1636;bitbase=bitbase+1) rin[bitbase]=$urandom_range(0,1);
for(integer bitbase=0;bitbase<2069;bitbase=bitbase+1) bin[bitbase]=$urandom_range(0,1);
for(integer bitbase=0;bitbase<100;bitbase=bitbase+1) gin[bitbase]=$urandom_range(0,1);
rst_n=(cycle>=16 && !(cycle>=2000 && cycle<2016));
#416.6665; clk=1; #200;
// Warm initial unreset library state before comparing defined operation.
if (cycle>=32) begin




if(u_split.u_own.local_enable !== u_split.u_own.cut_8870) $fatal(1,"enable mirror state differs from original8870"); enable_checks=enable_checks+1; checked=checked+1; end; #216.6665; clk=0;
end
$display("LOCAL_ICG_PHASE_tt checked=%0d enable_checks=%0d pulses=%0d",checked,enable_checks,pulses); if(pulses<100) $fatal(1,"no enabled pulses exercised");
if(mismatches) $fatal(1,"retained own logic differs from flat pinned parent");
$finish;
end
endmodule
