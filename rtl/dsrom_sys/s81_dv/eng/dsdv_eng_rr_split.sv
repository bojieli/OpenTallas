`timescale 1ns/1ps
// =====================================================================================================================
// CORE-S81-ENG (10-23): dsdv_eng_rr split into TWO hard cores (each <= 400k cells, the S81 hard-core cap; the whole
// cluster measured 418,942 cells = over the cap, die plan v4.7b G0C FAIL).  Behaviour is cycle / bit identical to
// dsdv_eng_rr (OT_S81ENG_RR_N32 profile = the gated eng_rr_a/_b profile, RA640 lookup): the split is drawn along an
// edge that is ALREADY registered on both sides in the monolithic RTL, so no cycle is added anywhere.
//
//   core LK  dsdv_eng_rr_lk   reset root (ot_s81eng_reset3n32, 32 leaves) + f_ks / cfg pin flops + window former
//                             (token map 8 ROM + per-user history SRAM) + RA640 lookup (hash, 3 row SRAMs, CRC,
//                             fixed-age return) + head (request / response chain ends rco / pci) + the st fold.
//   core XQ  dsdv_eng_rr_xq   ot_s81eng_xq_n32: row decode + act-quant (aq12x eng n32) + wait-line / beat-ring SRAMs
//                             (3 x 64x512) + both V-rung directions (vi_s/vo_s, vi_n/vo_n: 4 x 276 b).
//
// Crossing (LK -> XQ 274 b, XQ -> LK 1 b), every bit a flop at BOTH core pins:
//   x_v, x_col 5, x_beat 3, x_d 264  LK side: the lookup's o_* output flops (dsfd_engram_lkp_ra640 o_v/o_col/o_beat/
//                                    o_d registers); XQ side: ot_s81eng_xq_n32 input flops (iv / ic / ib / id_code +
//                                    the kept kq8 scale / wait-line captures) -- the same two flops as in the monolith.
//   x_rst_n                          LK reset leaf rl[4] (a flop) -> XQ's own ot_s81eng_reset3n32 root pair (the
//                                    monolith's u_xq rst_n) -- identical release edges.
//   xq_fault (XQ -> LK)              ot_s81eng_xq_n32 sticky fault flop -> LK st register (as u_c.st in the monolith).
// Static schedule: unchanged (no ready / credit / backpressure; the crossing is a fixed same-edge flop-to-flop hop).
// The die gives the crossing one partition-internal wire (the cores abut inside eng__t1; < 50 um at the plan pins).
// =====================================================================================================================
`ifndef OT_S81ENG_RR_N32
  `define OT_S81ENG_RR_SPLIT_NEEDS_N32
`endif

module dsdv_eng_rr_lk #(
    parameter integer RETURN_AGE = 640,
    parameter [29:0] PCBASE = 30'd0
) (
    input  wire          ck,
    input  wire          rst_n,
    input  wire          cfg_en,
    input  wire          cfg_layer,
    input  wire [1:0]    cfg_rank,
    input  wire [52:0]   f_ks,
    output wire [42:0]   rco,
    input  wire [267:0]  pci,
    // crossing to / from core XQ
    output wire          x_rst_n,
    output wire          x_v,
    output wire [4:0]    x_col,
    output wire [2:0]    x_beat,
    output wire [263:0]  x_d,
    input  wire          xq_fault,
    output reg  [3:0]    st
);
`ifdef OT_S81ENG_RR_SPLIT_NEEDS_N32
    ot_s81eng_rr_split_requires_OT_S81ENG_RR_N32 trap();
`endif
    wire [31:0] rl;
    ot_s81eng_reset3n32 #(.LEAVES(32)) u_r (.clk(ck), .rst_n_in(rst_n), .rst_n(rl), .early_n());
    assign x_rst_n = rl[4];
    reg [52:0] ks; reg en_q, ly_q; reg [1:0] rk_q;
    always @(posedge ck or negedge rl[0]) if (!rl[0]) ks[52] <= 1'b0; else ks[52] <= f_ks[52];
    always @(posedge ck) begin ks[51:0] <= f_ks[51:0]; en_q <= cfg_en; ly_q <= cfg_layer; rk_q <= cfg_rank; end
    wire win_v, wf; wire [2:0] win_slot; wire [67:0] win_ids;
    ot_s81eng_win_n32 u_win (.ck(ck), .rst_n(rl[2]), .rst_copy_n(rl[6:5]),
        .en(en_q), .ks_v(ks[52]), .ks_user(ks[51:42]), .ks_tok(ks[41:21]),
        .ks_pos(ks[20:0]), .win_v(win_v), .win_slot(win_slot), .win_ids(win_ids), .fault(wf));
    wire hq_v, hr_v, o_v, st_v, st_bad, lf; wire [30:0] hq_atom; wire [2:0] hq_tag, hr_slot, hr_tag, o_beat, o_slot, st_slot;
    wire [3:0] hr_idx; wire [255:0] hr_d; wire [4:0] o_col; wire [263:0] o_d;
    dsfd_engram_lkp_ra640 #(.RETURN_AGE(RETURN_AGE)) u_lkp (.ck(ck), .ck_seed(ck), .ck_hash({6{ck}}),
        .ck_n(ck), .ck_s(ck), .ck_rd(ck), .rst_n(rl[1]), .rst_regions(rl[31:16]),
        .cfg_layer(ly_q), .cfg_rank(rk_q),
        .win_v(win_v), .win_slot(win_slot), .win_ids(win_ids),
        .hq_v(hq_v), .hq_atom(hq_atom), .hq_tag(hq_tag),
        .hr_v(hr_v), .hr_slot(hr_slot), .hr_tag(hr_tag), .hr_idx(hr_idx), .hr_d(hr_d),
        .o_v(o_v), .o_col(o_col), .o_beat(o_beat), .o_slot(o_slot), .o_d(o_d),
        .st_v(st_v), .st_slot(st_slot), .st_bad(st_bad), .fault(lf));
    wire hf;
    ot_s81eng_head_n32 #(.PCBASE(PCBASE)) u_head (.ck(ck), .rst_n(rl[3]), .win_v(win_v), .win_slot(win_slot),
        .hq_v(hq_v), .hq_atom(hq_atom), .hq_tag(hq_tag), .rco(rco), .pci(pci), .hr_v(hr_v), .hr_slot(hr_slot),
        .hr_tag(hr_tag), .hr_idx(hr_idx), .hr_d(hr_d), .fault(hf));
    // lookup output flops ARE the LK-side crossing registers
    assign x_v = o_v; assign x_col = o_col; assign x_beat = o_beat; assign x_d = o_d;
    always @(posedge ck or negedge rl[0])
        if (!rl[0]) st <= 4'd0;
        else st <= st | {xq_fault, hf | (o_v && o_slot != hr_slot) | (st_v && st_slot != hr_slot), lf | (st_v & st_bad), wf};
endmodule

module dsdv_eng_rr_xq #(
    parameter integer XQ_MUT = 0
) (
    input  wire          ck,
    input  wire          rst_n,          // = LK x_rst_n (landed leaf)
    input  wire          o_v,
    input  wire [4:0]    o_col,
    input  wire [2:0]    o_beat,
    input  wire [263:0]  o_d,
    input  wire [275:0]  vi_s, output wire [275:0] vo_s,
    input  wire [275:0]  vi_n, output wire [275:0] vo_n,
    output wire          fault
);
    // xq input flops (iv / ic / ib / id_code / kq8 captures) ARE the XQ-side crossing registers
    ot_s81eng_xq_n32 #(.MUT(XQ_MUT)) u_xq (.ck(ck), .rst_n(rst_n), .o_v(o_v), .o_col(o_col), .o_beat(o_beat), .o_d(o_d),
        .vi_a(vi_s), .vo_a(vo_s), .vi_b(vi_n), .vo_b(vo_n), .fault(fault));
endmodule

// Thin wrapper: the dsdv_eng_rr ports, the two cores abutted.  SPLIT_MUT (bench negative controls only):
//   1 = crossing bit x_d[3] inverted on valid beats; 2 = the crossing gets one extra register stage (cycle shift).
module dsdv_eng_rr_split #(
    parameter integer RETURN_AGE = 640,
    parameter [29:0] PCBASE = 30'd0,
    parameter integer XQ_MUT = 0,
    parameter integer SPLIT_MUT = 0
) (
    input wire ck, input wire rst_n, input wire cfg_en, input wire cfg_layer, input wire [1:0] cfg_rank,
    input wire [52:0] f_ks, output wire [42:0] rco, input wire [267:0] pci,
    input wire [275:0] vi_s, output wire [275:0] vo_s, input wire [275:0] vi_n, output wire [275:0] vo_n,
    output wire [3:0] st
);
    wire x_rst_n, x_v, xf; wire [4:0] x_col; wire [2:0] x_beat; wire [263:0] x_d;
    wire m_v; wire [4:0] m_col; wire [2:0] m_beat; wire [263:0] m_d;
    dsdv_eng_rr_lk #(.RETURN_AGE(RETURN_AGE), .PCBASE(PCBASE)) u_lk (.ck(ck), .rst_n(rst_n), .cfg_en(cfg_en),
        .cfg_layer(cfg_layer), .cfg_rank(cfg_rank), .f_ks(f_ks), .rco(rco), .pci(pci), .x_rst_n(x_rst_n), .x_v(x_v),
        .x_col(x_col), .x_beat(x_beat), .x_d(x_d), .xq_fault(xf), .st(st));
    generate if (SPLIT_MUT == 2) begin : g_m2
        reg r_v; reg [4:0] r_col; reg [2:0] r_beat; reg [263:0] r_d;
        always @(posedge ck) begin r_v <= x_v; r_col <= x_col; r_beat <= x_beat; r_d <= x_d; end
        assign {m_v, m_col, m_beat, m_d} = {r_v, r_col, r_beat, r_d};
    end else if (SPLIT_MUT == 1) begin : g_m1
        assign {m_v, m_col, m_beat} = {x_v, x_col, x_beat};
        assign m_d = x_d ^ {260'd0, x_v, 3'd0};
    end else begin : g_m0
        assign {m_v, m_col, m_beat, m_d} = {x_v, x_col, x_beat, x_d};
    end endgenerate
    dsdv_eng_rr_xq #(.XQ_MUT(XQ_MUT)) u_xq (.ck(ck), .rst_n(x_rst_n), .o_v(m_v), .o_col(m_col), .o_beat(m_beat),
        .o_d(m_d), .vi_s(vi_s), .vo_s(vo_s), .vi_n(vi_n), .vo_n(vo_n), .fault(xf));
endmodule
