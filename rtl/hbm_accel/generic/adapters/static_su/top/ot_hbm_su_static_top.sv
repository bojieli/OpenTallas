`timescale 1ns/1ps
`default_nettype none
// ---------------------------------------------------------------------------------------------------------------------
// WHOLE static SU (H-ELEM-B 2026-10-15): four quarter masters ot_hbm_su_static_quarter (each 4 port-group slices + a core:
// 512 lanes, 512 pinned store banks, 4 reducers, 4 coherent RF replicas, the global-lane-0 SIDE pipe in quarter 0 slice 0)
// + the only cross-quarter wiring, the RF write relay network. Quarter q is placed in quadrant q's VM band beside VM slice
// q (T_band2__npg4_s5); its VM pins are the LG SU-station pins of slice q (4 bank-pair port groups, NPG 4 everywhere).
// RF coherence: the scalar result of reducer w (tag[8] = write RF word tag[7:0]) travels to EVERY quarter's replica over a
// dedicated point-to-point relay route of exactly RF_RELAY registered stages (16 routes; the local route is the same
// depth), so all four replicas commit each word on the same edge: reducer command edge n -> reducer issue n+2 -> scalar
// held from n+9 -> relay -> RF write pins sample n+10+RF_RELAY -> commit n+11+RF_RELAY -> an RF read command sampled at
// edge >= n+11+RF_RELAY sees it. RF_RELAY is set from the die geometry (worst quarter-to-quarter route / reach per stage);
// the compiler uses the same value.
// No credits/ready/arbitration anywhere; compile-time conflicts are checked (FAULT), never resolved at run time.
// MUT (bench): quarter mutants pass through (1 fill phase, 2 drain group, 4 RF-broadcast phase); 8 = the relay route from
// reducer 1 to quarter 3's replica is missing (replica incoherence).
// ---------------------------------------------------------------------------------------------------------------------
module ot_hbm_su_static_top #(
 parameter integer READ_RETURN=10,WRITE_RETURN=7,RF_RELAY=8,FETCH_EXTRA_EDGES=2,MLAT=3,ALAT=3,LEAF=0,MUT=0,MULTIRATE=0
)(
 input wire [15:0] pg_clk,                       // 4 port-group roots per quarter
 input wire [4095:0] clk_lane, input wire [2047:0] clk_insert, input wire [511:0] rst_lane_n,
 input wire [63:0] clk_bcast, rst_bcast_n,
 input wire [511:0] clk_bank,
 input wire [3071:0] clk_bank_macro, // six separately delivered SRAM clocks per store bank
 input wire [255:0] clk_rf,
 input wire [15:0] clk_ctl,                      // one root per port-group slice
 input wire [3:0] clk_core,clk_red,
 input wire [5:0] clk_side,
 input wire [3:0] clk_relay,                     // one root per source quarter's relay routes
 input wire rst_n,
 input wire bridge_rst_n, // phase-zero reset for MULTIRATE boundary only
 input wire [4*1742-1:0] control,
 input wire [4*8*30-1:0] vmr_cmd,
 input wire [4*8*39-1:0] vmw_cmd,
 input wire [4*6*9-1:0] rf_rd_cmd,
 input wire [4*74-1:0] red_cmd,
 output wire [4*8*17-1:0] lg_rq, output wire [4*8*281-1:0] lg_wq,
 input wire [4*8*257-1:0] lg_rr, input wire [31:0] lg_w_done,
 output wire [19:0] fault                        // per quarter {core, slice 3..0}
);
 localparam integer QMUT=(MUT==8)?0:MUT;
 wire [3:0] red_sv; wire [4*32-1:0] red_tag,red_x;
 // relay[w][d]: reducer w -> replica d, RF_RELAY stages of {v, addr8, data32}
 wire [40:0] rly_out [0:3][0:3];
 for(genvar w=0;w<4;w=w+1)begin:g_src
  wire [40:0] head={red_sv[w]&&red_tag[w*32+8],red_tag[w*32+:8],red_x[w*32+:32]};
  for(genvar d=0;d<4;d=d+1)begin:g_dst
   if(RF_RELAY==0)begin:g_wire
    assign rly_out[w][d]=head;
   end else begin:g_stages
    reg st_v [0:RF_RELAY-1]; reg [39:0] st_d [0:RF_RELAY-1];
    integer k;
    always @(posedge clk_relay[w] or negedge rst_n)
     if(!rst_n)for(k=0;k<RF_RELAY;k=k+1)st_v[k]<=1'b0;
     else begin st_v[0]<=head[40];for(k=1;k<RF_RELAY;k=k+1)st_v[k]<=st_v[k-1]; end
    always @(posedge clk_relay[w])begin st_d[0]<=head[39:0];for(k=1;k<RF_RELAY;k=k+1)st_d[k]<=st_d[k-1]; end
    assign rly_out[w][d]={st_v[RF_RELAY-1]&&!(MUT==8&&w==1&&d==3),st_d[RF_RELAY-1]};
   end
  end
 end
 for(genvar q=0;q<4;q=q+1)begin:g_q
  wire [3:0] wv; wire [31:0] wa; wire [127:0] wd;
  for(genvar w=0;w<4;w=w+1)begin:g_w
   assign wv[w]=rly_out[w][q][40]; assign wa[w*8+:8]=rly_out[w][q][39:32]; assign wd[w*32+:32]=rly_out[w][q][31:0];
  end
  ot_hbm_su_static_quarter #(.QID(q),.READ_RETURN(READ_RETURN),.WRITE_RETURN(WRITE_RETURN),
   .FETCH_EXTRA_EDGES(FETCH_EXTRA_EDGES),.MLAT(MLAT),.ALAT(ALAT),.LEAF(LEAF),.MUT(QMUT),.MULTIRATE(MULTIRATE)) u_quarter(
   .pg_clk(pg_clk[q*4+:4]),.clk_lane(clk_lane[q*1024+:1024]),.clk_insert(clk_insert[q*512+:512]),
   .rst_lane_n(rst_lane_n[q*128+:128]),.clk_bcast(clk_bcast[q*16+:16]),.rst_bcast_n(rst_bcast_n[q*16+:16]),
   .clk_bank(clk_bank[q*128+:128]),.clk_bank_macro(clk_bank_macro[q*768+:768]),.clk_rf(clk_rf[q*64+:64]),.clk_ctl(clk_ctl[q*4+:4]),.clk_core(clk_core[q]),
   .clk_red(clk_red[q]),.clk_side(clk_side),.rst_n(rst_n),.bridge_rst_n(bridge_rst_n),.control(control[q*1742+:1742]),
   .vmr_cmd(vmr_cmd[q*240+:240]),.vmw_cmd(vmw_cmd[q*312+:312]),.rf_rd_cmd(rf_rd_cmd[q*54+:54]),
   .red_cmd(red_cmd[q*74+:74]),.rf_wv(wv),.rf_wa(wa),.rf_wd(wd),.red_sv(red_sv[q]),.red_tag(red_tag[q*32+:32]),
   .red_x(red_x[q*32+:32]),.lg_rq(lg_rq[q*136+:136]),.lg_wq(lg_wq[q*2248+:2248]),.lg_rr(lg_rr[q*2056+:2056]),
   .lg_w_done(lg_w_done[q*8+:8]),.fault(fault[q*5+:5]));
 end
endmodule
`default_nettype wire
