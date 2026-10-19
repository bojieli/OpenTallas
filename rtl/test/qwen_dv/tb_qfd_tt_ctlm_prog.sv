`timescale 1ns/1ps
// QLB-PROG (10-18, G-C3) unit bench of the compiled deployment image: qfd_tt_ctlm_dv loads the ctlm_image.py image as
// qfd_sys_face replays it (tt pw + dh pw copy on the same edge, one word an edge, then DW0..7 on dh), then runs stages
// (dh h_start / stage / token / position) while the neighbours answer at their COMPILED cycles (the slices' status words
// ss5 / ag5 and native59's native_ret, from the image's status timeline: the static schedule's commitments, never a
// response to this block).  Every event is checked against the compiled expectation by tt_ctlm_prog_bench.py.
// Events (+EV, sorted, applied before posedge `cycle`): "cycle kind hex"
//   0 PW {addr 10, data 64}   1 DW {addr 3, data 64}   2 RUN {h_start, stage 6, tok 18, pos 18}
//   6 LEVEL {kok, kwd}        7 AG ag5 (10 b, held)    8 SS ss5 (107 b, held)    9 NRET native_ret (95 b, held)
// Log (+LOG), label = the posedge just taken: "c CMD hex" (cmd register), "c LOC kind base" (EMB / SEG start pulses),
//   "c ISSUE pc unit" (head fixed issue / END), "c ROM go" (ib go), "c NAT go" (native_cmd go), "c XPF hex" (arm word),
//   "c CSR" (control stores ready), "c CF bits" on a fault rise, "c STAGE s" (command_stage change),
//   "c TL hex" (QLB-C4b: a stream table word on tl, the dvs_W5 st_wi driver), "c ROMRAW hex" (hr[73] set without the
//   slice's go hr[452]: the as-built layout, QW-DIEFIX).
// Q-H16C 10-18: +define+TB_HARD (bench --hard 1) probes the hard leaf (HARD_HR 1) instead of the inline head.
`ifdef TB_HARD
`define TB_HEAD dut.g_hard_hr.u_hr.u_head
`define TB_HR   dut.g_hard_hr.u_hr
`else
`define TB_HEAD dut.g_soft_hr.u_head
`define TB_HR   dut.g_soft_hr
`endif
module tb_qfd_tt_ctlm_prog (input wire ck);
    // HARD_HR 0 = inline head; 1 = the h16c h17 hard leaf with the running-stage port (Q-H16C 10-18; bench --hard 1)
    parameter integer MUT = 0, XPF_EDGES = 26, STAGE_ME = 1, HARD_HR = 0, HRA = 0;   // HRA: HR_ASBUILT (mutant)
    reg rst_n = 1'b0;
    reg [74:0] pw = 0; reg [186:0] dh = 0; reg [106:0] ss5 = 0; reg [9:0] ag5 = 0; reg [94:0] nret = 95'd1;
    reg kok = 0, kwd = 0;
    wire [452:0] hr; wire [115:0] cmd; wire [1087:0] tl; wire emb_start; wire [17:0] emb_token; wire [55:0] dc; wire cf;
    wire [75:0] pobs, cobs; wire [68:0] dobs; wire csr, cir, lcv; wire [17:0] ntk, nps; wire [5:0] cst; wire [379:0] ncmd;
    qfd_tt_ctlm_dv #(.XPF_TRANSPORT_EDGES(XPF_EDGES), .MUT(MUT), .STAGE_ME(STAGE_ME), .HARD_HR(HARD_HR), .HR_ASBUILT(HRA)) dut (.ck(ck), .rst_n(rst_n),
        .pw(pw), .dh(dh), .kok(kok), .kwd(kwd), .fab(1'b0), .program_obs(pobs), .control_stores_ready(csr),
        .layer_context_v(lcv), .native_tok(ntk), .native_pos(nps), .command_stage(cst), .cal_program_obs(cobs),
        .cal_descriptor_obs(dobs), .cal_image_ready(cir), .dc(dc), .native_cmd(ncmd), .native_ret(nret), .hr(hr),
        .cmd(cmd), .tl(tl), .ss5(ss5), .ag5(ag5), .emb_start(emb_start), .emb_token(emb_token), .cf(cf));
    integer fd, lg, cyc, ncyc, ec, ek, r, pre = 0;
    reg [186:0] ev; reg have; reg [1023:0] evf, lgf; reg csr_l = 0, cf_l = 0; reg [5:0] cst_l = 0;
    initial begin
        if (!$value$plusargs("EV=%s", evf)) $fatal(1, "+EV");
        if (!$value$plusargs("LOG=%s", lgf)) $fatal(1, "+LOG");
        if (!$value$plusargs("NCYC=%d", ncyc)) ncyc = 4000;
        fd = $fopen(evf, "r"); lg = $fopen(lgf, "w"); cyc = 0;
        r = $fscanf(fd, "%d %d %h\n", ec, ek, ev); have = (r == 3);
    end
    wire fix_v = `TB_HEAD.fixed_issue | `TB_HEAD.fixed_end;
    always @(negedge ck) begin
        if (pre < 4) begin pre = pre + 1; if (pre == 4) rst_n = 1'b1; end
        else begin
            if (cmd != 116'd0) $fdisplay(lg, "%0d CMD %h", cyc, cmd);
            if (tl != 1088'd0) $fdisplay(lg, "%0d TL %h", cyc, tl);
            if (dut.c_emb) $fdisplay(lg, "%0d LOC EMB 0", cyc);
            if (dut.c_seg) $fdisplay(lg, "%0d LOC SEG %0d", cyc, dut.c_base);
            if (fix_v) $fdisplay(lg, "%0d ISSUE %0d %0d", cyc, `TB_HEAD.fixed_pc, `TB_HEAD.fixed_unit);
            // QW-DIEFIX 10-19: the go the SLICE reads is hr[452] (gi = {hr[451:73], hr[452]}); as built go sat on hr[73]
            if (hr[452]) $fdisplay(lg, "%0d ROM %h", cyc, hr[452:73]);
            if (hr[73] && !hr[452]) $fdisplay(lg, "%0d ROMRAW %h", cyc, hr[452:73]);
            if (ncmd[0]) $fdisplay(lg, "%0d NAT %h", cyc, ncmd);
            if (hr[1]) $fdisplay(lg, "%0d XPF %h", cyc, hr[72:1]);
            if (csr && !csr_l) $fdisplay(lg, "%0d CSR", cyc);
            if (cf && !cf_l) $fdisplay(lg, "%0d CF head %b reloc %b cp %b start %b xpf_ld %b xpf_sch %b cal %b", cyc,
                `TB_HR.head_fault, `TB_HR.relocation_sticky, dut.cp_fault, dut.start_fault, dut.xpf_loader_fault,
                dut.xpf_schedule_fault, dut.c_fault);
            if (cst != cst_l) $fdisplay(lg, "%0d STAGE %0d", cyc, cst);
            csr_l = csr; cf_l = cf; cst_l = cst;
            // events for the next posedge (cyc + 1)
            pw[74] = 1'b0; dh[186] = 1'b0; dh[118] = 1'b0; dh[42] = 1'b0;
            while (have && ec == cyc + 1) begin
                case (ek)
                    0: begin pw = {1'b1, ev[73:64], ev[63:0]}; dh[118:44] = {1'b1, ev[73:64], ev[63:0]}; end
                    1: dh[186:119] = {1'b1, ev[66:64], ev[63:0]};
                    2: dh[42:0] = ev[42:0];
                    6: begin kok = ev[1]; kwd = ev[0]; end
                    7: ag5 = ev[9:0];
                    8: ss5 = ev[106:0];
                    9: nret = ev[94:0];
                    default: ;
                endcase
                r = $fscanf(fd, "%d %d %h\n", ec, ek, ev); have = (r == 3);
            end
            if (cyc >= ncyc) begin
                $fdisplay(lg, "%0d END cf %b csr %b", cyc, cf, csr);
                $fclose(lg); $finish;
            end
        end
    end
`ifdef TB_LANDED
    // HF-4 10-18: the landed cluster qfd_tt_ctlm_dv_lpf_lp (lp.py) in lockstep with dut on the same compiled stimulus.
    // lp record: landed(rst) == flat(rst delayed RB = 3) with every output 3 edges later, every input on time.  So the
    // landed copy is released 3 edges BEFORE dut and its outputs are compared with dut's 3 edges later.  LMUT = lp MUT.
    parameter integer LMUT = 0;
    localparam integer LOFF = 3;
    reg rst_early = 1'b0;
    wire [452:0] l_hr; wire [115:0] l_cmd; wire l_emb_start; wire [17:0] l_emb_token; wire [55:0] l_dc; wire l_cf;
    wire [75:0] l_pobs, l_cobs; wire [68:0] l_dobs; wire l_csr, l_cir, l_lcv; wire [17:0] l_ntk, l_nps; wire [5:0] l_cst;
    wire [379:0] l_ncmd;
    wire [1087:0] l_tl;
    // MU-DIE-QW 10-19: the regenerated lp is the MU build (default NU 4 / OPSEG 1); this single-user bench runs it at NU 1 / OPSEG 0
    qfd_tt_ctlm_dv_lpf_lp #(.XPF_TRANSPORT_EDGES(XPF_EDGES), .STAGE_ME(STAGE_ME), .MUT(LMUT), .NU(1), .OPSEG(0)) u_lp (.ck_core(ck), .ck_hr(ck),
        .rst_n(rst_early), .pw(pw), .dh(dh), .kok(kok), .kwd(kwd), .fab(1'b0), .program_obs(l_pobs),
        .control_stores_ready(l_csr), .layer_context_v(l_lcv), .native_tok(l_ntk), .native_pos(l_nps), .command_stage(l_cst),
        .cal_program_obs(l_cobs), .cal_descriptor_obs(l_dobs), .cal_image_ready(l_cir), .dc(l_dc), .native_cmd(l_ncmd),
        .native_ret(nret), .hr(l_hr), .cmd(l_cmd), .tl(l_tl), .dh_user(2'd0), .ss5(ss5), .ag5(ag5), .emb_start(l_emb_start), .emb_token(l_emb_token), .cf(l_cf));
    wire [1290:0] v_d = {pobs, csr, lcv, ntk, nps, cst, cobs, dobs, cir, dc, ncmd, hr, cmd, emb_start, emb_token, cf};
    wire [1290:0] v_l = {l_pobs, l_csr, l_lcv, l_ntk, l_nps, l_cst, l_cobs, l_dobs, l_cir, l_dc, l_ncmd, l_hr, l_cmd,
                         l_emb_start, l_emb_token, l_cf};
    reg [1290:0] v_h [0:LOFF-1];
    integer l_nc = 0, l_bad = 0, l_act = 0, hj;
    always @(negedge ck) begin
        if (pre >= 1) rst_early = 1'b1;
        if (pre >= 4 && cyc > LOFF + 2) begin
            l_nc = l_nc + 1;
            if (v_l !== v_h[LOFF-1]) begin l_bad = l_bad + 1;
                if (l_bad <= 5) $fdisplay(lg, "%0d LANDED_MISMATCH dc %h/%h cmd %h/%h hr_lo %h/%h", cyc, v_h[LOFF-1][1024:969],
                    v_l[1024:969], v_h[LOFF-1][135:20], v_l[135:20], v_h[LOFF-1][208:136], v_l[208:136]); end
            if (v_h[LOFF-1] !== v_h[LOFF-2]) l_act = l_act + 1;
            if (cyc == ncyc - 1) $fdisplay(lg, "%0d LANDED_LOCKSTEP %s LMUT=%0d compared=%0d mismatches=%0d active=%0d", cyc,
                (l_bad == 0 && l_nc > 0) ? "PASS" : "FAIL", LMUT, l_nc, l_bad, l_act);
        end
        for (hj = LOFF - 1; hj > 0; hj = hj - 1) v_h[hj] = v_h[hj - 1];
        v_h[0] = v_d;
    end
`endif
    always @(posedge ck) if (pre >= 4) cyc <= cyc + 1;
endmodule
