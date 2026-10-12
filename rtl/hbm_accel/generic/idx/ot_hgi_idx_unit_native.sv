`timescale 1ns/1ps
`default_nettype none
// HGI IDX unit, die configuration (el1011-idxone 2026-10-11): a thin wrapper, NO logic of its own.  There is ONE
// implementation, ot_hgi_idx_unit; this module only fixes the die parameters so the die view (hfd_hgi_idx_native) and
// the unit route instantiate the same configuration:
//   NGLOB 1    IDX.INDEX global front (x_go2)
//   IKS 1      index-key stream to the four stacks' svc stripes (ot_hgi_idx_iks_issue)
//   IKS_EVEN 1 whole scorer beats (B_q rounded up to even; the odd-block L2 quarter retires)
//   PREF 1     IDX.TOPK streaming reader (4 reads in flight, back-to-back feed)
//   TOPKW 1, TWIW 8, TOPKC 1  IDX.TOPK on the hardened w8 cluster (ot_hgi_idx_topk_w8_cluster), sector-packed writes
// MUT is the unit's bench mutant, passed through (2 = R written from the wrong lane in ot_hgi_idx_index).
module ot_hgi_idx_unit_native #(
    parameter integer MUT = 0
) (
    input  wire          clk,
    input  wire          rst_n,
    input  wire [2074:0] rec,
    output wire [2:0]    ret,
    output wire [337:0]  vmq,
    input  wire [273:0]  vmr,
    output wire [89:0]   sel_fs,
    output wire [1047:0] sel_qb,
    input  wire          sel_qbr,
    output wire [344:0]  sel_kin,
    input  wire [611:0]  sel_to,
    output wire          sel_toc,
    input  wire [71:0]   sel_co,
    output wire          sel_coc,
    input  wire [1:0]    sel_ev,
    output wire [511:0]  iks_e
);
    ot_hgi_idx_unit #(.MUT(MUT), .NGLOB(1), .IKS(1), .IKS_EVEN(1), .PREF(1), .TOPKW(1), .TWIW(8), .TOPKC(1)) u (
        .clk(clk), .rst_n(rst_n), .rec(rec), .ret(ret), .vmq(vmq), .vmr(vmr),
        .sel_fs(sel_fs), .sel_qb(sel_qb), .sel_qbr(sel_qbr), .sel_kin(sel_kin), .sel_to(sel_to), .sel_toc(sel_toc),
        .sel_co(sel_co), .sel_coc(sel_coc), .sel_ev(sel_ev), .iks_e(iks_e));
endmodule
`default_nettype wire
