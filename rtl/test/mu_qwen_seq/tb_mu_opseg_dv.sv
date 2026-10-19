`timescale 1ns/1ps
// MU-QW-B1 bench harness (2026-10-19): qfd_tt_ctlm_dv (HARD_HR 1, STAGE_ME 1) at NU 1 / OPSEG 0 (the single-user
// reference) or NU 4 / OPSEG 1 (the op-start leaf inside the cluster, ROM image from +OT_ROM_DIR=<dir> with instance
// qfd_tt_ctlm_opseg), driven as qfd_sys_face drives it.  The fillers' initial context arrives as the image's DW5 / DW6
// boot context record (MU-QW-DIE 10-19, coordinator 0ka; no preload define / plusargs any more).  Events (+EV, sorted "cycle kind hex", applied before posedge
// `cycle`):
//   0 PW  {addr 10, data 64} -> tt pw and dh pw (both copies, the same edge)     1 DW {addr 3, data 64} -> dh dw
//   2 RUN {user 2 [44:43], h_start [42], stage 6, tok 18, pos 18} -> dh run levels (h_start one edge) + dh_user
//   3 RES {user 2 [43:42], val 24 [41:18], tok 18 [17:0]} -> ss5 for one edge: tok_v, tok_idx = tok, ss5[27:26] = user
//         (the MU-QW-AMIX contract), tok_val = val (the root result as qfd_dv_scalar2 returns it)
//   4 CTX {user 2 [37:36], tok 18 [35:18], pos 13 [12:0]} (MU-DQ-BOOTCTX 10-19, CTX_SRC 1): the KV die's MU-slot kind-12
//         HOST context record (MU-KV-CTX format, TAG epoch = {seq14, user2}) on the face's context slot for one edge, into
//         the REAL face receiver qfd_host_native_context_rx (must accept it) and the die-top leaf qfd_mu_ctx_rx_die,
//         whose ctx_x drives the cluster's ctx_x (in the die: via the GEN's hops; here direct).
// Log (+LOG), label = the posedge just taken:
//   "c CMD u hex", "c EMB u tok", "c SEG u base tok pos", "c MES tok pos", "c SUA n", "c HD hex", "c CST stage",
//   "c DC hex" (dc on change), "c STA user stage rng first cnt" (u_cal start consumed at the next posedge),
//   "c FAULT code" (calendar fault rise), "c OPF lcode coll" (op_fault rise / leaf code change), "c END f code sf opf lcode",
//   "c LCV tok pos stage" (layer_context_v: head + filler native contexts, MU-DQ-BOOTCTX FCTX),
//   "c XLD mask" (runtime context loaded: ctx_ld with x_ld), "c RXF rx leaf" (face receiver / ctx leaf fault rise).
module tb_mu_opseg_dv;
    parameter integer NU = 1, MUT = 0, OPSEG = 0, CTX_SRC = 0, LMUT = 0, CLMUT = 0, FCTX = 0;
    reg ck = 1'b0;
    always #5 ck = ~ck;
    reg rst_n = 1'b0;
    reg [74:0] pw = 0; reg [186:0] dh = 0; reg [1:0] dh_user = 0; reg [106:0] ss5 = 0;
    wire [452:0] hr; wire [115:0] cmd; wire emb_start; wire [17:0] emb_token; wire [55:0] dc; wire cf;
    wire [75:0] pobs, cobs; wire [68:0] dobs; wire csr, cir, lcv; wire [17:0] ntk, nps; wire [5:0] cst; wire [379:0] ncmd;
    wire [1087:0] tl;
    // ---- D2D kind-12 context record path (MU-DQ-BOOTCTX): real face receiver + the die-top ctx leaf
    localparam [15:0] PEP = 16'h0042; localparam [63:0] PDG = 64'h5eed_0bad_c0de_0001;
    reg observer_fault = 1'b0;
    reg ctx_slot = 1'b0; reg [547:0] rx_rec = 548'd0; reg [13:0] kseq = 14'd0;
    wire hev, rx_cf, lf_f; wire [15:0] hep; wire [58:0] htag; wire [1:0] hgen, xu; wire hcap; wire [15:0] hiep; wire [63:0] hidg;
    wire [128:0] ctx_x;
    qfd_host_native_context_rx u_rx (.ck(ck), .rst_n(rst_n), .receive_slot(ctx_slot), .rx_v(ctx_slot),
        .rx_record(rx_rec), .program_begin_v(1'b0), .program_ready(1'b1), .installed_fusedcap(1'b1), .program_epoch(PEP),
        .program_digest(PDG), .head_context_v(1'b0), .head_stage(6'd0), .head_token(18'd0), .head_position(18'd0),
        .native_active(1'b0), .host_epoch_valid(hev), .host_epoch(hep), .host_tag(htag), .host_gen(hgen),
        .host_fusedcap(hcap), .host_image_epoch(hiep), .host_image_digest(hidg), .fault(rx_cf));
    qfd_mu_ctx_rx_die #(.NU((NU > 1) ? NU : 4), .MUT(CLMUT)) u_cx (.ck(ck), .rst_n(rst_n), .prog_context_slot(ctx_slot),
        .prog_rx_v(ctx_slot), .rx_payload(rx_rec), .ctx_x(ctx_x), .ctx_user(xu), .mu_fault(lf_f));
    reg rxf_l = 0;
    qfd_tt_ctlm_dv #(.XPF_TRANSPORT_EDGES(1), .MUT(MUT), .NU(NU), .STAGE_ME(1), .OPSEG(OPSEG), .CTX_SRC(CTX_SRC), .FCTX(FCTX)) dut (.ck(ck), .rst_n(rst_n),
        .pw(pw), .dh(dh), .dh_user(dh_user), .mu_fault(observer_fault), .ctx_x(ctx_x), .kok(1'b0), .kwd(1'b1), .fab(1'b0), .program_obs(pobs),
        .control_stores_ready(csr), .layer_context_v(lcv), .native_tok(ntk), .native_pos(nps), .command_stage(cst),
        .cal_program_obs(cobs), .cal_descriptor_obs(dobs), .cal_image_ready(cir), .dc(dc), .native_cmd(ncmd),
        .native_ret(95'd0), .hr(hr), .cmd(cmd), .ss5(ss5), .ag5(10'd0), .emb_start(emb_start), .emb_token(emb_token),
        .cf(cf), .tl(tl));
    wire [1024:0] hd = {hr, ncmd, ntk, nps, cst, lcv, csr, pobs, cf};
    reg  [1024:0] hd_l = 0;
    integer fd, lg, cyc, ncyc, ec, ek, r, pre = 0;
    reg [186:0] ev; reg have; reg [1023:0] evf, lgf; reg flt_l = 0; reg [23:0] sua_l = 0; reg [5:0] cst_l = 0;
    reg [55:0] dc_l = 0; reg opf_l = 0; reg [3:0] lfc_l = 0; reg [1:0] eu_l = 0, su_l = 0;
    // MU-DQ-D2DUSER C8: native_pos[17:16] = the user of the latest head start (0 on a face ME start, the calendar's
    // cmd_user on a LOCAL SEG start), derived here from the logged starts, not from the dut's register
    reg sg_l = 0; reg [1:0] xu_l = 0; integer cu_bad = 0, cu_n1 = 0, cu_n2 = 0, cu_n3 = 0;
    initial begin
        if (!$value$plusargs("EV=%s", evf)) $fatal(1, "+EV");
        if (!$value$plusargs("LOG=%s", lgf)) $fatal(1, "+LOG");
        if (!$value$plusargs("NCYC=%d", ncyc)) ncyc = 4000;
        fd = $fopen(evf, "r"); lg = $fopen(lgf, "w"); cyc = 0;
        r = $fscanf(fd, "%d %d %h\n", ec, ek, ev); have = (r == 3);
    end
    always @(negedge ck) begin
        if (pre < 4) begin pre = pre + 1; if (pre == 4) rst_n = 1'b1; end
        else begin
            if (cmd != 116'd0) $fdisplay(lg, "%0d CMD %0d %h", cyc, dut.u_cal.cmd_user, cmd);
            if (emb_start) $fdisplay(lg, "%0d EMB %0d %h", cyc, eu_l, emb_token);
            if (dut.st_h && dut.st_base != 12'd0) $fdisplay(lg, "%0d SEG %0d %h %h %h", cyc, su_l, dut.st_base, dut.st_tok, dut.st_pos);
            if (dut.st_h && dut.st_base == 12'd0) $fdisplay(lg, "%0d MES %h %h", cyc, dut.st_tok, dut.st_pos);
            if (dut.su_acc != sua_l) $fdisplay(lg, "%0d SUA %0d", cyc, dut.su_acc);
            if (hd !== hd_l) $fdisplay(lg, "%0d HD %h", cyc, hd);
            if (cst != cst_l) $fdisplay(lg, "%0d CST %0d", cyc, cst);
            if (dc != dc_l) $fdisplay(lg, "%0d DC %h", cyc, dc);
            if (dut.u_start) $fdisplay(lg, "%0d STA %0d %0d %0d %0d %0d", cyc, dut.u_user, dut.u_stage, dut.l_start,
                                       dut.l_first, dut.l_cnt);
            if (dut.u_cal.fault && !flt_l) $fdisplay(lg, "%0d FAULT %b", cyc, dut.u_cal.fault_code);
            if ((dut.op_fault && !opf_l) || dut.l_fcode != lfc_l) $fdisplay(lg, "%0d OPF %b %0d", cyc, dut.l_fcode, dut.op_coll);
            if (lcv) $fdisplay(lg, "%0d LCV %h %h %0d", cyc, ntk, nps, cst);
            if (dut.x_ld && dut.ctx_ld) $fdisplay(lg, "%0d XLD %0d", cyc, dut.ctx_mask);
            if ((rx_cf | lf_f) && !rxf_l) $fdisplay(lg, "%0d RXF %0d %0d", cyc, rx_cf, lf_f);
            rxf_l = rx_cf | lf_f;
            if (dut.st_h) begin
                xu_l = sg_l ? su_l : 2'd0;
                if (xu_l == 2'd1) cu_n1 = cu_n1 + 1; if (xu_l == 2'd2) cu_n2 = cu_n2 + 1; if (xu_l == 2'd3) cu_n3 = cu_n3 + 1;
            end
            if (nps[17:16] !== ((NU > 1) ? xu_l : 2'd0)) begin
                cu_bad = cu_bad + 1;
                if (cu_bad <= 3) $fdisplay(lg, "%0d CTXU_ERR carried %0d want %0d", cyc, nps[17:16], xu_l);
            end
            sg_l = dut.c_seg;
            cst_l = cst; dc_l = dc; opf_l = dut.op_fault; lfc_l = dut.l_fcode;
            flt_l = dut.u_cal.fault; sua_l = dut.su_acc; hd_l = hd;
            // the user of a LOCAL EMB / SEG entry: the calendar's cmd_user on the edge it issued (c_emb / c_seg), one edge
            // before emb_start / st_h
            if (dut.c_emb) eu_l = dut.c_user;
            if (dut.c_seg) su_l = dut.c_user;
            // inputs for the next posedge (cyc + 1)
            pw[74] = 1'b0; dh[118] = 1'b0; dh[186] = 1'b0; dh[42] = 1'b0; ss5 = 107'd0; ctx_slot = 1'b0; observer_fault = 1'b0;
            while (have && ec == cyc + 1) begin
                case (ek)
                    0: begin pw = {1'b1, ev[73:0]}; dh[118:44] = {1'b1, ev[73:0]}; end
                    1: dh[186:119] = {1'b1, ev[66:0]};
                    2: begin dh[42:0] = ev[42:0]; dh_user = ev[44:43]; end
                    3: begin ss5[24] = 1'b1; ss5[17:0] = ev[17:0]; ss5[27:26] = ev[43:42]; ss5[97:74] = ev[41:18]; end
                    4: begin   // kind 12, TAG = {epoch {seq14, user2}, 6'd0, token18, position13, 6'd0}, header epoch = TAG epoch
                        ctx_slot = 1'b1; kseq = kseq + 14'd1;
                        rx_rec = {5'd0, 4'd12, 6'd63, kseq, ev[37:36], 5'd0, 370'd0, PDG, PEP, 1'b1, 2'd1,
                                  kseq, ev[37:36], 6'd0, ev[35:18], ev[12:0], 6'd0};
                    end
                    5: observer_fault = ev[0];
                    default: $fatal(1, "bad kind %0d", ek);
                endcase
                r = $fscanf(fd, "%d %d %h\n", ec, ek, ev); have = (r == 3);
            end
            if (have && ec <= cyc) $fatal(1, "event file not sorted at cycle %0d", ec);
            cyc = cyc + 1;
            if (cyc >= ncyc) begin
                $fdisplay(lg, "%0d CTXU %0d %0d %0d %0d", cyc, cu_bad, cu_n1, cu_n2, cu_n3);
                $fdisplay(lg, "%0d END %0d %b %0d %0d %b", cyc, dut.u_cal.fault, dut.u_cal.fault_code, dut.start_fault,
                          dut.op_fault, dut.l_fcode);
`ifdef TB_LANDED
                $fdisplay(lg, "%0d LANDED_LOCKSTEP %s LMUT=%0d compared=%0d mismatches=%0d active=%0d tl_words=%0d op_starts=%0d",
                    cyc, (l_bad == 0 && l_nc > 0) ? "PASS" : "FAIL", LMUT, l_nc, l_bad, l_act, l_tlw, l_ops);
`endif
                $fclose(lg);
                $finish;
            end
        end
    end
`ifdef TB_LANDED
    // MU-DQ-CTLMKIT 10-19: the landed cluster qfd_tt_ctlm_dv_lpf_lp (lp.py, MU re-cut: NU / OPSEG, leaf ROM from the same
    // +OT_ROM_DIR) in lockstep with dut on the same compiled op-segment stimulus.  lp record (MU-DQ-CTLMCLK 10-19: inputs
    // land from the hr region, tl straight from core): landed(rst) == flat(rst delayed RB = 3); outputs 6 edges later
    // except tl 3; inputs pw / kok / kwd / native_ret presented 6 edges later, dh / dh_user / fab / ss5 / ag5 on time ->
    // the landed copy is released 3 edges BEFORE dut, gets pw through a 6-stage delay, and its outputs are compared with
    // dut's 6 (tl: 3) edges later.  LMUT = lp MUT.
    localparam integer LOFF = 6, LOFF_TL = 3, LIN_PW = 6;
    reg [74:0] pw_dl [0:LIN_PW-1];
    integer pj;
    always @(posedge ck) begin
        for (pj = LIN_PW - 1; pj > 0; pj = pj - 1) pw_dl[pj] <= pw_dl[pj - 1];
        pw_dl[0] <= pw;
    end
    initial for (pj = 0; pj < LIN_PW; pj = pj + 1) pw_dl[pj] = 75'd0;
    reg rst_early = 1'b0;
    wire [452:0] l_hr; wire [115:0] l_cmd; wire l_emb_start; wire [17:0] l_emb_token; wire [55:0] l_dc; wire l_cf;
    wire [75:0] l_pobs, l_cobs; wire [68:0] l_dobs; wire l_csr, l_cir, l_lcv; wire [17:0] l_ntk, l_nps; wire [5:0] l_cst;
    wire [379:0] l_ncmd; wire [1087:0] l_tl;
    qfd_tt_ctlm_dv_lpf_lp #(.XPF_TRANSPORT_EDGES(1), .STAGE_ME(1), .NU(NU), .OPSEG(OPSEG), .CTX_SRC(CTX_SRC), .FCTX(FCTX), .MUT(LMUT)) u_lp (.ck_core(ck),
        .ck_hr(ck), .rst_n(rst_early), .pw(pw_dl[LIN_PW-1]), .dh(dh), .dh_user(dh_user), .ctx_x(ctx_x), .mu_fault(observer_fault), .kok(1'b0), .kwd(1'b1), .fab(1'b0),
        .program_obs(l_pobs), .control_stores_ready(l_csr), .layer_context_v(l_lcv), .native_tok(l_ntk), .native_pos(l_nps),
        .command_stage(l_cst), .cal_program_obs(l_cobs), .cal_descriptor_obs(l_dobs), .cal_image_ready(l_cir), .dc(l_dc),
        .native_cmd(l_ncmd), .native_ret(95'd0), .hr(l_hr), .cmd(l_cmd), .tl(l_tl), .ss5(ss5), .ag5(10'd0),
        .emb_start(l_emb_start), .emb_token(l_emb_token), .cf(l_cf));
    wire [2378:0] v_d = {tl, pobs, csr, lcv, ntk, nps, cst, cobs, dobs, cir, dc, ncmd, hr, cmd, emb_start, emb_token, cf};
    wire [2378:0] v_l = {l_tl, l_pobs, l_csr, l_lcv, l_ntk, l_nps, l_cst, l_cobs, l_dobs, l_cir, l_dc, l_ncmd, l_hr, l_cmd,
                         l_emb_start, l_emb_token, l_cf};
    reg [2378:0] v_h [0:LOFF-1];
    integer l_nc = 0, l_bad = 0, l_act = 0, l_tlw = 0, l_ops = 0, hj, lpre = 0;
    always @(negedge ck) begin
        lpre = lpre + 1;
        if (lpre >= 1) rst_early = 1'b1;
        if (pre >= 4 && cyc > LOFF + 2) begin
            l_nc = l_nc + 1;
            if ({v_l[2378:1291]} !== v_h[LOFF_TL-1][2378:1291] || v_l[1290:0] !== v_h[LOFF-1][1290:0]) begin l_bad = l_bad + 1;
                if (l_bad <= 5) $fdisplay(lg, "%0d LANDED_MISMATCH dc %h/%h cmd %h/%h tl_nz %0d/%0d", cyc, v_h[LOFF-1][1024:969],
                    v_l[1024:969], v_h[LOFF-1][135:20], v_l[135:20], v_h[LOFF-1][2378:1291] != 0, l_tl != 0); end
            if (v_h[LOFF-1] !== v_h[LOFF-2]) l_act = l_act + 1;
            if (v_h[LOFF_TL-1][2378:1291] != 0) l_tlw = l_tlw + 1;
            if (dut.l_start) l_ops = l_ops + 1;
        end
        for (hj = LOFF - 1; hj > 0; hj = hj - 1) v_h[hj] = v_h[hj - 1];
        v_h[0] = v_d;
    end
`endif
endmodule
