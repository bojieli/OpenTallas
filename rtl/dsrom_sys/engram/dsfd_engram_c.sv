`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------
// dsfd_engram_c (s81-svceng-1011, 2026-10-11): the Engram slab master of the S81 layer1e die (eng_SE), engine 10 of
// ADAPTER_CONTRACT_1011.  = the pinned command endpoint ot_s81_slab_ep (ot_s81_engine_adapter QD 8, done-credit)
//   + the closed lookup element dsfd_engram_lkp (hash, address, HBM row requests, CRC, row beats)
//   + the closed row sink dsfd_engram_sink (24 columns x 4 ranks -> BF16 rows, slot ready / poison)
//   + the prefetch buffer ot_dsrom_engram_prefetch_h (8 slots, the existing SECDED words; no new ECC; registered
//     SRAM array: per-macro access / capture registers, pipelined bank select -- el1011-ds-misc HIER 2026-10-11)
// ALL-TILE (el1011-ds-misc/engram 2026-10-11, textbook class 1): the top level holds NO register.  Every flop lives in a
// hardened tile with its own clock tree and registered faces (tiles/): T_WIN (window queue, all-gather, leaf resets,
// sink seams), T_IO (endpoint, done, VM side, decode), T_WS (sink write port + encode, HBM relays), the prefetch banks
// T_PBB (bank 1) and T_PBC x2 (banks 0, 2), plus the closed lookup / sink leaves.  The top clock tree drives 8 tile clock
// pins.  Physical spec: el1011-ds-misc.log "PHYSICAL SPEC dsfd_engram_c ALL-TILE".  Cycle changes vs the HIER version:
// window -> lookup +1 (registered), write commit t+5/6/7 (bank 1/0/2) -> rdy published 7 edges after the sink's (was 4),
// VM read out_v 13 edges after rd_v (was 11; valid-tagged).
// The die buses are ENG_BUSES of tools/dsrom_s81_fulldie.py (names below = the generator's port names).
//
// ENGINE SEMANTICS (one job = one token's Engram lookup on this rank):
//   start = the window: a lead-flit window (f_win) is HELD in a 2-entry queue (the collective's 2 window credits) and
//           released to the lookup only under a queued eng descriptor, in order (one window per descriptor).  A window
//           never reaches the lookup without a command (a dropped command holds it: no rows, no done).
//   done  = the job's prefetch slot became READY on this rank's sink (all 24 rows of the 4 ranks written and their
//           24 statuses counted; a poisoned slot completes too and carries perr on t_vm).  Slot s = n mod 8 of window
//           n; the done of window n is the (n / 8 + 1)-th rising edge of rdy[s] (rdy drops on every release), so a
//           slot still READY from window n - 8 can never complete window n.
//   descriptor arg (compiler schema "eng_job"): arg[15:0] = window sequence number n (mod 2^16), arg[23:16] = 0.
//           A released window whose n differs, or a reserved bit set, is a WRONG DESCRIPTOR: sticky fault (c_st[0]).
// The consumer (VM) reads the slot over f_vm (rd_v / rd_addr {slot, column, beat}, out on t_vm 10 cycles later, valid-tagged by out_v) after
// the done and releases it (rel_v / rel_slot); the lookup's credit is the 4 ranks' releases (f_win rel, carried by
// the collective ctrl lane).
// HBM: the lookup's request / response credit pair (hq / hr) is the backend port pair t_hq / f_hr (35 / 265 b), the
// SE half of ot_dsrom_engram_hbm_backend binds there (rowstripe read service + boot path; the SW half via svc_SW).
// MUT (negative controls): 5 early done (done when the window is released to the lookup); 6 done on the rdy LEVEL
// (equivalent in every legal flow: slot n - 8 is released before window n is accepted -- kept as a design note).  EPMUT -> ot_s81_slab_ep (2 tag / 3 early start / 4
// dropped done).
// ---------------------------------------------------------------------------------------------------------------
import ot_hdc_engram_tables_shipped_pkg::*;

module dsfd_engram_c #(
    parameter integer MUT = 0,
    parameter integer EPMUT = 0,
    parameter integer PIPE = 0,
    parameter integer SINK_PIN = 1
) (
    input  wire [0:0]    ck,
    input  wire [0:0]    rst,                // async die reset (active low), synchronised in every tile
    input  wire [84:0]   c_cmd,
    output wire [8:0]    c_done,
    output wire [1:0]    c_st,
    input  wire [2:0]    f_cfg,              // {cfg_rank 2, cfg_layer}
    input  wire [72:0]   f_win,              // {win_v, win_ids 4 x 17, rel 4}
    output wire [0:0]    t_collective,       // win_cred
    output wire [281:0]  t_ag,
    input  wire [0:0]    f_agc,
    input  wire [1123:0] f_ai,
    output wire [3:0]    t_air,
    output wire [531:0]  t_vm,
    input  wire [15:0]   f_vm,
    output wire [34:0]   t_hq,
    input  wire [264:0]  f_hr
);
    localparam integer NSLOT = 8, SLW = 3;
    // ---------------- seams
    wire        lk_wv, lk_wcred, lk_ocred, rn_lk, rn_sk, jf, werr_ws, werr_w;
    wire [67:0] lk_wid; wire [3:0] lk_rel, vrel_io, vrel_sk; wire [2:0] cfg_io, cfg_lk;
    wire lk_fault, lk_ov, lk_stv, lk_stb, lk_hqv; wire [4:0] lk_oc; wire [2:0] lk_ob, lk_os, lk_sts, lk_hqt;
    wire [263:0] lk_od; wire [30:0] lk_hqa; wire [264:0] lk_hr;
    wire [7:0] s_rdy, s_perr, rdy_w, perr_w; wire s_we; wire [10:0] s_wa; wire [511:0] s_wd;
    wire [17:0] jn; wire [15:0] wn;
    wire [5:0] w_oh, x0_oh, x1_oh, r0_oh, r1_oh, r2_oh; wire [7:0] w_a, x0_a, x1_a, r0_a, r1_a, r2_a;
    wire [255:0] b1_d, rd0, rd1, rd2w; wire [319:0] x_d, x0_d; wire [63:0] x1_d;

    ot_engc_t_win u_win (
        .ck(ck[0]), .rst(rst[0]), .f_win(f_win), .t_collective(t_collective[0]),
        .lk_wv(lk_wv), .lk_wid(lk_wid), .lk_wcred(lk_wcred), .lk_rel(lk_rel),
        .lk_ov(lk_ov), .lk_stv(lk_stv), .lk_stb(lk_stb), .lk_fault(lk_fault), .lk_oc(lk_oc), .lk_ob(lk_ob), .lk_os(lk_os),
        .lk_sts(lk_sts), .lk_od(lk_od), .t_ag(t_ag), .f_agc(f_agc[0]), .lk_ocred(lk_ocred),
        .cfg_i(cfg_io), .cfg_o(cfg_lk), .rn_lk(rn_lk), .rn_sk(rn_sk),
        .s_rdy(s_rdy), .s_perr(s_perr), .rdy_o(rdy_w), .perr_o(perr_w), .vrel_i(vrel_io), .vrel_o(vrel_sk),
        .jn_i(jn), .wn_o(wn), .jf_o(jf), .werr_i(werr_ws), .werr_o(werr_w));
`ifdef SYNTHESIS
    ot_engc_t_io u_io (
`else
    ot_engc_t_io #(.MUT(MUT), .EPMUT(EPMUT)) u_io (
`endif
        .ck(ck[0]), .rst(rst[0]), .c_cmd(c_cmd), .c_done(c_done), .c_st(c_st), .f_cfg(f_cfg), .cfg_o(cfg_io),
        .f_vm(f_vm), .t_vm(t_vm), .rdy_i(rdy_w), .perr_i(perr_w), .vrel_o(vrel_io), .jn_o(jn), .wn_i(wn), .jf_i(jf),
        .werr_i(werr_w), .r0_oh(r0_oh), .r1_oh(r1_oh), .r2_oh(r2_oh), .r0_a(r0_a), .r1_a(r1_a), .r2_a(r2_a),
        .rd0(rd0), .rd1(rd1), .rd2(rd2w[63:0]));
    ot_engc_t_ws u_ws (
        .ck(ck[0]), .rst(rst[0]), .wr_v(s_we), .wr_addr(s_wa), .wr_data(s_wd), .werr(werr_ws),
        .w_oh(w_oh), .w_a(w_a), .b1_d(b1_d), .x_d(x_d),
        .lk_hqv(lk_hqv), .lk_hqa(lk_hqa), .lk_hqt(lk_hqt), .t_hq(t_hq), .f_hr(f_hr), .lk_hr(lk_hr));
    // prefetch banks: band tile = bank 1 (+ write transit {bank 2, bank 0}); columns = bank 0, bank 2
    ot_engc_t_pbb u_pb1 (.ck(ck[0]), .rst(rst[0]), .w_oh(w_oh), .w_a(w_a), .w_d(b1_d), .x_d(x_d),
        .x_oh(x0_oh), .x_a(x0_a), .x_do(x0_d), .r_oh(r1_oh), .r_a(r1_a), .r_d(rd1));
    ot_engc_t_pbc u_pb0 (.ck(ck[0]), .rst(rst[0]), .w_oh(x0_oh), .w_a(x0_a), .w_d(x0_d[255:0]), .x_d(x0_d[319:256]),
        .x_oh(x1_oh), .x_a(x1_a), .x_do(x1_d), .r_oh(r0_oh), .r_a(r0_a), .r_d(rd0));
    ot_engc_t_pbc u_pb2 (.ck(ck[0]), .rst(rst[0]), .w_oh(x1_oh), .w_a(x1_a), .w_d({192'd0, x1_d}), .x_d(64'd0),
        .x_oh(), .x_a(), .x_do(), .r_oh(r2_oh), .r_a(r2_a), .r_d(rd2w));

    // ---------------- closed leaves (in synthesis: hardened views, built at exactly these parameter values)
`ifdef SYNTHESIS
    dsfd_engram_lkp u_lkp (
`else
    dsfd_engram_lkp #(.PIPE(PIPE), .NSLOT(NSLOT), .HQ_CRED(8), .O_CRED(16), .SLW(SLW)) u_lkp (
`endif
        .ck(ck[0]), .rst_n(rn_lk), .cfg_layer(cfg_lk[0]), .cfg_rank(cfg_lk[2:1]),
        .win_v(lk_wv), .win_ids(lk_wid), .win_cred(lk_wcred), .rel(lk_rel),
        .hq_v(lk_hqv), .hq_atom(lk_hqa), .hq_tag(lk_hqt), .hq_cred(lk_hr[0]),
        .hr_v(lk_hr[1]), .hr_tag(lk_hr[4:2]), .hr_idx(lk_hr[8:5]), .hr_d(lk_hr[264:9]),
        .o_v(lk_ov), .o_col(lk_oc), .o_beat(lk_ob), .o_slot(lk_os), .o_d(lk_od), .o_cred(lk_ocred),
        .st_v(lk_stv), .st_slot(lk_sts), .st_bad(lk_stb), .fault(lk_fault));
`ifdef SYNTHESIS
    dsfd_engram_sink u_sink (
`else
    dsfd_engram_sink #(.PIN_CAPTURE(SINK_PIN), .NSLOT(NSLOT), .SLW(SLW)) u_sink (
`endif
        .ck(ck[0]), .rst_n(rn_sk), .in_v(f_ai[3:0]), .in_r(t_air), .in_col(f_ai[23:4]), .in_beat(f_ai[35:24]),
        .in_slot(f_ai[47:36]), .in_d(f_ai[1103:48]), .st_v(f_ai[1107:1104]), .st_slot(f_ai[1119:1108]),
        .st_bad(f_ai[1123:1120]), .wr_en(s_we), .wr_addr(s_wa), .wr_data(s_wd), .rdy(s_rdy), .perr(s_perr),
        .rel_v(vrel_sk[0]), .rel_slot(vrel_sk[3:1]));
endmodule
