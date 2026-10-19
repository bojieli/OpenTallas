`timescale 1ns/1ps
// MU-KV-CTX bench harness (2026-10-19, coordinator 0kg): the fillers' initial context from the KV die host plane over the
// EXISTING KV->compute d2d record stream into the compute ctlm boot-context loader (qfd_tt_ctlm_dv OPSEG, main 811e75a88).
//   KV:      qkd_host_record_port_mu #(MU 1) (the 4-user host record port) + a reference qkd_host_record_port_mu #(MU 0)
//            (= the unchanged qkd_host_record_port) that sees user 0's epochs / requests and the existing slot only.
//   link:    the static D2D link as its fixed latency: the record port's pin register word is delayed LINK edges; the
//            compute RX slot is the KV send slot delayed by the same compiled latency (2 record-port edges + LINK).
//   compute: the face's own kind-12 receiver (qfd_host_native_context_rx, as inside qfd_sys_face), the proposed observer
//            leaf qfd_mu_ctx_rx, and qfd_tt_ctlm_dv NU 4 OPSEG 1 whose loader inputs c_ctx / c_ctxld are driven by the
//            leaf (force: the 129-b cluster input that MU-QW-DIE owes; the image DW5 / DW6 record is plain 0 here).
// The ctlm part is tb_mu_opseg_dv (rtl/test/mu_qwen_seq, MU-QW-B1) unchanged: same events 0..3 and log lines, so
// mu_opseg_bench.check_case runs on it.  Extra events (+EV "cycle kind hex", applied before posedge `cycle`):
//   4 KEP  epoch16: token_epoch_valid for one edge (both ports when epoch[1:0] == 0, else the MU port only)
//   5 KREQ {gen2 [60:59], tag59}: request_v (token = tag[36:19], position = tag[18:6]); same routing by tag[44:43]
//   6 KPAIR: the token run's compiled context slot pair: send_kind 3 at this edge (MU slot) and the next (user-0 slot);
//          the reference port gets send_kind 3 on the next edge only (the single-user calendar's slot)
//   7 KCAL (CAL 1): token-run calendar start (segment 1) of BOTH link-end calendars (see CAL below)
//   8 KHALT (CAL 1): stop both calendars (the bench plays only the token-run prefix that carries the context pair)
// CAL 1 (MU-DQ-SYSFACE 2026-10-19, the default of mu_kvctx_bench.py): the pair is no longer a bench edge pair.  The
//   compute face's REAL sequencer qfd_d2d_cal_seq and the KV die's qkd_d2d_cal_seq (ot_qwen_d2d_cal_seq_dies_mu.sv = the
//   MU image d2d_cal_image_mu.svh, as built into the qfd_sys_face MU kit) write their images through their cfg ports
//   into the link ends' REAL calendar playback ot_qwen_d2d_cal: the C end's RX calendar and the KV end's TX calendar.
//   The bench then loads the token-run segment-1 base (the sequencer does that only after an epoch's admission run, at
//   edge 1172 of the epoch; this ctlm schedule needs the pairs before S0 = 1100) and starts both calendars on one edge
//   (KCAL), as the two dies' anchored token starts do.  KV TX events port 1 kind 12 drive the MU port's send_kind 3
//   (both beats; the reference MU 0 port only on beat 0 = the single-user slot); C RX events port 1 kind 12 become
//   the face's prog_context_slot 2 edges later (ot_qwen_d2d_static_end rx_slot = r1v registered; qfd_d2d_static
//   prog_context_slot = rxs[1] && kind 12).  The link is the compiled fixed latency LINK = C pin arrival - K TX slot
//   (16 in the production image, die stages incl. pin registers); the words are NOT aligned by the bench: a C image
//   without the MU slot, or a slot one edge off, makes the face receiver fault (rx_v != slot).
//   CMUT 1: the compute face's sequencer image is the MU 0 image (CRX_MU0, the committed d2d_cal_image.svh C RX
//   entries) = a qfd_sys_face kit built without the MU image; it must FAIL.
// Extra log: "c KTX obs tag" (MU port word), "c KID BAD ..." (reference word != MU port word on a reference edge),
//   "c KIDN n" (reference edges compared, at END), "c FRX tag fault" (face receiver after each received slot),
//   "c CTXLD user tok pos" (leaf load), "c KEND kv_mu kv_ref face leaf" (sticky faults at END),
//   CAL 1: "c KCALEND cseq kseq crx_cal ktx_cal n_ktx_ctx n_crx_ctx" (sequencer / calendar faults + context events).
module tb_mu_kvctx;
    parameter integer NU = 4, MUT = 0, OPSEG = 1, KMUT = 0, RMUT = 0, LINK = 14;
    parameter integer CAL = 0, CMUT = 0;
    parameter [31:0] CRX_SEG1 = 32'd0, KTX_SEG1 = 32'd0;     // token-run segment-1 bases (the images' D2D_CAL_*_SEG1)
    parameter [1023:0] CRX_MU0 = 1024'd0;                   // CMUT 1: the MU 0 C RX image
    reg ck = 1'b0;
    always #5 ck = ~ck;
    reg rst_n = 1'b0;
    reg [74:0] pw = 0; reg [186:0] dh = 0; reg [1:0] dh_user = 0; reg [106:0] ss5 = 0;
    wire [452:0] hr; wire [115:0] cmd; wire emb_start; wire [17:0] emb_token; wire [55:0] dc; wire cf;
    wire [75:0] pobs, cobs; wire [68:0] dobs; wire csr, cir, lcv; wire [17:0] ntk, nps; wire [5:0] cst; wire [379:0] ncmd;
    qfd_tt_ctlm_dv #(.XPF_TRANSPORT_EDGES(1), .MUT(MUT), .NU(NU), .STAGE_ME(1), .OPSEG(OPSEG)) dut (.ck(ck), .rst_n(rst_n),
        .pw(pw), .dh(dh), .dh_user(dh_user), .kok(1'b0), .kwd(1'b1), .fab(1'b0), .program_obs(pobs),
        .control_stores_ready(csr), .layer_context_v(lcv), .native_tok(ntk), .native_pos(nps), .command_stage(cst),
        .cal_program_obs(cobs), .cal_descriptor_obs(dobs), .cal_image_ready(cir), .dc(dc), .native_cmd(ncmd),
        .native_ret(95'd0), .hr(hr), .cmd(cmd), .ss5(ss5), .ag5(10'd0), .emb_start(emb_start), .emb_token(emb_token),
        .cf(cf));

    // ------------------------------------------------------------------ KV die: host record ports
    localparam [15:0] PEP = 16'h0A51;  localparam [63:0] PDG = 64'h0123_4567_89AB_CDEF;
    reg  [1:0]  sk_mu_b = 0, sk_ref_b = 0;
    wire [1:0]  sk_mu, sk_ref;   // the record ports' send slots (CAL 1: from the KV TX calendar, below)
    reg         tev_mu = 0, tev_ref = 0, rq_mu = 0, rq_ref = 0;
    reg  [15:0] tep = 0; reg [58:0] rtag = 0; reg [1:0] rgen = 0;
    wire        m_tv, m_to, m_f, r_tv, r_to, r_f;
    wire [547:0] m_tr, r_tr;
    qkd_host_record_port_mu #(.MU(1), .MUT(KMUT)) kv_mu (.ck(ck), .rst_n(rst_n), .send_kind(sk_mu),
        .request_v(rq_mu), .request_tag(rtag), .request_gen(rgen), .request_token(rtag[36:19]), .request_position({5'd0, rtag[18:6]}),
        .token_epoch_valid(tev_mu), .token_epoch(tep), .begin_v(1'b0), .begin_epoch(16'd0), .expected_pw(11'd0), .expected_dw(4'd0),
        .auth_v(1'b0), .auth_epoch(16'd0), .auth_digest(64'd0), .program_ready(1'b1), .program_epoch(PEP), .program_digest(PDG),
        .authorized_footer_valid(1'b0), .authorized_footer(64'd0), .witness_slot(1'b0), .rx_v(1'b0), .rx_record(548'd0),
        .commit_v(), .installed_valid(), .installed_fusedcap(), .commit_epoch(), .commit_digest(),
        .tx_v(m_tv), .tx_observed_v(m_to), .tx_record(m_tr), .fault(m_f));
    qkd_host_record_port_mu #(.MU(0)) kv_ref (.ck(ck), .rst_n(rst_n), .send_kind(sk_ref),
        .request_v(rq_ref), .request_tag(rtag), .request_gen(rgen), .request_token(rtag[36:19]), .request_position({5'd0, rtag[18:6]}),
        .token_epoch_valid(tev_ref), .token_epoch(tep), .begin_v(1'b0), .begin_epoch(16'd0), .expected_pw(11'd0), .expected_dw(4'd0),
        .auth_v(1'b0), .auth_epoch(16'd0), .auth_digest(64'd0), .program_ready(1'b1), .program_epoch(PEP), .program_digest(PDG),
        .authorized_footer_valid(1'b0), .authorized_footer(64'd0), .witness_slot(1'b0), .rx_v(1'b0), .rx_record(548'd0),
        .commit_v(), .installed_valid(), .installed_fusedcap(), .commit_epoch(), .commit_digest(),
        .tx_v(r_tv), .tx_observed_v(r_to), .tx_record(r_tr), .fault(r_f));
    // NOTE: installed_fusedcap of a port without a witness is 0; the face below compares the record's cap bit with ITS
    // installed cap, so the compute side is given the same value (0): the record is accepted on image epoch / digest.

    // ------------------------------------------------------------------ static D2D link: fixed latency
    reg  [LINK-1:0] lv = 0, lo = 0; reg [547:0] lr [0:LINK-1];
    reg  [LINK+1:0] sl = 0;                      // the compiled RX slot: KV send slot + 2 port edges + LINK
    integer li;
    always @(posedge ck) begin
        lv <= {lv[LINK-2:0], m_tv}; lo <= {lo[LINK-2:0], m_to}; lr[0] <= m_tr;
        for (li = 1; li < LINK; li = li + 1) lr[li] <= lr[li - 1];
        sl <= {sl[LINK:0], sk_mu == 2'd3};
    end
    // ---- CAL 1: the two link ends' real sequencers + calendar playback (see the header)
    reg          kcal = 0, khalt = 0, bwe = 0;
    wire         cs_txwe, cs_rxwe, ks_txwe, ks_rxwe, cs_f, ks_f, cs_rdy, ks_rdy;
    wire [5:0]   cs_a, ks_a; wire [31:0] cs_d, ks_d;
    qfd_d2d_cal_seq u_cseq (.ck(ck), .rst_n(rst_n), .reload(1'b0), .tok_go(1'b0), .epoch_go(1'b0), .halt(1'b0),
        .cfg_tx_we(cs_txwe), .cfg_rx_we(cs_rxwe), .cfg_addr(cs_a), .cfg_data(cs_d), .cal_start(), .cal_seg(),
        .cal_ready(cs_rdy), .running(), .layer(), .adm_done(), .tok_start(), .fault(cs_f));
    qkd_d2d_cal_seq u_kseq (.ck(ck), .rst_n(rst_n), .reload(1'b0), .tok_go(1'b0), .epoch_go(1'b0), .halt(1'b0),
        .cfg_tx_we(ks_txwe), .cfg_rx_we(ks_rxwe), .cfg_addr(ks_a), .cfg_data(ks_d), .cal_start(), .cal_seg(),
        .cal_ready(ks_rdy), .running(), .layer(), .adm_done(), .tok_start(), .fault(ks_f));
    // C RX cfg: the face sequencer's writes (CMUT 1: the same writes carrying the MU 0 image's entries); bwe = the bench's
    // token-run base write (cfg_addr[5] = 1), on an edge where both sequencers are idle (after cal_ready)
    wire [31:0]  crx_d = bwe ? CRX_SEG1 : (CMUT == 1 && !cs_a[5]) ? CRX_MU0[32 * cs_a[4:0] +: 32] : cs_d;
    wire         crv, ktv, crf, ktf, crr, ktr; wire [2:0] crp, ktp; wire [3:0] crk, ktk; wire [4:0] crb, ktb;
    ot_qwen_d2d_cal #(.NE(32)) u_crx (.ck(ck), .rst_n(rst_n), .cfg_we(cs_rxwe | bwe), .cfg_addr(bwe ? 6'h20 : cs_a),
        .cfg_data(crx_d), .start(kcal), .start_seg(1'b1), .halt(khalt), .ev_v(crv), .ev_port(crp), .ev_kind(crk),
        .ev_beat(crb), .running(crr), .fault(crf));
    ot_qwen_d2d_cal #(.NE(32)) u_ktx (.ck(ck), .rst_n(rst_n), .cfg_we(ks_txwe | bwe), .cfg_addr(bwe ? 6'h20 : ks_a),
        .cfg_data(bwe ? KTX_SEG1 : ks_d), .start(kcal), .start_seg(1'b1), .halt(khalt), .ev_v(ktv), .ev_port(ktp),
        .ev_kind(ktk), .ev_beat(ktb), .running(ktr), .fault(ktf));
    wire         k_ctx = ktv && ktp == 3'd1 && ktk == 4'd12;          // KV TX: the record port's context send slot
    wire         c_ctx_ev = crv && crp == 3'd1 && crk == 4'd12;       // C RX: a context arrival (pin edge r)
    // CAL 1: the KV TX calendar's context events are the send slots (MU port: both beats; MU 0 reference: beat 0 only)
    assign      sk_mu  = CAL ? (k_ctx ? 2'd3 : 2'd0) : sk_mu_b;
    assign      sk_ref = CAL ? ((k_ctx && ktb == 5'd0) ? 2'd3 : 2'd0) : sk_ref_b;
    reg  [1:0]   cr_sl = 0;                                          // ot_qwen_d2d_static_end: rx_slot at r + 2
    always @(posedge ck) cr_sl <= {cr_sl[0], c_ctx_ev};
    integer nk_ctx = 0, nc_ctx = 0;
    always @(posedge ck) if (rst_n) begin if (k_ctx) nk_ctx <= nk_ctx + 1; if (c_ctx_ev) nc_ctx <= nc_ctx + 1; end
    wire         c_slot = CAL ? cr_sl[1] : sl[LINK + 1];
    wire         c_rxv  = lo[LINK - 1];          // the D2D end delivers an OBSERVED word only (tx_valid = observed)
    wire [547:0] c_rec  = lr[LINK - 1];

    // ------------------------------------------------------------------ compute die: face context RX + MU leaf
    wire        h_ev, h_cap, h_f; wire [15:0] h_ep, h_iep; wire [58:0] h_tag; wire [1:0] h_gen; wire [63:0] h_idg;
    qfd_host_native_context_rx face_rx (.ck(ck), .rst_n(rst_n), .receive_slot(c_slot), .rx_v(c_rxv), .rx_record(c_rec),
        .program_begin_v(1'b0), .program_ready(1'b1), .installed_fusedcap(1'b0), .program_epoch(PEP), .program_digest(PDG),
        .head_context_v(1'b0), .head_stage(6'd0), .head_token(18'd0), .head_position(18'd0), .native_active(1'b0),
        .host_epoch_valid(h_ev), .host_epoch(h_ep), .host_tag(h_tag), .host_gen(h_gen), .host_fusedcap(h_cap),
        .host_image_epoch(h_iep), .host_image_digest(h_idg), .fault(h_f));
    wire [128:0] ctx_x; wire [1:0] ctx_u; wire x_f;
    qfd_mu_ctx_rx #(.NU(NU), .MUT(RMUT)) mu_rx (.ck(ck), .rst_n(rst_n), .context_slot(c_slot), .rx_v(c_rxv),
        .rx_hdr(c_rec[547:517]), .rx_beat(c_rec[516:512]), .rx_tag(c_rec[58:0]), .ctx_x(ctx_x), .ctx_user(ctx_u), .mu_fault(x_f));
    // the ctlm loader takes the leaf's record (the proposed cluster input; see the header)
    initial begin
        force dut.c_ctx = ctx_x[127:0];
        force dut.c_ctxld = ctx_x[128];
    end

    // ------------------------------------------------------------------ driver + log (tb_mu_opseg_dv + KV events)
    wire [1024:0] hd = {hr, ncmd, ntk, nps, cst, lcv, csr, pobs, cf};
    reg  [1024:0] hd_l = 0;
    integer fd, lg, cyc, ncyc, ec, ek, r, pre = 0, kidn = 0;
    reg [186:0] ev; reg have; reg [1023:0] evf, lgf; reg flt_l = 0; reg [23:0] sua_l = 0; reg [5:0] cst_l = 0;
    reg [55:0] dc_l = 0; reg opf_l = 0; reg [3:0] lfc_l = 0; reg [1:0] eu_l = 0, su_l = 0;
    reg pair2 = 0, cslot_l = 0;
    // C8 (MU-DQ-D2DUSER) probe, identical to tb_mu_opseg_dv.sv: native_pos[17:16] = the user of the latest head start
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
            if (dut.st_h) begin
                xu_l = sg_l ? su_l : 2'd0;
                if (xu_l == 2'd1) cu_n1 = cu_n1 + 1; if (xu_l == 2'd2) cu_n2 = cu_n2 + 1; if (xu_l == 2'd3) cu_n3 = cu_n3 + 1;
            end
            if (nps[17:16] !== ((NU > 1) ? xu_l : 2'd0)) begin
                cu_bad = cu_bad + 1;
                if (cu_bad <= 3) $fdisplay(lg, "%0d CTXU_ERR carried %0d want %0d", cyc, nps[17:16], xu_l);
            end
            sg_l = dut.c_seg;
            // KV / link / compute-leaf observations (this posedge)
            if (m_tv) $fdisplay(lg, "%0d KTX %0d %h", cyc, m_to, m_tr[58:0]);
            if (r_tv) begin
                kidn = kidn + 1;
                if (!m_tv || m_to !== r_to || m_tr !== r_tr)
                    $fdisplay(lg, "%0d KID BAD mu %0d %0d %h ref %0d %h", cyc, m_tv, m_to, m_tr[58:0], r_to, r_tr[58:0]);
            end
            if (cslot_l) $fdisplay(lg, "%0d FRX %h %0d %0d", cyc, h_tag, h_ev, h_f);
            cslot_l = c_slot;
            if (ctx_x[128]) $fdisplay(lg, "%0d CTXLD %0d %h %h", cyc, ctx_u, ctx_x[36 * (ctx_u - 1) + 18 +: 18], ctx_x[36 * (ctx_u - 1) +: 18]);
            cst_l = cst; dc_l = dc; opf_l = dut.op_fault; lfc_l = dut.l_fcode;
            flt_l = dut.u_cal.fault; sua_l = dut.su_acc; hd_l = hd;
            if (dut.c_emb) eu_l = dut.c_user;
            if (dut.c_seg) su_l = dut.c_user;
            // inputs for the next posedge (cyc + 1)
            pw[74] = 1'b0; dh[118] = 1'b0; dh[186] = 1'b0; dh[42] = 1'b0; ss5 = 107'd0;
            tev_mu = 0; tev_ref = 0; rq_mu = 0; rq_ref = 0;
            sk_mu_b = pair2 ? 2'd3 : 2'd0; sk_ref_b = pair2 ? 2'd3 : 2'd0; pair2 = 0;
            kcal = 0; khalt = 0; bwe = 0;
            if (CAL && cyc + 1 == 150) begin
                if (!cs_rdy || !ks_rdy) $fatal(1, "sequencer images not loaded by edge 150");
                bwe = 1;
            end
            while (have && ec == cyc + 1) begin
                case (ek)
                    0: begin pw = {1'b1, ev[73:0]}; dh[118:44] = {1'b1, ev[73:0]}; end
                    1: dh[186:119] = {1'b1, ev[66:0]};
                    2: begin dh[42:0] = ev[42:0]; dh_user = ev[44:43]; end
                    3: begin ss5[24] = 1'b1; ss5[17:0] = ev[17:0]; ss5[27:26] = ev[43:42]; ss5[97:74] = ev[41:18]; end
                    4: begin tep = ev[15:0]; tev_mu = 1; tev_ref = (ev[1:0] == 2'd0); end
                    5: begin rtag = ev[58:0]; rgen = ev[60:59]; rq_mu = 1; rq_ref = (ev[44:43] == 2'd0); end
                    6: begin if (CAL) $fatal(1, "KPAIR in CAL mode"); sk_mu_b = 2'd3; pair2 = 1; end
                    7: begin if (!CAL) $fatal(1, "KCAL needs CAL 1"); kcal = 1; end
                    8: begin if (!CAL) $fatal(1, "KHALT needs CAL 1"); khalt = 1; end
                    default: $fatal(1, "bad kind %0d", ek);
                endcase
                r = $fscanf(fd, "%d %d %h\n", ec, ek, ev); have = (r == 3);
            end
            if (have && ec <= cyc) $fatal(1, "event file not sorted at cycle %0d", ec);
            cyc = cyc + 1;
            if (cyc >= ncyc) begin
                $fdisplay(lg, "%0d CTXU %0d %0d %0d %0d", cyc, cu_bad, cu_n1, cu_n2, cu_n3);
                $fdisplay(lg, "%0d KIDN %0d", cyc, kidn);
                $fdisplay(lg, "%0d KEND %0d %0d %0d %0d", cyc, m_f, r_f, h_f, x_f);
                if (CAL) $fdisplay(lg, "%0d KCALEND %0d %0d %0d %0d %0d %0d", cyc, cs_f, ks_f, crf, ktf, nk_ctx, nc_ctx);
                $fdisplay(lg, "%0d END %0d %b %0d %0d %b", cyc, dut.u_cal.fault, dut.u_cal.fault_code, dut.start_fault,
                          dut.op_fault, dut.l_fcode);
                $fclose(lg);
                $finish;
            end
        end
    end
endmodule
