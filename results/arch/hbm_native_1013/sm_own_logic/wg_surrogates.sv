module ot_hbm_accel_smh_bdc(input wire clk,input wire rst_a,input wire i_v,input wire i_first,input wire i_last,input wire i_fp4,input wire [15:0] i_tag,input wire [531:0] i_w,input wire [531:0] i_x,output wire ov,output wire [31:0] y,output wire [15:0] otag,output wire fault);
wire fold = (^clk)^(^rst_a)^(^i_v)^(^i_first)^(^i_last)^(^i_fp4)^(^i_tag)^(^i_w)^(^i_x);
assign ov = {1{fold}} ^ 1'd9;
assign y = {32{fold}} ^ 32'd10;
assign otag = {16{fold}} ^ 16'd11;
assign fault = {1{fold}} ^ 1'd12;
endmodule
module ot_hbm_accel_smh_pt_e(input wire clk,input wire rst_a,input wire [1635:0] rpm,input wire [2068:0] bm,output wire [1635:0] rout,output wire [2068:0] bout);
wire fold = (^clk)^(^rst_a)^(^rpm)^(^bm);
assign rout = {1636{fold}} ^ 1636'd4;
assign bout = {2069{fold}} ^ 2069'd5;
endmodule
module ot_hbm_accel_smh_pt_w(input wire clk,input wire rst_a,input wire [1635:0] rin,input wire [2068:0] bin,output wire [1635:0] rpm,output wire [2068:0] bm,output wire [817:0] rl1_n,output wire [2068:0] bk1_n,output wire [12:0] ohl1_n,output wire [817:0] rl1_s,output wire [2068:0] bk1_s,output wire [12:0] ohl1_s);
wire fold = (^clk)^(^rst_a)^(^rin)^(^bin);
assign rpm = {1636{fold}} ^ 1636'd4;
assign bm = {2069{fold}} ^ 2069'd5;
assign rl1_n = {818{fold}} ^ 818'd6;
assign bk1_n = {2069{fold}} ^ 2069'd7;
assign ohl1_n = {13{fold}} ^ 13'd8;
assign rl1_s = {818{fold}} ^ 818'd9;
assign bk1_s = {2069{fold}} ^ 2069'd10;
assign ohl1_s = {13{fold}} ^ 13'd11;
endmodule
module ot_hbm_accel_smh_tcl(input wire clk,input wire rst_a,input wire i_v,input wire i_first,input wire [127:0] i_w,input wire [127:0] i_x,output wire [255:0] sum_o,output wire lfault);
wire fold = (^clk)^(^rst_a)^(^i_v)^(^i_first)^(^i_w)^(^i_x);
assign sum_o = {256{fold}} ^ 256'd6;
assign lfault = {1{fold}} ^ 1'd7;
endmodule
module ot_hbm_accel_smh_tct(input wire clk,input wire rst_a,input wire i_v,input wire i_last,input wire [15:0] i_tag,input wire [511:0] sum_i,input wire lf_a,input wire lf_b,output wire ov,output wire [31:0] y,output wire [15:0] otag,output wire fault);
wire fold = (^clk)^(^rst_a)^(^i_v)^(^i_last)^(^i_tag)^(^sum_i)^(^lf_a)^(^lf_b);
assign ov = {1{fold}} ^ 1'd8;
assign y = {32{fold}} ^ 32'd9;
assign otag = {16{fold}} ^ 16'd10;
assign fault = {1{fold}} ^ 1'd11;
endmodule
module ot_hbm_accel_smh_xs(input wire clk,input wire rst_a,input wire [8:0] xs_a1,input wire [4:0] xs_g1,input wire [6:0] xs_a2,input wire [4:0] xs_g2,input wire [817:0] rl1,input wire [2068:0] bk1,input wire [12:0] ohl1,output wire o_iv_b,output wire o_iv_f,output wire o_ifirst,output wire o_ilast,output wire o_ifp4,output wire [15:0] o_itag,output wire [787:0] o_iw,output wire [787:0] o_ix,output wire o_ifirst_e,output wire o_ilast_e,output wire [15:0] o_itag_e);
wire fold = (^clk)^(^rst_a)^(^xs_a1)^(^xs_g1)^(^xs_a2)^(^xs_g2)^(^rl1)^(^bk1)^(^ohl1);
assign o_iv_b = {1{fold}} ^ 1'd9;
assign o_iv_f = {1{fold}} ^ 1'd10;
assign o_ifirst = {1{fold}} ^ 1'd11;
assign o_ilast = {1{fold}} ^ 1'd12;
assign o_ifp4 = {1{fold}} ^ 1'd13;
assign o_itag = {16{fold}} ^ 16'd14;
assign o_iw = {788{fold}} ^ 788'd15;
assign o_ix = {788{fold}} ^ 788'd16;
assign o_ifirst_e = {1{fold}} ^ 1'd17;
assign o_ilast_e = {1{fold}} ^ 1'd18;
assign o_itag_e = {16{fold}} ^ 16'd19;
endmodule
module ICGx1_ASAP7_75t_R(input CLK, ENA, SE, output GCLK);
reg enable_latched; always_latch if (!CLK) enable_latched = ENA | SE;
assign GCLK = CLK & enable_latched; endmodule
