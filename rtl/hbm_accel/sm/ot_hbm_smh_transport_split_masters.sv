// West beat transport split (H-ELEM-A 2026-10-15, structural repair of beat_w
// native FAIL launch 227 / capture 463.1 ps): the 216x216 beat_w master forked
// one W-face input bus to three register sets (transit + north + south landing),
// so the landing flops sat up to ~200 um from their W input pins. The split uses
//   transit : the CLOSED 43.2x216 ot_smh_tr_group_beat_e master (same RTL body as
//             beat_w's u_transit: 2 stages, same reset mask), and
//   landing : ONE new one-edge master, hardened once and instanced twice (N, S),
//             input on one long face and output on the opposite face 43.2 um away.
// Same 51 west logical slices, same edge counts (transit 2, landing 1): 0 cycles.
module ot_smh_tr_group_land(input wire clk,rst_a,input wire [2068:0] d,output wire [2068:0] q);
localparam [2068:0] BM=2069'b1<<2068;
for(genvar k=0;k<17;k=k+1)begin:g_slice
localparam integer OFF=k*128,W=(2069-OFF<128)?2069-OFF:128;
wire [W-1:0] unused;
`ifdef OT_SMH_LAND_MUT_LAT
// Mutant: landing one edge late (must fail the exact bench).
ot_hbm_smh_transport_slice #(.W(W),.STAGES(2),.RESET_MASK(BM[OFF+:W])) u_land
(.clk(clk),.rst_a(rst_a),.d(d[OFF+:W]),.first(unused),.last(q[OFF+:W]));
`else
ot_hbm_smh_transport_slice #(.W(W),.STAGES(1),.RESET_MASK(BM[OFF+:W])) u_land
(.clk(clk),.rst_a(rst_a),.d(d[OFF+:W]),.first(q[OFF+:W]),.last(unused));
`endif
end endmodule
