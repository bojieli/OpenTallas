// HARDENED-LEAF FORM of dsfd_engram_c_rso (die decision 10-14 06:36, el1013-s81-engram.log): the parent holds NO
// flop. Its former own state is hardened into leaves: three same-edge return relay leaves at the bank source pins
// (rd0 256 / rd1 256 / rd2 64 bits: ot_engc_rr256, ot_engc_rr256w, ot_engc_rr64) and TWO control leaves ot_engc_ctl_x /
// ot_engc_ctl_s (die r6 16:26 split; formerly one ot_engc_ctl_leaf beside IO_R1) (8 two-flop reset conditioners, the 16-bit status pipe, the 334-bit PB1->PB0 transit and the 4-bit release
// pipe, plus the registered consumer ACK rso = AND of the 8 conditioner terminals and the 6 child rso). Every leaf has
// one clock pin (delivered at phi - R by the die/cluster); all flops keep their reference edge, so the data path is
// cycle-identical to dsfd_engram_c_rso; rso is one registered edge later (asynchronously revoked by rst).
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

module dsfd_engram_c_hl #(
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
,
    output wire rso,
    // Native binder synchronizes each genuine source before reducing it.
    output wire [13:0] rso_contributors
);
    localparam integer NSLOT = 8, SLW = 3;
    wire [5:0] child_rso;
    wire [7:0] ctl_states;
    assign rso_contributors = {child_rso, ctl_states};
    // ---------------- seams
    wire        lk_wv, lk_wcred, lk_ocred, rn_lk, rn_sk, jf, werr_ws, werr_w;
    wire [67:0] lk_wid; wire [3:0] lk_rel, vrel_io, vrel_sk; wire [2:0] cfg_io, cfg_lk;
    wire lk_fault, lk_ov, lk_stv, lk_stb, lk_hqv; wire [4:0] lk_oc; wire [2:0] lk_ob, lk_os, lk_sts, lk_hqt;
    wire [263:0] lk_od; wire [30:0] lk_hqa; wire [264:0] lk_hr;
    wire [7:0] s_rdy, s_perr, s_rdy_pipe, s_perr_pipe, rdy_w, perr_w; wire s_we; wire [10:0] s_wa; wire [511:0] s_wd;
    wire [17:0] jn; wire [15:0] wn;
    wire [5:0] w_oh, x0_oh, x0_pipe_oh, x1_oh, r0_oh, r1_oh, r2_oh; wire [7:0] w_a, x0_a, x0_pipe_a, x1_a, r0_a, r1_a, r2_a;
    wire [3:0] vrel_sk_pipe;
    wire [575:0] read_return_pipe;
`ifdef OT_ENGC_RSO_MUT_RETURN_SKEW
    wire [575:0] read_to_io = {rd2w[63:0], rd1, rd0};
`else
    wire [575:0] read_to_io = read_return_pipe;
`endif
    wire [255:0] b1_d, rd0, rd1, rd2w; wire [319:0] x_d, x0_d, x0_pipe_d; wire [63:0] x1_d;

    // ---------------- cluster clock entry (el1013-s81-engram 2026-10-13): the 8 hardened children have different
    // internal clock insertion (TT max_clock_tree_path of the installed views: win 182, io 281, sink 294, ws 297,
    // lkp 365, pbc 454, pbb 462 ps) and the top tree reaches their 8 clock pins at different times (CTS-stop runs,
    // el1013-s81-engram.log).  The top tree cannot see inside the children, so each child's clock enters through
    // ot_engc_ck_entry: N kept HB4xp67 delay cells + one BUFx12 pin driver, placed at the child's clock pin
    // (physical/s81_engc_tiles/compose/ck_entry_{keep,place}.tcl).  N = (latest child - this child) / stage delay,
    // "child" = top-tree arrival + internal insertion, so every child's flops see the clock at the same time
    // (pin arrival + insertion spread <= 80 ps, measured in the CTS-stop gate).  A wire in simulation.
    // 2026-10-13 (after CTS-stop runs g3..g8): the entry chains are EMPTY and the children hang on the ck port net itself.
    // TritonCTS re-drew the top tree at every floorplan or chain-count change (child pin arrivals moved +-100 ps, so the
    // counts never held); the cluster clock is now the pre-placed balanced spine (physical/common_flow/clock_spine.tcl,
    // one leaf per child clock pin) padded to per-child targets (physical/s81_engc_tiles/compose/spine_engc.tcl).
    localparam integer CKN_WIN = 0, CKN_IO = 0, CKN_SINK = 0, CKN_WS = 0, CKN_LKP = 0, CKN_PB0 = 0, CKN_PB1 = 0, CKN_PB2 = 0;
    wire ck_win, ck_io, ck_sink, ck_ws, ck_lkp, ck_pb0, ck_pb2, ck_pb1;
    ot_engc_ck_entry #(.N(CKN_WIN))  u_hdly_ck_win  (.a(ck[0]), .y(ck_win));
    ot_engc_ck_entry #(.N(CKN_IO))   u_hdly_ck_io   (.a(ck[0]), .y(ck_io));
    ot_engc_ck_entry #(.N(CKN_SINK)) u_hdly_ck_sink (.a(ck[0]), .y(ck_sink));
    ot_engc_ck_entry #(.N(CKN_WS))   u_hdly_ck_ws   (.a(ck[0]), .y(ck_ws));
    ot_engc_ck_entry #(.N(CKN_LKP))  u_hdly_ck_lkp  (.a(ck[0]), .y(ck_lkp));
    ot_engc_ck_entry #(.N(CKN_PB0))  u_hdly_ck_pb0  (.a(ck[0]), .y(ck_pb0));
    ot_engc_ck_entry #(.N(CKN_PB2))  u_hdly_ck_pb2  (.a(ck[0]), .y(ck_pb2));
    ot_engc_ck_entry #(.N(CKN_PB1))  u_hdly_ck_pb1  (.a(ck[0]), .y(ck_pb1));

    // Condition the asynchronous die reset at EACH child's actual clock branch.
    // A reset released in WIN's clock domain cannot condition LKP/SINK's delayed clock.
    // The two-stage conditioners are placed at the corresponding macro reset pins;
    // stage-to-stage and final stage-to-child reset timing remain ordinary checks.
    wire rst_win_n, rst_io_n, rst_ws_n, rst_pb1_n, rst_pb0_n, rst_pb2_n, rst_lkp_n, rst_sink_n;
    // Control leaves (die r6 16:26, v19_engram_hl): ctl_x in the pb1|pb0 column (transit, io/pb conditioners, partial
    // ACK), ctl_s above the sink (status/release pipes, win/ws/lkp/sink conditioners, final ACK); ack_x -> ctl_s through
    // one closed die relay dsfd_rly_1_EW (rs = parent reset).  ctl_states keeps the former bit order
    // {sink, lkp, pb2, pb0, pb1, ws, io, win}, so rso_contributors is unchanged.
    wire [3:0] states_x, states_s; wire ack_x, ack_x_i;
    ot_engc_ctl_x u_ctl_x (.ck(ck[0]), .rst(rst[0]),
        .x_oh(x0_oh), .x_a(x0_a), .x_d(x0_d), .x_oh_q(x0_pipe_oh), .x_a_q(x0_pipe_a), .x_d_q(x0_pipe_d),
        .rst_io_n(rst_io_n), .rst_pb1_n(rst_pb1_n), .rst_pb0_n(rst_pb0_n), .rst_pb2_n(rst_pb2_n),
        .child_rso_x({child_rso[5], child_rso[4], child_rso[3], child_rso[1]}), .states_x(states_x), .ack_x(ack_x));
    dsfd_rly_1_EW u_rly_ack (.ck(ck[0]), .rs(rst[0]), .i(ack_x), .o(ack_x_i));
    ot_engc_ctl_s u_ctl_s (.ck(ck[0]), .rst(rst[0]),
        .rst_win_n(rst_win_n), .rst_ws_n(rst_ws_n), .rst_lkp_n(rst_lkp_n), .rst_sink_n(rst_sink_n),
        .child_rso_s({child_rso[2], child_rso[0]}), .states_s(states_s), .ack_x_i(ack_x_i), .rso(rso),
        .s_rdy(s_rdy), .s_perr(s_perr), .s_rdy_q(s_rdy_pipe), .s_perr_q(s_perr_pipe),
        .vrel(vrel_sk), .vrel_q(vrel_sk_pipe));
    assign ctl_states = {states_s[3], states_s[2], states_x[3], states_x[2], states_x[1], states_s[1], states_x[0], states_s[0]};

    ot_engc_t_win_rso u_win (
        .ck(ck_win), .rst(rst_win_n), .rso(child_rso[0]), .f_win(f_win), .t_collective(t_collective[0]),
        .lk_wv(lk_wv), .lk_wid(lk_wid), .lk_wcred(lk_wcred), .lk_rel(lk_rel),
        .lk_ov(lk_ov), .lk_stv(lk_stv), .lk_stb(lk_stb), .lk_fault(lk_fault), .lk_oc(lk_oc), .lk_ob(lk_ob), .lk_os(lk_os),
        .lk_sts(lk_sts), .lk_od(lk_od), .t_ag(t_ag), .f_agc(f_agc[0]), .lk_ocred(lk_ocred),
        .cfg_i(cfg_io), .cfg_o(cfg_lk), .rn_lk(rn_lk), .rn_sk(rn_sk),
        .s_rdy(s_rdy_pipe), .s_perr(s_perr_pipe), .rdy_o(rdy_w), .perr_o(perr_w), .vrel_i(vrel_io), .vrel_o(vrel_sk),
        .jn_i(jn), .wn_o(wn), .jf_o(jf), .werr_i(werr_ws), .werr_o(werr_w));
`ifdef SYNTHESIS
    ot_engc_t_io_rso_r1 u_io (
`else
    ot_engc_t_io_rso_r1 #(.MUT(MUT), .EPMUT(EPMUT)) u_io (
`endif
        .ck(ck_io), .rst(rst_io_n), .rso(child_rso[1]), .c_cmd(c_cmd), .c_done(c_done), .c_st(c_st), .f_cfg(f_cfg), .cfg_o(cfg_io),
        .f_vm(f_vm), .t_vm(t_vm), .rdy_i(rdy_w), .perr_i(perr_w), .vrel_o(vrel_io), .jn_o(jn), .wn_i(wn), .jf_i(jf),
        .werr_i(werr_w), .r0_oh(r0_oh), .r1_oh(r1_oh), .r2_oh(r2_oh), .r0_a(r0_a), .r1_a(r1_a), .r2_a(r2_a),
        .rd0(read_to_io[255:0]), .rd1(read_to_io[511:256]), .rd2(read_to_io[575:512]));
    ot_engc_t_ws_rso u_ws (
        .ck(ck_ws), .rst(rst_ws_n), .rso(child_rso[2]), .wr_v(s_we), .wr_addr(s_wa), .wr_data(s_wd), .werr(werr_ws),
        .w_oh(w_oh), .w_a(w_a), .b1_d(b1_d), .x_d(x_d),
        .lk_hqv(lk_hqv), .lk_hqa(lk_hqa), .lk_hqt(lk_hqt), .t_hq(t_hq), .f_hr(f_hr), .lk_hr(lk_hr));
    // prefetch banks: band tile = bank 1 (+ write transit {bank 2, bank 0}); columns = bank 0, bank 2
    ot_engc_t_pbb_rso_xt u_pb1 (.ck(ck_pb1), .rst(rst_pb1_n), .rso(child_rso[3]), .w_oh(w_oh), .w_a(w_a), .w_d(b1_d), .x_d(x_d),
        .x_oh(x0_oh), .x_a(x0_a), .x_do(x0_d), .r_oh(r1_oh), .r_a(r1_a), .r_d(rd1));
    ot_engc_t_pbc_rso u_pb0 (.ck(ck_pb0), .rst(rst_pb0_n), .rso(child_rso[4]), .w_oh(x0_pipe_oh), .w_a(x0_pipe_a), .w_d(x0_pipe_d[255:0]), .x_d(x0_pipe_d[319:256]),
        .x_oh(x1_oh), .x_a(x1_a), .x_do(x1_d), .r_oh(r0_oh), .r_a(r0_a), .r_d(rd0));
    ot_engc_t_pbc_rso u_pb2 (.ck(ck_pb2), .rst(rst_pb2_n), .rso(child_rso[5]), .w_oh(x1_oh), .w_a(x1_a), .w_d({192'd0, x1_d}), .x_d(64'd0),
        .x_oh(), .x_a(), .x_do(), .r_oh(r2_oh), .r_a(r2_a), .r_d(rd2w));

    // Same-edge return relay leaves at the bank source pins (reset by the IO conditioner, as before).
    ot_engc_rr256 u_rr0 (.ck(ck[0]), .rst(rst[0]), .d(rd0), .q(read_return_pipe[255:0]));      // own conditioner
    ot_engc_rr256w u_rr1 (.ck(ck[0]), .rst_n(rst_io_n), .d(rd1), .q(read_return_pipe[511:256]));
    ot_engc_rr64   u_rr2 (.ck(ck[0]), .rst(rst[0]), .d(rd2w[63:0]), .q(read_return_pipe[575:512]));   // own conditioner

    // ---------------- closed leaves (in synthesis: hardened views, built at exactly these parameter values)
`ifdef SYNTHESIS
    dsfd_engram_lkp u_lkp (
`else
    dsfd_engram_lkp #(.PIPE(PIPE), .NSLOT(NSLOT), .HQ_CRED(8), .O_CRED(16), .SLW(SLW)) u_lkp (
`endif
        .ck(ck_lkp), .rst_n(rst_lkp_n), .cfg_layer(cfg_lk[0]), .cfg_rank(cfg_lk[2:1]),
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
        .ck(ck_sink), .rst_n(rst_sink_n), .in_v(f_ai[3:0]), .in_r(t_air), .in_col(f_ai[23:4]), .in_beat(f_ai[35:24]),
        .in_slot(f_ai[47:36]), .in_d(f_ai[1103:48]), .st_v(f_ai[1107:1104]), .st_slot(f_ai[1119:1108]),
        .st_bad(f_ai[1123:1120]), .wr_en(s_we), .wr_addr(s_wa), .wr_data(s_wd), .rdy(s_rdy), .perr(s_perr),
        .rel_v(vrel_sk_pipe[0]), .rel_slot(vrel_sk_pipe[3:1]));
endmodule



