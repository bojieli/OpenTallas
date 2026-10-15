`timescale 1ns/1ps
// =====================================================================================================================
// Static successor, no collective credit pin. qfd_seq_su_static -- the Qwen3-8B TP8 split COMPUTE-die ROM sequencer under its DIE NAME (owner no-stub
// rule 10-14 08:05: every die instance binds to real RTL of its name, every die net lands on a real port of its width).
// Body = ot_qfd_seq_su_bi in the TP8 production shape: D 8 (8-rank argmax gather, RBW 3 = the collective's out_rank),
// G 3,072, the closed seq_su_bi febra options (PSRAM 1, HQ2 1, CRED0 STATIC1 collective face, RLY 2, RRG 1,
// PCUT 1), built with +define+OT_QFD_SEQ_SU_NOWROM (the split SU issues no weight-ROM reads: the two pi_su_wrom_* ports
// do not exist; compute-die lead answer 3, 17:26).
// Die bundles = the die.v port names of instance seq_su (C10/C11 smoke), every field at an explicit bit position:
//   dh[186:0]  in   ds levels from qfd_d2d_rom: {dw_v, dw_addr 3, dw_data 64, pw_v, pw_addr 10, pw_data 64,
//                   kv_write_drained, h_start, stage 6, tp_token 18, tp_pos 18}  (h_start [42], pw_v [118], dw_v [186])
//   dc[55:0]   out  sd levels to qfd_d2d_rom: {rom_fault, kv_write_flush, coll_busy, core_fault, s_fault, s_done,
//                   ntok 18, nval 32}; rom_fault = the body's rom_fault OR the 8 constant-buffer groups' faults
//   kvd[43:0]  out  posted KV descriptor: {v, kindk, pos 18, wbase 24}
//   cd_d[546:0] out collective request: [511:0] data, [512] last, [513] mode, [545:514] tag 32, [546] valid
//   Fixed collective slots have no credit return input.
//   cc[517:0]  in   collective result: [511:0] data, [512] last, [515:513] rank 3, [516] err, [517] valid
//   xm[91:0]   in   ME snapshot from qfd_tt_ctlm: {acc 24, idle, prog 16, fin, fidx 18, fval 32}
//   xs[56:0]   out  SU snapshot to qfd_tt_ctlm: {acc 24, idle, prog 16, rows 16}
//   st[48:0]   out  ME start to qfd_tt_ctlm: {h_start, token 18, pos 18, prog_base 12}
//   su[481:0]  out  SU issue to qfd_sp_su64_sfu, LSB first: [0] go, [18:1] nout, [36:19] nin, [37] asrc,
//                   [61:38] abase, [85:62] aso, [109:86] asi, [110] bsrc, [134:111] bbase, [158:135] bso, [182:159] bsi,
//                   [183] csrc, [207:184] cbase, [231:208] cso, [255:232] csi, [257:256] ma, [259:258] mb, [262:260] ad,
//                   [265:263] sfu, [266] mc, [267] md, [269:268] dst, [293:270] dbase, [317:294] dso, [341:318] dsi,
//                   [343:342] red, [344] redsq, [368:345] rbase, [392:369] rso, [424:393] imm1, [456:425] imm2,
//                   [457] a_src, [475:458] tok, [481:476] cb_stage (the stage travels with the issue, lead answer 1)
//   sd[107:0]  in   SU status, LSB first: [0] rt_active, [8:1] rt_inflight, [9] ready, [10] idle, [74:11] kv_we 64,
//                   [90:75] progress, [106:91] progress_rows, [107] fault          (wrom fields removed: 133 -> 108)
//   acc[23:0]  in   SU accepted ops
//   cbc<g>[24:0] out (g = 0..7) constant-buffer control = qfd_su_cbuf_g {tpos 18, tok_start, stage 6}
//   cbr<g>[9:0]  in  constant-buffer status = qfd_su_cbuf_g {fault_code 2, fault, st_rdy_stage 6, st_rdy}
//   vrd[20:0]   out  VM read {re, raddr 20};  vrq[511:0] in  VM read data;  vwr[532:0] out  VM write {we, waddr 20, wdata 512}
//   rsi        in   the sequencer's reset (die reset sequencer, released last)
// Constant-buffer readiness: the 8 groups prefetch the same stage; the sequencer's single cb_st_rdy is the registered AND
// of the 8 groups' st_rdy with all 8 st_rdy_stage equal (+1 edge on the stage-ready handshake, once per stage).
// OT_QFD_SEQ_SU_MUT (bench only): group 7's st_rdy is ignored in the ready AND.
// =====================================================================================================================
module qfd_seq_su_static (
    // Actual external SU operand request -> existing core INT8 decoder -> SU.
    input wire [63:0] su_va_re,
    input wire [1535:0] su_va_addr,
    output wire [2047:0] su_va_q,
    output wire [63:0] su_vm_va_re,
    output wire [1535:0] su_vm_va_addr,
    input wire [2047:0] su_vm_va_q,
    output wire embed_code_re,
    output wire [23:0] embed_code_addr,
    input wire [511:0] embed_code_q,
    output wire embed_scale_re,
    output wire [17:0] embed_scale_addr,
    input wire [15:0] embed_scale_q,
    input wire ck,
    input wire ck_sched,
    output wire [75:0] program_obs,
    output wire [68:0] descriptor_obs,
    output wire cfg_image_ready,
    output wire [15:0] su_observe,
    input  wire          rsi,
    input  wire [186:0]  dh,
    output wire [55:0]   dc,
    output wire [43:0]   kvd,
    output wire [546:0]  cd_d,
    output wire [49:0] coll_cmd,
    input wire coll_cmd_free,
    input  wire [517:0]  cc,
    input  wire [91:0]   xm,
    output wire [56:0]   xs,
    output wire [48:0]   st,
    output wire [481:0]  su,
    input  wire [107:0]  sd,
    input  wire [23:0]   acc,
    output wire [24:0]   cbc0, cbc1, cbc2, cbc3, cbc4, cbc5, cbc6, cbc7,
    input  wire [9:0]    cbr0, cbr1, cbr2, cbr3, cbr4, cbr5, cbr6, cbr7,
    output wire [20:0]   vrd,
    input  wire [511:0]  vrq,
    input  wire          svq_v, // actual scheduled row completion integrity
    output wire [532:0]  vwr
);
    localparam integer NW = 18, AW = 24, D = 8;
    // ---- constant-buffer readiness merge (8 groups) ----
    wire [9:0] cbr [0:7];
    assign cbr[0] = cbr0; assign cbr[1] = cbr1; assign cbr[2] = cbr2; assign cbr[3] = cbr3;
    assign cbr[4] = cbr4; assign cbr[5] = cbr5; assign cbr[6] = cbr6; assign cbr[7] = cbr7;
    reg  [7:0] g_rdy, g_same, g_flt;
    integer gi;
    always @* begin
        for (gi = 0; gi < 8; gi = gi + 1) begin
            g_rdy[gi]  = cbr[gi][0];
            g_same[gi] = (cbr[gi][6:1] == cbr[0][6:1]);
            g_flt[gi]  = cbr[gi][7];
        end
`ifdef OT_QFD_SEQ_SU_MUT
        g_rdy[7] = 1'b1;
`endif
    end
    reg       cb_rdy_q, cb_flt_q;
    reg [5:0] cb_stg_q;
    always @(posedge ck or negedge rsi)
        if (!rsi) begin cb_rdy_q <= 1'b0; cb_flt_q <= 1'b0; cb_stg_q <= 6'd0; end
        else begin
            cb_rdy_q <= (&g_rdy) & (&g_same);
            cb_stg_q <= cbr[0][6:1];
            cb_flt_q <= cb_flt_q | (|g_flt);          // sticky until reset
        end
    // ---- body ----
    wire        s_done, s_fault, core_fault, coll_busy, kv_write_flush, rom_fault;
    wire [NW-1:0] seq_ntok;
    wire [31:0] seq_nval;
    wire [5:0]  cb_stage;
    wire        cb_tok_start;
    wire [NW-1:0] cb_tpos;
    wire        vm_re, vm_we;
    wire [19:0] vm_raddr, vm_waddr;
    wire [511:0] vm_wdata;
    wire        c_valid, c_last, c_mode;
    wire [511:0] c_data;
    wire [31:0] c_tag;
    wire        su_asrc;
    wire [NW-1:0] su_tok;
    wire        me_start_o;
    wire [NW-1:0] me_token_o, me_pos_o;
    wire [11:0] me_prog_base_o;
    wire [23:0] su_acc_o;
    wire        su_idle_o;
    wire [15:0] su_prog_o, su_rows_o;
    wire        kvd_v, kvd_kindk;
    wire [AW-1:0] kvd_wbase;
    wire [NW-1:0] kvd_pos;
    wire        go;
    wire [NW-1:0] i_nout, i_nin;
    wire        i_asrc, i_bsrc, i_csrc, i_mc, i_md, i_redsq;
    wire [AW-1:0] i_abase, i_aso, i_asi, i_bbase, i_bso, i_bsi, i_cbase, i_cso, i_csi, i_dbase, i_dso, i_dsi, i_rbase, i_rso;
    wire [1:0]  i_ma, i_mb, i_dst, i_red;
    wire [2:0]  i_ad, i_sfu;
    wire [31:0] i_imm1, i_imm2;
    ot_qfd_seq_su_bi_static #(.RRG(1), .PCUT(1), .G(3072), .D(D), .PSRAM(1), .HQ2(1), .CRED(0), .RLY(2)) u_seq (
        .su_va_re(su_va_re),
        .su_va_addr(su_va_addr),
        .su_va_q(su_va_q),
        .su_vm_va_re(su_vm_va_re),
        .su_vm_va_addr(su_vm_va_addr),
        .su_vm_va_q(su_vm_va_q),
        .embed_code_re(embed_code_re),
        .embed_code_addr(embed_code_addr),
        .embed_code_q(embed_code_q),
        .embed_scale_re(embed_scale_re),
        .embed_scale_addr(embed_scale_addr),
        .embed_scale_q(embed_scale_q),
        .clk(ck),.ck_sched(ck_sched), .rst_n(rsi),.program_obs(program_obs),.descriptor_obs(descriptor_obs),.cfg_image_ready(body_cfg_ready),.su_observe(su_observe),
        .h_start(dh[42]), .stage_in(dh[41:36]), .tp_token(dh[35:18]), .tp_pos(dh[17:0]), .kv_write_drained(dh[43]),
        .pw_v(dh[118]), .pw_addr(dh[117:108]), .pw_data(dh[107:44]),
        .dw_v(dh[186]), .dw_addr(dh[185:183]), .dw_data(dh[182:119]),
        .cb_st_rdy(cb_rdy_q), .cb_st_rdy_stage(cb_stg_q), .cb_stage(cb_stage), .cb_tok_start(cb_tok_start), .cb_tpos(cb_tpos),
        .vm_rq(vrq), .vm_rvalid(svq_v), .c_ready(1'b0),
        .r_valid(cc[517]), .r_data(cc[511:0]), .r_last(cc[512]), .r_rank(cc[515:513]), .r_err(cc[516]),
        .pi_su_rt_active(sd[0]), .pi_su_rt_inflight(sd[8:1]), .pi_su_ready(sd[9]), .pi_su_idle(sd[10]),
        .pi_su_kv_we(sd[74:11]), .pi_su_progress(sd[90:75]), .pi_su_progress_rows(sd[106:91]), .pi_su_fault(sd[107]),
        .x_oacc(xm[91:68]), .x_oidle(xm[67]), .x_oprog(xm[66:51]), .x_ofin(xm[50]), .x_fidx(xm[49:32]), .x_fval(xm[31:0]),
        .pi_su_acc(acc),
        .s_done(s_done), .seq_ntok(seq_ntok), .seq_nval(seq_nval), .s_fault(s_fault), .core_fault(core_fault),
        .coll_busy(coll_busy), .kv_write_flush(kv_write_flush),
        .vm_re(vm_re), .vm_raddr(vm_raddr), .vm_we(vm_we), .vm_waddr(vm_waddr), .vm_wdata(vm_wdata),
        .c_valid(c_valid), .c_data(c_data), .c_last(c_last), .c_mode(c_mode), .c_tag(c_tag),
        .rom_fault(rom_fault), .su_asrc(su_asrc), .su_tok(su_tok),
        .po_su_go(go), .po_su_i_nout(i_nout), .po_su_i_nin(i_nin), .po_su_i_asrc(i_asrc), .po_su_i_abase(i_abase),
        .po_su_i_aso(i_aso), .po_su_i_asi(i_asi), .po_su_i_bsrc(i_bsrc), .po_su_i_bbase(i_bbase), .po_su_i_bso(i_bso),
        .po_su_i_bsi(i_bsi), .po_su_i_csrc(i_csrc), .po_su_i_cbase(i_cbase), .po_su_i_cso(i_cso), .po_su_i_csi(i_csi),
        .po_su_i_ma(i_ma), .po_su_i_mb(i_mb), .po_su_i_ad(i_ad), .po_su_i_sfu(i_sfu), .po_su_i_mc(i_mc), .po_su_i_md(i_md),
        .po_su_i_dst(i_dst), .po_su_i_dbase(i_dbase), .po_su_i_dso(i_dso), .po_su_i_dsi(i_dsi), .po_su_i_red(i_red),
        .po_su_i_redsq(i_redsq), .po_su_i_rbase(i_rbase), .po_su_i_rso(i_rso), .po_su_i_imm1(i_imm1), .po_su_i_imm2(i_imm2),
        .me_start_o(me_start_o), .me_token_o(me_token_o), .me_pos_o(me_pos_o), .me_prog_base_o(me_prog_base_o),
        .su_acc_o(su_acc_o), .su_idle_o(su_idle_o), .su_prog_o(su_prog_o), .su_rows_o(su_rows_o),
        .kvd_v(kvd_v), .kvd_wbase(kvd_wbase), .kvd_ts(), .kvd_ks(), .kvd_js(), .kvd_wcs(), .kvd_split(), .kvd_jsh(),
        .kvd_tiles(), .kvd_k(), .kvd_nout(), .kvd_kindk(kvd_kindk), .kvd_pos(kvd_pos));
    // rom_fault leaves from a flop: the body's rom_fault OR the constant-buffer groups' sticky fault (+1 edge, flag only)
    reg rom_fault_q;
    always @(posedge ck or negedge rsi) if (!rsi) rom_fault_q <= 1'b0; else rom_fault_q <= rom_fault | cb_flt_q;
    wire coll_issue_fault,coll_cfg_ready,body_cfg_ready;
    // The joint seal is a configuration fact, exported from a source pin FF.
    // Its loss still revokes the downstream installation; no timeline gates.
    ot_hdc_delay #(.W(1),.D(1),.RESET(1))u_image_ready_pin
      (.clk(ck),.rst_n(rsi),.d(body_cfg_ready&&coll_cfg_ready),.q(cfg_image_ready));
    qfd_seq_su_collective_calendar u_coll_calendar(.ck(ck_sched),.rsi(rsi),.dh(dh),
      .cmd_free(coll_cmd_free),.cmd(coll_cmd),.cfg_ready(coll_cfg_ready),.fault(coll_issue_fault));
    assign dc   = {rom_fault_q | coll_issue_fault, kv_write_flush, coll_busy, core_fault, s_fault, s_done, seq_ntok, seq_nval};
    assign kvd  = {kvd_v, kvd_kindk, kvd_pos, kvd_wbase};
    assign cd_d = {c_valid, c_tag, c_mode, c_last, c_data};
    assign xs   = {su_acc_o, su_idle_o, su_prog_o, su_rows_o};
    assign st   = {me_start_o, me_token_o, me_pos_o, me_prog_base_o};
    assign su   = {cb_stage, su_tok, su_asrc, i_imm2, i_imm1, i_rso, i_rbase, i_redsq, i_red, i_dsi, i_dso, i_dbase, i_dst,
                   i_md, i_mc, i_sfu, i_ad, i_mb, i_ma, i_csi, i_cso, i_cbase, i_csrc, i_bsi, i_bso, i_bbase, i_bsrc,
                   i_asi, i_aso, i_abase, i_asrc, i_nin, i_nout, go};
    wire [24:0] cbw = {cb_tpos, cb_tok_start, cb_stage};
    assign cbc0 = cbw; assign cbc1 = cbw; assign cbc2 = cbw; assign cbc3 = cbw;
    assign cbc4 = cbw; assign cbc5 = cbw; assign cbc6 = cbw; assign cbc7 = cbw;
    assign vrd  = {vm_re, vm_raddr};
    assign vwr  = {vm_we, vm_waddr, vm_wdata};
endmodule
