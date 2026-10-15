`timescale 1ns/1ps
// q14 r9 (2026-10-14): die-bundle contract bench of qfd_seq_su (rtl/qwen_split/qfd_seq_su.sv).  A reference
// ot_qfd_seq_su_bi with the same TP8 parameters is driven from the same random die bundles through an INDEPENDENT
// bench-side field map (written from the CONTRACT text, not from the wrapper), with the constant-buffer readiness merge
// and the rom_fault flop modelled here; every die output bit of the wrapper is compared with the reference's field every
// cycle.  The sequencer is driven to real work: program / descriptor writes through dh, h_start pulses with stage-ready
// from all 8 groups (one group late at random), random collective / SU / VM / snapshot inputs, a reset every 1,500
// cycles.  Build with +define+OT_QFD_SEQ_SU_NOWROM.  +define+OT_QFD_SEQ_SU_MUT (group 7's ready ignored) must FAIL.
module tb_qfd_seq_su_die;
    parameter integer NCYC = 12000, SEED = 1;
    reg ck = 0, rsi = 0;
    always #1 ck = ~ck;
    reg  [186:0] dh = 0;  reg cd_cr = 0;  reg [517:0] cc = 0;  reg [91:0] xm = 0;  reg [107:0] sd = 0;
    reg  [23:0]  acc = 0; reg [511:0] vrq = 0;
    reg  [9:0]   cbr [0:7];
    wire [55:0] dc;  wire [43:0] kvd;  wire [546:0] cd_d;  wire [56:0] xs;  wire [48:0] st;  wire [481:0] su;
    wire [24:0] cbc [0:7];  wire [20:0] vrd;  wire [532:0] vwr;
    qfd_seq_su dut (.ck(ck), .rsi(rsi), .dh(dh), .dc(dc), .kvd(kvd), .cd_d(cd_d), .cd_cr(cd_cr), .cc(cc), .xm(xm), .xs(xs),
        .st(st), .su(su), .sd(sd), .acc(acc),
        .cbc0(cbc[0]), .cbc1(cbc[1]), .cbc2(cbc[2]), .cbc3(cbc[3]), .cbc4(cbc[4]), .cbc5(cbc[5]), .cbc6(cbc[6]), .cbc7(cbc[7]),
        .cbr0(cbr[0]), .cbr1(cbr[1]), .cbr2(cbr[2]), .cbr3(cbr[3]), .cbr4(cbr[4]), .cbr5(cbr[5]), .cbr6(cbr[6]), .cbr7(cbr[7]),
        .vrd(vrd), .vrq(vrq), .vwr(vwr));
    // ---- reference: the body with the CONTRACT field map (bench-side) ----
    reg r_rdy = 0, r_flt = 0; reg [5:0] r_stg = 0;
    integer g; reg all_rdy, all_same, any_f;
    always @* begin
        all_rdy = 1; all_same = 1; any_f = 0;
        for (g = 0; g < 8; g = g + 1) begin
            all_rdy = all_rdy & cbr[g][0]; all_same = all_same & (cbr[g][6:1] == cbr[0][6:1]); any_f = any_f | cbr[g][7];
        end
    end
    always @(posedge ck or negedge rsi)
        if (!rsi) begin r_rdy <= 0; r_flt <= 0; r_stg <= 0; end
        else begin r_rdy <= all_rdy & all_same; r_stg <= cbr[0][6:1]; r_flt <= r_flt | any_f; end
    wire s_done, s_fault, core_fault, coll_busy, kvwf, romf, c_valid, c_last, c_mode, vm_re, vm_we, su_asrc, me_start,
         su_idle, kvd_v, kvd_kindk, go, i_asrc, i_bsrc, i_csrc, i_mc, i_md, i_redsq, cb_tok;
    wire [17:0] ntok, su_tok, me_tok, me_pos, kvd_pos, cb_tpos, i_nout, i_nin;
    wire [31:0] nval, c_tag, i_imm1, i_imm2;
    wire [511:0] c_data, vm_wdata;
    wire [19:0] vm_raddr, vm_waddr;
    wire [11:0] me_pb;
    wire [23:0] su_acc, kvd_wbase, i_abase, i_aso, i_asi, i_bbase, i_bso, i_bsi, i_cbase, i_cso, i_csi, i_dbase, i_dso,
                i_dsi, i_rbase, i_rso;
    wire [15:0] su_prog, su_rows;
    wire [5:0] cb_stage;
    wire [1:0] i_ma, i_mb, i_dst, i_red;
    wire [2:0] i_ad, i_sfu;
    ot_qfd_seq_su_bi #(.RRG(1), .PCUT(1), .G(3072), .D(8), .PSRAM(1), .HQ2(1), .CRED(128), .RLY(2)) u_ref (
        .clk(ck), .rst_n(rsi),
        .h_start(dh[42]), .stage_in(dh[41:36]), .tp_token(dh[35:18]), .tp_pos(dh[17:0]), .kv_write_drained(dh[43]),
        .pw_v(dh[118]), .pw_addr(dh[117:108]), .pw_data(dh[107:44]), .dw_v(dh[186]), .dw_addr(dh[185:183]),
        .dw_data(dh[182:119]), .cb_st_rdy(r_rdy), .cb_st_rdy_stage(r_stg), .cb_stage(cb_stage), .cb_tok_start(cb_tok),
        .cb_tpos(cb_tpos), .vm_rq(vrq), .c_ready(cd_cr), .r_valid(cc[517]), .r_data(cc[511:0]), .r_last(cc[512]),
        .r_rank(cc[515:513]), .r_err(cc[516]), .pi_su_rt_active(sd[0]), .pi_su_rt_inflight(sd[8:1]), .pi_su_ready(sd[9]),
        .pi_su_idle(sd[10]), .pi_su_kv_we(sd[74:11]), .pi_su_progress(sd[90:75]), .pi_su_progress_rows(sd[106:91]),
        .pi_su_fault(sd[107]), .x_oacc(xm[91:68]), .x_oidle(xm[67]), .x_oprog(xm[66:51]), .x_ofin(xm[50]),
        .x_fidx(xm[49:32]), .x_fval(xm[31:0]), .pi_su_acc(acc), .s_done(s_done), .seq_ntok(ntok), .seq_nval(nval),
        .s_fault(s_fault), .core_fault(core_fault), .coll_busy(coll_busy), .kv_write_flush(kvwf), .vm_re(vm_re),
        .vm_raddr(vm_raddr), .vm_we(vm_we), .vm_waddr(vm_waddr), .vm_wdata(vm_wdata), .c_valid(c_valid), .c_data(c_data),
        .c_last(c_last), .c_mode(c_mode), .c_tag(c_tag), .rom_fault(romf), .su_asrc(su_asrc), .su_tok(su_tok),
        .po_su_go(go), .po_su_i_nout(i_nout), .po_su_i_nin(i_nin), .po_su_i_asrc(i_asrc), .po_su_i_abase(i_abase),
        .po_su_i_aso(i_aso), .po_su_i_asi(i_asi), .po_su_i_bsrc(i_bsrc), .po_su_i_bbase(i_bbase), .po_su_i_bso(i_bso),
        .po_su_i_bsi(i_bsi), .po_su_i_csrc(i_csrc), .po_su_i_cbase(i_cbase), .po_su_i_cso(i_cso), .po_su_i_csi(i_csi),
        .po_su_i_ma(i_ma), .po_su_i_mb(i_mb), .po_su_i_ad(i_ad), .po_su_i_sfu(i_sfu), .po_su_i_mc(i_mc), .po_su_i_md(i_md),
        .po_su_i_dst(i_dst), .po_su_i_dbase(i_dbase), .po_su_i_dso(i_dso), .po_su_i_dsi(i_dsi), .po_su_i_red(i_red),
        .po_su_i_redsq(i_redsq), .po_su_i_rbase(i_rbase), .po_su_i_rso(i_rso), .po_su_i_imm1(i_imm1),
        .po_su_i_imm2(i_imm2), .me_start_o(me_start), .me_token_o(me_tok), .me_pos_o(me_pos), .me_prog_base_o(me_pb),
        .su_acc_o(su_acc), .su_idle_o(su_idle), .su_prog_o(su_prog), .su_rows_o(su_rows), .kvd_v(kvd_v),
        .kvd_wbase(kvd_wbase), .kvd_ts(), .kvd_ks(), .kvd_js(), .kvd_wcs(), .kvd_split(), .kvd_jsh(), .kvd_tiles(),
        .kvd_k(), .kvd_nout(), .kvd_kindk(kvd_kindk), .kvd_pos(kvd_pos));
    reg r_romf = 0;
    always @(posedge ck or negedge rsi) if (!rsi) r_romf <= 0; else r_romf <= romf | r_flt;
    // ---- checks (the contract field positions, written out bit range by bit range) ----
    integer bad = 0, checks = 0, i, goes = 0, sdone = 0, cvs = 0, rdys = 0, wfe = 0, suc = 0, dcc = 0, stc = 0, cdc = 0;
    reg [481:0] su_l = 0; reg [55:0] dc_l = 0; reg [48:0] st_l = 0; reg [546:0] cd_l = 0;
    task chk(input integer ok, input [8*24-1:0] what);
        begin if (!ok) begin bad = bad + 1; if (bad < 12) $display("MISMATCH %0s at cycle %0d", what, i); end end
    endtask
    task check_all; integer k; begin
        checks = checks + 1;
        chk(dc[31:0] === nval && dc[49:32] === ntok && dc[50] === s_done && dc[51] === s_fault && dc[52] === core_fault &&
            dc[53] === coll_busy && dc[54] === kvwf && dc[55] === r_romf, "dc");
        chk(kvd[23:0] === kvd_wbase && kvd[41:24] === kvd_pos && kvd[42] === kvd_kindk && kvd[43] === kvd_v, "kvd");
        chk(cd_d[511:0] === c_data && cd_d[512] === c_last && cd_d[513] === c_mode && cd_d[545:514] === c_tag &&
            cd_d[546] === c_valid, "cd_d");
        chk(xs[15:0] === su_rows && xs[31:16] === su_prog && xs[32] === su_idle && xs[56:33] === su_acc, "xs");
        chk(st[11:0] === me_pb && st[29:12] === me_pos && st[47:30] === me_tok && st[48] === me_start, "st");
        chk(su[0] === go && su[18:1] === i_nout && su[36:19] === i_nin && su[37] === i_asrc && su[61:38] === i_abase &&
            su[85:62] === i_aso && su[109:86] === i_asi && su[110] === i_bsrc && su[134:111] === i_bbase &&
            su[158:135] === i_bso && su[182:159] === i_bsi && su[183] === i_csrc && su[207:184] === i_cbase &&
            su[231:208] === i_cso && su[255:232] === i_csi && su[257:256] === i_ma && su[259:258] === i_mb &&
            su[262:260] === i_ad && su[265:263] === i_sfu && su[266] === i_mc && su[267] === i_md &&
            su[269:268] === i_dst && su[293:270] === i_dbase && su[317:294] === i_dso && su[341:318] === i_dsi &&
            su[343:342] === i_red && su[344] === i_redsq && su[368:345] === i_rbase && su[392:369] === i_rso &&
            su[424:393] === i_imm1 && su[456:425] === i_imm2 && su[457] === su_asrc && su[475:458] === su_tok &&
            su[481:476] === cb_stage, "su");
        for (k = 0; k < 8; k = k + 1)
            chk(cbc[k][5:0] === cb_stage && cbc[k][6] === cb_tok && cbc[k][24:7] === cb_tpos, "cbc");
        chk(vrd[19:0] === vm_raddr && vrd[20] === vm_re, "vrd");
        chk(vwr[511:0] === vm_wdata && vwr[531:512] === vm_waddr && vwr[532] === vm_we, "vwr");
        suc = suc + (su !== su_l); dcc = dcc + (dc !== dc_l); stc = stc + (st !== st_l); cdc = cdc + (cd_d !== cd_l);
        su_l = su; dc_l = dc; st_l = st; cd_l = cd_d;
        goes = goes + go; sdone = sdone + s_done; cvs = cvs + c_valid; rdys = rdys + r_rdy; wfe = wfe + vm_we;
    end endtask
    function [511:0] rnd512(input integer dummy); integer k; begin for (k = 0; k < 16; k = k + 1) rnd512[32*k +: 32] = $random; end endfunction
    integer seed, k, stg = 0, lag = 0, hs_wait = 0;
    reg [23:0] xacc = 0;
    initial begin
        seed = SEED; k = $random(seed);
        for (k = 0; k < 8; k = k + 1) cbr[k] = 0;
        repeat (3) @(negedge ck);
        rsi = 1;
        // boot (the psram bench's program shape): program slices through dh pw (slice 0 biased to ME / SU ops), then the
        // 8 descriptors through dh dw with program bases inside the store
        for (k = 0; k < 1024; k = k + 1) begin
            @(negedge ck);
            dh = 0; dh[118] = 1; dh[117:108] = k[9:0]; dh[107:44] = {$random(seed), $random(seed)};
            if (k % 16 == 0) begin
                dh[44 +: 2] = (($random(seed) & 15) == 0) ? 2'd0 : (($random(seed) & 1) ? 2'd1 : 2'd2);
                dh[46 +: 2] = (($random(seed) & 7) == 0) ? 2'($random(seed)) : 2'd0;
                dh[64 +: 2] = (($random(seed) & 7) == 0) ? 2'($random(seed)) : 2'd0;
            end
        end
        for (k = 0; k < 8; k = k + 1) begin
            @(negedge ck); dh = 0; dh[186] = 1; dh[185:183] = k[2:0];
            dh[182:119] = {20'($random(seed)), 6'd0, 6'(k * 7 % 48), 32'($random(seed))};
        end
        @(negedge ck); dh = 0;
        repeat (8) @(posedge ck);
        for (i = 0; i < NCYC; i = i + 1) begin
            @(negedge ck);
            rsi = (i % 400) != 399;                       // a reset every 400 cycles (store kept), as the psram bench
            dh[42] = 0; dh[43] = 1; dh[118] = 0; dh[186] = 0;
            if (i % 400 == 12) begin stg = (stg + 1) % 38; dh[42] = 1; dh[41:36] = stg; dh[35:18] = $random(seed); dh[17:0] = $random(seed); lag = $random(seed) & 7; end
            // constant buffers: all 8 groups report the stage, group (i/400)%8 late
            for (k = 0; k < 8; k = k + 1) begin
                cbr[k][6:1] = stg; cbr[k][0] = !((k == (i / 400) % 8) && ((i % 400) < 14 + lag));
                cbr[k][7] = ((i % 2999) == 2998) && (k == 3); cbr[k][9:8] = $random(seed);
            end
            // status inputs follow the controllers' ICUT contract (psram bench): SU ready / idle, KV drained, other unit idle
            cd_cr = 1; cc = {1'b0, rnd512(0)} | ({$random(seed)} << 512); cc[517] = ($random(seed) & 3) == 0;
            xm = {$random(seed), $random(seed), $random(seed)}; if (!rsi) xacc = 0; else if (($random(seed) & 3) == 0) xacc = xacc + 1; xm[91:68] = xacc; xm[67] = 1; xm[50] = ($random(seed) & 3) == 0;
            sd = {$random(seed), $random(seed), $random(seed), $random(seed)}; sd[0] = 0; sd[8:1] = 0; sd[9] = 1; sd[10] = 1;
            sd[107] = 0; acc = $random(seed);
            vrq = rnd512(0);
            #0.2 check_all;
            @(posedge ck); #0.2 check_all;
        end
        if (bad == 0 && goes > 0 && rdys > 0)
            $display("PASS qfd_seq_su_die checks=%0d su_go=%0d s_done=%0d c_valid=%0d cb_ready=%0d vm_we=%0d changes su/dc/st/cd %0d/%0d/%0d/%0d", checks, goes, sdone, cvs, rdys, wfe, suc, dcc, stc, cdc);
        else
            $display("FAIL qfd_seq_su_die checks=%0d mismatches=%0d su_go=%0d cb_ready=%0d changes su/dc/st/cd %0d/%0d/%0d/%0d", checks, bad, goes, rdys, suc, dcc, stc, cdc);
        $finish;
    end
endmodule
