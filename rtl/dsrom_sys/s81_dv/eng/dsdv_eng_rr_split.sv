`timescale 1ns/1ps
// =====================================================================================================================
// CORE-S81-ENG (10-23): dsdv_eng_rr split into THREE hard cores, each <= 400k cells (the S81 hard-core cap; the whole
// cluster measured 418,942 = over the cap, die plan v4.7b G0C FAIL).  Measured (ORFS asap7lock Yosys, flat): the
// Engram hash ot_s81_engram_hash_n32 alone is 351,528 cells of it, so a balanced cut must go THROUGH the hash.  The
// flat hash is layer-separable (products 4 l + k, rolls, columns 24 l .. 24 l + 23), so:
//   core E   dsdv_eng_rr_e    reset root + f_ks / cfg pin flops + window former (8 ROM + history SRAM) + RA640 lookup
//                             engine with the hash EXTERNAL (dsfd_engram_lkp_ra640_hx: 3 row SRAMs, CRC, fixed-age
//                             return) + head (rco / pci) + XQ join (3 SRAMs, both V rungs) + st fold.  15 macros.
//   core H0  dsdv_eng_rr_h0   hash layer 0 (ot_s81_engram_hash_n32_l0): 4 products, rolls, 24 residue columns.
//   core H1  dsdv_eng_rr_h1   hash layer 1 (ot_s81_engram_hash_n32_l1).
// Behaviour is cycle / bit identical to dsdv_eng_rr (OT_S81ENG_RR_N32 profile, RA640): the cut is the monolith's own
// registered core <-> hash hops, so no cycle is added anywhere:
//   E -> H0, H1  hx_w[67:0]   E: win_n (ck NEGEDGE window register) ; H: kept kq17 window copies (ck posedge)
//   H0 -> E      res[575:0]   H: res_n (column NEGEDGE)               ; E: res_c (ck posedge, no logic between)
//   H1 -> E      res[575:0]   idem (E hx_res[1151:576])
// Both hops are HALF-cycle (negedge -> posedge, 417 ps) exactly as in the monolith; the cores abut at those faces.
// S81-KITS-RTLA 10-24: H0 / H1 register every in_w pin in ONE capture flop (was: 16 kq17 copies per pin bit): the hash
// result reaches E one edge later than in the monolith; E's capture edge (hdone) is unchanged and the result is still
// stable there (see the note at dsdv_eng_rr_split), so the core outputs stay cycle / bit identical to dsdv_eng_rr.
// Static schedule: unchanged (no ready / credit / backpressure).  The hash cores have no reset (none in the RTL).
// =====================================================================================================================
`ifndef OT_S81ENG_RR_N32
  `define OT_S81ENG_RR_SPLIT_NEEDS_N32
`endif

module dsdv_eng_rr_e #(
    parameter integer RETURN_AGE = 640,
    parameter [29:0] PCBASE = 30'd0,
    parameter integer XQ_MUT = 0
) (
    input  wire          ck,
    input  wire          rst_n,
    input  wire          cfg_en,
    input  wire          cfg_layer,
    input  wire [1:0]    cfg_rank,
    input  wire [52:0]   f_ks,
    // OWNER DECISION 8 (S81-KITS-RTLA 10-24): constant / unused pins dropped from the core.  rco = request chain
    // {tag 7, sec 30, pc 5, v} without sec[29:26] (old rco[35:32]): sec = PCBASE + atom[30:5], a 26-b offset, so
    // sec[29:26] = PCBASE[29:26] when PCBASE[25:0] == 0 (TIELO at the kit's PCBASE 0); new rco[31:0] = old [31:0],
    // new rco[38:32] = old [42:36]; the unit wrapper re-inserts PCBASE[29:26].  pci = response chain {d 256, tag 7,
    // own 4, v} without own (old pci[4:1], no load: the head only reads v / tag / d), new pci[0] = old [0],
    // new pci[263:1] = old [267:5].  (rco[31:25] are live: their earlier raw-netlist TIELO was the csa31 slang bug.)
    output wire [38:0]   rco,
    input  wire [263:0]  pci,
    input  wire [275:0]  vi_s, output wire [275:0] vo_s,
    input  wire [275:0]  vi_n, output wire [275:0] vo_n,
    output reg  [3:0]    st,
    // hash cores
    output wire [67:0]   hx_w,
    input  wire [1151:0] hx_res
);
`ifdef OT_S81ENG_RR_SPLIT_NEEDS_N32
    ot_s81eng_rr_split_requires_OT_S81ENG_RR_N32 trap();
`endif
    wire [31:0] rl;
    ot_s81eng_reset3n32 #(.LEAVES(32)) u_r (.clk(ck), .rst_n_in(rst_n), .rst_n(rl), .early_n());
    reg [52:0] ks; reg en_q, ly_q; reg [1:0] rk_q;
    always @(posedge ck or negedge rl[0]) if (!rl[0]) ks[52] <= 1'b0; else ks[52] <= f_ks[52];
    always @(posedge ck) begin ks[51:0] <= f_ks[51:0]; en_q <= cfg_en; ly_q <= cfg_layer; rk_q <= cfg_rank; end
    wire win_v, wf; wire [2:0] win_slot; wire [67:0] win_ids;
    ot_s81eng_win_n32 u_win (.ck(ck), .rst_n(rl[2]), .rst_copy_n(rl[6:5]),
        .en(en_q), .ks_v(ks[52]), .ks_user(ks[51:42]), .ks_tok(ks[41:21]),
        .ks_pos(ks[20:0]), .win_v(win_v), .win_slot(win_slot), .win_ids(win_ids), .fault(wf));
    wire hq_v, hr_v, o_v, st_v, st_bad, lf; wire [30:0] hq_atom; wire [2:0] hq_tag, hr_slot, hr_tag, o_beat, o_slot, st_slot;
    wire [3:0] hr_idx; wire [255:0] hr_d; wire [4:0] o_col; wire [263:0] o_d;
    dsfd_engram_lkp_ra640_hx #(.RETURN_AGE(RETURN_AGE)) u_lkp (.ck(ck), .ck_seed(ck), .ck_hash({6{ck}}),
        .ck_n(ck), .ck_s(ck), .ck_rd(ck), .rst_n(rl[1]), .rst_regions(rl[31:16]),
        .cfg_layer(ly_q), .cfg_rank(rk_q), .hx_w(hx_w), .hx_res(hx_res),
        .win_v(win_v), .win_slot(win_slot), .win_ids(win_ids),
        .hq_v(hq_v), .hq_atom(hq_atom), .hq_tag(hq_tag),
        .hr_v(hr_v), .hr_slot(hr_slot), .hr_tag(hr_tag), .hr_idx(hr_idx), .hr_d(hr_d),
        .o_v(o_v), .o_col(o_col), .o_beat(o_beat), .o_slot(o_slot), .o_d(o_d),
        .st_v(st_v), .st_slot(st_slot), .st_bad(st_bad), .fault(lf));
    wire hf; wire [42:0] rco_f;
    assign rco = {rco_f[42:36], rco_f[31:0]};
    ot_s81eng_head_n32 #(.PCBASE(PCBASE)) u_head (.ck(ck), .rst_n(rl[3]), .win_v(win_v), .win_slot(win_slot),
        .hq_v(hq_v), .hq_atom(hq_atom), .hq_tag(hq_tag), .rco(rco_f), .pci({pci[263:1], 4'd0, pci[0]}), .hr_v(hr_v),
        .hr_slot(hr_slot),
        .hr_tag(hr_tag), .hr_idx(hr_idx), .hr_d(hr_d), .fault(hf));
    wire xf;
    ot_s81eng_xq_n32 #(.MUT(XQ_MUT)) u_xq (.ck(ck), .rst_n(rl[4]), .o_v(o_v), .o_col(o_col), .o_beat(o_beat), .o_d(o_d),
        .vi_a(vi_s), .vo_a(vo_s), .vi_b(vi_n), .vo_b(vo_n), .fault(xf));
    // S81-KITS-RTLA 10-24 (face_guard: register on every pin): the sticky status lives in st_s; the pin flops st are an
    // output-only copy loaded with the same next value (was: st fed back into its own D).  0 cycles, bit / cycle identical.
    (* keep *) reg [3:0] st_s;
    wire [3:0] st_n = st_s | {xf, hf | (o_v && o_slot != hr_slot) | (st_v && st_slot != hr_slot), lf | (st_v & st_bad), wf};
    always @(posedge ck or negedge rl[0])
        if (!rl[0]) begin st <= 4'd0; st_s <= 4'd0; end
        else begin st <= st_n; st_s <= st_n; end
endmodule

// hash layer cores: the column clocks of a layer are branches of ck (as in the monolith, where ck_hash = {6{ck}})
module dsdv_eng_rr_h0 (input wire ck, input wire [67:0] in_w, output wire [575:0] out_res);
    // S81-KITS-RTLA 10-24 (face_guard: register on every pin): ONE capture flop per in_w bit (ck posedge, the half-cycle
    // seam hop from E's negedge win_n lands here); the 16 kept kq17 window copies load from it.  +1 edge on the
    // E -> H -> E hash path, absorbed by the hash result's hold window at E's hdone capture (bench_rr_split lockstep:
    // E / split outputs bit + cycle identical to the monolith; crossing res_m = monolith hres one edge later).
    (* keep *) reg [67:0] w_q;
    always @(posedge ck) w_q <= in_w;
    ot_s81_engram_hash_n32_l0 u_hash (.clk(ck), .clk_columns({3{ck}}), .in_w(w_q), .out_res(out_res));
endmodule

module dsdv_eng_rr_h1 (input wire ck, input wire [67:0] in_w, output wire [575:0] out_res);
    // S81-KITS-RTLA 10-24 (face_guard: register on every pin): ONE capture flop per in_w bit (ck posedge, the half-cycle
    // seam hop from E's negedge win_n lands here); the 16 kept kq17 window copies load from it.  +1 edge on the
    // E -> H -> E hash path, absorbed by the hash result's hold window at E's hdone capture (bench_rr_split lockstep:
    // E / split outputs bit + cycle identical to the monolith; crossing res_m = monolith hres one edge later).
    (* keep *) reg [67:0] w_q;
    always @(posedge ck) w_q <= in_w;
    ot_s81_engram_hash_n32_l1 u_hash (.clk(ck), .clk_columns({3{ck}}), .in_w(w_q), .out_res(out_res));
endmodule

// Thin wrapper: the dsdv_eng_rr ports, the three cores abutted.  S81/PORTFIX-CFG 10-25: same die ports as the new
// dsdv_eng_rr (cfg_* inputs removed, st -> 1-bit fault): the soft dsdv_eng_cfg (dsdv_eng_rr.sv) drives core E's
// unchanged cfg_en / cfg_layer / cfg_rank pins and folds its unchanged st pins into fault.  SPLIT_MUT (bench negative controls only):
//   1 = crossing bit hx_res[864] inverted (residue of column 36 = the (layer 1, rank 2) candidate the bench selects);
//   2 = the two layer halves swapped at E (H0 <-> H1 wiring error).
// Note (bench 10-23): ONE extra register stage on the H -> E hop is NOT observable -- the hash result of a window is
// stable for >= 2 edges around its res_c capture (hdone), so the hop has a free extra cycle of slack (not used here).
module dsdv_eng_rr_split #(
    parameter integer RETURN_AGE = 640,
    parameter [29:0] PCBASE = 30'd0,
    parameter integer XQ_MUT = 0,
    parameter integer SPLIT_MUT = 0,
    parameter integer CFG_MUT = 0
) (
    input wire ck, input wire rst_n,
    input wire [52:0] f_ks, output wire [42:0] rco, input wire [267:0] pci,
    input wire [275:0] vi_s, output wire [275:0] vo_s, input wire [275:0] vi_n, output wire [275:0] vo_n,
    output wire fault
);
    wire [67:0] hx_w; wire [1151:0] res, res_m; wire [38:0] rco_e;
    wire cfg_en, cfg_layer; wire [1:0] cfg_rank; wire [3:0] st;
    dsdv_eng_cfg #(.MUT(CFG_MUT)) u_cfg (.ck(ck), .rst_n(rst_n), .vi_s(vi_s), .vi_n(vi_n), .ks_v(f_ks[52]), .st(st),
        .cfg_en(cfg_en), .cfg_layer(cfg_layer), .cfg_rank(cfg_rank), .fault(fault));
    // the dropped core pins (OWNER DECISION 8): rco sector bits [29:26] (old rco[35:32]) are PCBASE[29:26] (the atom
    // sector offset is 26 b, so with PCBASE[25:0] == 0 nothing carries into them); pci own [4:1] is not read by the core
    assign rco = {rco_e[38:32], PCBASE[29:26], rco_e[31:0]};
`ifndef SYNTHESIS
    initial if (PCBASE[25:0] != 26'd0) $fatal(1, "dsdv_eng_rr_split: PCBASE[25:0] must be 0 (rco[35:32] = PCBASE[29:26])");
`endif
    dsdv_eng_rr_e #(.RETURN_AGE(RETURN_AGE), .PCBASE(PCBASE), .XQ_MUT(XQ_MUT)) u_e (.ck(ck), .rst_n(rst_n),
        .cfg_en(cfg_en), .cfg_layer(cfg_layer), .cfg_rank(cfg_rank), .f_ks(f_ks), .rco(rco_e), .pci({pci[267:5], pci[0]}), .vi_s(vi_s),
        .vo_s(vo_s), .vi_n(vi_n), .vo_n(vo_n), .st(st), .hx_w(hx_w), .hx_res(res_m));
    dsdv_eng_rr_h0 u_h0 (.ck(ck), .in_w(hx_w), .out_res(res[575:0]));
    dsdv_eng_rr_h1 u_h1 (.ck(ck), .in_w(hx_w), .out_res(res[1151:576]));
    generate if (SPLIT_MUT == 2) begin : g_m2
        assign res_m = {res[575:0], res[1151:576]};
    end else if (SPLIT_MUT == 1) begin : g_m1
        assign res_m = res ^ (1152'd1 << 864);
    end else begin : g_m0
        assign res_m = res;
    end endgenerate
endmodule
