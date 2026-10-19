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
// Log (+LOG), label = the posedge just taken:
//   "c CMD u hex", "c EMB u tok", "c SEG u base tok pos", "c MES tok pos", "c SUA n", "c HD hex", "c CST stage",
//   "c DC hex" (dc on change), "c STA user stage rng first cnt" (u_cal start consumed at the next posedge),
//   "c FAULT code" (calendar fault rise), "c OPF lcode coll" (op_fault rise / leaf code change), "c END f code sf opf lcode".
module tb_mu_opseg_dv;
    parameter integer NU = 1, MUT = 0, OPSEG = 0;
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
            pw[74] = 1'b0; dh[118] = 1'b0; dh[186] = 1'b0; dh[42] = 1'b0; ss5 = 107'd0;
            while (have && ec == cyc + 1) begin
                case (ek)
                    0: begin pw = {1'b1, ev[73:0]}; dh[118:44] = {1'b1, ev[73:0]}; end
                    1: dh[186:119] = {1'b1, ev[66:0]};
                    2: begin dh[42:0] = ev[42:0]; dh_user = ev[44:43]; end
                    3: begin ss5[24] = 1'b1; ss5[17:0] = ev[17:0]; ss5[27:26] = ev[43:42]; ss5[97:74] = ev[41:18]; end
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
                $fclose(lg);
                $finish;
            end
        end
    end
endmodule
