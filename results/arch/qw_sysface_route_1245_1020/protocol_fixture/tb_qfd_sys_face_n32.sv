`timescale 1ns/1ps
// Q-NETLIST 2026-10-16: component bench of the compute-die system face qfd_sys_face + the word-level embedding provider
// qfd_embedding_word_provider (both die masters, real RTL; ROM = the ot_rom_4096x72_m8 functional model loaded with the
// compiler via map of tools/qwen_split/sys_face_image.py).
// Declared external stimuli at this component boundary: the KV/system-die side of the link records (produced by the REAL
// KV-side encoders qkd_program_auth_tx / qkd_host_native_context_tx; the D2D slot link is a wire), the KV-die embedding
// row words (header + 64 code words at their compiled RX cycles), the sequencer dc level, and the TT/SU program-store
// consumed-write observers (bench vehicle: the actual pw/dw pins registered one edge, sealed after DW7).
// Checks (exact): (1) every boot record reaches its target in ROM order (D2D cfg port + the three face calendars);
// (2) the BEGIN/AUTH-triggered replay writes PW0..1023 / DW0..7 bit-exact, both ledgers commit, the kind-14 witness is
// accepted by the real KV-side witness receiver with the compiler digest; (3) every compiled event (T/L/E) reaches its
// consumer pin on exactly its compiled cycle and no other event fires; (4) the embedding row lands bit-exact in the
// provider SRAM and scale register; (5) RESULT carries the sequencer's argmax and the token loop feeds it to dh;
// (6) no fault anywhere.  MUT 1/2/3 (face parameter) and 4 (D2D sequencer layer-5 start +1: the face must flag the
// calendar disagreement) must FAIL.  MUT 5: a one-edge embedding-provider fault pulse must reach the face fault and FAIL.
// MU 1 (MU-DQ-SYSFACE 2026-10-19, run_sys_face_bench.sh D2D_MU=1): the face is built #(MU 1) with the MU D2D image; after
// the HOST context lands, the ctlm head drives layer contexts of user 0 (the HOST token / position, stage 2) and of the
// fillers 1..3 (user on tt_native_pos[17:16], their own token / position, stages 3..5): (7) none may fault.
// MUT 6 (MU 1): the face checks filler contexts against the HOST tag (the closed MU 0 face) -> FAIL; MUT 7 (MU 1, bench):
// a filler context at position 8192 (pos[15:13] != 0) -> FAIL.
module tb_qfd_sys_face;
    initial if(MU!=1) $fatal(1,"SYSFACE32 protocol proof requires production MU1");
    parameter integer MUT = 0;
    parameter integer MU = 0;
    parameter integer MU_HEAD = 1;   // ROOT4-SYSFACE 10-19: the die binds qfd_sys_face MU 1 MU_HEAD 1 (die_params MU-DQ-BOOTCTX)
    parameter IMG = "img";
    reg ck = 0; always #0.4167 ck = ~ck;
    reg rst_n = 0;
    integer cyc = 0; always @(posedge ck) cyc <= cyc + 1;
    integer errs = 0;
    task automatic err(input [8*96-1:0] msg); begin errs = errs + 1; if (errs < 20) $display("ERR @%0d %0s", cyc, msg); end endtask

    // ---------------- expected image ----------------
    reg [63:0] prog [0:1031];
    reg [43:0] wexp [0:255];
    integer nexp;
    initial begin
        for (nexp = 0; nexp < 256; nexp = nexp + 1) wexp[nexp] = 44'hfffffffffff;  // file shorter than 256: sentinel
        $readmemh({IMG, "/program.memh"}, prog);
        $readmemh({IMG, "/cfg_writes.memh"}, wexp);
        nexp = 0; while (nexp < 256 && wexp[nexp] !== 44'hfffffffffff) nexp = nexp + 1;
    end

    // ---------------- DUT + provider ----------------
    wire cfg_tx_we, cfg_rx_we, cal_start, cal_seg; wire [5:0] cfg_addr; wire [31:0] cfg_data;
    reg  [547:0] rx_payload = 0; reg prog_rx_v = 0, prog_auth_slot = 0, prog_context_slot = 0, prog_witness_slot = 0;
    reg  emb_rx_v = 0;
    wire prog_tx_ov; wire [547:0] prog_tx_rec;
    wire [15:0] st_ep; wire vmd, cod, cob, crf, exa, adm, rv, rd, rf; wire [3:0] rc; wire [58:0] rt; wire [1:0] rg;
    wire [17:0] rtok; wire [31:0] rval, rcyc;
    reg  [55:0] seq_dc = 0;
    reg  [75:0] seq_obs = 0, tt_obs = 0; reg [68:0] dsc_obs = 0; reg seq_rdy = 0, tt_rdy = 0;
    wire [186:0] dh; wire [74:0] tt_pw; wire kok, kwd, fab;
    wire hev, hcap; wire [15:0] hep; wire [58:0] htag; wire [1:0] hgen;
    wire qs, kvs, vis, cpl; wire [4:0] qb; wire [1:0] kvi;
    wire ew_v, ew_s, ex_s, ex_sc, fb; wire [511:0] ew_d; wire [17:0] ew_t, ex_t, f_t; wire [5:0] ew_i, ex_w; wire [15:0] ew_e, ex_e, f_e, c_e;
    wire face_fault;
    reg fwd_epoch = 0;
    reg hc_v = 0; reg [5:0] hc_st = 0; reg [17:0] hc_tok = 0, hc_pos = 0; integer n_hc = 0;
    // MUT 5 (Q-STUB 10-17): one-edge provider fault pulse after reset -- the face must latch it (face_fault / fab) and FAIL
    wire prov_fault; reg prov_inj = 0; integer rel_cyc = -1;
    always @(posedge ck) begin if (rst_n && rel_cyc < 0) rel_cyc = cyc; prov_inj <= (MUT == 5) && rel_cyc >= 0 && cyc == rel_cyc + 50; end
    // FUNCTIONAL ADAPTER ONLY: these aliases are not physical producer copies.
    wire [34:0] protocol_only_pin_aliases;
    assign protocol_only_pin_aliases[0] = prog_auth_slot;
    assign protocol_only_pin_aliases[1] = prog_witness_slot;
    assign protocol_only_pin_aliases[2] = prog_witness_slot;
    assign protocol_only_pin_aliases[3] = prog_witness_slot;
    assign protocol_only_pin_aliases[4] = prog_witness_slot;
    assign protocol_only_pin_aliases[5] = prog_witness_slot;
    assign protocol_only_pin_aliases[6] = prog_witness_slot;
    assign protocol_only_pin_aliases[7] = prog_witness_slot;
    assign protocol_only_pin_aliases[8] = prog_witness_slot;
    assign protocol_only_pin_aliases[9] = prog_witness_slot;
    assign protocol_only_pin_aliases[10] = prog_witness_slot;
    assign protocol_only_pin_aliases[11] = dsc_obs[68];
    assign protocol_only_pin_aliases[12] = dsc_obs[68];
    assign protocol_only_pin_aliases[13] = dsc_obs[68];
    assign protocol_only_pin_aliases[14] = dsc_obs[68];
    assign protocol_only_pin_aliases[15] = dsc_obs[68];
    assign protocol_only_pin_aliases[16] = dsc_obs[68];
    assign protocol_only_pin_aliases[17] = dsc_obs[68];
    assign protocol_only_pin_aliases[18] = dsc_obs[68];
    assign protocol_only_pin_aliases[19] = dsc_obs[68];
    assign protocol_only_pin_aliases[20] = dsc_obs[68];
    assign protocol_only_pin_aliases[21] = prog_context_slot;
    assign protocol_only_pin_aliases[22] = prog_context_slot;
    assign protocol_only_pin_aliases[23] = prog_auth_slot;
    assign protocol_only_pin_aliases[24] = prog_auth_slot;
    assign protocol_only_pin_aliases[25] = dsc_obs[68];
    assign protocol_only_pin_aliases[26] = dsc_obs[68];
    assign protocol_only_pin_aliases[27] = prog_auth_slot;
    assign protocol_only_pin_aliases[28] = dsc_obs[68];
    assign protocol_only_pin_aliases[29] = tt_obs[75];
    assign protocol_only_pin_aliases[30] = seq_obs[75];
    assign protocol_only_pin_aliases[31] = prog_auth_slot;
    assign protocol_only_pin_aliases[32] = dsc_obs[68];
    assign protocol_only_pin_aliases[33] = prog_auth_slot;
    assign protocol_only_pin_aliases[34] = dsc_obs[68];
    qfd_sys_face_core_n32 #(.MUT((MUT == 4 || MUT == 5 || MUT == 7) ? 0 : MUT), .MU(MU), .MU_HEAD(MU_HEAD), .GO_OFS(GO_OFS), .START_ADJ(MUT == 4 ? (720'd1 << (20 * 5)) : 720'd0), .ROM_VIAMAP({IMG, "/sys_face_cfg.viamap.hex"})) u_dut (.pin_source_copies(protocol_only_pin_aliases), 
        .ck(ck), .rst_n(rst_n),
        .cfg_tx_we(cfg_tx_we), .cfg_rx_we(cfg_rx_we), .cfg_addr(cfg_addr), .cfg_data(cfg_data), .cal_start(cal_start), .cal_seg(cal_seg), .fwd_epoch(fwd_epoch),
        .rx_payload(rx_payload), .prog_rx_v(prog_rx_v), .prog_witness_slot(prog_witness_slot), .prog_auth_slot(prog_auth_slot),
        .prog_context_slot(prog_context_slot), .prog_tx_observed_v(prog_tx_ov), .prog_tx_record(prog_tx_rec),
        .emb_rx_v(emb_rx_v), .emb_rx_slot(emb_rx_v), .d2d_fault(1'b0), .d2d_epoch_abort(1'b0),
        .status_epoch16(st_ep), .vm_drained(vmd), .collective_drained(cod), .collective_busy(cob), .crom_fault(crf),
        .execution_active(exa), .admit_ready(adm), .result_v(rv), .result_done(rd), .result_fault(rf), .result_cause(rc),
        .result_tag(rt), .result_gen(rg), .result_token(rtok), .result_value(rval), .result_cycles(rcyc),
        .seq_dc(seq_dc), .seq_program_obs(seq_obs), .seq_descriptor_obs(dsc_obs), .seq_cfg_image_ready(seq_rdy), .seq_dh(dh),
        .tt_program_obs(tt_obs), .tt_control_stores_ready(tt_rdy), .tt_layer_context_v(hc_v), .tt_command_stage(hc_st),
        .tt_native_tok(hc_tok), .tt_native_pos(hc_pos), .tt_pw(tt_pw), .tt_kok(kok), .tt_kwd(kwd), .tt_fab(fab),
        .host_epoch_valid(hev), .host_fused_capability(hcap), .host_epoch(hep), .host_tag(htag), .host_generation(hgen),
        .q_slot(qs), .q_slot_beat(qb), .kv_word_slot(kvs), .kv_word_index(kvi), .visibility_slot(vis), .complete_slot(cpl),
        .native_fault(1'b0),
        .emb_word_v(ew_v), .emb_word_data(ew_d), .emb_word_token(ew_t), .emb_word_index(ew_i), .emb_word_scale(ew_s),
        .emb_word_epoch(ew_e), .emb_expected_slot(ex_s), .emb_expected_token(ex_t), .emb_expected_word(ex_w),
        .emb_expected_scale(ex_sc), .emb_expected_epoch(ex_e), .emb_fill_begin(fb), .emb_fill_token(f_t), .emb_fill_epoch(f_e),
        .emb_core_epoch(c_e), .emb_prov_fault(prov_fault | prov_inj), .io_cmd_free(1'b1), .io_fault(1'b0), .io_shared_fault(1'b0),
        .fault(face_fault));
    reg core_start = 0, code_re = 0, scale_re = 0; reg [23:0] code_addr = 0; reg [17:0] scale_addr = 0;
    wire [511:0] code_q; wire [15:0] scale_q;
    qfd_embedding_word_provider u_prov (.ck(ck), .rst_n(rst_n), .word_v(ew_v), .word_data(ew_d), .word_token(ew_t),
        .word_index(ew_i), .word_scale(ew_s), .word_epoch(ew_e), .expected_word_slot(ex_s), .expected_token(ex_t),
        .expected_word(ex_w), .expected_scale(ex_sc), .expected_epoch(ex_e), .fill_begin(fb), .fill_token(f_t), .fill_epoch(f_e),
        .core_start(core_start), .core_token(scale_addr), .core_epoch(c_e), .embed_code_re(code_re), .embed_code_addr(code_addr),
        .embed_code_q(code_q), .embed_scale_re(scale_re), .embed_scale_addr(scale_addr), .embed_scale_q(scale_q), .fault(prov_fault));

    // ---------------- (1) boot records in ROM order ----------------
    integer wi = 0;
    always @(posedge ck) if (rst_n) begin : boot_mon
        reg [3:0] t; reg [7:0] a; reg [31:0] d; reg any;
        any = 1; t = 0; a = 0; d = 0;
        if (u_dut.t_we) begin t = 3; a = u_dut.c_addr; d = u_dut.c_data; end
        else if (u_dut.l_we) begin t = 4; a = u_dut.c_addr; d = u_dut.c_data; end
        else if (u_dut.e_we) begin t = 5; a = u_dut.c_addr; d = u_dut.c_data; end
        else any = 0;
        if (any) begin
            while (wi < nexp && wexp[wi][43:40] == 4'd6) begin           // first-token offset: a register, checked below
                if (u_dut.first_ofs !== wexp[wi][31:0] && u_dut.boot_done) err("first-token offset");
                wi = wi + 1;
            end
            if (wi >= nexp || {t, a, d} !== wexp[wi]) err("boot record mismatch");
            wi = wi + 1;
        end
    end

    // ---------------- TT / SU program-store observers (bench vehicle) ----------------
    integer pw_seen = 0, dw_seen = 0;
    always @(posedge ck) begin
        tt_obs <= {tt_pw[74], 1'b1, tt_pw[73:0]};
        seq_obs <= {dh[118], 1'b1, dh[117:44]};
        dsc_obs <= {dh[186], 1'b1, dh[185:119]};
        if (tt_pw[74]) begin
            if (tt_pw[73:64] != pw_seen[9:0] || tt_pw[63:0] !== prog[pw_seen] || dh[118] !== 1'b1 || dh[107:44] !== prog[pw_seen])
                err("PW replay word mismatch");
            pw_seen = pw_seen + 1;
        end
        if (dh[186]) begin
            if (dh[185:183] != dw_seen[2:0] || dh[182:119] !== prog[1024 + dw_seen]) err("DW replay word mismatch");
            dw_seen = dw_seen + 1;
            if (dw_seen == 8) begin seq_rdy <= 1; tt_rdy <= 1; end
        end
    end

    // ---------------- KV-side record encoders (real RTL) ----------------
    reg [63:0] digest; reg [63:0] footer;
    reg a_begin = 0, a_auth = 0, a_send = 0; reg [1:0] a_type = 0;
    wire a_tv, a_ov, a_f; wire [547:0] a_rec;
    qkd_program_auth_tx u_atx (.ck(ck), .rst_n(rst_n), .send_slot(a_send), .send_type(a_type), .begin_v(a_begin),
        .begin_epoch(16'h0b0b), .expected_pw(11'd1024), .expected_dw(4'd8), .auth_v(a_auth), .auth_epoch(16'h0b0b),
        .auth_digest(digest), .tx_v(a_tv), .tx_observed_v(a_ov), .tx_record(a_rec), .fault(a_f));
    reg c_req = 0, c_send = 0;
    wire c_tv, c_ov, c_f; wire [547:0] c_rec;
    localparam [17:0] TOK0 = 18'd1234, POS0 = 18'd55; localparam [15:0] TEP = 16'h0c0c;
    qkd_host_native_context_tx u_ctx (.ck(ck), .rst_n(rst_n), .send_slot(c_send), .request_v(c_req),
        .request_tag({TEP, 6'd0, TOK0, POS0[12:0], 6'd0}), .request_gen(2'd1), .request_token(TOK0), .request_position(POS0),
        .token_epoch_valid(1'b1), .token_epoch(TEP), .program_ready(1'b1), .installed_fusedcap(1'b1),
        .program_epoch(16'h0b0b), .program_digest(digest), .tx_v(c_tv), .tx_observed_v(c_ov), .tx_record(c_rec), .fault(c_f));
    reg [547:0] emb_word_drv = 0;
    // the link: a KV record sent in slot c is the compute end's checked RX word in its compiled slot (bench: next edge)
    always @* begin
        prog_rx_v = a_ov | c_ov; prog_auth_slot = a_tv; prog_context_slot = c_tv;
        rx_payload = a_tv ? a_rec : c_tv ? c_rec : emb_word_drv;
    end
    reg w_rslot = 0; always @(posedge ck) w_rslot <= prog_witness_slot;
    wire w_commit, w_inst, w_cap, w_f; wire [15:0] w_ep; wire [63:0] w_dg;
    qkd_program_witness_rx u_wrx (.ck(ck), .rst_n(rst_n), .program_begin_v(a_begin), .receive_slot(w_rslot), .rx_v(prog_tx_ov),
        .rx_record(prog_tx_rec), .expected_epoch(16'h0b0b), .expected_digest(digest), .authorized_footer_valid(1'b1),
        .authorized_footer(footer), .program_commit_v(w_commit), .program_commit_epoch(w_ep), .program_commit_digest(w_dg),
        .program_installed_valid(w_inst), .installed_fusedcap(w_cap), .fault(w_f));

    // ---------------- (3) compiled event trace ----------------
    // expected pin edges relative to the edge that samples the T start (t0; the bench observes a pin one edge after it is
    // set, hence cyc - t0 - 1); L / E events relative to the pin edge of the T STAGE event that starts them.  The list is
    // generated from the same events JSON as the ROM image (run_sys_face_bench.sh), with LEVEL events kept only where
    // the kok / kwd level changes.
    integer t0 = -1, n_ev = 0, ev_t [0:4095], ev_k [0:4095], ev_a [0:4095], ev_seen [0:4095];
    integer i, j;
    task automatic add(input integer t, input integer k, input integer a);
        begin ev_t[n_ev] = t; ev_k[n_ev] = k; ev_a[n_ev] = a; ev_seen[n_ev] = 0; n_ev = n_ev + 1; end
    endtask
    `include "tb_qfd_sys_face_events.svh"
    // observed events at the face pins, as (class, arg)
    task automatic seen(input integer k, input integer a);
        integer m, hit; begin
            hit = 0;
            for (m = 0; m < n_ev; m = m + 1)
                if (!hit && ev_seen[m] == 0 && ev_k[m] == k && ev_a[m] == a && t0 >= 0 && ev_t[m] == cyc - t0 - 1) begin ev_seen[m] = 1; hit = 1; end
            if (!hit) begin $display("  unexpected event class %0d arg %0d at T+%0d", k, a, cyc - t0 - 1); err("event off its compiled cycle"); end
        end
    endtask
    reg kok_q = 0, kwd_q = 0, trace_on = 0; integer t1 = -1, ep_cyc = -1;
    always @(posedge ck) if (fwd_epoch && ep_cyc < 0) ep_cyc = cyc;
    // admission (sequencer layer 63) and first-token D2D starts: the same compiled distance as the KV sequencer's
    integer adm_cyc = -1, tok_cyc = -1;
    always @(posedge ck) if (rst_n && cal_start) begin
        if (u_dut.cs_layer == 6'd63 && adm_cyc < 0) adm_cyc = cyc;
        else if (cal_seg && tok_cyc < 0) begin
            tok_cyc = cyc;
            if (adm_cyc < 0 || tok_cyc - adm_cyc != ADM_TO_TOKEN) begin
                $display("  admission->token %0d, compiled %0d", tok_cyc - adm_cyc, ADM_TO_TOKEN); err("first token off D2D_FIRST_TOKEN");
            end
        end
    end
    always @(posedge ck) if (rst_n) begin
        if (u_dut.t_go && t0 < 0) begin
            t0 = cyc;
            if (t0 - ep_cyc != u_dut.first_ofs) err("first token not first_token edges after the epoch strobe");
        end
        else if (u_dut.t_go && t0 >= 0 && t1 < 0) t1 = cyc;            // second token start
        if (t1 >= 0 && cyc > t1 + 1) trace_on = 0;                       // first token's pins complete
        if (trace_on) begin
            if (dh[42]) seen(0, dh[41:36]);
            if (cal_start) seen(10, cal_seg);
            if (rv) seen(9, 0);
            if (qs) seen(2, qb);
            if (kvs) seen(3, kvi);
            if (vis) seen(4, 0);
            if (cpl) seen(4, 1);
            if (ex_s) seen(6, ex_sc ? 64 : ex_w);
            if (fb) seen(7, 0);
            if (kok !== kok_q || kwd !== kwd_q) seen(1, {kwd, kok});
        end
        kok_q <= kok; kwd_q <= kwd;
    end

    // ---------------- stimulus ----------------
    reg [511:0] row [0:63]; reg [15:0] scale = 16'h3f99;
    integer w, k; reg rows_read = 0;
    initial begin
        for (w = 0; w < 64; w = w + 1) for (k = 0; k < 16; k = k + 1) row[w][k*32 +: 32] = 32'h9e3779b9 * (w * 131 + k + 7);
        digest = 64'h51484f5354505247;
        for (i = 0; i < 1032; i = i + 1) begin
            #0; digest = {digest[56:0], digest[63:57]} ^ prog[i] ^ (i < 1024 ? 64'(i) : (64'd1 << 10) | 64'(i - 1024));
        end
        footer = prog[1023];
        repeat (4) @(negedge ck); rst_n = 1;
        wait (u_dut.boot_done && u_dut.cal_ready && u_shadow_old.u_ot_pr_core.boot_done && u_shadow_old.u_ot_pr_core.cal_ready && u_shadow_new.n_4216 && u_shadow_new.n_4548); repeat (4) @(negedge ck);
        while (wi < nexp && wexp[wi][43:40] == 4'd6) begin if (u_dut.first_ofs !== wexp[wi][31:0]) err("first-token offset"); wi = wi + 1; end
        if (wi != nexp) err("boot record count");
        // epoch strobe (forwarded bump): the first token starts first_token edges later
        fwd_epoch = 1; @(negedge ck); fwd_epoch = 0;
        // BEGIN, AUTH
        a_begin = 1; @(negedge ck); a_begin = 0; a_auth = 1; @(negedge ck); a_auth = 0;
        a_type = 1; a_send = 1; @(negedge ck); a_send = 0; repeat (3) @(negedge ck);
        a_type = 2; a_send = 1; @(negedge ck); a_send = 0;
        wait (dw_seen == 8); repeat (8) @(negedge ck);
        if (pw_seen != 1024) err("PW count");
        if (!u_dut.rp_program_ready) err("program ledgers did not commit");
        prog_witness_slot = 1; @(negedge ck); prog_witness_slot = 0; repeat (3) @(negedge ck);
        if (!w_inst || w_dg !== digest) err("kind-14 witness not accepted by the KV-side receiver");
        // HOST context -> token loop
        c_req = 1; @(negedge ck); c_req = 0; repeat (2) @(negedge ck);
        trace_on = 1;
        seq_dc = {1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b1, 18'd777, 32'h0000abcd};
        c_send = 1; @(negedge ck); c_send = 0;
        wait (t0 >= 0);
        // (7) MU head contexts: user 0 = the HOST context's token / position, fillers 1..3 their own (pos[17:16] = user)
        if (MU) fork
            begin : mu_hc
                integer u;
                repeat (6) @(negedge ck);
                if (!hev) err("HOST context not valid before the head contexts");
                hc_v = 1; hc_st = 6'd2; hc_tok = TOK0; hc_pos = POS0; n_hc = n_hc + 1; @(negedge ck);
                for (u = 1; u < 4; u = u + 1) begin
                    hc_v = 1; hc_st = 6'(2 + u); hc_tok = 18'(4000 + 111 * u);
                    hc_pos = {2'(u), (MUT == 7 && u == 2) ? 3'd1 : 3'd0, 13'(300 + 7 * u)}; n_hc = n_hc + 1; @(negedge ck);
                end
                hc_v = 0; hc_st = 0; hc_tok = 0; hc_pos = 0;
                repeat (2) @(negedge ck);
                if (face_fault) err("MU head context faulted the face");
            end
        join_none
        // embedding row: the compute end's emb_rx_v edge is the E word event's calendar edge (pin cycle - 1)
        fork
            begin
                wait (u_dut.ev_embw && u_dut.ea[6]);
                emb_rx_v = 1; emb_word_drv = {TOK0, 6'd0, 12'd0, 464'd0, TEP, 16'd0, scale};
                @(posedge ck); #0.01;
                for (w = 0; w < 64; w = w + 1) begin
                    if (!(u_dut.ev_embw && !u_dut.ea[6])) err("embedding word slot not compiled back-to-back");
                    emb_word_drv = {TOK0, 6'(w), 12'd0, row[w]}; @(posedge ck); #0.01;
                end
                emb_rx_v = 0; emb_word_drv = 0;
                // the provider row, read through the sequencer's ROM ports (the embedding stage of this token)
                repeat (3) @(negedge ck); core_start = 1; scale_addr = TOK0; @(negedge ck); core_start = 0;
                for (k = 0; k < 64; k = k + 1) begin
                    code_re = 1; code_addr = {TOK0, 6'(k)}; @(negedge ck); code_re = 0; #0.1;
                    if (code_q !== row[k]) err("embedding word not stored bit-exact");
                end
                scale_re = 1; @(negedge ck); scale_re = 0; #0.1;
                if (scale_q !== scale) err("embedding scale");
                rows_read = 1;
            end
        join_none
        wait (rv); @(negedge ck);
        if (!rows_read) err("row not read back before RESULT");
        if (rtok != 18'd777 || rval != 32'habcd || !rd || rf || rt != htag) err("RESULT record fields");
        // next token: back-to-back, its token is the argmax result, position + 1
        wait (t1 >= 0); repeat (4) @(negedge ck);
        if (u_dut.tok != 18'd777 || u_dut.pos != POS0 + 1) err("token loop did not take the RESULT token");
        if (t1 - t0 != TOKEN_PERIOD) err("token period differs from the compiled END cycle");
        for (i = 0; i < n_ev; i = i + 1) if (!ev_seen[i]) begin
            $display("  missing event class %0d arg %0d at T+%0d", ev_k[i], ev_a[i], ev_t[i]); err("compiled event missing"); end
        if (face_fault || prov_fault || a_f || c_f || w_f || fab) err("fault raised");
        if (adm_cyc < 0 || tok_cyc < 0) err("admission / first-token D2D start not seen");
        if (MU && n_hc != 4) err("MU head contexts not driven");
        if (errs == 0) $display("SYS_FACE_PASS MUT=%0d MU=%0d head contexts %0d, boot %0d records, PW %0d DW %0d, %0d events exact, row 64+scale exact",
                                MUT, MU, n_hc, wi, pw_seen, dw_seen, n_ev);
        else $display("SYS_FACE_FAIL MUT=%0d errors %0d (face_fault %0d prov_fault %0d)", MUT, errs, face_fault, prov_fault);
        $finish;
    end
    reg pf_q = 0; always @(posedge ck) begin pf_q <= prov_fault; if (prov_fault && !pf_q) $display("  provider fault @%0d (T+%0d) face %b store %b", cyc, cyc - t0 - 1, u_prov.ff, u_prov.sf); end
    initial begin #450000; $display("SYS_FACE_FAIL MUT=%0d timeout (errors %0d, face_fault %0d cal_fault %0d)", MUT, errs, face_fault, u_dut.cal_fault); $finish; end
    wire  shadow_old_cfg_tx_we, shadow_new_cfg_tx_we;
    wire  shadow_old_cfg_rx_we, shadow_new_cfg_rx_we;
    wire [5:0] shadow_old_cfg_addr, shadow_new_cfg_addr;
    wire [31:0] shadow_old_cfg_data, shadow_new_cfg_data;
    wire  shadow_old_cal_start, shadow_new_cal_start;
    wire  shadow_old_cal_seg, shadow_new_cal_seg;
    wire  shadow_old_prog_tx_observed_v, shadow_new_prog_tx_observed_v;
    wire [547:0] shadow_old_prog_tx_record, shadow_new_prog_tx_record;
    wire [15:0] shadow_old_status_epoch16, shadow_new_status_epoch16;
    wire  shadow_old_vm_drained, shadow_new_vm_drained;
    wire  shadow_old_collective_drained, shadow_new_collective_drained;
    wire  shadow_old_collective_busy, shadow_new_collective_busy;
    wire  shadow_old_crom_fault, shadow_new_crom_fault;
    wire  shadow_old_execution_active, shadow_new_execution_active;
    wire  shadow_old_admit_ready, shadow_new_admit_ready;
    wire  shadow_old_result_v, shadow_new_result_v;
    wire  shadow_old_result_done, shadow_new_result_done;
    wire  shadow_old_result_fault, shadow_new_result_fault;
    wire [3:0] shadow_old_result_cause, shadow_new_result_cause;
    wire [58:0] shadow_old_result_tag, shadow_new_result_tag;
    wire [1:0] shadow_old_result_gen, shadow_new_result_gen;
    wire [17:0] shadow_old_result_token, shadow_new_result_token;
    wire [31:0] shadow_old_result_value, shadow_new_result_value;
    wire [31:0] shadow_old_result_cycles, shadow_new_result_cycles;
    wire [186:0] shadow_old_seq_dh, shadow_new_seq_dh;
    wire [74:0] shadow_old_tt_pw, shadow_new_tt_pw;
    wire  shadow_old_tt_kok, shadow_new_tt_kok;
    wire  shadow_old_tt_kwd, shadow_new_tt_kwd;
    wire  shadow_old_tt_fab, shadow_new_tt_fab;
    wire  shadow_old_host_epoch_valid, shadow_new_host_epoch_valid;
    wire  shadow_old_host_fused_capability, shadow_new_host_fused_capability;
    wire [15:0] shadow_old_host_epoch, shadow_new_host_epoch;
    wire [58:0] shadow_old_host_tag, shadow_new_host_tag;
    wire [1:0] shadow_old_host_generation, shadow_new_host_generation;
    wire  shadow_old_q_slot, shadow_new_q_slot;
    wire [4:0] shadow_old_q_slot_beat, shadow_new_q_slot_beat;
    wire  shadow_old_kv_word_slot, shadow_new_kv_word_slot;
    wire [1:0] shadow_old_kv_word_index, shadow_new_kv_word_index;
    wire  shadow_old_visibility_slot, shadow_new_visibility_slot;
    wire  shadow_old_complete_slot, shadow_new_complete_slot;
    wire  shadow_old_emb_word_v, shadow_new_emb_word_v;
    wire [511:0] shadow_old_emb_word_data, shadow_new_emb_word_data;
    wire [17:0] shadow_old_emb_word_token, shadow_new_emb_word_token;
    wire [5:0] shadow_old_emb_word_index, shadow_new_emb_word_index;
    wire  shadow_old_emb_word_scale, shadow_new_emb_word_scale;
    wire [15:0] shadow_old_emb_word_epoch, shadow_new_emb_word_epoch;
    wire  shadow_old_emb_expected_slot, shadow_new_emb_expected_slot;
    wire [17:0] shadow_old_emb_expected_token, shadow_new_emb_expected_token;
    wire [5:0] shadow_old_emb_expected_word, shadow_new_emb_expected_word;
    wire  shadow_old_emb_expected_scale, shadow_new_emb_expected_scale;
    wire [15:0] shadow_old_emb_expected_epoch, shadow_new_emb_expected_epoch;
    wire  shadow_old_emb_fill_begin, shadow_new_emb_fill_begin;
    wire [17:0] shadow_old_emb_fill_token, shadow_new_emb_fill_token;
    wire [15:0] shadow_old_emb_fill_epoch, shadow_new_emb_fill_epoch;
    wire [15:0] shadow_old_emb_core_epoch, shadow_new_emb_core_epoch;
    wire  shadow_old_fault, shadow_new_fault;
    qfd_sys_face_gold_wrap u_shadow_old(.ck(ck),.rst_n(rst_n),.cfg_tx_we(shadow_old_cfg_tx_we),.cfg_rx_we(shadow_old_cfg_rx_we),.cfg_addr(shadow_old_cfg_addr),.cfg_data(shadow_old_cfg_data),.cal_start(shadow_old_cal_start),.cal_seg(shadow_old_cal_seg),.fwd_epoch(fwd_epoch),.rx_payload(rx_payload),.prog_rx_v(prog_rx_v),.prog_witness_slot(prog_witness_slot),.prog_auth_slot(prog_auth_slot),.prog_context_slot(prog_context_slot),.prog_tx_observed_v(shadow_old_prog_tx_observed_v),.prog_tx_record(shadow_old_prog_tx_record),.emb_rx_v(emb_rx_v),.emb_rx_slot(emb_rx_v),.d2d_fault(1'b0),.d2d_epoch_abort(1'b0),.status_epoch16(shadow_old_status_epoch16),.vm_drained(shadow_old_vm_drained),.collective_drained(shadow_old_collective_drained),.collective_busy(shadow_old_collective_busy),.crom_fault(shadow_old_crom_fault),.execution_active(shadow_old_execution_active),.admit_ready(shadow_old_admit_ready),.result_v(shadow_old_result_v),.result_done(shadow_old_result_done),.result_fault(shadow_old_result_fault),.result_cause(shadow_old_result_cause),.result_tag(shadow_old_result_tag),.result_gen(shadow_old_result_gen),.result_token(shadow_old_result_token),.result_value(shadow_old_result_value),.result_cycles(shadow_old_result_cycles),.seq_dc(seq_dc),.seq_program_obs(seq_obs),.seq_descriptor_obs(dsc_obs),.seq_cfg_image_ready(seq_rdy),.seq_dh(shadow_old_seq_dh),.tt_program_obs(tt_obs),.tt_control_stores_ready(tt_rdy),.tt_layer_context_v(hc_v),.tt_command_stage(hc_st),.tt_native_tok(hc_tok),.tt_native_pos(hc_pos),.tt_pw(shadow_old_tt_pw),.tt_kok(shadow_old_tt_kok),.tt_kwd(shadow_old_tt_kwd),.tt_fab(shadow_old_tt_fab),.host_epoch_valid(shadow_old_host_epoch_valid),.host_fused_capability(shadow_old_host_fused_capability),.host_epoch(shadow_old_host_epoch),.host_tag(shadow_old_host_tag),.host_generation(shadow_old_host_generation),.q_slot(shadow_old_q_slot),.q_slot_beat(shadow_old_q_slot_beat),.kv_word_slot(shadow_old_kv_word_slot),.kv_word_index(shadow_old_kv_word_index),.visibility_slot(shadow_old_visibility_slot),.complete_slot(shadow_old_complete_slot),.native_fault(1'b0),.emb_word_v(shadow_old_emb_word_v),.emb_word_data(shadow_old_emb_word_data),.emb_word_token(shadow_old_emb_word_token),.emb_word_index(shadow_old_emb_word_index),.emb_word_scale(shadow_old_emb_word_scale),.emb_word_epoch(shadow_old_emb_word_epoch),.emb_expected_slot(shadow_old_emb_expected_slot),.emb_expected_token(shadow_old_emb_expected_token),.emb_expected_word(shadow_old_emb_expected_word),.emb_expected_scale(shadow_old_emb_expected_scale),.emb_expected_epoch(shadow_old_emb_expected_epoch),.emb_fill_begin(shadow_old_emb_fill_begin),.emb_fill_token(shadow_old_emb_fill_token),.emb_fill_epoch(shadow_old_emb_fill_epoch),.emb_core_epoch(shadow_old_emb_core_epoch),.emb_prov_fault(prov_fault | prov_inj),.io_cmd_free(1'b1),.io_fault(1'b0),.io_shared_fault(1'b0),.fault(shadow_old_fault));
    reg tb_obs_fault = 1'b0;
    // MUT 40 (obs_fault causal negative): pulse the die fault-OR root after the epoch anchor;
    // the paired wrapper comparison stays on, so the port must flip `fault` 2 edges later.
    always @(negedge ck) if (MUT == 40 && ep_cyc >= 0 && cyc >= ep_cyc + 50) tb_obs_fault <= 1'b1;
    qfd_sys_face_n32_opt u_shadow_new(.obs_fault(tb_obs_fault),.ck(ck),.rst_n(rst_n),.cfg_tx_we(shadow_new_cfg_tx_we),.cfg_rx_we(shadow_new_cfg_rx_we),.cfg_addr(shadow_new_cfg_addr),.cfg_data(shadow_new_cfg_data),.cal_start(shadow_new_cal_start),.cal_seg(shadow_new_cal_seg),.fwd_epoch(fwd_epoch),.rx_payload(rx_payload),.prog_rx_v(prog_rx_v),.prog_witness_slot(prog_witness_slot),.prog_auth_slot(prog_auth_slot),.prog_context_slot(prog_context_slot),.prog_tx_observed_v(shadow_new_prog_tx_observed_v),.prog_tx_record(shadow_new_prog_tx_record),.emb_rx_v(emb_rx_v),.emb_rx_slot(emb_rx_v),.d2d_fault(1'b0),.d2d_epoch_abort(1'b0),.status_epoch16(shadow_new_status_epoch16),.vm_drained(shadow_new_vm_drained),.collective_drained(shadow_new_collective_drained),.collective_busy(shadow_new_collective_busy),.crom_fault(shadow_new_crom_fault),.execution_active(shadow_new_execution_active),.admit_ready(shadow_new_admit_ready),.result_v(shadow_new_result_v),.result_done(shadow_new_result_done),.result_fault(shadow_new_result_fault),.result_cause(shadow_new_result_cause),.result_tag(shadow_new_result_tag),.result_gen(shadow_new_result_gen),.result_token(shadow_new_result_token),.result_value(shadow_new_result_value),.result_cycles(shadow_new_result_cycles),.seq_dc(seq_dc),.seq_program_obs(seq_obs),.seq_descriptor_obs(dsc_obs),.seq_cfg_image_ready(seq_rdy),.seq_dh(shadow_new_seq_dh),.tt_program_obs(tt_obs),.tt_control_stores_ready(tt_rdy),.tt_layer_context_v(hc_v),.tt_command_stage(hc_st),.tt_native_tok(hc_tok),.tt_native_pos(hc_pos),.tt_pw(shadow_new_tt_pw),.tt_kok(shadow_new_tt_kok),.tt_kwd(shadow_new_tt_kwd),.tt_fab(shadow_new_tt_fab),.host_epoch_valid(shadow_new_host_epoch_valid),.host_fused_capability(shadow_new_host_fused_capability),.host_epoch(shadow_new_host_epoch),.host_tag(shadow_new_host_tag),.host_generation(shadow_new_host_generation),.q_slot(shadow_new_q_slot),.q_slot_beat(shadow_new_q_slot_beat),.kv_word_slot(shadow_new_kv_word_slot),.kv_word_index(shadow_new_kv_word_index),.visibility_slot(shadow_new_visibility_slot),.complete_slot(shadow_new_complete_slot),.native_fault(1'b0),.emb_word_v(shadow_new_emb_word_v),.emb_word_data(shadow_new_emb_word_data),.emb_word_token(shadow_new_emb_word_token),.emb_word_index(shadow_new_emb_word_index),.emb_word_scale(shadow_new_emb_word_scale),.emb_word_epoch(shadow_new_emb_word_epoch),.emb_expected_slot(shadow_new_emb_expected_slot),.emb_expected_token(shadow_new_emb_expected_token),.emb_expected_word(shadow_new_emb_expected_word),.emb_expected_scale(shadow_new_emb_expected_scale),.emb_expected_epoch(shadow_new_emb_expected_epoch),.emb_fill_begin(shadow_new_emb_fill_begin),.emb_fill_token(shadow_new_emb_fill_token),.emb_fill_epoch(shadow_new_emb_fill_epoch),.emb_core_epoch(shadow_new_emb_core_epoch),.emb_prov_fault(prov_fault | prov_inj),.io_cmd_free(1'b1),.io_fault(1'b0),.io_shared_fault(1'b0),.fault(shadow_new_fault));
    integer wrapper_checks=0;
    integer old_boot_cycle=-1,new_boot_cycle=-1,old_ready_cycle=-1,new_ready_cycle=-1;
    always @(posedge ck) begin #0.02;
      if(u_shadow_old.u_ot_pr_core.boot_done && old_boot_cycle<0) old_boot_cycle=cyc;
      if(u_shadow_new.n_4216 && new_boot_cycle<0) new_boot_cycle=cyc;
      if(u_shadow_old.u_ot_pr_core.cal_ready && old_ready_cycle<0) old_ready_cycle=cyc;
      if(u_shadow_new.n_4548 && new_ready_cycle<0) new_ready_cycle=cyc;
      if((MUT==0 || MUT==40) && ep_cyc>=0) begin
        if(!u_shadow_old.u_ot_pr_core.boot_done || !u_shadow_new.n_4216 || !u_shadow_old.u_ot_pr_core.cal_ready || !u_shadow_new.n_4548) $fatal(1,"SYSFACE32_WRAPPER_NOT_BOOTED_AT_EPOCH");
        wrapper_checks=wrapper_checks+1;
        if(shadow_old_cfg_tx_we !== shadow_new_cfg_tx_we) $fatal(1,"SYSFACE32_WRAPPER_MISMATCH port=cfg_tx_we cyc=%0d",cyc);
        if(shadow_old_cfg_rx_we !== shadow_new_cfg_rx_we) $fatal(1,"SYSFACE32_WRAPPER_MISMATCH port=cfg_rx_we cyc=%0d",cyc);
        if(shadow_old_cfg_addr !== shadow_new_cfg_addr) $fatal(1,"SYSFACE32_WRAPPER_MISMATCH port=cfg_addr cyc=%0d",cyc);
        if(shadow_old_cfg_data !== shadow_new_cfg_data) $fatal(1,"SYSFACE32_WRAPPER_MISMATCH port=cfg_data cyc=%0d",cyc);
        if(shadow_old_cal_start !== shadow_new_cal_start) $fatal(1,"SYSFACE32_WRAPPER_MISMATCH port=cal_start cyc=%0d",cyc);
        if(shadow_old_cal_seg !== shadow_new_cal_seg) $fatal(1,"SYSFACE32_WRAPPER_MISMATCH port=cal_seg cyc=%0d",cyc);
        if(shadow_old_prog_tx_observed_v !== shadow_new_prog_tx_observed_v) $fatal(1,"SYSFACE32_WRAPPER_MISMATCH port=prog_tx_observed_v cyc=%0d",cyc);
        if(shadow_old_prog_tx_record !== shadow_new_prog_tx_record) $fatal(1,"SYSFACE32_WRAPPER_MISMATCH port=prog_tx_record cyc=%0d",cyc);
        if(shadow_old_status_epoch16 !== shadow_new_status_epoch16) $fatal(1,"SYSFACE32_WRAPPER_MISMATCH port=status_epoch16 cyc=%0d",cyc);
        if(shadow_old_vm_drained !== shadow_new_vm_drained) $fatal(1,"SYSFACE32_WRAPPER_MISMATCH port=vm_drained cyc=%0d",cyc);
        if(shadow_old_collective_drained !== shadow_new_collective_drained) $fatal(1,"SYSFACE32_WRAPPER_MISMATCH port=collective_drained cyc=%0d",cyc);
        if(shadow_old_collective_busy !== shadow_new_collective_busy) $fatal(1,"SYSFACE32_WRAPPER_MISMATCH port=collective_busy cyc=%0d",cyc);
        if(shadow_old_crom_fault !== shadow_new_crom_fault) $fatal(1,"SYSFACE32_WRAPPER_MISMATCH port=crom_fault cyc=%0d",cyc);
        if(shadow_old_execution_active !== shadow_new_execution_active) $fatal(1,"SYSFACE32_WRAPPER_MISMATCH port=execution_active cyc=%0d",cyc);
        if(shadow_old_admit_ready !== shadow_new_admit_ready) $fatal(1,"SYSFACE32_WRAPPER_MISMATCH port=admit_ready cyc=%0d",cyc);
        if(shadow_old_result_v !== shadow_new_result_v) $fatal(1,"SYSFACE32_WRAPPER_MISMATCH port=result_v cyc=%0d",cyc);
        if(shadow_old_result_done !== shadow_new_result_done) $fatal(1,"SYSFACE32_WRAPPER_MISMATCH port=result_done cyc=%0d",cyc);
        if(shadow_old_result_fault !== shadow_new_result_fault) $fatal(1,"SYSFACE32_WRAPPER_MISMATCH port=result_fault cyc=%0d",cyc);
        if(shadow_old_result_cause !== shadow_new_result_cause) $fatal(1,"SYSFACE32_WRAPPER_MISMATCH port=result_cause cyc=%0d",cyc);
        if(shadow_old_result_tag !== shadow_new_result_tag) $fatal(1,"SYSFACE32_WRAPPER_MISMATCH port=result_tag cyc=%0d",cyc);
        if(shadow_old_result_gen !== shadow_new_result_gen) $fatal(1,"SYSFACE32_WRAPPER_MISMATCH port=result_gen cyc=%0d",cyc);
        if(shadow_old_result_token !== shadow_new_result_token) $fatal(1,"SYSFACE32_WRAPPER_MISMATCH port=result_token cyc=%0d",cyc);
        if(shadow_old_result_value !== shadow_new_result_value) $fatal(1,"SYSFACE32_WRAPPER_MISMATCH port=result_value cyc=%0d",cyc);
        if(shadow_old_result_cycles !== shadow_new_result_cycles) $fatal(1,"SYSFACE32_WRAPPER_MISMATCH port=result_cycles cyc=%0d",cyc);
        if(shadow_old_seq_dh !== shadow_new_seq_dh) $fatal(1,"SYSFACE32_WRAPPER_MISMATCH port=seq_dh cyc=%0d",cyc);
        if(shadow_old_tt_pw !== shadow_new_tt_pw) $fatal(1,"SYSFACE32_WRAPPER_MISMATCH port=tt_pw cyc=%0d",cyc);
        if(shadow_old_tt_kok !== shadow_new_tt_kok) $fatal(1,"SYSFACE32_WRAPPER_MISMATCH port=tt_kok cyc=%0d",cyc);
        if(shadow_old_tt_kwd !== shadow_new_tt_kwd) $fatal(1,"SYSFACE32_WRAPPER_MISMATCH port=tt_kwd cyc=%0d",cyc);
        if(shadow_old_tt_fab !== shadow_new_tt_fab) $fatal(1,"SYSFACE32_WRAPPER_MISMATCH port=tt_fab cyc=%0d",cyc);
        if(shadow_old_host_epoch_valid !== shadow_new_host_epoch_valid) $fatal(1,"SYSFACE32_WRAPPER_MISMATCH port=host_epoch_valid cyc=%0d",cyc);
        if(shadow_old_host_fused_capability !== shadow_new_host_fused_capability) $fatal(1,"SYSFACE32_WRAPPER_MISMATCH port=host_fused_capability cyc=%0d",cyc);
        if(shadow_old_host_epoch !== shadow_new_host_epoch) $fatal(1,"SYSFACE32_WRAPPER_MISMATCH port=host_epoch cyc=%0d",cyc);
        if(shadow_old_host_tag !== shadow_new_host_tag) $fatal(1,"SYSFACE32_WRAPPER_MISMATCH port=host_tag cyc=%0d",cyc);
        if(shadow_old_host_generation !== shadow_new_host_generation) $fatal(1,"SYSFACE32_WRAPPER_MISMATCH port=host_generation cyc=%0d",cyc);
        if(shadow_old_q_slot !== shadow_new_q_slot) $fatal(1,"SYSFACE32_WRAPPER_MISMATCH port=q_slot cyc=%0d",cyc);
        if(shadow_old_q_slot_beat !== shadow_new_q_slot_beat) $fatal(1,"SYSFACE32_WRAPPER_MISMATCH port=q_slot_beat cyc=%0d",cyc);
        if(shadow_old_kv_word_slot !== shadow_new_kv_word_slot) $fatal(1,"SYSFACE32_WRAPPER_MISMATCH port=kv_word_slot cyc=%0d",cyc);
        if(shadow_old_kv_word_index !== shadow_new_kv_word_index) $fatal(1,"SYSFACE32_WRAPPER_MISMATCH port=kv_word_index cyc=%0d",cyc);
        if(shadow_old_visibility_slot !== shadow_new_visibility_slot) $fatal(1,"SYSFACE32_WRAPPER_MISMATCH port=visibility_slot cyc=%0d",cyc);
        if(shadow_old_complete_slot !== shadow_new_complete_slot) $fatal(1,"SYSFACE32_WRAPPER_MISMATCH port=complete_slot cyc=%0d",cyc);
        if(shadow_old_emb_word_v !== shadow_new_emb_word_v) $fatal(1,"SYSFACE32_WRAPPER_MISMATCH port=emb_word_v cyc=%0d",cyc);
        if(shadow_old_emb_word_data !== shadow_new_emb_word_data) $fatal(1,"SYSFACE32_WRAPPER_MISMATCH port=emb_word_data cyc=%0d",cyc);
        if(shadow_old_emb_word_token !== shadow_new_emb_word_token) $fatal(1,"SYSFACE32_WRAPPER_MISMATCH port=emb_word_token cyc=%0d",cyc);
        if(shadow_old_emb_word_index !== shadow_new_emb_word_index) $fatal(1,"SYSFACE32_WRAPPER_MISMATCH port=emb_word_index cyc=%0d",cyc);
        if(shadow_old_emb_word_scale !== shadow_new_emb_word_scale) $fatal(1,"SYSFACE32_WRAPPER_MISMATCH port=emb_word_scale cyc=%0d",cyc);
        if(shadow_old_emb_word_epoch !== shadow_new_emb_word_epoch) $fatal(1,"SYSFACE32_WRAPPER_MISMATCH port=emb_word_epoch cyc=%0d",cyc);
        if(shadow_old_emb_expected_slot !== shadow_new_emb_expected_slot) $fatal(1,"SYSFACE32_WRAPPER_MISMATCH port=emb_expected_slot cyc=%0d",cyc);
        if(shadow_old_emb_expected_token !== shadow_new_emb_expected_token) $fatal(1,"SYSFACE32_WRAPPER_MISMATCH port=emb_expected_token cyc=%0d",cyc);
        if(shadow_old_emb_expected_word !== shadow_new_emb_expected_word) $fatal(1,"SYSFACE32_WRAPPER_MISMATCH port=emb_expected_word cyc=%0d",cyc);
        if(shadow_old_emb_expected_scale !== shadow_new_emb_expected_scale) $fatal(1,"SYSFACE32_WRAPPER_MISMATCH port=emb_expected_scale cyc=%0d",cyc);
        if(shadow_old_emb_expected_epoch !== shadow_new_emb_expected_epoch) $fatal(1,"SYSFACE32_WRAPPER_MISMATCH port=emb_expected_epoch cyc=%0d",cyc);
        if(shadow_old_emb_fill_begin !== shadow_new_emb_fill_begin) $fatal(1,"SYSFACE32_WRAPPER_MISMATCH port=emb_fill_begin cyc=%0d",cyc);
        if(shadow_old_emb_fill_token !== shadow_new_emb_fill_token) $fatal(1,"SYSFACE32_WRAPPER_MISMATCH port=emb_fill_token cyc=%0d",cyc);
        if(shadow_old_emb_fill_epoch !== shadow_new_emb_fill_epoch) $fatal(1,"SYSFACE32_WRAPPER_MISMATCH port=emb_fill_epoch cyc=%0d",cyc);
        if(shadow_old_emb_core_epoch !== shadow_new_emb_core_epoch) $fatal(1,"SYSFACE32_WRAPPER_MISMATCH port=emb_core_epoch cyc=%0d",cyc);
        if(shadow_old_fault !== shadow_new_fault) $fatal(1,"SYSFACE32_WRAPPER_MISMATCH port=fault cyc=%0d",cyc);
      end
    end
    final $display("SYSFACE32_WRAPPER_CHECKS %0d",wrapper_checks);
    final $display("SYSFACE32_BOOT old=%0d new=%0d delta=%0d CAL_READY old=%0d new=%0d delta=%0d EPOCH=%0d",old_boot_cycle,new_boot_cycle,new_boot_cycle-old_boot_cycle,old_ready_cycle,new_ready_cycle,new_ready_cycle-old_ready_cycle,ep_cyc);
endmodule
