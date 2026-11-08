`timescale 1ns/1ps
// TOKc-SEGCAL 10-22: the QLB-PROG / QLB-C4b compiled-image bench (rtl/test/qwen_dv/tb_qfd_tt_ctlm_prog.sv, the bench the
// dv-form TOKEN PASS head stage ran) with the DIE FORM as the DUT: the HP13 parent qfd_tt_ctlm_dv_lpf_hp13 (u_gi + the
// h16za native32_1r hard head leaf u_hr, SEGCAL 1 + u_go + u_thru) and, with +define+TB_LANDED, its landed cluster
// qfd_tt_ctlm_dv_lpf_hp13_lp in lockstep (the lp.py record offsets of tb_qfd_tt_ctlm_dv_lpf_hp13_lp: lp reset 3 edges
// early, inputs off_in later, outputs off_out later).  Same stimulus file, same log lines, graded by the same
// tt_ctlm_prog_bench.py checker (img0 123 / imgh 131 checks) -> hp13_prog_bench.py.
// Defines: TB_GO_SEG0 -> u_go SEG_CAL 0 (the go as on main before the port; default 1 = the port); TB_GO_MUT37 -> u_go
// MUT 37 (no segment-G XPF start); +define+TB_TRACE: per-cycle output vector (+TRACE file) for the lockstep vs the dv form.
// Single-user bench configuration (NU 1, OPSEG / CTX / INIT / CALR / F16 off) = the dv bench's qfd_tt_ctlm_dv defaults.
module tb_qfd_tt_ctlm_prog (input wire ck);
    parameter integer MUT = 0, XPF_EDGES = 26, STAGE_ME = 1, HARD_HR = 1, HRA = 0, SEG_CAL = 1;
    reg rst_n = 1'b0;
    reg [74:0] pw = 0; reg [186:0] dh = 0; reg [106:0] ss5 = 0; reg [9:0] ag5 = 0; reg [94:0] nret = 95'd1;
    reg kok = 0, kwd = 0;
    wire [452:0] hr; wire [115:0] cmd; wire emb_start; wire [17:0] emb_token, emb_position; wire [1:0] emb_user;
    wire [55:0] dc; wire cf; wire [1087:0] tl; wire [16:0] f16_st; wire [8:0] table_req;
    wire [75:0] pobs, cobs; wire [68:0] dobs; wire csr, cir, lcv; wire [17:0] ntk, nps; wire [5:0] cst; wire [379:0] ncmd;
    qfd_tt_ctlm_dv_lpf_hp13 #(.XPF_TRANSPORT_EDGES(XPF_EDGES), .STAGE_ME(STAGE_ME), .LAST_STAGE(37), .NU(1)) dut (
        .ck(ck), .rst_n(rst_n), .pw(pw), .dh(dh), .init_u0(1'b0), .ctx_x(129'd0), .mu_fault(1'b0), .dh_user(2'd0),
        .kok(kok), .kwd(kwd), .fab(1'b0), .program_obs(pobs), .control_stores_ready(csr), .layer_context_v(lcv),
        .native_tok(ntk), .native_pos(nps), .command_stage(cst), .cal_program_obs(cobs), .cal_descriptor_obs(dobs),
        .cal_image_ready(cir), .dc(dc), .native_cmd(ncmd), .native_ret(nret), .hr(hr), .cmd(cmd), .tl(tl), .ss5(ss5),
        .ag5(ag5), .emb_start(emb_start), .emb_token(emb_token), .emb_position(emb_position), .emb_user(emb_user), .cf(cf),
        .f16_auth(83'd0), .f16_obs(38'd0), .f16_st(f16_st), .table_req(table_req));
    // u_go SEG_CAL / MUT for the comparison runs (Verilator defparam takes literals): hp13_prog_bench.py adds
    // TB_GO_SEG0 for --segcal 0 (the go as on main before the port) and TB_GO_MUT37 for --mut 37
`ifdef TB_GO_SEG0
    defparam dut.u_go.SEG_CAL = 0;
`endif
`ifdef TB_GO_MUT37
    defparam dut.u_go.MUT = 37;
`endif
    integer fd, lg, cyc, ncyc, ec, ek, r, pre = 0;
    reg [186:0] ev; reg have; reg [1023:0] evf, lgf; reg csr_l = 0, cf_l = 0; reg [5:0] cst_l = 0;
    initial begin
        if (!$value$plusargs("EV=%s", evf)) $fatal(1, "+EV");
        if (!$value$plusargs("LOG=%s", lgf)) $fatal(1, "+LOG");
        if (!$value$plusargs("NCYC=%d", ncyc)) ncyc = 4000;
        fd = $fopen(evf, "r"); lg = $fopen(lgf, "w"); cyc = 0;
        r = $fscanf(fd, "%d %d %h\n", ec, ek, ev); have = (r == 3);
    end
    // the h16za netlist keeps the head's fixed-issue nets (keep=1)
    wire        fix_issue = dut.u_hr.\u_head.fixed_issue ;
    wire        fix_end   = dut.u_hr.\u_head.fixed_end ;
    wire [11:0] fix_pc    = dut.u_hr.\u_head.fixed_pc ;
    wire [1:0]  fix_unit  = dut.u_hr.\u_head.fixed_unit ;
    wire fix_v = fix_issue | fix_end;
    wire [2480:0] v_d = {pobs, csr, lcv, ntk, nps, cst, cobs, dobs, cir, dc, ncmd, hr, cmd, tl, emb_start, emb_token,
                         emb_position, emb_user, cf};
`ifdef TB_TRACE
    integer tr; reg [1023:0] trf;
    initial begin if (!$value$plusargs("TRACE=%s", trf)) trf = "trace.txt"; tr = $fopen(trf, "w"); end
`endif
    always @(negedge ck) begin
        if (pre < 4) begin pre = pre + 1; if (pre == 4) rst_n = 1'b1; end
        else begin
`ifdef TB_TRACE
            $fdisplay(tr, "%0d %h", cyc, v_d);
`endif
            if (cmd != 116'd0) $fdisplay(lg, "%0d CMD %h", cyc, cmd);
            if (dut.u_gi.c_emb) $fdisplay(lg, "%0d LOC EMB 0", cyc);
            if (dut.u_gi.c_seg) $fdisplay(lg, "%0d LOC SEG %0d", cyc, dut.u_gi.c_base);
            if (fix_v) $fdisplay(lg, "%0d ISSUE %0d %0d", cyc, fix_pc, fix_unit);
            if (hr[452]) $fdisplay(lg, "%0d ROM %h", cyc, hr[452:73]);
            if (hr[73] && !hr[452]) $fdisplay(lg, "%0d ROMRAW %h", cyc, hr[452:73]);
            if (ncmd[0]) $fdisplay(lg, "%0d NAT %h", cyc, ncmd);
            if (hr[1]) $fdisplay(lg, "%0d XPF %h", cyc, hr[72:1]);
            if (csr && !csr_l) $fdisplay(lg, "%0d CSR", cyc);
            if (cf && !cf_l) $fdisplay(lg, "%0d CF hr_fault %b cp %b start %b xpf_ld %b xpf_sch %b g %b cal %b", cyc,
                dut.u_go.hr_fault, dut.u_go.cp_fault, dut.u_go.start_fault, dut.u_go.xpf_loader_fault,
                dut.u_go.xpf_schedule_fault, dut.u_go.g_fault, dut.u_go.c_fault);
            if (cst != cst_l) $fdisplay(lg, "%0d STAGE %0d", cyc, cst);
            csr_l = csr; cf_l = cf; cst_l = cst;
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
    // the landed cluster (lp.py, 2 regions, 33 landings): record offsets as tb_qfd_tt_ctlm_dv_lpf_hp13_lp -- lp reset
    // released 3 edges before dut; input p presented DI(p) posedges later; output o compared with dut's DO(o) later.
    // LMUT = the lp mutant (bench: --defs TB_LMUT=N; 4 = u_gi reset run one stage long, 5 = landing rq one edge late)
`ifdef TB_LMUT
    parameter integer LMUT = `TB_LMUT;
`else
    parameter integer LMUT = 0;
`endif
    reg rst_early = 1'b0;
    reg [74:0] d_pw [0:2]; reg kok_d [0:5]; reg kwd_d [0:5]; reg [94:0] nret_d [0:5];
    integer i;
    always @(posedge ck) begin
        d_pw[0] <= pw; kok_d[0] <= kok; kwd_d[0] <= kwd; nret_d[0] <= nret;
        for (i = 1; i < 3; i = i + 1) d_pw[i] <= d_pw[i - 1];
        for (i = 1; i < 6; i = i + 1) begin kok_d[i] <= kok_d[i - 1]; kwd_d[i] <= kwd_d[i - 1]; nret_d[i] <= nret_d[i - 1]; end
    end
    wire [452:0] l_hr; wire [115:0] l_cmd; wire l_emb_start; wire [17:0] l_emb_token, l_emb_position; wire [1:0] l_emb_user;
    wire [55:0] l_dc; wire l_cf; wire [1087:0] l_tl; wire [16:0] l_f16_st; wire [8:0] l_table_req;
    wire [75:0] l_pobs, l_cobs; wire [68:0] l_dobs; wire l_csr, l_cir, l_lcv; wire [17:0] l_ntk, l_nps; wire [5:0] l_cst;
    wire [379:0] l_ncmd;
    qfd_tt_ctlm_dv_lpf_hp13_lp #(.XPF_TRANSPORT_EDGES(XPF_EDGES), .STAGE_ME(STAGE_ME), .LAST_STAGE(37), .NU(1), .MUT(LMUT)) u_lp (
        .ck_core(ck), .ck_hr(ck), .rst_n(rst_early), .pw(d_pw[2]), .dh(dh), .init_u0(1'b0), .ctx_x(129'd0), .mu_fault(1'b0),
        .dh_user(2'd0), .kok(kok_d[5]), .kwd(kwd_d[5]), .fab(1'b0), .program_obs(l_pobs), .control_stores_ready(l_csr),
        .layer_context_v(l_lcv), .native_tok(l_ntk), .native_pos(l_nps), .command_stage(l_cst), .cal_program_obs(l_cobs),
        .cal_descriptor_obs(l_dobs), .cal_image_ready(l_cir), .dc(l_dc), .native_cmd(l_ncmd), .native_ret(nret_d[5]),
        .hr(l_hr), .cmd(l_cmd), .tl(l_tl), .ss5(ss5), .ag5(ag5), .emb_start(l_emb_start), .emb_token(l_emb_token),
        .emb_position(l_emb_position), .emb_user(l_emb_user), .cf(l_cf), .f16_auth(83'd0), .f16_obs(38'd0),
        .f16_st(l_f16_st), .table_req(l_table_req));
`ifdef TB_GO_SEG0
    defparam u_lp.u_go.SEG_CAL = 0;
`elsif TB_LP_SEG0
    defparam u_lp.u_go.SEG_CAL = 0;      // sensitivity witness: only the landed copy loses the port (must FAIL)
`endif
`ifdef TB_GO_MUT37
    defparam u_lp.u_go.MUT = 37;
`endif
    // flat output history (h[k] = k + 1 edges old); off_out 6 for every port but csr 8 and tl 3 (generated tb dlo[5] / [7] / [2])
    wire [1392:0] f_main = {pobs, lcv, ntk, nps, cst, cobs, dobs, cir, dc, ncmd, hr, cmd, emb_start, emb_token, emb_position, emb_user, cf};
    wire [1392:0] l_main = {l_pobs, l_lcv, l_ntk, l_nps, l_cst, l_cobs, l_dobs, l_cir, l_dc, l_ncmd, l_hr, l_cmd, l_emb_start,
                            l_emb_token, l_emb_position, l_emb_user, l_cf};
    reg [1392:0] h_main [0:6]; reg h_csr [0:8]; reg [1087:0] h_tl [0:3];
    always @(posedge ck) begin
        h_main[0] <= f_main; h_csr[0] <= csr; h_tl[0] <= tl;
        for (i = 1; i < 7; i = i + 1) h_main[i] <= h_main[i - 1];
        for (i = 1; i < 9; i = i + 1) h_csr[i] <= h_csr[i - 1];
        for (i = 1; i < 4; i = i + 1) h_tl[i] <= h_tl[i - 1];
    end
    integer l_nc = 0, l_bad = 0;
    always @(negedge ck) begin
        if (pre >= 1) rst_early = 1'b1;
        if (pre >= 4 && cyc > 40) begin
            l_nc = l_nc + 1;
            if (l_main !== h_main[5] || l_csr !== h_csr[7] || l_tl !== h_tl[2]) begin
                l_bad = l_bad + 1;
                if (l_bad <= 5) $fdisplay(lg, "%0d LANDED_MISMATCH main %0d csr %b/%b tl %0d", cyc, l_main !== h_main[5],
                    h_csr[7], l_csr, l_tl !== h_tl[2]);
            end
            if (cyc == ncyc - 1) $fdisplay(lg, "%0d LANDED_LOCKSTEP %s LMUT=%0d compared=%0d mismatches=%0d", cyc,
                (l_bad == 0 && l_nc > 0) ? "PASS" : "FAIL", LMUT, l_nc, l_bad);
        end
    end
`endif
    always @(posedge ck) if (pre >= 4) cyc <= cyc + 1;
endmodule
