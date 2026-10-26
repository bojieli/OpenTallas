`timescale 1ns/1ps
// MU-ADOPT-CTLM bench harness (2026-10-19): qfd_tt_ctlm_dv (HARD_HR 1, STAGE_ME 1 as the die binds it) at NU 1 or 4, driven as qfd_sys_face drives it
// (tt pw + seq_dh program copies, one word an edge, then the run levels + seq_dh_user).  Events (+EV, sorted "cycle kind
// hex", applied before posedge `cycle`):
//   0 PW  {addr 10, data 64} -> tt pw and dh pw (both copies, the same edge)     1 DW {addr 3, data 64} -> dh dw
//   2 RUN {user 2 [44:43], h_start [42], stage 6, tok 18, pos 18} -> dh run levels (h_start one edge) + dh_user
// Log (+LOG), label = the posedge just taken:
//   "c CMD u hex" (cmd != 0; u = the calendar's cmd_user, a label only: the checks compare the WORD), "c EMB tok",
//   "c SEG base tok pos" (ME segment start, base != 0), "c MES tok pos" (ME programme start, base 0), "c SUA n" (head SU
//   accepted count, on change), "c HD hex" (head-side outputs on change: hr, native_cmd / tok / pos, command_stage,
//   layer_context_v, control_stores_ready, program_obs, cf), "c CST stage" (head running stage, on change), "c FAULT code" (calendar fault rise), "c END f code sf".
module tb_mu_ctlm_dv;
    parameter integer NU = 1, MUT = 0;
    reg ck = 1'b0;
    always #5 ck = ~ck;
    reg rst_n = 1'b0;
    reg [74:0] pw = 0; reg [186:0] dh = 0; reg [1:0] dh_user = 0;
    wire [452:0] hr; wire [115:0] cmd; wire emb_start; wire [17:0] emb_token; wire [55:0] dc; wire cf;
    wire [75:0] pobs, cobs; wire [68:0] dobs; wire csr, cir, lcv; wire [17:0] ntk, nps; wire [5:0] cst; wire [379:0] ncmd;
    qfd_tt_ctlm_dv #(.XPF_TRANSPORT_EDGES(1), .MUT(MUT), .NU(NU), .STAGE_ME(1)) dut (.ck(ck), .rst_n(rst_n), .pw(pw), .dh(dh),
        .dh_user(dh_user), .kok(1'b0), .kwd(1'b1), .fab(1'b0), .program_obs(pobs), .control_stores_ready(csr),
        .layer_context_v(lcv), .native_tok(ntk), .native_pos(nps), .command_stage(cst), .cal_program_obs(cobs),
        .cal_descriptor_obs(dobs), .cal_image_ready(cir), .dc(dc), .native_cmd(ncmd), .native_ret(95'd0), .hr(hr),
        .cmd(cmd), .ss5(107'd0), .ag5(10'd0), .emb_start(emb_start), .emb_token(emb_token), .cf(cf));
    wire [1024:0] hd = {hr, ncmd, ntk, nps, cst, lcv, csr, pobs, cf};
    reg  [1024:0] hd_l = 0;
    integer fd, lg, cyc, ncyc, ec, ek, r, pre = 0;
    reg [186:0] ev; reg have; reg [1023:0] evf, lgf; reg flt_l = 0; reg [23:0] sua_l = 0; reg [5:0] cst_l = 0;
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
            if (emb_start) $fdisplay(lg, "%0d EMB %h", cyc, emb_token);
            if (dut.st_h && dut.st_base != 12'd0) $fdisplay(lg, "%0d SEG %h %h %h", cyc, dut.st_base, dut.st_tok, dut.st_pos);
            if (dut.st_h && dut.st_base == 12'd0) $fdisplay(lg, "%0d MES %h %h", cyc, dut.st_tok, dut.st_pos);
            if (dut.su_acc != sua_l) $fdisplay(lg, "%0d SUA %0d", cyc, dut.su_acc);
            if (hd !== hd_l) $fdisplay(lg, "%0d HD %h", cyc, hd);
            if (cst != cst_l) $fdisplay(lg, "%0d CST %0d", cyc, cst);
            cst_l = cst;
            if (dut.u_cal.fault && !flt_l) $fdisplay(lg, "%0d FAULT %b", cyc, dut.u_cal.fault_code);
            flt_l = dut.u_cal.fault; sua_l = dut.su_acc; hd_l = hd;
            // inputs for the next posedge (cyc + 1)
            pw[74] = 1'b0; dh[118] = 1'b0; dh[186] = 1'b0; dh[42] = 1'b0;
            while (have && ec == cyc + 1) begin
                case (ek)
                    0: begin pw = {1'b1, ev[73:0]}; dh[118:44] = {1'b1, ev[73:0]}; end
                    1: dh[186:119] = {1'b1, ev[66:0]};
                    2: begin dh[42:0] = ev[42:0]; dh_user = ev[44:43]; end
                    default: $fatal(1, "bad kind %0d", ek);
                endcase
                r = $fscanf(fd, "%d %d %h\n", ec, ek, ev); have = (r == 3);
            end
            if (have && ec <= cyc) $fatal(1, "event file not sorted at cycle %0d", ec);
            cyc = cyc + 1;
            if (cyc >= ncyc) begin
                $fdisplay(lg, "%0d END %0d %b %0d", cyc, dut.u_cal.fault, dut.u_cal.fault_code, dut.start_fault);
                $fclose(lg);
                $finish;
            end
        end
    end
endmodule
