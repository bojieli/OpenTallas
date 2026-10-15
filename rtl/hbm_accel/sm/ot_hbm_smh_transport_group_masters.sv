// Four physical group masters retain the original96logical128-bit/tail slices.
// Groups keep original edge counts and reset masks; hardened boundaries add no cycles.
module ot_smh_tr_group_row_w(input wire clk,rst_a,input wire [817:0] d,output wire [817:0] first,last);
localparam [817:0] RM=(818'b11<<816)|(818'b1<<7);
for(genvar k=0;k<7;k=k+1)begin:g_slice
localparam integer OFF=k*128,W=(818-OFF<128)?818-OFF:128;
ot_hbm_smh_transport_slice #(.W(W),.RESET_MASK(RM[OFF+:W])) u_slice
(.clk(clk),.rst_a(rst_a),.d(d[OFF+:W]),.first(first[OFF+:W]),.last(last[OFF+:W]));
end endmodule
module ot_smh_tr_group_row_e(input wire clk,rst_a,input wire [817:0] d,output wire [817:0] last);
localparam [817:0] RM=(818'b11<<816)|(818'b1<<7);
for(genvar k=0;k<7;k=k+1)begin:g_slice
localparam integer OFF=k*128,W=(818-OFF<128)?818-OFF:128;
wire [W-1:0] unused_first;
ot_hbm_smh_transport_slice #(.W(W),.RESET_MASK(RM[OFF+:W])) u_slice
(.clk(clk),.rst_a(rst_a),.d(d[OFF+:W]),.first(unused_first),.last(last[OFF+:W]));
end endmodule
module ot_smh_tr_group_beat_w(input wire clk,rst_a,input wire [2068:0] d,output wire [2068:0] north,south,last);
localparam [2068:0] BM=2069'b1<<2068;
for(genvar k=0;k<17;k=k+1)begin:g_slice
localparam integer OFF=k*128,W=(2069-OFF<128)?2069-OFF:128;
wire [W-1:0] unused_first;
ot_hbm_smh_transport_slice #(.W(W),.RESET_MASK(BM[OFF+:W])) u_transit
(.clk(clk),.rst_a(rst_a),.d(d[OFF+:W]),.first(unused_first),.last(last[OFF+:W]));
wire [W-1:0] unused_north;
ot_hbm_smh_transport_slice #(.W(W),.STAGES(1),.RESET_MASK(BM[OFF+:W])) u_north
(.clk(clk),.rst_a(rst_a),.d(d[OFF+:W]),.first(north[OFF+:W]),.last(unused_north));
wire [W-1:0] unused_south;
ot_hbm_smh_transport_slice #(.W(W),.STAGES(1),.RESET_MASK(BM[OFF+:W])) u_south
(.clk(clk),.rst_a(rst_a),.d(d[OFF+:W]),.first(south[OFF+:W]),.last(unused_south));
end endmodule
module ot_smh_tr_group_beat_e(input wire clk,rst_a,input wire [2068:0] d,output wire [2068:0] last);
localparam [2068:0] BM=2069'b1<<2068;
for(genvar k=0;k<17;k=k+1)begin:g_slice
localparam integer OFF=k*128,W=(2069-OFF<128)?2069-OFF:128;
wire [W-1:0] unused_first;
ot_hbm_smh_transport_slice #(.W(W),.RESET_MASK(BM[OFF+:W])) u_transit
(.clk(clk),.rst_a(rst_a),.d(d[OFF+:W]),.first(unused_first),.last(last[OFF+:W]));
end endmodule
