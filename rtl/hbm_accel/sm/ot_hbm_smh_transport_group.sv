// Wires-only production parents of six physical transport groups.
module ot_hbm_smh_group_pt_w #(parameter integer TAGW=16,NBEAT=13,CHUNK=128) (input wire clk,rst_a,input wire [1635:0] rin,input wire [2068:0] bin,output wire [1635:0] rpm,output wire [2068:0] bm,output wire [817:0] rl1_n,rl1_s,output wire [2068:0] bk1_n,bk1_s,output wire [12:0] ohl1_n,ohl1_s);
generate if(TAGW!=16||NBEAT!=13||CHUNK!=128) begin:g_illegal SMH_GROUP_PRODUCTION_SHAPE_REQUIRED fail(); end endgenerate
ot_smh_tr_group_row_w u_row0(.clk(clk),.rst_a(rst_a),.d(rin[817:0]),.first(rl1_n),.last(rpm[817:0]));
ot_smh_tr_group_row_w u_row1(.clk(clk),.rst_a(rst_a),.d(rin[1635:818]),.first(rl1_s),.last(rpm[1635:818]));
`ifdef OT_SMH_WEST_SPLIT
ot_smh_tr_group_beat_e u_beat_t(.clk(clk),.rst_a(rst_a),.d(bin),.last(bm));
ot_smh_tr_group_land u_land_n(.clk(clk),.rst_a(rst_a),.d(bin),.q(bk1_n));
ot_smh_tr_group_land u_land_s(.clk(clk),.rst_a(rst_a),.d(bin),.q(bk1_s));
`else
ot_smh_tr_group_beat_w u_beat(.clk(clk),.rst_a(rst_a),.d(bin),.north(bk1_n),.south(bk1_s),.last(bm));
`endif
assign ohl1_n=bk1_n[2048+:13];assign ohl1_s=bk1_s[2048+:13];
endmodule
module ot_hbm_smh_group_pt_e #(parameter integer TAGW=16,NBEAT=13,CHUNK=128) (input wire clk,rst_a,input wire [1635:0] rpm,input wire [2068:0] bm,output wire [1635:0] rout,output wire [2068:0] bout);
generate if(TAGW!=16||NBEAT!=13||CHUNK!=128) begin:g_illegal SMH_GROUP_PRODUCTION_SHAPE_REQUIRED fail(); end endgenerate
ot_smh_tr_group_row_e u_row0(.clk(clk),.rst_a(rst_a),.d(rpm[817:0]),.last(rout[817:0]));
ot_smh_tr_group_row_e u_row1(.clk(clk),.rst_a(rst_a),.d(rpm[1635:818]),.last(rout[1635:818]));
ot_smh_tr_group_beat_e u_beat(.clk(clk),.rst_a(rst_a),.d(bm),.last(bout));
endmodule
