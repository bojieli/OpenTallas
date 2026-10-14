`timescale 1ns/1ps
`default_nettype none
// ---------------------------------------------------------------------------------------------------------------------
// HBM B2 native MTP SWAP-IN (el1013-ds-mtp-lead [mtp-rtl] 2026-10-13): the dispatch group of HBM -> VM LOADs.
// Same transaction as the swap-out (ot_hgi_b2_swap_disp.sv): beats {v, last, cluster 2, move 227} into the UNCHANGED
// spine-side dispatcher S (group collect, same-edge release, credit 2 a cluster, join), the UNCHANGED relays and the
// UNCHANGED cluster-side move station E; the engine of cluster q is one UNCHANGED ot_hgi_dma_front B2 1 / QID q (svc
// request lane + NL data lanes of its own stack -> the wide WRITE lanes of its local VM slice).
//   ot_hgi_b2_swapin_fe  (cluster side, glue at the front's mv pin): the front reports one mv_done a move (every
//     destination sector's wide write acknowledged) and no src / quiet; the glue gives E what S's join needs:
//       src   = the front's mv_done   (S's credit return: outstanding = accepted - done),
//       quiet = no move in the front  (a 2-b count: + the accept edge, - mv_done).
//     So S.done = every VM write of every released LOAD acknowledged, nothing held: the group's load is visible.
// Wires a cluster (spine <-> cluster): down 228 b, up 3 b -- the SAME links as the swap-out (a move word says its own
// direction: src space HBM = load); in the die ONE S / relay / E set carries both, E hands a load to the front and a
// store to the back.  Cross-cluster payload: none.
// ---------------------------------------------------------------------------------------------------------------------
module ot_hgi_b2_swapin_fe (
    input  wire  clk,
    input  wire  rst_n,
    input  wire  acc,          // the front accepts a move at this edge (mv_v && mv_rdy)
    input  wire  f_done,       // the front's mv_done pulse
    output wire  src,
    output wire  quiet
);
    reg [1:0] act;             // moves in the front (<= the station's credit 2)
    assign src = f_done;
    assign quiet = act == 2'd0;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) act <= 2'd0;
        else act <= act + {1'b0, acc} - {1'b0, f_done};
    end
endmodule

// ---------------------------------------------------------------------------------------------------------------------
// the composition under test: S + 4 x (down relay, E, glue, ot_hgi_dma_front B2 1 / QID q, up relay).
// The front's indexed-stream ports belong to the cluster's DMA unit (ot_hgi_dma_engines), not to the group path: this
// bench composition holds them idle.  Per cluster only its own stack's svc lanes are brought out.
// ---------------------------------------------------------------------------------------------------------------------
module ot_hgi_b2_swapin_grp #(
    parameter integer DHOPS = 10,
    parameter integer NL = 8,
    parameter integer NB = 8,             // wide WRITE lanes of a cluster's local VM slice
    parameter integer LD = 16,
    parameter integer MUT = 0
) (
    input  wire                 clk,
    input  wire                 rst_n,
    input  wire                 g_v,
    output wire                 g_rdy,
    input  wire                 g_last,
    input  wire [1:0]           g_q,
    input  wire [226:0]         g_mv,
    output wire                 fence_quiet,
    output wire                 done,
    output wire                 fault,
    output wire [3:0]           e_acc,     // (bench) the fronts' accept edges
    output wire [4*51-1:0]      dq,        // cluster q: its stack's request lane {v, tag 4, nsec 9, addr 37}
    input  wire [3:0]           dq_rdy,
    input  wire [4*NL*270-1:0]  dd,        // cluster q: its stack's NL data lanes
    output wire [4*NL-1:0]      dd_cr,
    output wire [4*NB*280-1:0]  wl,        // cluster q: NB wide write lanes {v, sector 15, data 256, mask 8}
    input  wire [4*NB-1:0]      wl_done
);
    wire [4*228-1:0] dn, dn_e; wire [4*3-1:0] up, up_e;
    ot_hgi_b2_swap_disp #(.MUT(MUT)) u_s (.clk(clk), .rst_n(rst_n), .g_v(g_v), .g_rdy(g_rdy), .g_last(g_last), .g_q(g_q),
        .g_mv(g_mv), .dn(dn), .up(up), .fence_quiet(fence_quiet), .done(done), .fault(fault));
    genvar gq;
    generate for (gq = 0; gq < 4; gq = gq + 1) begin : g_c
        wire mv_v, mv_rdy, f_done, f_fault, src, quiet; wire [226:0] mv;
        wire [4*51-1:0] f_dq; wire [4*NL-1:0] f_cr;
        reg  [4*NL*270-1:0] f_dd; reg [3:0] f_qr;
        // verilator lint_off UNUSEDSIGNAL
        wire ix_rdy, id_rdy;                             // the stream ports (held idle here)
        // verilator lint_on UNUSEDSIGNAL
        always @* begin
            f_dd = '0; f_dd[gq*NL*270 +: NL*270] = dd[gq*NL*270 +: NL*270];
            f_qr = 4'd0; f_qr[gq] = dq_rdy[gq];
        end
        ot_hgi_b2_swap_relay #(.W(228), .CW(1), .N(DHOPS)) u_rd (.clk(clk), .rst_n(rst_n), .d(dn[gq*228 +: 228]), .q(dn_e[gq*228 +: 228]));
        ot_hgi_b2_swap_relay #(.W(3), .CW(3), .N(DHOPS)) u_ru (.clk(clk), .rst_n(rst_n), .d(up_e[gq*3 +: 3]), .q(up[gq*3 +: 3]));
        ot_hgi_b2_swap_ep u_e (.clk(clk), .rst_n(rst_n), .dn(dn_e[gq*228 +: 228]), .up(up_e[gq*3 +: 3]), .mv_v(mv_v), .mv_rdy(mv_rdy),
            .mv(mv), .mv_src(src), .mv_fault(f_fault), .quiet(quiet));
        ot_hgi_b2_swapin_fe u_g (.clk(clk), .rst_n(rst_n), .acc(mv_v && mv_rdy), .f_done(f_done), .src(src), .quiet(quiet));
        ot_hgi_dma_front #(.NS(4), .NL(NL), .NB(NB), .LD(LD), .B2(1), .QID(gq)) u_f (.clk(clk), .rst_n(rst_n),
            .mv_v(mv_v), .mv_rdy(mv_rdy), .mv(mv), .mv_done(f_done), .mv_fault(f_fault),
            .ix_v(1'b0), .ix_rdy(ix_rdy), .ix_cmd(176'd0), .id_v(1'b0), .id_rdy(id_rdy), .id(32'd0),
            .dq(f_dq), .dq_rdy(f_qr), .dd(f_dd), .dd_cr(f_cr),
            .wl(wl[gq*NB*280 +: NB*280]), .wl_done(wl_done[gq*NB +: NB]), .wl_rdy({NB{1'b1}}));
        assign dq[gq*51 +: 51] = f_dq[gq*51 +: 51];
        assign dd_cr[gq*NL +: NL] = f_cr[gq*NL +: NL];
        assign e_acc[gq] = mv_v && mv_rdy;
        // verilator lint_off UNUSEDSIGNAL
        wire unused_ok = &{1'b0, f_dq, f_cr};            // the lanes of the other stacks: constant 0 in a B2 front
        // verilator lint_on UNUSEDSIGNAL
    end endgenerate
endmodule
`default_nettype wire
