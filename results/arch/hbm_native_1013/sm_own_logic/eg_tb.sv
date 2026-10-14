module tb;
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
gold_eg u_gold(.clk(clk),.rst_n(rst_n),.cgi(cgi),.cgo(g_cgo),.xs_a1(xs_a1),.xs_g1(xs_g1),.xs_a2(xs_a2),.xs_g2(xs_g2),.rin(rin),.bin(bin),.rout(g_rout),.bout(g_bout),.gin(gin),.gout(g_gout));
split_eg u_split(.clk(clk),.rst_n(rst_n),.cgi(cgi),.cgo(s_cgo),.xs_a1(xs_a1),.xs_g1(xs_g1),.xs_a2(xs_a2),.xs_g2(xs_g2),.rin(rin),.bin(bin),.rout(s_rout),.bout(s_bout),.gin(gin),.gout(s_gout),.clk_child_0(clk),.clk_child_1(clk),.clk_child_2(clk),.clk_child_3(clk),.clk_child_4(clk),.clk_child_5(clk),.clk_child_6(clk),.clk_child_7(clk),.clk_child_8(clk),.clk_child_9(clk),.clk_child_10(clk),.clk_child_11(clk));
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
#2; clk=1; #2;
// Warm initial unreset library state before comparing defined operation.
if (cycle>=32) begin
if(g_cgo !== s_cgo) mismatches=mismatches+1;
if(g_rout !== s_rout) mismatches=mismatches+1;
if(g_bout !== s_bout) mismatches=mismatches+1;
if(g_gout !== s_gout) mismatches=mismatches+1;
checked=checked+1; end; clk=0; #2;
end
$display("OWN_LOGIC_CYCLE_BENCH checked=%0d mismatches=%0d",checked,mismatches);
if(mismatches) $fatal(1,"retained own logic differs from flat pinned parent");
$finish;
end
endmodule
