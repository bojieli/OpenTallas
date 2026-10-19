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
//   hr[452:0]  -> W5 hr_wi   {ib 380, xpf 72, v}: one register (+1 edge on ib and xpf vs b2; the compiler's ib / XPF
//                             calendars count it, XPF_TRANSPORT_EDGES included)
//   cmd[115:0] -> W5 cmd_wi  the static command calendar qfd_dv_cmd_cal (SETID at boot, every slice / XC command)
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
// SEG_CAL (QLB-C4b 10-18; default = STAGE_ME, 0 = as built): the LM-head ME programme (stage LAST_STAGE, started by the
//   calendar's LOCAL SEG at its programme base) gets its own compiled calendars, so it issues on compiled cycles:
//   (a) the head fixed-issue calendar honours the programme base (qfd_tt_ctlm_head_static SEGCAL 1: a start at base 0 runs
//       ME8 [976..983] as built, a start at the image's CALB [993] base runs the segment-G rows [984..991], CALG [992]);
//   (b) a segment-G XPF schedule (qfd_dv_xpf_seg_loader [993..1003] + ot_qfd_xpf_static_schedule N 3) starts on that
//       segment start and monitors / arms that segment's producers; the base-0 schedule is unchanged.  Every monitored
//       issue goes to exactly one schedule (G while G is active, else base 0), so an issue outside both windows FAULTS.
//   An image without the G words (all zero) behaves exactly as built.  0 extra edges on every path.
// MUT (bench only): 1..3 -> qfd_dv_cmd_cal MUT; 4 = x_oprog / x_orows swapped; 5 = dc rom_fault from ag any (not vm);
//   6 = nval from the old (pre-widening) ss bits [73:42] instead of tok_val; 7 = ME idle ignores ag stn_busy;
//   8 = coll_busy clears on the ar_last rise only (the pre-widening rule); 9 = the head calendar armed at base 0 only
//   (SEGCAL 0, the pre-C4b gate); 10 = the segment-G XPF schedule never starts (the pre-C4b base-0-only XPF start).
// =====================================================================================================================
module qfd_tt_ctlm_dv #(
    parameter integer XPF_TRANSPORT_EDGES = -1,
    parameter integer MUT = 0,
    parameter integer LAST_STAGE = 37,
    parameter integer STAGE_ME = 0,
    parameter integer SEG_CAL = STAGE_ME
) (
    input  wire          ck,
    input  wire          rst_n,
    // ---------------- system face (qfd_sys_face)
    input  wire [74:0]   pw,
    input  wire [186:0]  dh,
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
    output reg  [452:0]  hr,
    output wire [115:0]  cmd,
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
    always @(posedge ck or negedge rst_n)
        if (!rst_n) begin dh_q <= 187'd0; ss_q <= 107'd0; ag_q <= 10'd0; fab_q <= 1'b0; end
        else begin dh_q <= dh; ss_q <= ss5; ag_q <= ag5; fab_q <= fab; end
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

    // ------------------------------------------------------------------ static command calendar
    wire        c_emb, c_seg, c_su, c_xc, c_run, c_done, c_fault, c_ready;
    wire [11:0] c_base; wire [8:0] c_pidx;
    qfd_dv_cmd_cal #(.MUT((MUT >= 1 && MUT <= 3) ? MUT : 0), .LAST_STAGE(LAST_STAGE)) u_cal (.ck(ck), .rst_n(rst_n),
        .pw_v(dh_q[118]), .pw_addr(dh_q[117:108]), .pw_data(dh_q[107:44]),
        .dw_v(dh_q[186]), .dw_addr(dh_q[185:183]), .dw_data(dh_q[182:119]),
        .start(s_start), .stage(s_stage), .cmd(cmd), .loc_emb(c_emb), .loc_seg(c_seg), .loc_base(c_base),
        .su_issue(c_su), .su_pidx(c_pidx), .xc_issue(c_xc), .program_obs(cal_program_obs),
        .descriptor_obs(cal_descriptor_obs), .image_ready(c_ready), .running(c_run), .done(c_done), .fault(c_fault));
    assign cal_image_ready = c_ready;

    // ------------------------------------------------------------------ token / ME start (was seq_su's st face)
    // STAGE_ME: the ME programme starts only in decode stages (see the header)
    wire        s_me = (STAGE_ME == 0) ? s_start : (s_start && s_stage != 6'd0 && s_stage < LAST_STAGE[5:0]);
    reg  [17:0] tok_r, pos_r;
    reg         st_h; reg [17:0] st_tok, st_pos; reg [11:0] st_base;
    reg         start_fault;
    always @(posedge ck or negedge rst_n)
        if (!rst_n) begin
            tok_r <= 18'd0; pos_r <= 18'd0; st_h <= 1'b0; st_tok <= 18'd0; st_pos <= 18'd0; st_base <= 12'd0;
            start_fault <= 1'b0; emb_start <= 1'b0; emb_token <= 18'd0;
        end else begin
            if (s_start) begin tok_r <= s_tok; pos_r <= s_pos; end
            st_h <= s_me | c_seg;
            if (s_me) begin st_tok <= s_tok; st_pos <= s_pos; st_base <= 12'd0; end
            else if (c_seg) begin st_tok <= tok_r; st_pos <= pos_r; st_base <= c_base; end
            if (s_me && c_seg) start_fault <= 1'b1;
            emb_start <= c_emb; emb_token <= tok_r;
        end
    wire [48:0] st = {st_h, st_tok, st_pos, st_base};

    // ------------------------------------------------------------------ SU observation (was seq_su's xs / su_observe)
    reg  [23:0] su_acc;                       // SU commands issued (the head's other-unit accepted count)
    reg  [15:0] su_obs;
    always @(posedge ck or negedge rst_n)
        if (!rst_n) begin su_acc <= 24'd0; su_obs <= 16'd0; end
        else begin
            if (c_su) su_acc <= su_acc + 24'd1;
            su_obs <= {c_su, c_su, 2'd2, 3'd0, c_pidx};
        end
    wire [15:0] x_oprog = (MUT == 4) ? ss_rows : ss_prog;
    wire [15:0] x_orows = (MUT == 4) ? ss_prog : ss_rows;

    // ------------------------------------------------------------------ ME head (the b2 parent minus the tree)
    wire [379:0] hcmd, local_rom_cmd, ib;
    wire [94:0]  ret, rom_ret;
    wire         head_fault, relocation_fault, me_image_ready;
    wire [55:0]  cp;
    wire [15:0]  actual_me_observe;
    reg  [5:0]   loaded_stage;
    reg          relocation_sticky, cp_fault;
    always @(posedge ck or negedge rst_n)
        if (!rst_n) begin loaded_stage <= 6'd0; relocation_sticky <= 1'b0; cp_fault <= 1'b0; end
        else begin
            if (STAGE_ME != 0) begin if (s_start) loaded_stage <= s_stage; end
            else if (pw[74] && pw[73:64] == 10'd1017 && pw[63:32] == 32'h43414c53) loaded_stage <= pw[17:12];
            if (relocation_fault) relocation_sticky <= 1'b1;
            if (cp[0]) cp_fault <= 1'b1;      // a CP copy row: no copy engine on the DV die
        end
    assign command_stage = loaded_stage;
    ot_qwen_tp8_rom_relocate u_resident_relocation (.in_cmd(local_rom_cmd), .in_stage(loaded_stage), .out_cmd(ib),
        .fault(relocation_fault));
    ot_qfd_native_cmd_route u_native_route (.clk(ck), .rst_n(rst_n), .cmd(hcmd), .rom_ret(rom_ret), .native_ret(native_ret),
        .rom_cmd(local_rom_cmd), .native_cmd(native_cmd), .ret(ret));
    // ME status: see the header (ME STATUS); ret layout {fault, progress 16, am_any, am_val 32, am_idx 18, wrom_addr 24,
    // wrom_re, idle, ready}
    assign rom_ret = {ag_stn, 16'd0, 1'b0, 32'd0, 18'd0, 24'd0, 1'b0, !ag_stn_busy, 1'b1};
    wire unused_me = &{1'b0, actual_me_observe[14:0]};
    qfd_tt_ctlm_head_static #(.SEGCAL((SEG_CAL != 0 && MUT != 9) ? 1 : 0)) u_head (
        .me_observe(actual_me_observe), .cp_active(1'b0), .cp(cp),
        .me_image_ready(me_image_ready), .program_obs(program_obs),
        .layer_context_v(layer_context_v), .native_tok(native_tok), .native_pos(native_pos),
        .clk(ck), .ck_sched(ck), .rst_n(rst_n),
        .h_start(st[48]), .token(st[47:30]), .pos(st[29:12]), .prog_base(st[11:0]),
        .pw_v(pw[74]), .pw_addr(pw[73:64]), .pw_data(pw[63:0]),
        .x_oacc(su_acc), .x_oidle(!ag_su_busy), .x_oprog(x_oprog), .x_orows(x_orows),
        .kv_ok(kok), .kv_write_drained(kwd), .me_mem_ok(1'b1),       // no VM port on the ME path: x arrives in the stream
        .m_fin_o(), .m_fidx_o(), .m_fval_o(), .me_clk_en(), .c_fault(head_fault),
        .kvd_v(), .kvd_wbase(), .kvd_ts(), .kvd_ks(), .kvd_js(), .kvd_wcs(), .kvd_split(), .kvd_jsh(), .kvd_tiles(),
        .kvd_k(), .kvd_nout(), .kvd_kindk(), .kvd_pos(),
        .cmd(hcmd), .ret(ret));

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
    // every monitored issue goes to one schedule: segment G while it is active (SEG_CAL), else base 0
    wire to_g, g_ready, g_fault;
    wire [71:0] xpf_g;
    wire ev_cp = monitor_me[15] && monitor_me[13:12] == 3, ev_me = xpf_me_event && monitor_me[13:12] == 1, ev_su = monitor_su[15];
    ot_qfd_xpf_static_schedule #(.N(4), .ARM_TRANSPORT_EDGES(XPF_TRANSPORT_EDGES)) u_xpf_schedule (.clk(ck),
        .rst_n(monitor_rs), .cfg_clear(cfg_clear), .cfg_v(cfg_v), .cfg_seal(cfg_seal),
        .cfg_index(cfg_index[1:0]), .cfg_data(cfg_data), .cfg_count(cfg_count[2:0]),
        .start(dvm_stage_start), .stop(xpf_active && xpf_cycle == stop_cycle), .stage(xpf_stage),
        .cp_issue(ev_cp && !to_g), .cp_pc(xpf_me_pc),
        .me_issue(ev_me && !to_g), .me_pc(xpf_me_pc),
        .su_issue(ev_su && !to_g), .su_pc(monitor_su[11:0]),
        .xpf(xpf), .image_ready(xpf_monitor_ready), .fault(xpf_schedule_fault), .active(xpf_active), .cycle(xpf_cycle));
    // segment-G XPF schedule (SEG_CAL, see the header)
    generate if (SEG_CAL != 0) begin : g_segx
        wire gl_clear, gl_v, gl_seal, gl_present, gl_ready, gl_fault, gs_ready, gs_fault, gs_active;
        wire [1:0] gl_index; wire [187:0] gl_data; wire [2:0] gl_count; wire [5:0] gl_stage; wire [11:0] gl_base;
        wire [31:0] gl_stop, gs_cycle;
        qfd_dv_xpf_seg_loader u_g_loader (.clk(ck), .rst_n(monitor_rs), .stage_active(gs_active),
            .pw_v(monitor_pw[74]), .pw_addr(monitor_pw[73:64]), .pw_data(monitor_pw[63:0]),
            .cfg_clear(gl_clear), .cfg_v(gl_v), .cfg_seal(gl_seal), .cfg_index(gl_index), .cfg_data(gl_data),
            .cfg_count(gl_count), .stage(gl_stage), .stop_cycle(gl_stop), .base(gl_base), .present(gl_present),
            .image_ready(gl_ready), .fault(gl_fault));
        wire g_start = (MUT != 10) && gl_present && monitor_start[48] && monitor_start[11:0] != 12'd0 &&
                       monitor_start[11:0] == gl_base;
        ot_qfd_xpf_static_schedule #(.N(3), .ARM_TRANSPORT_EDGES(XPF_TRANSPORT_EDGES)) u_g_schedule (.clk(ck),
            .rst_n(monitor_rs), .cfg_clear(gl_clear), .cfg_v(gl_v), .cfg_seal(gl_seal),
            .cfg_index(gl_index), .cfg_data(gl_data), .cfg_count(gl_count),
            .start(g_start), .stop(gs_active && gs_cycle == gl_stop), .stage(gl_stage),
            .cp_issue(ev_cp && to_g), .cp_pc(xpf_me_pc), .me_issue(ev_me && to_g), .me_pc(xpf_me_pc),
            .su_issue(ev_su && to_g), .su_pc(monitor_su[11:0]),
            .xpf(xpf_g), .image_ready(gs_ready), .fault(gs_fault), .active(gs_active), .cycle(gs_cycle));
        assign to_g = gs_active;
        assign g_ready = gl_ready && (!gl_present || gs_ready);
        assign g_fault = gl_fault | gs_fault;
    end else begin : g_nosegx
        assign to_g = 1'b0; assign g_ready = 1'b1; assign g_fault = 1'b0; assign xpf_g = 72'd0;
    end endgenerate
    wire [71:0] xpf_hr = xpf_g[0] ? xpf_g : xpf;
    assign control_stores_ready = me_image_ready && c_ready && xpf_loader_ready && xpf_monitor_ready && g_ready;

    // ------------------------------------------------------------------ hr (head row) to W5: one register
    reg hv;
    always @(posedge ck or negedge rst_n)
        if (!rst_n) begin hv <= 1'b0; hr <= 453'd0; end
        else begin
            hv <= 1'b1;
            hr <= {ib, xpf_hr, hv};
        end

    // ------------------------------------------------------------------ dc (was seq_su's dc) and faults
    wire core_fault = head_fault | relocation_sticky | cp_fault | start_fault | xpf_loader_fault | xpf_schedule_fault | g_fault;
    reg  tok_seen, xc_busy, arl_d;
    reg  [17:0] ntok;
    reg  [31:0] nval;
    wire        coll_done = (MUT == 8) ? (ss_arl && !arl_d) : (ss_arland && ss_arl);
    always @(posedge ck or negedge rst_n)
        if (!rst_n) begin tok_seen <= 1'b0; ntok <= 18'd0; nval <= 32'd0; xc_busy <= 1'b0; arl_d <= 1'b0; dc <= 56'd0; end
        else begin
            arl_d <= ss_arl;
            if (s_start && s_stage == 6'd0) tok_seen <= 1'b0;           // token start
            else if (ss_tokv) begin tok_seen <= 1'b1; ntok <= ss_tok[17:0]; nval <= ss_tval; end
            if (c_xc) xc_busy <= 1'b1; else if (coll_done) xc_busy <= 1'b0;
            // nval: the merged argmax value of the status token (G9b closed by ss tok_val)
            dc <= {(MUT == 5) ? ag_any : ag_vm, !ag_su_busy, xc_busy, core_fault, c_fault | ag_any | fab_q, tok_seen, ntok, nval};
        end
    assign cf = core_fault | c_fault;
    wire unused = &{1'b0, c_run, c_done, ss_q[73:61], ss_q[28:26], ss_tok[23:18], dh_q[43], unused_me};
endmodule

`timescale 1ns/1ps
// qfd_dv_xpf_seg_loader (QLB-C4b 10-18): the segment-G XPF table of the dense PW1024 image, beside the base-0 loader
// (ot_qfd_xpf_dense_pw_loader, PW1004..1023, unchanged).  Ascending full image; PW0 clears.
//   [993]        CALB {32'h43414c42, 4'b0, count4, 12'b0, base12}: the segment-G programme base (the head calendar reads
//                the same word); absent = 0
//   [994..1002]  three XPF188 records (3 beats each, top nibble 0, LSB valid, one stage; zero padding after)
//   [1003]       XPTG {32'h58505447, stop32 != 0}: seals (present: >= 1 record; absent: every G word zero)
// cfg_* drive an ot_qfd_xpf_static_schedule N 3 exactly as the base-0 loader drives its schedule.
module qfd_dv_xpf_seg_loader (
    input wire clk, rst_n, stage_active,
    input wire pw_v, input wire [9:0] pw_addr, input wire [63:0] pw_data,
    output reg cfg_clear, cfg_v, cfg_seal, output reg [1:0] cfg_index,
    output reg [187:0] cfg_data, output reg [2:0] cfg_count,
    output reg [5:0] stage, output reg [31:0] stop_cycle, output reg [11:0] base, output reg present,
    output wire image_ready, output reg fault
);
    reg loading, sealed, desc_seen, padding; reg [3:0] beats; reg [1:0] part, index_r; reg [127:0] payload;
    wire [187:0] record_word = {pw_data[59:0], payload};
    assign image_ready = sealed && !fault;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            cfg_clear <= 0; cfg_v <= 0; cfg_seal <= 0; cfg_index <= 0; cfg_data <= 0; cfg_count <= 0; stage <= 0;
            stop_cycle <= 0; base <= 0; present <= 0; fault <= 0; loading <= 0; sealed <= 0; desc_seen <= 0; padding <= 0;
            beats <= 0; part <= 0; index_r <= 0; payload <= 0;
        end else begin
            cfg_clear <= 0; cfg_v <= 0; cfg_seal <= 0;
            if (pw_v) begin
                if (stage_active) fault <= 1;
                else if (pw_addr == 0) begin
                    if (loading) fault <= 1;
                    else begin
                        cfg_clear <= 1; loading <= 1; sealed <= 0; desc_seen <= 0; padding <= 0; beats <= 0; part <= 0;
                        index_r <= 0; cfg_count <= 0; present <= 0; base <= 0; fault <= 0;
                    end
                end else if (pw_addr == 10'd993) begin
                    if (!loading || desc_seen) fault <= 1;
                    else begin
                        desc_seen <= 1;
                        if (pw_data != 0) begin
                            if (pw_data[63:32] != 32'h43414c42 || pw_data[11:0] == 0) fault <= 1;
                            present <= 1; base <= pw_data[11:0];
                        end
                    end
                end else if (pw_addr >= 10'd994 && pw_addr <= 10'd1002) begin
                    if (!loading || !desc_seen || pw_addr != 10'd994 + beats || beats >= 9) fault <= 1;
                    else begin
                        beats <= beats + 1'b1;
                        if (part == 0) begin payload[63:0] <= pw_data; part <= 1; end
                        else if (part == 1) begin payload[127:64] <= pw_data; part <= 2; end
                        else begin
                            if (pw_data[63:60] != 0) fault <= 1;
                            else if (record_word == 0) padding <= 1;
                            else if (!present || padding || !record_word[0] || (cfg_count != 0 && payload[91:86] != stage))
                                fault <= 1;
                            else begin
                                cfg_data <= record_word; cfg_index <= index_r; cfg_v <= 1; cfg_count <= cfg_count + 1'b1;
                                stage <= payload[91:86];
                            end
                            part <= 0; index_r <= index_r + 1'b1;
                        end
                    end
                end else if (pw_addr == 10'd1003) begin
                    if (!loading || fault || !desc_seen || part != 0 || beats != 9) fault <= 1;
                    else if (present) begin
                        if (pw_data[63:32] != 32'h58505447 || pw_data[31:0] == 0 || cfg_count == 0) fault <= 1;
                        else begin stop_cycle <= pw_data[31:0]; cfg_seal <= 1; loading <= 0; sealed <= 1; end
                    end else begin
                        if (pw_data != 0 || cfg_count != 0) fault <= 1;
                        else begin loading <= 0; sealed <= 1; end
                    end
                end
            end
        end
    end
endmodule
