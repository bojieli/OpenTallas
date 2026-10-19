`timescale 1ns/1ps
// Q-CTLM calendar bench harness: qfd_tt_ctlm_dv driven as qfd_sys_face drives it (tt_pw + seq_dh, one program word an
// edge, then the run levels), optionally with NSL qfd_dv_slice2 on its cmd / hr chain (the W5 .. E5 row) for the SETID
// enumeration.  Events (+EV, sorted): "cycle kind hex" applied before posedge `cycle`:
//   0 PW  {addr 10, data 64}  -> tt pw and dh pw (both program copies, the same edge, as sys_face)
//   1 DW  {addr 3, data 64}   -> dh dw
//   2 RUN {h_start, stage 6, tok 18, pos 18} -> dh run levels (h_start only on this edge, levels held)
//   3 SS  ss5 (one edge; 107 b, Q-DIEPLAN6: tok_val [105:74])
//   4 BEGIN / 5 AUTH {digest 64}: the program record port's sink 1 (qkd_program_commit, as qfd_program_record_port wires
//     the calendar copy: program_obs + descriptor_obs + cal_image_ready) -> "c COMMIT" when it commits, "c SINKF" on fault
// Log (+LOG), label = the posedge just taken: "c CMD hex", "c EMB tok", "c SEG base", "c DC hex" (on change),
// "c READY", "c FAULT" (calendar fault rise), and at the end "c SID k id" per slice, "c CF f".
module tb_qfd_tt_ctlm_cal (input wire ck);
    parameter integer MUT = 0, NSL = 0;
    reg rst_n = 1'b0;
    reg [74:0] pw = 0; reg [186:0] dh = 0; reg [106:0] ss5 = 0;
    wire [452:0] hr; wire [115:0] cmd; wire emb_start; wire [17:0] emb_token; wire [55:0] dc; wire cf;
    wire [75:0] pobs, cobs; wire [68:0] dobs; wire csr, cir, lcv; wire [17:0] ntk, nps; wire [5:0] cst; wire [379:0] ncmd;
    wire [9:0] ag5;
    qfd_tt_ctlm_dv #(.XPF_TRANSPORT_EDGES(1), .MUT(MUT)) dut (.ck(ck), .rst_n(rst_n), .pw(pw), .dh(dh), .kok(1'b0),
        .kwd(1'b1), .fab(1'b0), .program_obs(pobs), .control_stores_ready(csr), .layer_context_v(lcv), .native_tok(ntk),
        .native_pos(nps), .command_stage(cst), .cal_program_obs(cobs), .cal_descriptor_obs(dobs), .cal_image_ready(cir),
        .dc(dc), .native_cmd(ncmd), .native_ret(95'd0), .hr(hr), .cmd(cmd), .ss5(ss5), .ag5(ag5),
        .emb_start(emb_start), .emb_token(emb_token), .cf(cf));
    // ---------------- the slice row (cmd / hr chain; every other input is the idle word)
    wire [115:0] cmdc [0:NSL]; wire [452:0] hrc [0:NSL]; wire [106:0] sst [0:NSL];
    assign cmdc[0] = cmd; assign hrc[0] = hr;
    assign ag5 = 10'd0;
    genvar k;
    generate for (k = 0; k < NSL; k = k + 1) begin : g_s
        qfd_dv_slice2 u (.ck(ck), .rst_n(rst_n), .cmd_i(cmdc[k]), .cmd_o(cmdc[k+1]), .hr_i(hrc[k]), .hr_o(hrc[k+1]),
            .rs_s(1028'd0), .rs_n(1028'd0), .l9_i(514'd0), .l9_o(), .st_up_i(1088'd0), .st_up_o(), .st_dn_i(1088'd0),
            .st_dn_o(), .sc_up_i(48'd0), .sc_up_o(), .sc_dn_i(48'd0), .sc_dn_o(), .ch_up_i(1094'd0), .ch_dn_o(),
            .ch_dn_i(1038'd0), .ch_up_o(), .cw_n0(), .cw_n1(), .cw_n2(), .cw_n3(), .cw_s0(), .cw_s1(), .cw_s2(), .cw_s3(),
            .st(sst[k]));
    end endgenerate
    reg bg_v = 0, au_v = 0; reg [63:0] au_d = 0; wire sk_ready, sk_fault;
    qkd_program_commit u_sink (.ck(ck), .rst_n(rst_n), .execution_active(1'b0), .control_stores_ready(cir),
        .begin_v(bg_v), .begin_epoch(16'd5), .expected_pw(11'd1024), .expected_dw(4'd8), .auth_v(au_v), .auth_epoch(16'd5),
        .auth_digest(au_d), .pw_v(cobs[75]), .pw_full_word(cobs[74]), .pw_addr(cobs[73:64]), .pw_data(cobs[63:0]),
        .dw_v(dobs[68]), .dw_full_word(dobs[67]), .dw_addr(dobs[66:64]), .dw_data(dobs[63:0]), .commit_v(), .ready(sk_ready),
        .fault(sk_fault), .installed_fusedcap(), .commit_epoch(), .commit_digest());
    reg sk_l = 0, skf_l = 0;
    integer fd, lg, cyc, ncyc, ec, ek, r, pre = 0, i;
    reg [186:0] ev; reg have; reg [1023:0] evf, lgf; reg [55:0] dc_l = 0; reg rdy_l = 0, flt_l = 0;
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
            if (cmd != 116'd0) $fdisplay(lg, "%0d CMD %h", cyc, cmd);
            if (emb_start) $fdisplay(lg, "%0d EMB %h", cyc, emb_token);
            if (dut.st_h && dut.st_base != 12'd0) $fdisplay(lg, "%0d SEG %h", cyc, dut.st_base);
            if (dc != dc_l) $fdisplay(lg, "%0d DC %h", cyc, dc);
            if (cir && !rdy_l) $fdisplay(lg, "%0d READY", cyc);
            if (dut.u_cal.fault && !flt_l) $fdisplay(lg, "%0d FAULT", cyc);
            if (sk_ready && !sk_l) $fdisplay(lg, "%0d COMMIT", cyc);
            if (sk_fault && !skf_l) $fdisplay(lg, "%0d SINKF", cyc);
            sk_l = sk_ready; skf_l = sk_fault;
            dc_l = dc; rdy_l = cir; flt_l = dut.u_cal.fault;
            // inputs for the next posedge (cyc + 1)
            pw[74] = 1'b0; dh[118] = 1'b0; dh[186] = 1'b0; dh[42] = 1'b0; ss5 = 107'd0; bg_v = 0; au_v = 0;
            while (have && ec == cyc + 1) begin
                case (ek)
                    0: begin pw = {1'b1, ev[73:0]}; dh[118:44] = {1'b1, ev[73:0]}; end
                    1: dh[186:119] = {1'b1, ev[66:0]};
                    2: dh[42:0] = ev[42:0];
                    3: ss5 = ev[106:0];
                    4: bg_v = 1;
                    5: begin au_v = 1; au_d = ev[63:0]; end
                    default: $fatal(1, "bad kind %0d", ek);
                endcase
                r = $fscanf(fd, "%d %d %h\n", ec, ek, ev); have = (r == 3);
            end
            if (have && ec <= cyc) $fatal(1, "event file not sorted at cycle %0d", ec);
            cyc = cyc + 1;
            if (cyc >= ncyc) begin
                for (i = 0; i < NSL; i = i + 1) $fdisplay(lg, "%0d SID %0d %0d", cyc, i, sst[i][73:70]);
                $fdisplay(lg, "%0d CF %0d %0d", cyc, cf, dut.u_cal.fault);
                $fclose(lg);
                $finish;
            end
        end
    end
endmodule
