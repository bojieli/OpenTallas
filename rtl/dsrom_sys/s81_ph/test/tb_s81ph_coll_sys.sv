`timescale 1ns/1ps
// tb_s81ph_coll_sys (CLAUDE S81-PH collective): a 4-die TP4 group (ranks 0..3, packages {0,1} {2,3}) of
// dsfd_sp_collective slabs, every lane a raw 512-b beat channel (ot_dsrom_link_chan: delay, deterministic bit
// flips -- the link macros are hard IP), against the REFERENCE = four ot_w15_rom_oneshot_die_px_acceptedpop built
// with RANK = 0..3 (the C8 parent's parameters) wired directly as in the C8 die model.  Each die's VM model sends the
// same message plan (mode, words, last, tag) with its own FP32 data (specials included) under the contract's
// credits, plus pass-through flits on lanes W3/E0..E3; it accepts t_vm beats under random ts backpressure.
// CHECK: per die, every reduce word (data, last; err OR per beat) and every all-gather beat equals the reference
// engine of that rank, in order; every pass-through flit arrives in order at the partner die; no fault.
// PASS line "TB_S81PH_COLL_SYS PASS".  +define+TB_CTRL (s81-ctl-1011): the slabs are dsfd_sp_collective_c driven by
// the real stage sequencer (block TB_CTRL below).  Cycle report: the last result cycle of DUT and reference.
module tb_s81ph_coll_sys;
    parameter integer SPEC = 1, FIXW = 0, FIXM = -1, PERF = 0, NM = 40, MAXW = 12, NPT = 30, CHB = 60, CHU = 12, EPER = 97, SEED = 7, TSR = 7,
                      WARM = 20,   // VM sends nothing before this cycle (pricing: links trained before the first collective)
                      // TB_MTP (mtp-colllane-1011): the dedicated MTP lane W4 (dies d <-> d ^ 1, board channel CHB) with the
                      // head-die sequencer's token / seed / accept traffic at the real 8 / 8 hub stations; MSTALL see
                      // tb_mtp_lane_io.  MTP_HOLD: cycles to wait for MTP after the collective is complete.
                      NTOK = 300, NSEED = 80, NACC = 24, MSTALL = 0, MTP_HOLD = 40000, TGAP = 0,
                      MAXCYC = 400000;   // bench time-out (cycles)
    localparam integer FW = 512, PW = 547, W = 552;
    reg [63:0] rs = 64'h243F6A8885A308D3 ^ SEED;
    function [31:0] rnd(input integer d);
        begin rs = rs ^ (rs << 13); rs = rs ^ (rs >> 7); rs = rs ^ (rs << 17); rnd = rs[31:0]; end
    endfunction
    function [31:0] fp(input integer d);
        reg [31:0] r; begin
            r = rnd(0);
            case (SPEC ? rnd(0) % 64 : 63)
                0: fp = 32'h7F80_0000; 1: fp = 32'hFF80_0000; 2: fp = 32'h7FC0_0000; 3: fp = 32'h8000_0000;
                4: fp = 32'h0000_0000; 5: fp = {r[31], 8'd0, r[22:0]}; 6: fp = {r[31], 8'hFE, r[22:0]};
                default: fp = {r[31], 8'd100 + r[30:24] % 8'd56, r[22:0]};
            endcase
        end
    endfunction
    // ------------------------------------------------------------------ message plan
    integer nmw [0:NM-1]; reg nmm [0:NM-1];
    integer TOT;
    reg [FW-1:0] own [0:3][0:NM*MAXW-1];
    reg ownl [0:NM*MAXW-1]; reg ownm [0:NM*MAXW-1]; reg [31:0] ownt [0:NM*MAXW-1];
    integer first_send_cyc = -1;
    reg [W-1:0] ptd [0:3][0:4][0:NPT-1]; reg ptl [0:3][0:4][0:NPT-1];
    integer i, j, k, d, l;
    initial begin
        TOT = 0;
        for (i = 0; i < NM; i = i + 1) begin
            nmw[i] = FIXW ? FIXW : 1 + rnd(0) % MAXW; nmm[i] = (FIXM >= 0) ? FIXM[0] : (rnd(0) % 3 == 0);
            for (j = 0; j < nmw[i]; j = j + 1) begin
                ownl[TOT] = (j == nmw[i] - 1); ownm[TOT] = nmm[i]; ownt[TOT] = i * 16 + j;
                for (d = 0; d < 4; d = d + 1) for (k = 0; k < 16; k = k + 1) own[d][TOT][32*k +: 32] = fp(0);
                TOT = TOT + 1;
            end
        end
        for (d = 0; d < 4; d = d + 1) for (l = 0; l < 5; l = l + 1) for (i = 0; i < NPT; i = i + 1) begin
            for (k = 0; k < W; k = k + 32) ptd[d][l][i][k +: 32] = rnd(0);
            ptl[d][l][i] = rnd(0);
        end
    end
    // ------------------------------------------------------------------ clocks
    reg refclk = 0; always #5 refclk = ~refclk;
    reg por = 0;
    initial begin #50 por = 1; end
    wire [3:0] cks;
    wire clk = cks[0];
    // ------------------------------------------------------------------ DUT dies
    wire [514:0] rx [0:3][0:7];
    wire [511:0] tx [0:3][0:7];
    wire [3:0] rsts;
    reg  [591:0] fvm [0:3];
    reg  [2:0] tsr [0:3];
    wire [2099:0] tvm [0:3];
    wire [511:0] mtx [0:3];
    // TB_CTRL (s81-ctl-1011): engine-3 die nets between the controller (ot_s81_stage_seq) and the slab
    wire [84:0] c3a [0:3]; wire [8:0] d3a [0:3]; wire [1:0] csta [0:3];
`ifdef TB_CTRL
`ifdef TB_MTP
    initial $fatal(1, "TB_CTRL with TB_MTP: dsfd_sp_collective_c has no MTP-lane ports yet");
`endif
`endif
    genvar gd, gl;
    generate for (gd = 0; gd < 4; gd = gd + 1) begin : g_die
        wire tf0, tf1, tf2, tf3, tf4, tf5, tf6, tf7;
`ifdef TB_CTRL
        dsfd_sp_collective_c u (.refclk(refclk), .por(por), .f_vm(fvm[gd]), .ts(tsr[gd]),
            .c_cmd(c3a[gd]), .c_done(d3a[gd]), .c_st(csta[gd]),
`else
        dsfd_sp_collective u (.refclk(refclk), .por(por), .f_vm(fvm[gd]), .ts(tsr[gd]),
`endif
            .rW0(rx[gd][0]), .rW1(rx[gd][1]), .rW2(rx[gd][2]), .rW3(rx[gd][3]),
            .rE0(rx[gd][4]), .rE1(rx[gd][5]), .rE2(rx[gd][6]), .rE3(rx[gd][7]),
            .pll_stream(cks[gd]), .pll_serial(), .pll_hbm(), .rst_stream(rsts[gd]), .rst_serial(), .rst_hbm(),
            .t_vm(tvm[gd]),
            .tdW0(tx[gd][0]), .tdW1(tx[gd][1]), .tdW2(tx[gd][2]), .tdW3(tx[gd][3]),
            .tdE0(tx[gd][4]), .tdE1(tx[gd][5]), .tdE2(tx[gd][6]), .tdE3(tx[gd][7]),
            .tfW0(tf0), .tfW1(tf1), .tfW2(tf2), .tfW3(tf3), .tfE0(tf4), .tfE1(tf5), .tfE2(tf6), .tfE3(tf7)
`ifdef TB_MTP
            , .f_mtp(fmtp), .t_mtp(tmtp), .rW4(mrx), .tdW4(mtx[gd]), .tfW4(), .t_mrt(mrt), .f_mrt(fmrt), .t_mrs(mrs),
            .f_mrs(fmrs), .t_macc(macc)
`endif
            );
`ifdef TB_MTP
        wire [647:0] fmtp; wire [1:0] tmtp; wire [514:0] mrx; wire [512:0] mrt; wire [77:0] mrs; wire [56:0] macc;
        wire fmrt, fmrs, mov; wire [511:0] mod;
        ot_dsrom_link_chan #(.W(512), .MAXD(CHB), .ERR_PERIOD(EPER), .ERR_OFFSET(gd * 8 + 8), .ERR_STRIDE(37)) u_mch (
            .clk(clk), .rst_n(rsts[gd ^ 1]), .delay(16'd0), .in_valid(rsts[gd ^ 1]), .in_data(mtx[gd ^ 1]),
            .out_valid(mov), .out_data(mod), .err_injected());
        assign mrx = {1'b0, 1'b1, mod, mov};
        integer tok_rx, seed_rx, acc_rx, tok_tx, seed_tx, acc_tx, merrs, tf_tx, tf_rx, tl_rx, tm_rx;
        tb_mtp_lane_io #(.DIE(gd), .NTOK(NTOK), .NSEED(NSEED), .NACC(NACC), .MSTALL(MSTALL), .TGAP(TGAP)) u_io (
            .clk(clk), .rst_n(rsts[gd]), .cyc(cyc), .f_mtp(fmtp), .t_mtp(tmtp), .t_mrt(mrt), .f_mrt(fmrt), .t_mrs(mrs),
            .f_mrs(fmrs), .t_macc(macc), .tok_rx(tok_rx), .seed_rx(seed_rx), .acc_rx(acc_rx), .tok_tx(tok_tx),
            .seed_tx(seed_tx), .acc_tx(acc_tx), .errs(merrs), .tok_first_tx(tf_tx), .tok_first_rx(tf_rx), .tok_last_rx(tl_rx), .tok_mid_rx(tm_rx));
`endif
        for (gl = 0; gl < 8; gl = gl + 1) begin : g_lane
            // lane gl of die gd receives lane gl of die gd ^ X(gl)
            localparam integer X = (gl == 0) ? 1 : (gl == 1) ? 2 : (gl == 2) ? 3 : (gl == 6) ? 2 : (gl == 7) ? 3 : 1;
            localparam integer DL = (gl == 0 || gl == 4) ? CHU : CHB;
            wire ov; wire [511:0] od;
            ot_dsrom_link_chan #(.W(512), .MAXD(DL), .ERR_PERIOD(EPER), .ERR_OFFSET(gd * 8 + gl), .ERR_STRIDE(37)) u_ch (
                .clk(clk), .rst_n(rsts[gd ^ X]), .delay(16'd0), .in_valid(rsts[gd ^ X]), .in_data(tx[gd ^ X][gl]),
                .out_valid(ov), .out_data(od), .err_injected());
            assign rx[gd][gl] = {1'b0, 1'b1, od, ov};
        end
    end endgenerate
    // ------------------------------------------------------------------ reference engines (C8 parameters)
    reg  [3:0] r_iv; wire [3:0] r_ir;
    wire [3:0] r_txv [0:3]; wire [PW-1:0] r_txr [0:3]; wire [7:0] r_cro [0:3];
    wire [3:0] r_ov, r_ol, r_oe; wire [4*FW-1:0] r_od [0:3];
    integer rptr [0:3];
    generate for (gd = 0; gd < 4; gd = gd + 1) begin : g_ref
        wire [3:0] rxv; wire [4*PW-1:0] rxr; wire [7:0] cri;
        for (gl = 0; gl < 4; gl = gl + 1) begin : g_s
            assign rxv[gl] = (gl == gd) ? 1'b0 : r_txv[gl][gd];
            assign rxr[gl*PW +: PW] = (gl == gd) ? {PW{1'b0}} : r_txr[gl];
            assign cri[2*gl +: 2] = (gl == gd) ? 2'b00 : r_cro[gl][2*gd +: 2];
        end
        ot_w15_rom_oneshot_die_px_acceptedpop #(.FIX_ACCEPTED_POP(1), .N(4), .RANK(gd), .LANES(16), .TAGW(32),
            .DEPTH(256), .PKG_DIES(2), .RELAY(0), .ADD_LAT(3), .PAIRWISE(1), .GW(4), .OUT_BP(1)) u (
            .clk(clk), .rst_n(rsts[0]),
            .in_valid(r_iv[gd]), .in_ready(r_ir[gd]), .in_data(own[gd][rptr[gd]]), .in_last(ownl[rptr[gd]]),
            .in_mode(ownm[rptr[gd]]), .in_tag(ownt[rptr[gd]]),
            .tx_valid(r_txv[gd]), .tx_rec(r_txr[gd]), .tx_ready(4'hF), .cr_in(cri),
            .rx_valid(rxv), .rx_rec(rxr), .cr_out(r_cro[gd]),
            .rl_tx_valid(), .rl_tx_rec(), .rl_rx_valid(4'd0), .rl_rx_rec({4*PW{1'b0}}),
            .out_valid(r_ov[gd]), .out_ready(1'b1), .out_data(r_od[gd]), .out_last(r_ol[gd]), .out_rank(),
            .out_err(r_oe[gd]), .fault(), .fault_code());
    end endgenerate
    // reference outputs recorded in order: reduce words {err, last, data} and gather beats
    reg [4*FW+1:0] rq [0:3][0:NM*MAXW];  // {gather, last, data}; err separately
    reg            rqe [0:3][0:NM*MAXW];
    integer rn [0:3], r_last_cyc;
    integer ridx [0:3];                  // plan index of the next reference output (one output per record)
    integer cyc, rp_n;
    integer cdone_cyc = -1;           // the cycle the collective traffic is complete
`ifdef TB_FVM_TRACE
    integer tf_n [0:3]; initial for (integer i = 0; i < 4; i = i + 1) tf_n[i] = 0;
    always @(posedge clk) begin
        for (integer i = 0; i < 4; i = i + 1) tf_n[i] = tf_n[i] + fvm[i][0];
        if (cyc == 25 || cyc == 30 || cyc == 3000 || (cyc >= 1105 && cyc <= 1120))
            $display("TBGRD t=%0t cyc=%0d tf0=%0d rsts0=%b warm=%0d cfgd0=%0d fvm00=%b sp0=%0d cr00=%0d", $time, cyc, tf_n[0], rsts[0], WARM, cfgd[0],
                     fvm[0][0], sp[0], cr[0][0]);
        if (cyc % 50000 == 3000) $display("TBFVM cyc=%0d rsts=%b sent=%0d %0d %0d %0d slab0_fvm=%b", cyc, rsts, tf_n[0], tf_n[1],
                                          tf_n[2], tf_n[3], g_die[0].u.f_vm[0]);
    end
`endif
    always @(posedge clk) begin
        cyc <= cyc + 1;
        for (d = 0; d < 4; d = d + 1) begin
            if (r_ov[d]) begin
                rq[d][rn[d]] = {ownm[ridx[d]], r_ol[d], r_od[d]}; rqe[d][rn[d]] = r_oe[d]; rn[d] = rn[d] + 1; ridx[d] = ridx[d] + 1;
                r_last_cyc = cyc;
            end
`ifdef TB_S81PH_MUT_REFRACE
            // negative control: the v1..v3 reference driver (a blocking pointer update read by the engine's
            // continuous inputs in the same edge -- a race; dropped a record at 256 / 1024 records)
            if (r_iv[d] && r_ir[d]) rptr[d] = rptr[d] + 1;
            r_iv[d] <= rsts[0] && (first_send_cyc >= 0) && (rptr[d] + ((r_iv[d] && r_ir[d]) ? 1 : 0) < TOT);
`else
            // CLAUDE S81-PH coll v4 (2026-10-07): the reference input pointer is a register (nonblocking), so the
            // engine samples in_data / in_last / in_mode of the record it accepts on this edge
            rp_n = rptr[d] + ((r_iv[d] && r_ir[d]) ? 1 : 0);
            rptr[d] <= rp_n;
            r_iv[d] <= rsts[0] && (first_send_cyc >= 0) && (rp_n < TOT);
`endif
        end
    end
    // the reference engine's output kind: gather beats are the outputs of mode-1 indices, in index order
    // ------------------------------------------------------------------ VM models
    integer cr [0:3][0:5];               // credits per input queue
    integer sp [0:3];                    // next own record to send
    integer pts [0:3][0:4];              // pass-through flits sent per lane
    integer ptr_ [0:3][0:4];             // pass-through flits received per lane
    integer dn [0:3];                    // DUT outputs (words / beats) checked
    integer errs, d_last_cyc, cfgd [0:3];
    reg [2099:0] b;
    reg [591:0]  nf;   // next f_vm word of the die being driven: ONE nonblocking write per die per cycle
    integer nwv, q;
    reg acc_err;
    initial begin
        errs = 0; cyc = 0; r_last_cyc = 0; d_last_cyc = 0;
        for (d = 0; d < 4; d = d + 1) begin
            rptr[d] = 0; rn[d] = 0; ridx[d] = 0; sp[d] = 0; dn[d] = 0; cfgd[d] = 0; fvm[d] = 0; tsr[d] = 0;
            for (q = 0; q < 6; q = q + 1) cr[d][q] = (q == 0) ? 16 : 8;
            for (l = 0; l < 5; l = l + 1) begin pts[d][l] = 0; ptr_[d][l] = 0; end
        end
        r_iv = 0;
    end
    always @(posedge clk) begin
        for (d = 0; d < 4; d = d + 1) begin
            // ---- consume t_vm
            b = tvm[d];
            if (b[0]) begin
                for (q = 0; q < 6; q = q + 1) cr[d][q] = cr[d][q] + b[17 + 4*q +: 4];
                // the engine's arithmetic flag (out_err on Inf / NaN operands) raises the slab fault exactly as the
                // reference engine's fault; any other fault source is an error
                if (b[41] && (b[49:42] & ~(SPEC ? 8'b0000_1000 : 8'b0)) != 0) begin
                    errs = errs + 1; if (errs < 20) $display("DIE %0d FAULT vec %b", d, b[49:42]); end
                if (b[2:1] == 2'd1) begin
                    d_last_cyc = cyc;
                    if (b[15]) begin
                        if (dn[d] >= rn[d] || rq[d][dn[d]] !== {1'b1, b[13], b[52 +: 4*FW]}) begin
                            errs = errs + 1; if (errs < 20) $display("DIE %0d GATHER beat %0d mismatch", d, dn[d]); end
                        dn[d] = dn[d] + 1;
                    end else begin
                        nwv = b[6] + b[7] + b[8] + b[9]; acc_err = 0;
                        for (k = 0; k < nwv; k = k + 1) begin
                            if (dn[d] >= rn[d] || rq[d][dn[d]] !== {1'b0, b[10 + k], {3*FW{1'b0}}, b[52 + k*FW +: FW]}) begin
                                errs = errs + 1; if (errs < 20) $display("DIE %0d REDUCE word %0d mismatch", d, dn[d]); end
                            acc_err = acc_err | rqe[d][dn[d]];
                            dn[d] = dn[d] + 1;
                        end
                        if (acc_err !== b[16]) begin errs = errs + 1; if (errs < 20) $display("DIE %0d err flag", d); end
                    end
                end else if (b[2:1] == 2'd2) begin
                    l = b[5:3];
                    begin : chk
                        integer src; src = d ^ ((l == 3) ? 2 : (l == 4) ? 3 : 1);
                        if (ptr_[d][l] >= NPT || {b[14], b[52 +: W]} !== {ptl[src][l][ptr_[d][l]], ptd[src][l][ptr_[d][l]]}) begin
                            errs = errs + 1; if (errs < 20) $display("DIE %0d PT lane %0d flit %0d mismatch", d, l, ptr_[d][l]); end
                    end
                    ptr_[d][l] = ptr_[d][l] + 1;
                end
            end
            tsr[d] <= {2'b01, (rnd(0) % 8) < TSR};
            // ---- send (one word a cycle): config, then engine records / pass-through flits by credits
            nf = 0;
            if (rsts[d] && cyc > WARM) begin
                if (cfgd[d] < 2) begin
                    cfgd[d] = cfgd[d] + 1;
                    if (cfgd[d] == 2) nf = {{(W-3){1'b0}}, 1'b1, d[1:0], 32'd0, 1'b0, 1'b0, 3'd0, 2'd3, 1'b1};
                end else begin
                    q = PERF ? ((sp[d] < TOT) ? 0 : 1 + rnd(0) % 5) : rnd(0) % 6;
                    if (q == 0 && cr[d][0] > 0 && sp[d] < TOT) begin
                        nf = {{(W-FW){1'b0}}, own[d][sp[d]], ownt[sp[d]], ownm[sp[d]], ownl[sp[d]], 3'd0, 2'd1, 1'b1};
                        if (first_send_cyc < 0) first_send_cyc = cyc;
                        sp[d] = sp[d] + 1; cr[d][0] = cr[d][0] - 1;
                    end else if (q != 0 && cr[d][q] > 0 && pts[d][q-1] < NPT) begin
                        nf = {ptd[d][q-1][pts[d][q-1]], 32'd0, 1'b0, ptl[d][q-1][pts[d][q-1]], 3'(q - 1), 2'd2, 1'b1};
                        pts[d][q-1] = pts[d][q-1] + 1; cr[d][q] = cr[d][q] - 1;
                    end
                end
            end
            fvm[d] <= nf;
        end
        // ---- end
        if (cdone_cyc < 0 && cyc > 1000 && dn[0] == rn[0] && dn[1] == rn[1] && dn[2] == rn[2] && dn[3] == rn[3] &&
             rn[0] > 0 && ridx[0] == TOT_IDX() && all_pt()) cdone_cyc = cyc;
        if (cyc > MAXCYC || (cdone_cyc >= 0 && ((mtp_done() && ctrl_done()) || cyc > cdone_cyc + MTP_HOLD))) begin
            mtp_end(); ctrl_end();
            for (d = 0; d < 4; d = d + 1) if (dn[d] != rn[d] || ridx[d] != TOT_IDX()) begin
                errs = errs + 1; $display("DIE %0d INCOMPLETE dut %0d ref %0d of %0d", d, dn[d], rn[d], TOT_IDX()); end
            if (!all_pt()) begin errs = errs + 1; $display("PT INCOMPLETE"); end
`ifdef OT_S81PH_COLL_CES_SPLIT
            // COVERAGE REFUSAL (s81-cesn 2026-10-13): the split lane-slices must be IN the build (4 ces0 + 12 cesn
            // parents) and every seam of both parents must have carried beats, the same number in every slice
            // (lockstep: ces0 x 3 = cesn); otherwise a pass says nothing about the split and is refused.
            begin : cov
                integer k, i, bad;
                bad = 0;
                if (s81ph_ces_cov::inst[0] != 4 || s81ph_ces_cov::inst[1] != 12) bad = bad + 1;
                for (k = 0; k < 2; k = k + 1) begin
                    if (s81ph_ces_cov::ln[k] == 0 || s81ph_ces_cov::lny[k] == 0 || s81ph_ces_cov::ow[k] == 0 ||
                        s81ph_ces_cov::bw[k] == 0) bad = bad + 1;
                    for (i = 1; i < 4; i = i + 1) if (s81ph_ces_cov::xl[k][i] == 0 || s81ph_ces_cov::xli[k][i] == 0) bad = bad + 1;
                    for (i = 0; i < 5; i = i + 1) if (s81ph_ces_cov::pt[k][i] == 0 || s81ph_ces_cov::pti[k][i] == 0) bad = bad + 1;
                end
                if (s81ph_ces_cov::ln[1] != 3 * s81ph_ces_cov::ln[0] || s81ph_ces_cov::lny[1] != 3 * s81ph_ces_cov::lny[0] ||
                    s81ph_ces_cov::ow[1] != 3 * s81ph_ces_cov::ow[0] || s81ph_ces_cov::bw[1] != 3 * s81ph_ces_cov::bw[0]) bad = bad + 1;
                for (i = 1; i < 4; i = i + 1) if (s81ph_ces_cov::xl[1][i] != 3 * s81ph_ces_cov::xl[0][i]) bad = bad + 1;
                for (i = 0; i < 5; i = i + 1) if (s81ph_ces_cov::pt[1][i] != 3 * s81ph_ces_cov::pt[0][i]) bad = bad + 1;
                $display("COV split parents %0d + %0d; ces0: ln %0d lny %0d xl %0d %0d %0d pt %0d %0d %0d %0d %0d ow %0d bw %0d; cesn: ln %0d lny %0d xl %0d %0d %0d pt %0d %0d %0d %0d %0d ow %0d bw %0d",
                    s81ph_ces_cov::inst[0], s81ph_ces_cov::inst[1],
                    s81ph_ces_cov::ln[0], s81ph_ces_cov::lny[0], s81ph_ces_cov::xl[0][1], s81ph_ces_cov::xl[0][2], s81ph_ces_cov::xl[0][3],
                    s81ph_ces_cov::pt[0][0], s81ph_ces_cov::pt[0][1], s81ph_ces_cov::pt[0][2], s81ph_ces_cov::pt[0][3], s81ph_ces_cov::pt[0][4],
                    s81ph_ces_cov::ow[0], s81ph_ces_cov::bw[0],
                    s81ph_ces_cov::ln[1], s81ph_ces_cov::lny[1], s81ph_ces_cov::xl[1][1], s81ph_ces_cov::xl[1][2], s81ph_ces_cov::xl[1][3],
                    s81ph_ces_cov::pt[1][0], s81ph_ces_cov::pt[1][1], s81ph_ces_cov::pt[1][2], s81ph_ces_cov::pt[1][3], s81ph_ces_cov::pt[1][4],
                    s81ph_ces_cov::ow[1], s81ph_ces_cov::bw[1]);
                if (bad != 0) begin errs = errs + 1; $display("TB_S81PH_COLL_SYS FAIL coverage: %0d split-seam coverage conditions unmet", bad); end
            end
`endif
            $display("CYCLES dut_last %0d ref_last %0d first_send %0d records %0d messages %0d coll_done %0d", d_last_cyc, r_last_cyc, first_send_cyc, TOT, NM, cdone_cyc);
            if (errs == 0) $display("TB_S81PH_COLL_SYS PASS"); else $display("TB_S81PH_COLL_SYS FAIL errs %0d", errs);
            $finish;
        end
    end
`ifdef TB_MTP
    // every die's MTP streams are complete: tokens (unless both consumers are stalled forever), seeds (unless the
    // seed consumer is), accept events (always: they need no consumer)
    function mtp_done();
        mtp_done = mtp_die_done(g_die[0].tok_rx, g_die[0].seed_rx, g_die[0].acc_rx) && mtp_die_done(g_die[1].tok_rx, g_die[1].seed_rx, g_die[1].acc_rx) &&
                   mtp_die_done(g_die[2].tok_rx, g_die[2].seed_rx, g_die[2].acc_rx) && mtp_die_done(g_die[3].tok_rx, g_die[3].seed_rx, g_die[3].acc_rx);
    endfunction
    function mtp_die_done(input integer t, input integer s_, input integer a);
        mtp_die_done = (MSTALL == 2 || t == NTOK) && (MSTALL == 1 || MSTALL == 2 || s_ == NSEED) && a == NACC;
    endfunction
    task mtp_end();
        integer dd, t, s_, a, e, ttx, ftx, frx, lrx, mdr;
        for (dd = 0; dd < 4; dd = dd + 1) begin
            case (dd)
                0: begin t = g_die[0].tok_rx; s_ = g_die[0].seed_rx; a = g_die[0].acc_rx; e = g_die[0].merrs; ttx = g_die[1].tok_tx; ftx = g_die[1].tf_tx; frx = g_die[0].tf_rx; lrx = g_die[0].tl_rx; mdr = g_die[0].tm_rx; end
                1: begin t = g_die[1].tok_rx; s_ = g_die[1].seed_rx; a = g_die[1].acc_rx; e = g_die[1].merrs; ttx = g_die[0].tok_tx; ftx = g_die[0].tf_tx; frx = g_die[1].tf_rx; lrx = g_die[1].tl_rx; mdr = g_die[1].tm_rx; end
                2: begin t = g_die[2].tok_rx; s_ = g_die[2].seed_rx; a = g_die[2].acc_rx; e = g_die[2].merrs; ttx = g_die[3].tok_tx; ftx = g_die[3].tf_tx; frx = g_die[2].tf_rx; lrx = g_die[2].tl_rx; mdr = g_die[2].tm_rx; end
                default: begin t = g_die[3].tok_rx; s_ = g_die[3].seed_rx; a = g_die[3].acc_rx; e = g_die[3].merrs; ttx = g_die[2].tok_tx; ftx = g_die[2].tf_tx; frx = g_die[3].tf_rx; lrx = g_die[3].tl_rx; mdr = g_die[3].tm_rx; end
            endcase
            $display("MTP DIE %0d rx tokens %0d / %0d (peer sent %0d) seeds %0d / %0d accepts %0d / %0d errs %0d first_tok_latency %0d last_tok %0d second_half_tokens %0d in %0d cycles",
                     dd, t, NTOK, ttx, s_, NSEED, a, NACC, e, frx - ftx, lrx, NTOK - NTOK / 2, lrx - mdr);
            errs = errs + e;
            if (!mtp_die_done(t, s_, a)) begin errs = errs + 1; $display("MTP DIE %0d INCOMPLETE", dd); end
            if (MSTALL == 1 && s_ != 0) begin errs = errs + 1; $display("MTP DIE %0d seed consumer stalled but received", dd); end
        end
    endtask
`else
    function mtp_done(); mtp_done = 1'b1; endfunction
    task mtp_end(); endtask
`endif
`ifdef TB_CTRL
    // ------------------------------------------------------------------ TB_CTRL (s81-ctl-1011): real control
    // Per die: ot_s81_stage_seq (the dsfd_sp_ctrl sequencer: NOPS 128, 12 ports, QD 8) holds the stage program = one
    // coll job per message {eng 3, arg {mode, records}} and issues the descriptors under credits; the slab's coll
    // endpoint (ot_s81_coll_job inside dsfd_sp_collective_c) releases a message's records only under its descriptor
    // and returns the done when the message's last result leaves the slab.  CHECKS (in addition to the data): every
    // done tag = {slot 0, op k} in program order, done k never before message k's last result left t_vm, exactly NM
    // dones, one job_done after the last, no command on any other port, no endpoint / sequencer fault, online.
    // Mutants: TB_MUT_DROPSTART (die 0's 5th coll command never reaches the slab), TB_MUT_WRONGDESC (die 0's 3rd
    // descriptor names one record more), +define+OT_S81PH_COLL_JOB_MUT=5 (early done: the endpoint done on the first result beat).
    wire [11:0]     sq_cv [0:3];
    wire [12*84-1:0] sq_cd [0:3];
    wire [8:0]      sq_dn [0:3];
    wire [1:0]      sq_st [0:3];
    wire [3:0]      sq_jd, sq_flt, sq_rdy;
    reg             sq_pwv; reg [6:0] sq_pwa; reg [27:0] sq_pwd; reg [7:0] sq_len; reg [3:0] sq_jv;
    integer         sq_ncmd [0:3], sq_ndn [0:3], sq_lr [0:3], sq_njd [0:3], sq_err;
    integer         sq_ld, sq_i;
    reg [2099:0]    sq_b;
    initial begin
        sq_pwv = 0; sq_pwa = 0; sq_pwd = 0; sq_len = NM[7:0]; sq_jv = 0; sq_err = 0; sq_ld = 0;
        for (sq_i = 0; sq_i < 4; sq_i = sq_i + 1) begin sq_ncmd[sq_i] = 0; sq_ndn[sq_i] = 0; sq_lr[sq_i] = 0; sq_njd[sq_i] = 0; end
        if (NM > 128) $fatal(1, "TB_CTRL: NM <= 128 (stage program size)");
    end
    function [84:0] sq_mut(input integer dd, input integer k, input [84:0] c);
        begin
            sq_mut = c;
`ifdef TB_MUT_DROPSTART
            if (dd == 0 && k == 4) sq_mut[84] = 1'b0;
`endif
`ifdef TB_MUT_WRONGDESC
            if (dd == 0 && k == 2) sq_mut[22:7] = c[22:7] + 16'd1;
`endif
        end
    endfunction
    generate for (gd = 0; gd < 4; gd = gd + 1) begin : g_sq
        wire [84:0] c3 = {sq_cv[gd][3], sq_cd[gd][3*84 +: 84]};
        reg  [84:0] c3m;
        always @(*) c3m = sq_mut(gd, sq_ncmd[gd], c3);
        ot_s81_stage_seq #(.NOPS(128), .NENG(12), .ARGW(24), .USER_W(10), .NW(21), .QD(8), .FQ(4)) u_sq (
            .clk(cks[gd]), .rst_n(rsts[gd]), .pw_v(sq_pwv), .pw_a(sq_pwa), .pw_d(sq_pwd), .prog_len(sq_len),
            .job_v(sq_jv[gd]), .job_rdy(sq_rdy[gd]), .job_user(10'(gd)), .job_pos(21'd1048575), .job_tok(21'd12345),
            .job_done(sq_jd[gd]), .cmd_v(sq_cv[gd]), .cmd_d(sq_cd[gd]),
            .dn_v({8'd0, sq_dn[gd][8], 3'd0}), .dn_tag({64'd0, sq_dn[gd][7:0], 24'd0}),
            .busy(), .fault(sq_flt[gd]), .fault_code(), .st_jobs(), .st_cmds());
        assign c3a[gd] = c3m;
        assign sq_dn[gd] = d3a[gd];
        assign sq_st[gd] = csta[gd];
    end endgenerate
    // program load (all dies at once), then one job per die
    always @(posedge clk) begin
        if (rsts == 4'hF) begin
            sq_pwv <= 0;
            if (sq_ld < NM) begin
                sq_pwv <= 1; sq_pwa <= sq_ld[6:0]; sq_pwd <= {4'd3, 7'd0, nmm[sq_ld], 16'(nmw[sq_ld])}; sq_ld = sq_ld + 1;
            end else if (sq_ld < NM + 4) sq_ld = sq_ld + 1;
            else if (sq_ld == NM + 4) begin sq_jv <= 4'hF; sq_ld = sq_ld + 1; end
            else if (sq_jv != 0) sq_jv <= sq_jv & ~sq_rdy;
        end
    end
    // checks (controller clock = the die's stream clock)
    always @(posedge clk) begin
        for (sq_i = 0; sq_i < 4; sq_i = sq_i + 1) begin
            if (rsts[sq_i]) begin
                sq_b = tvm[sq_i];
                if (sq_b[0] && sq_b[2:1] == 2'd1) sq_lr[sq_i] = sq_lr[sq_i] + ((sq_b[13] & sq_b[9]) + (sq_b[12] & sq_b[8]) + (sq_b[11] & sq_b[7]) + (sq_b[10] & sq_b[6]));
                if ((sq_cv[sq_i] & ~12'h008) != 0) begin sq_err = sq_err + 1; $display("CTRL DIE %0d command on a non-coll port", sq_i); end
                if (sq_cv[sq_i][3]) sq_ncmd[sq_i] = sq_ncmd[sq_i] + 1;
                if (sq_dn[sq_i][8]) begin
                    if (sq_dn[sq_i][7:0] !== {1'b0, 7'(sq_ndn[sq_i])}) begin sq_err = sq_err + 1;
                        if (sq_err < 20) $display("CTRL DIE %0d done tag %h expected op %0d", sq_i, sq_dn[sq_i][7:0], sq_ndn[sq_i]); end
                    sq_ndn[sq_i] = sq_ndn[sq_i] + 1;
                    if (sq_ndn[sq_i] > sq_lr[sq_i]) begin sq_err = sq_err + 1;
                        if (sq_err < 20) $display("CTRL DIE %0d EARLY done %0d: only %0d message lasts left the slab", sq_i, sq_ndn[sq_i], sq_lr[sq_i]); end
                end
                if (sq_jd[sq_i]) begin
                    sq_njd[sq_i] = sq_njd[sq_i] + 1;
                    if (sq_ndn[sq_i] != NM) begin sq_err = sq_err + 1; $display("CTRL DIE %0d job_done after %0d of %0d dones", sq_i, sq_ndn[sq_i], NM); end
                end
                if (sq_flt[sq_i] || sq_st[sq_i][0]) begin sq_err = sq_err + 1;
                    if (sq_err < 20) $display("CTRL DIE %0d FAULT seq %b endpoint %b", sq_i, sq_flt[sq_i], sq_st[sq_i][0]); end
            end
        end
    end
    task ctrl_end();
        for (sq_i = 0; sq_i < 4; sq_i = sq_i + 1) begin
            $display("CTRL DIE %0d cmds %0d dones %0d lasts %0d job_done %0d online %b", sq_i, sq_ncmd[sq_i], sq_ndn[sq_i], sq_lr[sq_i], sq_njd[sq_i], sq_st[sq_i][1]);
            if (sq_ndn[sq_i] != NM || sq_njd[sq_i] != 1 || !sq_st[sq_i][1]) sq_err = sq_err + 1;
        end
        errs = errs + sq_err;
    endtask
    function ctrl_done(); ctrl_done = sq_njd[0] == 1 && sq_njd[1] == 1 && sq_njd[2] == 1 && sq_njd[3] == 1; endfunction
`else
    function ctrl_done(); ctrl_done = 1'b1; endfunction
    task ctrl_end(); endtask
`endif
    // outputs per die = reduce words (one per mode-0 record) + gather beats (one per mode-1 record)
    function integer TOT_IDX(); TOT_IDX = TOT; endfunction
    function all_pt();
        integer dd, ll; begin all_pt = 1;
            for (dd = 0; dd < 4; dd = dd + 1) for (ll = 0; ll < 5; ll = ll + 1) if (ptr_[dd][ll] != NPT) all_pt = 0;
        end
    endfunction
endmodule
