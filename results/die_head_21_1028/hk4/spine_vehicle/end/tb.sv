`timescale 1ns/1ps
module tb; reg clk=0; always #5 clk=~clk; reg arst_n=0; integer cycle,bitn,errors=0;
reg [565:0] x_i;
wire [565:0] b_o;
wire [565:0] ref_b_o;
wire [565:0] xw_o;
wire [565:0] ref_xw_o;
wire [565:0] xe_o;
wire [565:0] ref_xe_o;
reg [565:0] bw_i;
reg [565:0] be_i;
reg [276:0] hu_i;
wire [276:0] hu_o;
wire [276:0] ref_hu_o;
reg [277:0] hd_i;
wire [277:0] hd_o;
wire [277:0] ref_hd_o;
reg [64:0] au_i;
wire [64:0] au_o;
wire [64:0] ref_au_o;
reg [64:0] ad_i;
wire [64:0] ad_o;
wire [64:0] ref_ad_o;
reg [64:0] bu_i;
wire [64:0] bu_o;
wire [64:0] ref_bu_o;
reg [64:0] bd_i;
wire [64:0] bd_o;
wire [64:0] ref_bd_o;
wire [565:0] inner_xw_o;
wire [565:0] inner_xe_o;
wire [565:0] inner_bw_i;
wire [565:0] inner_be_i;
spine_reference u_reference(.clk(clk),.arst_n(arst_n),.x_i(x_i),.b_o(ref_b_o),.xw_o(ref_xw_o),.xe_o(ref_xe_o),.bw_i(bw_i),.be_i(be_i),.hu_i(hu_i),.hu_o(ref_hu_o),.hd_i(hd_i),.hd_o(ref_hd_o),.au_i(au_i),.au_o(ref_au_o),.ad_i(ad_i),.ad_o(ref_ad_o),.bu_i(bu_i),.bu_o(ref_bu_o),.bd_i(bd_i),.bd_o(ref_bd_o));
ot_s81hd_spn_end_strip u_hd_spn_end(.clk(clk),.arst_n(arst_n),.x_i(x_i),.b_o(b_o),.xw_o(inner_xw_o),.xe_o(inner_xe_o),.bw_i(inner_bw_i),.be_i(inner_be_i),.hu_i(hu_i),.hu_o(hu_o),.hd_i(hd_i),.hd_o(hd_o),.au_i(au_i),.au_o(au_o),.ad_i(ad_i),.ad_o(ad_o),.bu_i(bu_i),.bu_o(bu_o),.bd_i(bd_i),.bd_o(bd_o));
ot_s81hd_spn_wshim u_shim_xw_o(.clk(clk),.arst_n(arst_n),.link_i(inner_xw_o),.link_o(xw_o));
ot_s81hd_spn_wshim u_shim_bw_i(.clk(clk),.arst_n(arst_n),.link_i(bw_i),.link_o(inner_bw_i));
ot_s81hd_spn_eshim u_shim_xe_o(.clk(clk),.arst_n(arst_n),.link_i(inner_xe_o),.link_o(xe_o));
ot_s81hd_spn_eshim u_shim_be_i(.clk(clk),.arst_n(arst_n),.link_i(be_i),.link_o(inner_be_i));
initial begin
x_i='0;
bw_i='0;
be_i='0;
hu_i='0;
hd_i='0;
au_i='0;
ad_i='0;
bu_i='0;
bd_i='0;
repeat(5) @(negedge clk); arst_n=1;
for(cycle=0;cycle<1000;cycle=cycle+1)begin @(negedge clk);
for(bitn=0;bitn<566;bitn=bitn+1)x_i[bitn]=$urandom();
x_i[565]=1; x_i[512]=(cycle%64==0); x_i[513]=1; x_i[514]=(cycle%9==0);
for(bitn=0;bitn<566;bitn=bitn+1)bw_i[bitn]=$urandom();
bw_i[565]=1; bw_i[512]=(cycle%64==0); bw_i[513]=1; bw_i[514]=(cycle%9==0);
for(bitn=0;bitn<566;bitn=bitn+1)be_i[bitn]=$urandom();
be_i[565]=1; be_i[512]=(cycle%64==0); be_i[513]=1; be_i[514]=(cycle%9==0);
for(bitn=0;bitn<277;bitn=bitn+1)hu_i[bitn]=$urandom();
for(bitn=0;bitn<278;bitn=bitn+1)hd_i[bitn]=$urandom();
for(bitn=0;bitn<65;bitn=bitn+1)au_i[bitn]=$urandom();
for(bitn=0;bitn<65;bitn=bitn+1)ad_i[bitn]=$urandom();
for(bitn=0;bitn<65;bitn=bitn+1)bu_i[bitn]=$urandom();
for(bitn=0;bitn<65;bitn=bitn+1)bd_i[bitn]=$urandom();
@(posedge clk);#1;if(cycle>180)begin
if(b_o!==ref_b_o)begin errors=errors+1;if(errors<5)$display("MISMATCH b_o cycle=%0d",cycle);end
if(xw_o!==ref_xw_o)begin errors=errors+1;if(errors<5)$display("MISMATCH xw_o cycle=%0d",cycle);end
if(xe_o!==ref_xe_o)begin errors=errors+1;if(errors<5)$display("MISMATCH xe_o cycle=%0d",cycle);end
if(hu_o!==ref_hu_o)begin errors=errors+1;if(errors<5)$display("MISMATCH hu_o cycle=%0d",cycle);end
if(hd_o!==ref_hd_o)begin errors=errors+1;if(errors<5)$display("MISMATCH hd_o cycle=%0d",cycle);end
if(au_o!==ref_au_o)begin errors=errors+1;if(errors<5)$display("MISMATCH au_o cycle=%0d",cycle);end
if(ad_o!==ref_ad_o)begin errors=errors+1;if(errors<5)$display("MISMATCH ad_o cycle=%0d",cycle);end
if(bu_o!==ref_bu_o)begin errors=errors+1;if(errors<5)$display("MISMATCH bu_o cycle=%0d",cycle);end
if(bd_o!==ref_bd_o)begin errors=errors+1;if(errors<5)$display("MISMATCH bd_o cycle=%0d",cycle);end
end end if(errors)$fatal(1,"SPINE_STRIP_FAIL errors=%0d",errors);$display("SPINE_STRIP_PASS cycles=1000");$finish;end endmodule