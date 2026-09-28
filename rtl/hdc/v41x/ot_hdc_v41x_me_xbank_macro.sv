`timescale 1ns/1ps
// Macro-backed variant of the V4.1 ME activation store.  Eight 16-bit lanes
// with the same c=b%8 are one 128-bit SRAM word.  There is one 1R1W macro per
// (position,c), because the tile reads both positions on the same cycle.
// The ASAP7 macro is an analytical abstract, not measured silicon.
module ot_hdc_v41x_me_xbank_macro #(
    parameter integer MG = 8,
    parameter integer MP = 2,
    parameter integer G = 4,
    parameter integer KMAX = 5120,
    parameter integer NBW = 14,
    parameter integer EW = 13
) (
    input wire clk,
    input wire wr_v,
    input wire [$clog2(MP+1)-1:0] wr_p,
    input wire [EW-1:0] wr_e,
    input wire [G*16-1:0] wr_d,
    input wire pre_v,
    input wire [$clog2(MP+1)-1:0] pre_p,
    input wire [EW-1:0] pre_e,
    input wire [8*MG*16-1:0] pre_d,
    input wire [1:0] rd_rot,
    input wire [7:0] rq_v,
    input wire [8*NBW-1:0] rq_q,
    input wire [8*4-1:0] rq_plg,
    output wire [8*MG*MP*16-1:0] rd_x
);
    localparam integer LANES = 8*MG;
    localparam integer ROWS = (KMAX+LANES-1)/LANES;
    localparam integer LG = $clog2(LANES);
    wire [MP*8*128-1:0] q_bus;
    genvar p,c,b;
    generate for (p=0;p<MP;p=p+1) begin : g_pos
        for (c=0;c<8;c=c+1) begin : g_c
            reg hit;
            reg [6:0] wa;
            reg [127:0] wd,wm;
            integer j,u;
            always @* begin
                hit=1'b0; wa='0; wd='0; wm='0;
                if (pre_v && pre_p == p && pre_e < KMAX) begin
                    hit=1'b1;
                    wa=pre_e >> LG;
                    for (u=0;u<MG;u=u+1) begin
                        wd[16*u +:16]=pre_d[(8*u+c)*16 +:16];
                        wm[16*u +:16]=16'hffff;
                    end
                end else if (wr_v && wr_p == p) begin
                    for (j=0;j<G;j=j+1)
                        if (wr_e+j < KMAX && ((wr_e+j)%8)==c) begin
                            hit=1'b1;
                            wa=(wr_e+j)>>LG;
                            wd[(((wr_e+j)%LANES)/8)*16 +:16]=wr_d[j*16 +:16];
                            wm[(((wr_e+j)%LANES)/8)*16 +:16]=16'hffff;
                        end
                end
            end
            wire [3:0] plg = rq_plg[c*4 +:4];
            wire [NBW-1:0] beat = rq_q[c*NBW +:NBW];
            wire [NBW+3:0] first_term = {4'b0,beat} << (3+plg);
            wire [6:0] ra = first_term >> LG;
            wire [255:0] q;
            ot_sram_1r1w_128x256_m1_r2c2 u_mem (
                .clk(clk), .r_ce_in(rq_v[c] && ra < ROWS), .r_addr_in(ra), .rd_out(q),
                .w_ce_in(hit), .w_addr_in(wa), .wd_in({128'b0,wd}),
                .w_mask_in({128'b0,wm}), .rr_en(2'b0), .rr_addr(14'b0),
                .cr_en(2'b0), .cr_sel(16'b0));
            assign q_bus[(p*8+c)*128 +:128] = q[127:0];
        end
    end endgenerate
    generate for (b=0;b<LANES;b=b+1) begin : g_broadcast
        wire [3:0] plg = rq_plg[(b%8)*4 +:4];
        wire [NBW-1:0] beat = rq_q[(b%8)*NBW +:NBW];
        wire [LG-1:0] logical_src = ((beat << (3+plg)) + (b & ((8 << plg)-1))) & (LANES-1);
        wire [LG-1:0] src = ((((logical_src >> 4)+rd_rot)&3)<<4) | (logical_src&15);
        // Every source keeps chain index c=b%8.  Select only among the eight
        // lanes of this local macro; a dynamic c select would synthesize an
        // unnecessary die-wide 16-macro crossbar.
        reg [$clog2(MG)-1:0] src_u_q;
        always @(posedge clk) src_u_q <= src >> 3;
        for (p=0;p<MP;p=p+1) begin : g_bpos
            assign rd_x[(b*MP+p)*16 +:16] = q_bus[(p*8+(b%8))*128+src_u_q*16 +:16];
        end
    end endgenerate
endmodule
