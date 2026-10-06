`timescale 1ns/1ps
// tb_s81ph_coll_sys (CLAUDE S81-PH collective): a 4-die TP4 group (ranks 0..3, packages {0,1} {2,3}) of
// dsfd_sp_collective slabs, every lane a raw 512-b beat channel (ot_dsrom_link_chan: delay, deterministic bit
// flips -- the link macros are hard IP), against the REFERENCE = four ot_w15_rom_oneshot_die_px_acceptedpop built
// with RANK = 0..3 (the C8 parent's parameters) wired directly as in the C8 die model.  Each die's VM model sends the
// same message plan (mode, words, last, tag) with its own FP32 data (specials included) under the contract's
// credits, plus pass-through flits on lanes W3/E0..E3; it accepts t_vm beats under random ts backpressure.
// CHECK: per die, every reduce word (data, last; err OR per beat) and every all-gather beat equals the reference
// engine of that rank, in order; every pass-through flit arrives in order at the partner die; no fault.
// PASS line "TB_S81PH_COLL_SYS PASS".  Cycle report: the last result cycle of DUT and reference.
module tb_s81ph_coll_sys;
    parameter integer SPEC = 1, FIXW = 0, FIXM = -1, PERF = 0, NM = 40, MAXW = 12, NPT = 30, CHB = 60, CHU = 12, EPER = 97, SEED = 7, TSR = 7;
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
    genvar gd, gl;
    generate for (gd = 0; gd < 4; gd = gd + 1) begin : g_die
        wire tf0, tf1, tf2, tf3, tf4, tf5, tf6, tf7;
        dsfd_sp_collective u (.refclk(refclk), .por(por), .f_vm(fvm[gd]), .ts(tsr[gd]),
            .rW0(rx[gd][0]), .rW1(rx[gd][1]), .rW2(rx[gd][2]), .rW3(rx[gd][3]),
            .rE0(rx[gd][4]), .rE1(rx[gd][5]), .rE2(rx[gd][6]), .rE3(rx[gd][7]),
            .pll_stream(cks[gd]), .pll_serial(), .pll_hbm(), .rst_stream(rsts[gd]), .rst_serial(), .rst_hbm(),
            .t_vm(tvm[gd]),
            .tdW0(tx[gd][0]), .tdW1(tx[gd][1]), .tdW2(tx[gd][2]), .tdW3(tx[gd][3]),
            .tdE0(tx[gd][4]), .tdE1(tx[gd][5]), .tdE2(tx[gd][6]), .tdE3(tx[gd][7]),
            .tfW0(tf0), .tfW1(tf1), .tfW2(tf2), .tfW3(tf3), .tfE0(tf4), .tfE1(tf5), .tfE2(tf6), .tfE3(tf7));
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
    integer cyc;
    always @(posedge clk) begin
        cyc <= cyc + 1;
        for (d = 0; d < 4; d = d + 1) begin
            if (r_ov[d]) begin
                rq[d][rn[d]] = {ownm[ridx[d]], r_ol[d], r_od[d]}; rqe[d][rn[d]] = r_oe[d]; rn[d] = rn[d] + 1; ridx[d] = ridx[d] + 1;
                r_last_cyc = cyc;
            end
            if (r_iv[d] && r_ir[d]) rptr[d] = rptr[d] + 1;
            r_iv[d] <= rsts[0] && (first_send_cyc >= 0) && (rptr[d] + ((r_iv[d] && r_ir[d]) ? 1 : 0) < TOT);
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
            fvm[d] <= 0;
            if (rsts[d] && cyc > 20) begin
                if (cfgd[d] < 2) begin
                    cfgd[d] = cfgd[d] + 1;
                    if (cfgd[d] == 2) fvm[d] <= {{(W-3){1'b0}}, 1'b1, d[1:0], 32'd0, 1'b0, 1'b0, 3'd0, 2'd3, 1'b1};
                end else begin
                    q = PERF ? ((sp[d] < TOT) ? 0 : 1 + rnd(0) % 5) : rnd(0) % 6;
                    if (q == 0 && cr[d][0] > 0 && sp[d] < TOT) begin
                        fvm[d] <= {{(W-FW){1'b0}}, own[d][sp[d]], ownt[sp[d]], ownm[sp[d]], ownl[sp[d]], 3'd0, 2'd1, 1'b1};
                        if (first_send_cyc < 0) first_send_cyc = cyc;
                        sp[d] = sp[d] + 1; cr[d][0] = cr[d][0] - 1;
                    end else if (q != 0 && cr[d][q] > 0 && pts[d][q-1] < NPT) begin
                        fvm[d] <= {ptd[d][q-1][pts[d][q-1]], 32'd0, 1'b0, ptl[d][q-1][pts[d][q-1]], 3'(q - 1), 2'd2, 1'b1};
                        pts[d][q-1] = pts[d][q-1] + 1; cr[d][q] = cr[d][q] - 1;
                    end
                end
            end
        end
        // ---- end
        if (cyc > 400000 || (cyc > 1000 && dn[0] == rn[0] && dn[1] == rn[1] && dn[2] == rn[2] && dn[3] == rn[3] &&
             rn[0] > 0 && ridx[0] == TOT_IDX() && all_pt())) begin
            for (d = 0; d < 4; d = d + 1) if (dn[d] != rn[d] || ridx[d] != TOT_IDX()) begin
                errs = errs + 1; $display("DIE %0d INCOMPLETE dut %0d ref %0d of %0d", d, dn[d], rn[d], TOT_IDX()); end
            if (!all_pt()) begin errs = errs + 1; $display("PT INCOMPLETE"); end
            $display("CYCLES dut_last %0d ref_last %0d first_send %0d records %0d messages %0d", d_last_cyc, r_last_cyc, first_send_cyc, TOT, NM);
            if (errs == 0) $display("TB_S81PH_COLL_SYS PASS"); else $display("TB_S81PH_COLL_SYS FAIL errs %0d", errs);
            $finish;
        end
    end
    // outputs per die = reduce words (one per mode-0 record) + gather beats (one per mode-1 record)
    function integer TOT_IDX(); TOT_IDX = TOT; endfunction
    function all_pt();
        integer dd, ll; begin all_pt = 1;
            for (dd = 0; dd < 4; dd = dd + 1) for (ll = 0; ll < 5; ll = ll + 1) if (ptr_[dd][ll] != NPT) all_pt = 0;
        end
    endfunction
endmodule
