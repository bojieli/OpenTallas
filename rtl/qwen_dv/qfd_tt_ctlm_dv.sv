`timescale 1ns/1ps
// =====================================================================================================================
// qfd_tt_ctlm_dv -- the Qwen compute-die control element re-ported to the distributed-vector die dv2f7 (Q-CTLM 10-17).
// Successor of rtl/qwen_sys/static_schedule_20261014/qfd_tt_ctlm_b2.sv (kept, historical pre-DV).  Contract:
// results/arch/qwen_split_compute_1014/q_slice_1017/W5_CONTRACT.md (claude/qslice-1017 be28f313b), gaps G7/G8/G9.
//
// KEPT (real machinery with DV consumers, unchanged RTL): the ME head controller qfd_tt_ctlm_head_static (program store,
// fixed issue calendar, ot_qwen_rom_core_ctrl_static), ot_qfd_native_cmd_route, ot_qwen_tp8_rom_relocate (ib), the XPF
// loader + static schedule (xpf), native_cmd / native_tok / native_pos / layer_context_v / command_stage, program_obs,
// control_stores_ready, pw / kok / kwd / fab.
// GONE (their peers left the die): the tree controller qfd_tt_ctlm_tree_b2 and qfd_b2_train_source (tc0..5, lc0..5,
// am0..5, sel, mx, mee, mer0..5, rsi_me_*, rsi_tag_*, ld, meok, rf0..5, uf, xflt, b2_status_fault, ovf), the seq_su faces
// (st, xs, xm, su_image_ready, su_observe) and the CP copy engine faces (cp, cp_active).
// NEW:
//   hr[452:0]  -> W5 hr_wi   {go, ib 379 (me_array order: qfd_dv_hr_pack), xpf 72, v}: one register (+1 edge on ib and xpf vs b2; the compiler's ib / XPF
//                             calendars count it, XPF_TRANSPORT_EDGES included)
//   cmd[115:0] -> W5 cmd_wi  the static command calendar qfd_dv_cmd_cal (SETID at boot, every slice / XC command)
//   tl[1087:0] -> W5 st_wi   (QLB-C4b 10-18; MU-QW-DIE 10-19 ported into qfd_dv_cmd_cal_mu) the slice stream TABLE words
//                             (kinds 1..3: PROG / CROM / BTAB) played by the calendar's LOCAL TLOAD entries from blocks of
//                             this installed image (the only load path of the slice tables on the die).  A register, one edge.
//   ss5[106:0] <- W5 ss_wo, ag5[9:0] <- W5 ag_wo (pin registers): the DV status that replaces seq_su's xs / dc sources.
//              Q-DIEPLAN6 10-17: widened to the Q-SLICE 2f8b7015b contract (ss 107 = {ar_land, tok_val 32, <74 b>},
//              ag 10 = {stn_busy, <9 b>}) and closes the Q-CTLM gaps: G9b dc nval = ss tok_val latched with tok_v;
//              G10 ME idle (rom_ret idle) = !ag stn_busy; coll_busy clears on an AR word landing with last
//              (ar_land & ar_last), so a single-beat AR clears it.
//   emb_start / emb_token[17:0] -> qfd_embedding_word_provider core_start / core_token (calendar LOCAL EMB entry)
//   dh[186:0] <- qfd_sys_face seq_dh (the ds levels seq_su used to take): the token start / stage / token / position
//              ({kwd, h_start [42], stage [41:36], token [35:18], pos [17:0]}) and the calendar's program copy
//              (pw [118:44], dw [186:119]) -- G9 token / position source
//   cal_program_obs[75:0] / cal_descriptor_obs[68:0] / cal_image_ready -> sys_face seq_program_obs /
//              seq_descriptor_obs / seq_cfg_image_ready (sink 1 of the program record port, was seq_su)
//   dc[55:0] -> sys_face seq_dc  {rom_fault, kv_write_flush, coll_busy, core_fault, s_fault, s_done, ntok 18, nval 32}
// ME START: the stage start (dh h_start) starts the ME program at base 0 one register edge later (the seq_su stage gate's
// one-edge pulse); a calendar LOCAL SEG entry starts a later ME segment at its base.  Both start the head exactly as
// seq_su's st face did.  Neither waits on anything.
// ME STATUS (rom_ret): the ME engines are the slice column heads fed by hr; the DV status words (ss / ag) carry no ME
// ready / idle / progress, so the head's ME availability checks have no DV producer (rule c).  The check moved into the
// slices: a station word outside its STN window faults the station (ag5 stn bit), which this block returns as the ME
// fault.  Gap G10 (contract change requested in lanes/Q-CTLM.md): ag += stn_busy restores a head-side idle check.
// STAGE_ME (QLB-PROG 10-18, G-C3; opt-in, 0 = as built): ONE installed image runs every stage of a token (qfd_sys_face
//   installs the PW1024 + DW8 image once per epoch), so the stage start must not restart the decode-layer ME programme in
//   stages that have none, and the ROM relocation must follow the RUNNING stage.  STAGE_ME = 1:
//   (a) the dh h_start starts the ME programme (base 0, head fixed-issue calendar, XPF schedule) only for the decode
//       stages 1 .. LAST_STAGE-1; stage 0 (embedding) and LAST_STAGE (LM head) run their calendar segments only;
//   (b) command_stage (= the ot_qwen_tp8_rom_relocate stage, sys_face head_stage) is the running stage, latched from dh on
//       the stage start edge, instead of the image's CALS stage (PW1017 [17:12]): as built, all 36 layers would read the
//       weights of the one layer named in the image.
//   0 extra edges on the issue path (the stage latch loads on the same edge as tok_r / pos_r).
// MUT (bench only): 1..3 -> qfd_dv_cmd_cal(_mu) MUT; 16 = calendar UFOLD off (NU > 1); 17 = SU count / observation of
//   every user (NU > 1); 18 = one shared tok / pos register instead of the per-user bank (NU > 1); 19 = every user's dh
//   start starts the ME programme (NU > 1); 20 = head stage latched on every dh start, not on LOCAL SEG (NU > 1); 4 = x_oprog / x_orows swapped; 5 = dc rom_fault from ag any (not vm);
//   6 = nval from the old (pre-widening) ss bits [73:42] instead of tok_val; 7 = ME idle ignores ag stn_busy;
//   8 = coll_busy clears on the ar_last rise only (the pre-widening rule); 9 = HARD_HR leaf stage from the CALS word.
// HARD_HR (S-QWCOL 10-18, default 1): the head side is the hardened TT head leaf ot_qfd_tt_ctlm_static_hr (kit
//   qfd_tt_head_static_h16c, claude/q-tth16: head_static_rk H15 + native route + resident relocation + loaded stage +
//   the registered relocated ROM command, CMDREG 1) instead of the same three blocks inline.  Edges unchanged: the
//   child's rom_cmd register IS the ib field of hr (hr = {ib, xpf, v} still one register after the relocated command);
//   the child's reset stations release its state one ck edge after rst_n (no data / command edge changes).  Its three
//   clock entries (ck_head, ck_pm0, ck_pm1) are this block's ck.  HARD_HR = 0: the previous inline head (reference).
// NU (MU-ADOPT-CTLM 10-19, Qwen ROM 4 users, MU-QWEN R1/R2/R5; design record results/rtl/mu_qwen_1018/README.md s3 and
//   results/rtl/mu_qwen_1018/ctlm/README.md).  NU = 1 (default) = the single-user block on every edge (the calendar is
//   qfd_dv_cmd_cal_mu at NU 1, lockstep-identical to qfd_dv_cmd_cal).  NU = 2..4:
//   - dh_user[1:0] (new input, pin-registered beside dh) = the user of the dh stage start (qfd_sys_face seq_dh_user,
//     MU-QWEN R3 USER prefix event).  Ignored at NU = 1 (tie 0).
//   - u_cal = qfd_dv_cmd_cal_mu #(NU, UVM_STRIDE, PIDX_STRIDE, UTAG_LSB, UFOLD 1): one playhead per user; the issued
//     word carries its user (PORTS / STN-VM bases + u*UVM_STRIDE, SU pidx + u*PIDX_STRIDE, XC tag user bits, and STN
//     cmd[52:51] / AMAX cmd[9:8] = user for the R4 per-user LM-head argmax).  No new output: the slices see the user in
//     the cmd fields.  Strides = tools/qwen_static_schedule/mu_calendar.py DV_UVM_STRIDE / DV_PIDX_STRIDE / DV_UTAG_LSB.
//   - per-user token / position bank (R2, token row part): a start latches tok/pos of ITS user; a LOCAL SEG entry starts
//     the ME segment with the token / position of the entry's user; LOCAL EMB sends the entry's user's token.
//   - the dh stage start starts the decode ME programme (base 0, XPF schedule) for user 0 only (the latency user):
//     fillers' ME work runs as compiled LOCAL SEG entries of their own calendar segments (op-level interleave).
//   - head running stage (STAGE_ME 1, ROM relocation): latched on user 0's dh start and on every LOCAL SEG start with
//     the segment's user's stage (per-user stage bank); a filler's dh start leaves it alone.
//   - SU accepted count / SU observation (head o-sync, XPF su events) count user 0's SU commands only, so the latency
//     user's head and XPF see exactly the single-user event stream.
//   User 0 is cycle-identical to NU = 1 (bench rtl/test/mu_qwen_seq ctlm cases).  Static schedule: no ready / credit;
//   every violation is a sticky fault (calendar fault_code, start_fault), never a stall.
// OPSEG (MU-QW-B1 10-19, coordinator B1 = option 2, opt-in, NU 2..4; 0 = everything above, unchanged): op-granular
//   playback of the 4-user calendar (tools/qwen_static_schedule/mu_opcal.py) WITHOUT changing the closed qfd_sys_face.
//   - the face's T calendar carries the latency user's stage starts only (its dh starts are user 0; dh_user ignored);
//   - u_leaf = qfd_sys_face_mu_dhuser #(OPSEG 1) INSIDE this cluster, observing dh_q (the same edge as u_cal's start):
//     ROM ot_rom_4096x72_m8 (OPSEG_VIAMAP / +OT_ROM_DIR with OPSEG_INST) of filler op starts {t, user, stage, first,
//     cnt, FIRST}, frame counter anchored on the latency user's first L0 start; its registered op start drives u_cal on
//     the compiled edge with an EXPLICIT entry range (start_rng);
//   - u_cal start = face start (user 0) | leaf start (its user, stage, range); both on one edge = sticky op_fault (the
//     face start wins: the latency user is never delayed; the compiler reserves one start port, mu_opcal cp.start);
//   - per-user stage bank: written on the face start (user 0) and on every leaf start (its user);
//   - filler token / position: the face carries user 0 only, so tok_b[u] <= the root token (ss5 tok_idx) and pos_b[u] <=
//     pos_b[u] + 1 at user u's result (ss5 tok_v with ss5[27:26] = u: the contract with MU-QW-AMIX, the user of tok_idx;
//     bits spare today).  dc ntok / nval / tok_seen take user-0 results only (the face's RESULT capture never sees a
//     filler token).
//   - filler INITIAL context (MU-QW-DIE 10-19, coordinator 0ka: boot-loaded through the image / host config plane, the
//     KV schedule-param pattern; the bench-only preload is GONE): the calendar image's DW5 / DW6 (reserved 0 before)
//     carry the context record CTX = {DW6, DW5} (u_cal CTX_DW 1: the seal accepts them, ctx_dw = the calendar's own dwr
//     registers, ctx_load = the accepted seal edge).  Layout (tools/qwen_static_schedule/mu_opcal.ctx_words):
//       CTX[36(u-1) +: 36] = {tok 18, pos 18} of filler u = 1..3;  CTX[108 +: 3] = load mask (bit u-1);  CTX[111] = 0;
//       CTX[127:112] = tag 16'h4D43.
//     On ctx_load with a good record every masked filler's tok_b / pos_b takes its record (the boot of that image;
//     unmasked fillers keep their bank, so a later install can leave running fillers alone).  A bad record (tag,
//     CTX[111], or a mask bit of a user >= NU) is a sticky op_fault and loads nothing.  The image reaches the cluster
//     only as dh PW / DW rows: on this die the closed qfd_sys_face replays its config image under the host's BEGIN /
//     AUTH, so the record is part of the boot image (fixed in operation, no handshake); no port change.
//   - op_fault (sticky) = leaf fault | start collision, into core_fault (dc, cf).
//   No port change.  New macro in the cluster: 1 x ot_rom_4096x72_m8 (leaf image).  Bench rtl/test/mu_qwen_seq/
//   mu_opseg_bench.py.  MUT (bench only): 21 u_cal range ignored; 22 collision not flagged; 23 filler result written to
//   the next filler's bank; 24 / 25 / 26 -> leaf MUT 4 (entry one edge late) / 5 (re-anchor every L0) / 6 (no drift check);
//   30 / 31 -> calendar MUT 4 / 5 (TLOAD payload halves swapped / table word one edge late; QLB-C4b's 9 / 10 -- 9 is
//   HARD_HR's here);  27 context record never loaded (banks start at 0: the pre-0ka hardware); 28 record of user u loaded into user
//   (u mod (NU-1)) + 1; 29 record not checked (a bad tag loads and does not fault).
// D2D USER (MU-DQ-D2DUSER 10-19, NU > 1): native_pos[17:16] = the user of the latest head start (see hu below), the
//   carrier native59 stamps into the D2D CMD / Q epoch[1:0]; no port change, no added edge.  MUT 32 = user not carried.
// =====================================================================================================================
module qfd_tt_ctlm_dv #(
    parameter integer XPF_TRANSPORT_EDGES = -1,
    parameter integer MUT = 0,
    parameter integer LAST_STAGE = 37,
    parameter integer HARD_HR = 1,
    parameter integer STAGE_ME = 0,
    parameter integer NU = 1,
    parameter integer UVM_STRIDE = 4096,
    parameter integer PIDX_STRIDE = 128,
    parameter integer UTAG_LSB = 6,
    parameter integer OPSEG = 0,
    parameter string  OPSEG_VIAMAP = "",
    parameter string  OPSEG_INST = "qfd_tt_ctlm_opseg",
    parameter integer HR_ASBUILT = 0                // QW-DIEFIX: 1 = bench mutant (as-built hr layout)
) (
    input  wire          ck,
    input  wire          rst_n,
    // ---------------- system face (qfd_sys_face)
    input  wire [74:0]   pw,
    input  wire [186:0]  dh,
    input  wire [1:0]    dh_user,
    input  wire          kok,
    input  wire          kwd,
    input  wire          fab,
    output wire [75:0]   program_obs,
    output wire          control_stores_ready,
    output wire          layer_context_v,
    output wire [17:0]   native_tok,
    output wire [17:0]   native_pos,
    output wire [5:0]    command_stage,
    output wire [75:0]   cal_program_obs,
    output wire [68:0]   cal_descriptor_obs,
    output wire          cal_image_ready,
    output reg  [55:0]   dc,
    // ---------------- native59
    output wire [379:0]  native_cmd,
    input  wire [94:0]   native_ret,
    // ---------------- W5 slice (qfd_dv_slice2_w dn face)
    output wire [452:0]  hr,
    output wire [115:0]  cmd,
    output wire [1087:0] tl,
    input  wire [106:0]  ss5,
    input  wire [9:0]    ag5,
    // ---------------- embedding provider
    output reg           emb_start,
    output reg  [17:0]   emb_token,
    output wire          cf
);
    // ------------------------------------------------------------------ pin registers (flop-first inputs)
    reg  [186:0] dh_q;
    reg  [106:0] ss_q;
    reg  [9:0]   ag_q;
    reg          fab_q;                   // kok / kwd / pw land in the head's own pin stations (AUD 4 / IS 1)
    reg  [1:0]   dhu_q;
    always @(posedge ck or negedge rst_n)
        if (!rst_n) begin dh_q <= 187'd0; ss_q <= 107'd0; ag_q <= 10'd0; fab_q <= 1'b0; dhu_q <= 2'd0; end
        else begin dh_q <= dh; ss_q <= ss5; ag_q <= ag5; fab_q <= fab; dhu_q <= (NU > 1) ? dh_user : 2'd0; end
    localparam integer UB = (NU > 1) ? $clog2(NU) : 1;
    localparam integer OPS = (OPSEG != 0 && NU > 1) ? 1 : 0;
    wire [UB-1:0] s_user = (OPS != 0) ? {UB{1'b0}} : dhu_q[UB-1:0];
    wire        s_start = dh_q[42];
    wire [5:0]  s_stage = dh_q[41:36];
    wire [17:0] s_tok = dh_q[35:18], s_pos = dh_q[17:0];
    // ss5 = {ar_land, tok_val 32, sid 4, any, su, vm, stn, sc, stm, port, su_idle, sc_busy, su_prog 16, su_rows 16,
    //        ar_rank 3, ar_last, tok_v, tok_idx 24};  ag5 = {stn_busy, any, su, vm, stn, sc, stm, port, su_busy, root_busy}
    wire [15:0] ss_prog = ss_q[60:45], ss_rows = ss_q[44:29];
    wire        ss_arl = ss_q[25], ss_tokv = ss_q[24];
    wire [23:0] ss_tok = ss_q[23:0];
    wire [31:0] ss_tval = (MUT == 6) ? ss_q[73:42] : ss_q[105:74];
    wire        ss_arland = ss_q[106];
    wire        ag_stn_busy = (MUT == 7) ? 1'b0 : ag_q[9];
    wire        ag_any = ag_q[8], ag_vm = ag_q[6], ag_stn = ag_q[5], ag_su_busy = ag_q[1];
    wire [1:0]  ss_tu = ss_q[27:26];                // OPSEG: the user of tok_idx when tok_v (MU-QW-AMIX contract)

    // ------------------------------------------------------------------ OPSEG op-start leaf (filler op starts)
    wire        l_v, l_ff; wire [1:0] l_u2; wire [5:0] l_stage; wire [9:0] l_first, l_cnt; wire [3:0] l_fcode;
    wire        l_fault;
    generate if (OPS != 0) begin : g_op
        qfd_sys_face_mu_dhuser #(.NU(NU), .OPSEG(1), .LAST_STAGE(LAST_STAGE), .VIAMAP(OPSEG_VIAMAP),
            .INSTANCE(OPSEG_INST), .MUT((MUT >= 24 && MUT <= 26) ? MUT - 20 : 0)) u_leaf (.ck(ck), .rst_n(rst_n),
            .dh_run(dh_q[43:0]), .dh_user(), .res_user(), .mu_fault(l_fault), .op_v(l_v), .op_user(l_u2),
            .op_stage(l_stage), .op_first(l_first), .op_cnt(l_cnt), .op_ff(l_ff), .op_fcode(l_fcode));
    end else begin : g_no_op
        assign l_v = 1'b0; assign l_ff = 1'b0; assign l_u2 = 2'd0; assign l_stage = 6'd0; assign l_first = 10'd0;
        assign l_cnt = 10'd0; assign l_fcode = 4'd0; assign l_fault = 1'b0;
    end endgenerate
    wire [UB-1:0] l_user = l_u2[UB-1:0];
    // filler initial context record (CTX_DW, see the header): checked and loaded on the accepted seal edge
    wire [127:0] c_ctx; wire c_ctxld;                                // from u_cal (below)
    localparam integer NF = (NU > 1) ? NU - 1 : 1;                   // fillers
    wire [2:0]  ctx_mask = c_ctx[110:108];
    wire        ctx_ok = (MUT == 29) || (c_ctx[127:112] == 16'h4D43 && !c_ctx[111] && (({1'b0, ctx_mask} >> (NU - 1)) == 4'd0));
    wire        ctx_ld = (OPS != 0) && c_ctxld && ctx_ok && (MUT != 27);
    wire        ctx_bad = (OPS != 0) && c_ctxld && !ctx_ok;
    wire        l_start = (OPS != 0) && l_v && !(s_start);          // the face start wins a collision
    wire        op_coll = (OPS != 0) && l_v && s_start;
    reg         op_fault;
    always @(posedge ck or negedge rst_n)
        if (!rst_n) op_fault <= 1'b0;
        else if (l_fault || (op_coll && MUT != 22) || ctx_bad) op_fault <= 1'b1;
    wire        u_start = s_start || l_start;
    wire [5:0]  u_stage = l_start ? l_stage : s_stage;
    wire [UB-1:0] u_user = l_start ? l_user : s_user;

    // ------------------------------------------------------------------ static command calendar
    wire        c_emb, c_seg, c_su, c_xc, c_run, c_done, c_fault, c_ready;
    wire [11:0] c_base; wire [8:0] c_pidx;
    wire [UB-1:0] c_user, c_done_user; wire [NU-1:0] c_run_u; wire [5:0] c_fcode;
    // MUT 1..3 -> the calendar's MUT; MUT 16 (bench only, NU > 1) -> the calendar's UFOLD-off mutant
    qfd_dv_cmd_cal_mu #(.MUT((MUT >= 1 && MUT <= 3) ? MUT : (MUT == 16 || MUT == 21 || MUT == 33) ? MUT : (MUT == 30) ? 4 : (MUT == 31) ? 5 : 0), .LAST_STAGE(LAST_STAGE), .NU(NU),
        .UVM_STRIDE(UVM_STRIDE), .PIDX_STRIDE(PIDX_STRIDE), .UTAG_LSB(UTAG_LSB), .UFOLD((NU > 1) ? 1 : 0), .CTX_DW(OPS)) u_cal (
        .ck(ck), .rst_n(rst_n),
        .pw_v(dh_q[118]), .pw_addr(dh_q[117:108]), .pw_data(dh_q[107:44]),
        .dw_v(dh_q[186]), .dw_addr(dh_q[185:183]), .dw_data(dh_q[182:119]),
        .start(u_start), .stage(u_stage), .start_user(u_user), .start_rng(l_start), .start_first(l_first),
        .start_cnt(l_cnt), .cmd(cmd), .tl(tl), .cmd_user(c_user), .loc_emb(c_emb),
        .loc_seg(c_seg), .loc_base(c_base),
        .su_issue(c_su), .su_pidx(c_pidx), .xc_issue(c_xc), .program_obs(cal_program_obs),
        .descriptor_obs(cal_descriptor_obs), .image_ready(c_ready), .running(c_run), .running_u(c_run_u), .done(c_done),
        .done_user(c_done_user), .fault(c_fault), .fault_code(c_fcode), .ctx_dw(c_ctx), .ctx_load(c_ctxld));
    // user-0 gates (NU > 1): the head / XPF see the latency user's SU stream only (MUT 17: every user's)
    wire        c_u0 = (NU == 1) || (c_user == {UB{1'b0}}) || (MUT == 17);
    wire        s_u0 = (NU == 1) || (s_user == {UB{1'b0}}) || (MUT == 19);
    assign cal_image_ready = c_ready;

    // ------------------------------------------------------------------ token / ME start (was seq_su's st face)
    // STAGE_ME: the ME programme starts only in decode stages (see the header)
    // head running stage (NU > 1): the hard leaf has ONE loaded stage (ROM relocation).  Latch it on user 0's dh start
    // (as today) and on every LOCAL SEG start with the stage of the SEGMENT's user (per-user stage bank), so each ME
    // segment reads its own user's layer.  A filler's dh start does not touch it.  NU = 1: hd = the dh start / stage.
    // (MUT 20, bench only: every dh start latches, no SEG latch = the single-user wiring.)
    reg  [5:0]  stg_b [0:NU-1];
    integer     sg_i;
    always @(posedge ck or negedge rst_n)
        if (!rst_n) begin for (sg_i = 0; sg_i < NU; sg_i = sg_i + 1) stg_b[sg_i] <= 6'd0; end
        else begin
            if (s_start) stg_b[s_user] <= s_stage;
            else if (l_start) stg_b[l_user] <= l_stage;                // OPSEG: the leaf start's user
        end
    wire        hd_start = (NU == 1 || (MUT == 20)) ? s_start : ((s_start && s_u0) || c_seg);
    wire [5:0]  hd_stage = (NU == 1 || (MUT == 20)) ? s_stage : ((s_start && s_u0) ? s_stage : stg_b[c_user]);
    // NU > 1: the dh start runs the ME programme for user 0 only; per-user tok / pos bank (MUT 18: one shared register)
    wire        s_me0 = (STAGE_ME == 0) ? s_start : (s_start && s_stage != 6'd0 && s_stage < LAST_STAGE[5:0]);
    wire        s_me = s_me0 && s_u0;
    reg  [17:0] tok_b [0:NU-1], pos_b [0:NU-1];
    reg         st_h; reg [17:0] st_tok, st_pos; reg [11:0] st_base;
    reg         start_fault;
    wire [UB-1:0] b_wr = (MUT == 18) ? {UB{1'b0}} : s_user, b_rd = (MUT == 18) ? {UB{1'b0}} : c_user;
    // OPSEG filler result: tok_b / pos_b of the result's user (MUT 23: the next filler's bank)
    wire        r_fill = (OPS != 0) && ss_tokv && ss_tu != 2'd0 && {1'b0, ss_tu} < 3'(NU);
    wire [1:0]  r_u2 = (MUT == 23) ? ((ss_tu == 2'(NU - 1)) ? 2'd1 : ss_tu + 2'd1) : ss_tu;
    wire [UB-1:0] r_wr = r_u2[UB-1:0];
    integer     ub_i;
    always @(posedge ck or negedge rst_n)
        if (!rst_n) begin
            for (ub_i = 0; ub_i < NU; ub_i = ub_i + 1) begin tok_b[ub_i] <= 18'd0; pos_b[ub_i] <= 18'd0; end
            st_h <= 1'b0; st_tok <= 18'd0; st_pos <= 18'd0; st_base <= 12'd0;
            start_fault <= 1'b0; emb_start <= 1'b0; emb_token <= 18'd0;
        end else begin
            // boot context (OPSEG): masked fillers take their record (MUT 28: rotated records); the image loads only while
            // no segment plays (calendar image fault), so no start / result of a filler shares this edge in a legal run
            if (ctx_ld)
                for (ub_i = 1; ub_i < NU; ub_i = ub_i + 1)
                    if (ctx_mask[ub_i - 1]) begin
                        tok_b[ub_i] <= c_ctx[36 * (((MUT == 28) ? (ub_i % NF) + 1 : ub_i) - 1) + 18 +: 18];
                        pos_b[ub_i] <= c_ctx[36 * (((MUT == 28) ? (ub_i % NF) + 1 : ub_i) - 1) +: 18];
                    end
            if (s_start) begin tok_b[b_wr] <= s_tok; pos_b[b_wr] <= s_pos; end
            if (r_fill) begin tok_b[r_wr] <= ss_tok[17:0]; pos_b[r_wr] <= pos_b[r_wr] + 18'd1; end
            st_h <= s_me | c_seg;
            if (s_me) begin st_tok <= s_tok; st_pos <= s_pos; st_base <= 12'd0; end
            else if (c_seg) begin st_tok <= tok_b[b_rd]; st_pos <= pos_b[b_rd]; st_base <= c_base; end
            if (s_me && c_seg) start_fault <= 1'b1;
            emb_start <= c_emb; emb_token <= tok_b[b_rd];
        end
    wire [48:0] st = {st_h, st_tok, st_pos, st_base};
    // MU-DQ-D2DUSER (10-19): the user of the latest head start (0 on the face's dh start, cmd_user on a LOCAL SEG start;
    // same edge as st) rides on native_pos[17:16] toward native59, which stamps it into the D2D attention records'
    // epoch[1:0] (positions are < 8192, so bits [17:13] are 0 on every legal head output).  NU = 1: constant 0 (no
    // change).  MUT 32 (bench only): the user is never carried (bits stay 0).
    reg  [1:0]  hu;
    always @(posedge ck or negedge rst_n)
        if (!rst_n) hu <= 2'd0;
        else if (s_me) hu <= 2'd0;
        else if (c_seg) hu <= (NU > 1 && MUT != 32) ? 2'(c_user) : 2'd0;
    wire [17:0] native_pos_h;
    assign native_pos = (NU > 1) ? (native_pos_h | {hu, 16'd0}) : native_pos_h;

    // ------------------------------------------------------------------ SU observation (was seq_su's xs / su_observe)
    reg  [23:0] su_acc;                       // SU commands issued (the head's other-unit accepted count)
    reg  [15:0] su_obs;
    always @(posedge ck or negedge rst_n)
        if (!rst_n) begin su_acc <= 24'd0; su_obs <= 16'd0; end
        else begin
            if (c_su && c_u0) su_acc <= su_acc + 24'd1;
            su_obs <= {c_su && c_u0, c_su && c_u0, 2'd2, 3'd0, c_pidx};
        end
    wire [15:0] x_oprog = (MUT == 4) ? ss_rows : ss_prog;
    wire [15:0] x_orows = (MUT == 4) ? ss_prog : ss_rows;

    // ------------------------------------------------------------------ ME head (the b2 parent minus the tree)
    wire [94:0]  rom_ret;
    wire         me_image_ready;
    wire [55:0]  cp;
    wire [15:0]  actual_me_observe;
    reg          cp_fault;
    always @(posedge ck or negedge rst_n)
        if (!rst_n) cp_fault <= 1'b0;
        else if (cp[0]) cp_fault <= 1'b1;      // a CP copy row: no copy engine on the DV die
    wire         hr_fault;                     // head fault | relocation sticky
    wire [379:0] ib_q;                         // the relocated ROM command, registered (hr ib field)
    // ME status: see the header (ME STATUS); ret layout {fault, progress 16, am_any, am_val 32, am_idx 18, wrom_addr 24,
    // wrom_re, idle, ready}
    assign rom_ret = {ag_stn, 16'd0, 1'b0, 32'd0, 18'd0, 24'd0, 1'b0, !ag_stn_busy, 1'b1};
    wire unused_me = &{1'b0, actual_me_observe[14:0]};
    generate if (HARD_HR != 0) begin : g_hard_hr
        // STAGE_ME (b) lives INSIDE the hard head leaf: the h17 leaf (Q-H16C 10-18) latches loaded_stage from its
        // stage_start / stage ports when STAGE_ME = 1, else from the image CALS word.  Part (a) is here in the parent.
        // MUT 9 (bench only) = the as-built leaf (stage from the CALS word) under STAGE_ME = 1.
        ot_qfd_tt_ctlm_static_hr #(.STAGE_ME((STAGE_ME != 0 && MUT != 9) ? 1 : 0)) u_hr (
            .stage_start(hd_start), .stage(hd_stage),
            .rom_ret_i(rom_ret), .cp_active(1'b0), .cp(cp), .me_image_ready(me_image_ready), .program_obs(program_obs),
            .layer_context_v(layer_context_v), .native_tok(native_tok), .native_pos(native_pos_h), .rom_cmd(ib_q),
            .command_stage(command_stage), .native_cmd(native_cmd), .me_observe(actual_me_observe),
            .native_ret(native_ret), .ck_head(ck), .ck_pm0(ck), .ck_pm1(ck), .rst_n(rst_n),
            .h_start(st[48]), .token(st[47:30]), .pos(st[29:12]), .prog_base(st[11:0]),
            .pw_v(pw[74]), .pw_addr(pw[73:64]), .pw_data(pw[63:0]),
            .x_oacc(su_acc), .x_oidle(!ag_su_busy), .x_oprog(x_oprog), .x_orows(x_orows),
            .kv_ok(kok), .kv_write_drained(kwd), .me_mem_ok(1'b1),
            .m_fin_o(), .m_fidx_o(), .m_fval_o(),
            .kvd_v(), .kvd_wbase(), .kvd_ts(), .kvd_ks(), .kvd_js(), .kvd_wcs(), .kvd_split(), .kvd_jsh(), .kvd_tiles(),
            .kvd_k(), .kvd_nout(), .kvd_kindk(), .kvd_pos(), .me_clk_en(), .c_fault(hr_fault));
    end else begin : g_soft_hr
        reg  [5:0]   loaded_stage;
        reg          relocation_sticky;
        reg  [379:0] ib_r;
        wire [379:0] hcmd, local_rom_cmd, ib;
        wire [94:0]  ret;
        wire         head_fault, relocation_fault;
        always @(posedge ck or negedge rst_n)
            if (!rst_n) begin loaded_stage <= 6'd0; relocation_sticky <= 1'b0; ib_r <= 380'd0; end
            else begin
                if (STAGE_ME != 0) begin if (hd_start) loaded_stage <= hd_stage; end
                else if (pw[74] && pw[73:64] == 10'd1017 && pw[63:32] == 32'h43414c53) loaded_stage <= pw[17:12];
                if (relocation_fault) relocation_sticky <= 1'b1;
                ib_r <= ib;
            end
        assign command_stage = loaded_stage;
        assign ib_q = ib_r;
        assign hr_fault = head_fault | relocation_sticky;
        ot_qwen_tp8_rom_relocate u_resident_relocation (.in_cmd(local_rom_cmd), .in_stage(loaded_stage), .out_cmd(ib),
            .fault(relocation_fault));
        ot_qfd_native_cmd_route u_native_route (.clk(ck), .rst_n(rst_n), .cmd(hcmd), .rom_ret(rom_ret),
            .native_ret(native_ret), .rom_cmd(local_rom_cmd), .native_cmd(native_cmd), .ret(ret));
        qfd_tt_ctlm_head_static u_head (
            .me_observe(actual_me_observe), .cp_active(1'b0), .cp(cp),
            .me_image_ready(me_image_ready), .program_obs(program_obs),
            .layer_context_v(layer_context_v), .native_tok(native_tok), .native_pos(native_pos_h),
            .clk(ck), .ck_sched(ck), .rst_n(rst_n),
            .h_start(st[48]), .token(st[47:30]), .pos(st[29:12]), .prog_base(st[11:0]),
            .pw_v(pw[74]), .pw_addr(pw[73:64]), .pw_data(pw[63:0]),
            .x_oacc(su_acc), .x_oidle(!ag_su_busy), .x_oprog(x_oprog), .x_orows(x_orows),
            .kv_ok(kok), .kv_write_drained(kwd), .me_mem_ok(1'b1),       // no VM port on the ME path: x arrives in the stream
            .m_fin_o(), .m_fidx_o(), .m_fval_o(), .me_clk_en(), .c_fault(head_fault),
            .kvd_v(), .kvd_wbase(), .kvd_ts(), .kvd_ks(), .kvd_js(), .kvd_wcs(), .kvd_split(), .kvd_jsh(), .kvd_tiles(),
            .kvd_k(), .kvd_nout(), .kvd_kindk(), .kvd_pos(),
            .cmd(hcmd), .ret(ret));
    end endgenerate

    // ------------------------------------------------------------------ XPF (unchanged loader + static schedule)
    generate if (XPF_TRANSPORT_EDGES < 0) begin : g_unassigned_arm_route
        initial $error("native XPF transport edges require assigned physical route");
    end endgenerate
    wire monitor_rs;
    ot_reset_sync #(.ASYNC_STAGES(2)) u_xpf_reset (.clk(ck), .async_rst_n(rst_n), .sync_rst_n(monitor_rs));
    wire [48:0] monitor_start;
    ot_hdc_delay #(.W(49), .D(1), .RESET(1)) u_xpf_start_face (.clk(ck), .rst_n(monitor_rs), .d(st), .q(monitor_start));
    wire dvm_stage_start = monitor_start[48] && monitor_start[11:0] == 0;
    wire [15:0] monitor_su;
    ot_hdc_delay #(.W(16), .D(1), .RESET(1)) u_xpf_su_face (.clk(ck), .rst_n(monitor_rs), .d(su_obs), .q(monitor_su));
    wire [74:0] monitor_pw;
    ot_hdc_delay #(.W(75), .D(1), .RESET(1)) u_xpf_pw_face (.clk(ck), .rst_n(monitor_rs), .d(pw), .q(monitor_pw));
    wire xpf_loader_fault, xpf_schedule_fault, xpf_active, xpf_loader_ready, xpf_monitor_ready;
    wire cfg_clear, cfg_v, cfg_seal; wire [2:0] cfg_index; wire [187:0] cfg_data;
    wire [3:0] cfg_count; wire [5:0] xpf_stage; wire [31:0] stop_cycle, xpf_cycle;
    wire [71:0] xpf;
    ot_qfd_xpf_dense_pw_loader u_xpf_loader (.clk(ck), .rst_n(monitor_rs), .stage_active(xpf_active),
        .pw_v(monitor_pw[74]), .pw_addr(monitor_pw[73:64]), .pw_data(monitor_pw[63:0]),
        .cfg_clear(cfg_clear), .cfg_v(cfg_v), .cfg_seal(cfg_seal), .cfg_index(cfg_index), .cfg_data(cfg_data),
        .cfg_count(cfg_count), .stage(xpf_stage), .stop_cycle(stop_cycle), .image_ready(xpf_loader_ready),
        .fault(xpf_loader_fault));
    wire [15:0] monitor_me;
    ot_hdc_delay #(.W(16), .D(1), .RESET(1)) u_xpf_me_face (.clk(ck), .rst_n(monitor_rs), .d(actual_me_observe), .q(monitor_me));
    wire xpf_me_event = monitor_me[15];
    wire [11:0] xpf_me_pc = monitor_me[11:0];
    ot_qfd_xpf_static_schedule #(.N(4), .ARM_TRANSPORT_EDGES(XPF_TRANSPORT_EDGES)) u_xpf_schedule (.clk(ck),
        .rst_n(monitor_rs), .cfg_clear(cfg_clear), .cfg_v(cfg_v), .cfg_seal(cfg_seal),
        .cfg_index(cfg_index[1:0]), .cfg_data(cfg_data), .cfg_count(cfg_count[2:0]),
        .start(dvm_stage_start), .stop(xpf_active && xpf_cycle == stop_cycle), .stage(xpf_stage),
        .cp_issue(monitor_me[15] && monitor_me[13:12] == 3), .cp_pc(xpf_me_pc),
        .me_issue(xpf_me_event && monitor_me[13:12] == 1), .me_pc(xpf_me_pc),
        .su_issue(monitor_su[15]), .su_pc(monitor_su[11:0]),
        .xpf(xpf), .image_ready(xpf_monitor_ready), .fault(xpf_schedule_fault), .active(xpf_active), .cycle(xpf_cycle));
    assign control_stores_ready = me_image_ready && c_ready && xpf_loader_ready && xpf_monitor_ready;

    // ------------------------------------------------------------------ hr (head row) to W5: one register
    // QW-DIEFIX 10-19: hr[452:73] carries the ROM command in the SLICE's layout {go, ib 379 in ot_qwen_me_array_w12
    // order} (qfd_dv_slice2 gi decode), not the raw cmd380 {mbase .. nout, go}: as built go sat on hr[73] and the ib
    // fields were reversed, so no column head ever started a matvec (QW-XHEAD XT1 'asbuilt').  qfd_dv_hr_pack is a
    // zero-logic field permutation generated by tools/qwen_split/hr_contract.py (whose check is the die contract); it
    // follows the ib register (ib_q: the hard head's rom_cmd register, or g_soft_hr.ib_r), so no edge changes.
    // HR_ASBUILT = 1: bench mutant (the as-built layout).
    wire [379:0] ib_hr;
    qfd_dv_hr_pack #(.ASBUILT(HR_ASBUILT)) u_hr_pack (.cmd(ib_q), .hr(ib_hr));
    reg hv; reg [72:0] hr_lo;
    always @(posedge ck or negedge rst_n)
        if (!rst_n) begin hv <= 1'b0; hr_lo <= 73'd0; end
        else begin
            hv <= 1'b1;
            hr_lo <= {xpf, hv};
        end
    assign hr = {ib_hr, hr_lo};

    // ------------------------------------------------------------------ dc (was seq_su's dc) and faults
    wire core_fault = hr_fault | cp_fault | start_fault | xpf_loader_fault | xpf_schedule_fault | op_fault;
    reg  tok_seen, xc_busy, arl_d;
    reg  [17:0] ntok;
    reg  [31:0] nval;
    wire        coll_done = (MUT == 8) ? (ss_arl && !arl_d) : (ss_arland && ss_arl);
    always @(posedge ck or negedge rst_n)
        if (!rst_n) begin tok_seen <= 1'b0; ntok <= 18'd0; nval <= 32'd0; xc_busy <= 1'b0; arl_d <= 1'b0; dc <= 56'd0; end
        else begin
            arl_d <= ss_arl;
            if (s_start && s_stage == 6'd0) tok_seen <= 1'b0;           // token start
            else if (ss_tokv && (OPS == 0 || ss_tu == 2'd0)) begin tok_seen <= 1'b1; ntok <= ss_tok[17:0]; nval <= ss_tval; end
            if (c_xc) xc_busy <= 1'b1; else if (coll_done) xc_busy <= 1'b0;
            // nval: the merged argmax value of the status token (G9b closed by ss tok_val)
            dc <= {(MUT == 5) ? ag_any : ag_vm, !ag_su_busy, xc_busy, core_fault, c_fault | ag_any | fab_q, tok_seen, ntok, nval};
        end
    assign cf = core_fault | c_fault;
    wire unused = &{1'b0, c_run, c_done, ss_q[73:61], ss_q[28:26], ss_tok[23:18], dh_q[43], unused_me, c_run_u,
                    c_done_user, c_fcode, l_ff, l_fcode};
endmodule
