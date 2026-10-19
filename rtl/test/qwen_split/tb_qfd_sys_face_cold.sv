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
module tb_qfd_sys_face_cold;
    parameter integer MUT = 0;
    parameter integer MU = 0;
    parameter integer SRAM_CAL = 1;
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
    wire face_fault, init_u0;
    reg fwd_epoch = 0;
    reg hc_v = 0; reg [5:0] hc_st = 0; reg [17:0] hc_tok = 0, hc_pos = 0; integer n_hc = 0;
    // MUT 5 (Q-STUB 10-17): one-edge provider fault pulse after reset -- the face must latch it (face_fault / fab) and FAIL
    wire prov_fault; reg prov_inj = 0; integer rel_cyc = -1;
    always @(posedge ck) begin if (rst_n && rel_cyc < 0) rel_cyc = cyc; prov_inj <= (MUT == 5) && rel_cyc >= 0 && cyc == rel_cyc + 50; end
    qfd_sys_face #(.MUT(0), .MU(MU), .SRAM_CAL(SRAM_CAL), .OVL(1), .OVL_ROM_DIR(IMG), .COLD_PREFIX(1), .COLD_START_OFS(2000), .OVL_FIRST_OFS(20000), .CTX_ACCEPTED(1), .GO_OFS(GO_OFS), .START_ADJ(MUT == 4 ? (720'd1 << (20 * 5)) : 720'd0), .ROM_VIAMAP({IMG, "/sys_face_cfg.viamap.hex"})) u_dut (
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
        .init_u0(init_u0), .fault(face_fault));
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
    localparam integer GO_OFS=3;
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


    integer i,w,k,cstart=-1,epedge=-1,ecal=-1,init_edge=-1,ninit=0,nfill=0,nword=0;
    reg [511:0] row[0:63]; reg [15:0] scale=16'h3f99; reg rows_read=0;
    always @(posedge ck) if(rst_n) begin
      if(fwd_epoch && epedge<0)epedge=cyc;
      if(u_dut.cold_t_go)begin cstart=cyc;$display("COLDAGE epoch%0d cold_start%0d ADMdone%0d",epedge,cyc,u_dut.cs_adm_done);end
      if(u_dut.ecal_go)begin ecal=cyc;$display("COLDAGE E_start_sample%0d relative%0d",cyc,cyc-cstart);end
      if(dh[42])begin
        ninit=ninit+1;init_edge=cyc;
        if(dh[41:36]!=0 || !init_u0)err("INIT not stage0/aligned init_u0");
        if(cyc-cstart-1!=212)err("INIT off immutable T prefix edge");
        $display("COLDAGE INIT_pin_sample%0d relative%0d",cyc,cyc-cstart);
      end else if(init_u0)err("init_u0 without DH");
      if(fb)begin nfill=nfill+1;$display("COLDAGE FILL_pin_sample%0d relativeE%0d",cyc,cyc-ecal);end
      if(ex_s)begin
        if(nword==0 && cyc-ecal-1!=209)err("cold E SEG1 header offset");
        nword=nword+1;
      end
    end
    initial begin
      for(w=0;w<64;w=w+1)for(k=0;k<16;k=k+1)row[w][k*32+:32]=32'h9e3779b9*(w*131+k+7);
      digest=64'h51484f5354505247;
      for(i=0;i<1032;i=i+1)begin #0;digest={digest[56:0],digest[63:57]}^prog[i]^(i<1024?64'(i):(64'd1<<10)|64'(i-1024));end
      footer=prog[1023];repeat(4)@(negedge ck);rst_n=1;
      wait(u_dut.boot_done);repeat(4)@(negedge ck);
      while(wi<nexp && wexp[wi][43:40]==6)begin if(u_dut.first_ofs!==wexp[wi][31:0])err("first offset");wi=wi+1;end
      if(wi!=nexp)err("boot count");
      fwd_epoch=1;@(negedge ck);fwd_epoch=0;
      a_begin=1;@(negedge ck);a_begin=0;a_auth=1;@(negedge ck);a_auth=0;
      a_type=1;a_send=1;@(negedge ck);a_send=0;repeat(3)@(negedge ck);
      a_type=2;a_send=1;@(negedge ck);a_send=0;
      wait(dw_seen==8);repeat(8)@(negedge ck);
      if(!u_dut.rp_program_ready)err("programme did not commit");
      prog_witness_slot=1;@(negedge ck);prog_witness_slot=0;repeat(3)@(negedge ck);
      if(!w_inst || w_dg!==digest)err("witness rejected");
      c_req=1;@(negedge ck);c_req=0;repeat(2)@(negedge ck);
      c_send=1;@(negedge ck);c_send=0;
      wait(cstart>=0);
      wait(u_dut.ev_embw && u_dut.ea[6]);
      emb_rx_v=1;emb_word_drv={TOK0,6'd0,12'd0,464'd0,TEP,16'd0,scale};
      @(posedge ck);#0.01;
      for(w=0;w<64;w=w+1)begin
        if(!(u_dut.ev_embw && !u_dut.ea[6]))err("row slots not contiguous");
        emb_word_drv={TOK0,6'(w),12'd0,row[w]};@(posedge ck);#0.01;
      end
      emb_rx_v=0;emb_word_drv=0;
      repeat(3)@(negedge ck);core_start=1;scale_addr=TOK0;@(negedge ck);core_start=0;
      for(k=0;k<64;k=k+1)begin code_re=1;code_addr={TOK0,6'(k)};@(negedge ck);code_re=0;#0.1;if(code_q!==row[k])err("row data");end
      scale_re=1;@(negedge ck);scale_re=0;#0.1;if(scale_q!==scale)err("scale");
      repeat(20)@(negedge ck);
      if(ninit!=1 || nfill!=1 || nword!=65 || u_dut.cold_active || u_dut.t_run)err("prefix count/end");
      if(face_fault || prov_fault || a_f || c_f || w_f || fab)err("fault raised");
      if(errs==0)$display("SYS_FACE_COLD_PASS MUT%0d Tprefix3 Esegment1 init1 row64+scale",MUT);
      else begin $display("SYS_FACE_COLD_FAIL MUT%0d errors%0d face%0d provider%0d",MUT,errs,face_fault,prov_fault);$fatal(1);end
      $finish;
    end
    initial begin repeat(12000)@(negedge ck);$fatal(1,"cold bench timeout");end
endmodule
