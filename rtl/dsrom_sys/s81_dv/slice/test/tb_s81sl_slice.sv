`timescale 1ns/1ps
// S81-TILES6 WHOLE-slice bench (10-17): tb_s81sl_leaf's 1M-token SU cases (tools/s81_slice/vs_gold.py) driven through the
// WHOLE ot_s81sl_slice (5 beat leaves + xg (ring stop + x streamer) + xr1 + cap + xfin + relays), at the slice PINS only:
//   in   every leaf-store row write and every vp command is a CTL beat on the tier line ri_w (E-bound from the W
//        neighbour, hops 1): payload {body 160, leaf mask 5, target 5, slice mask 16}; target 5 = row write, 0 = vp
//        command to beat leaf KL, 4 = send config, 2 = x-streamer issuer word (gather-window open between the XQ beats).
//   out  RDOUT row pairs leave as send beats on ro_e (send config: dir E, kind 4, hops 1, one pair a beat): compared
//        against the golden; the vq XQ beats leave as the slice's own ring beats on ro_w (col 7: W hops 7): compared
//        against the golden act-quant.  The slice fault pin must stay 0.
// Hierarchical reads are observation only (vs busy for op completion, the per-leaf fault split in the report).
// Negative controls: -GMUT=1..6 (ot_s81sl_slice VS_MUT -> every leaf's vs MUT) must FAIL.
module tb_s81sl_slice #(parameter integer MUT = 0, parameter integer BEAT = 37, parameter integer XMEM = 2);
    reg clk = 1'b0;
    always #0.5 clk = ~clk;
    reg [127:0] img [0:1023]; reg imgv [0:1023];
    reg [191:0] prog [0:63];
    reg [255:0] exp_ [0:255]; reg [7:0] expm [0:255];
    reg [531:0] xqe [0:7]; reg [7:0] xqi [0:7];
    initial begin
        $readmemh("img.mem", img); $readmemh("imgv.mem", imgv); $readmemh("prog.mem", prog);
        $readmemh("exp.mem", exp_); $readmemh("expm.mem", expm); $readmemh("xq.mem", xqe); $readmemh("xqi.mem", xqi);
    end
    localparam [3:0] SID = BEAT / 5; localparam integer KL = BEAT % 5;
    reg rst_n = 1'b0;
    reg [1103:0] ri_w = 0;
    wire [1103:0] ro_e, ro_w, bo; wire [275:0] vo; wire [4*1104-1:0] xc;
    wire [15:0] ck_line, ck_xc; wire [1:0] ck_v; wire [7:0] ck_rt; wire s_fault;
    ot_s81sl_slice #(.VQ_XMEM(XMEM), .VS_MUT(MUT)) u_sl (.clk(clk), .rst_n(rst_n), .sid(SID),
        .ri_w(ri_w), .ri_e(1104'd0), .ro_e(ro_e), .ro_w(ro_w), .vi(276'd0), .vo(vo), .bi(1104'd0), .bo(bo), .xc(xc),
        .rt(560'd0), .ck_line(ck_line), .ck_v(ck_v), .ck_xc(ck_xc), .ck_rt(ck_rt), .fault(s_fault));
    // observation only
    wire busy = u_sl.lf[KL].u_lf.u_vs.busy;
    wire u_v = u_sl.lf[KL].u_lf.u_v, x_wv = u_sl.lf[KL].u_lf.x_wv;
    wire fp = u_sl.lf[KL].u_lf.f_vp, fs = u_sl.lf[KL].u_lf.f_vs, fq = u_sl.lf[KL].u_lf.f_vq;
    // a CTL line beat for this slice
    function automatic [1103:0] ctl(input [4:0] tgt, input [4:0] lm, input [159:0] body);
        begin ctl = 1104'd0; ctl[0] = 1'b1; ctl[3:1] = 3'd0; ctl[8:4] = 5'd1; ctl[12:9] = SID - 4'd1;
              ctl[21 +: 16] = 16'd1 << SID; ctl[37 +: 5] = tgt; ctl[42 +: 5] = lm; ctl[47 +: 160] = body; end
    endfunction
    localparam [4:0] LM = 5'd1 << KL;
    localparam integer T_PROG = 1100;
    integer idl = 0, cyc = 0, pc = 0, st = 0, t0 = 0, tl = 0, nxq = 0, k, w, wt = 0, npair = 0, cidx = 0, cpair = 0, r;
    integer err [8:13]; integer nck [8:13]; integer cop = 0; integer nrow = 0; reg gw_pend = 0;
    initial for (k = 8; k < 14; k = k + 1) begin err[k] = 0; nck[k] = 0; end
    always @(posedge clk) if (x_wv || u_v) tl <= cyc;
    always @(posedge clk) begin
        cyc <= cyc + 1;
        ri_w <= 1104'd0;
        if (cyc == 3) rst_n <= 1'b1;
        // leaf-store image: one CTL row write a cycle (valid rows only)
        if (cyc >= 10 && cyc < 1034 && imgv[cyc - 10]) begin
            ri_w <= ctl(5'd5, LM, {18'd0, img[cyc - 10], 4'hf, 10'(cyc - 10)}); nrow = nrow + 1;
        end
        // send config: dir E, kind 4, hops 1, mask 0, leaf 0, row 0, one pair a beat
        if (cyc == 1040) ri_w <= ctl(5'd4, 5'd0, {116'd0, 1'b0, 2'd0, 10'd0, 3'd0, 16'd0, 5'd1, 3'd4, 4'b0001});
        // gather window (family q, parity 1) after the first XQ beat: the second XQ beat may reuse the beat index
        if (gw_pend && cyc >= T_PROG && st != 2 && !(st == 0 && prog[pc][191:188] != 4'd0)) begin
            ri_w <= ctl(5'd2, 5'd0, {37'd0, 1'b1, 1'b0, 1'b1, 120'd0}); gw_pend = 1'b0;
        end else if (cyc >= T_PROG) case (st)
            0: if (prog[pc][191:188] == 4'd1) begin
                   ri_w <= ctl(5'd0, LM, prog[pc][159:0]); cop = prog[pc][187:184]; t0 = cyc; st = 1; wt = 0; idl = 0;
               end else if (prog[pc][191:188] == 4'd2) begin
                   cop = prog[pc][187:184]; cidx = prog[pc][183:170]; cpair = prog[pc][167:160];
                   ri_w <= ctl(5'd0, LM, {128'd0, cpair[7:0], 10'd0, prog[pc][9:0], 4'd6}); npair = 0; st = 2; wt = 0;
               end else if (prog[pc][191:188] == 4'd0) st = 3;
            1: begin
                   wt = wt + 1;
                   idl = (wt > 30 && !busy) ? idl + 1 : 0;
                   if (idl == 6) begin
                       $display("VSOP op=%0d cmd=%0d cycles_cmd_to_last_result=%0d", cop, t0, tl - t0);
                       pc = pc + 1; st = 0;
                   end else if (wt > 3000) begin $display("TIMEOUT op %0d", cop); err[cop] = err[cop] + 1; pc = pc + 1; st = 0; end
               end
            2: begin
                   wt = wt + 1;
                   if (ro_e[0] && ro_e[3:1] == 3'd4) begin
                       for (w = 0; w < 8; w = w + 1)
                           if (expm[cidx + npair][w] && ro_e[52 + 32 * w +: 32] !== exp_[cidx + npair][32 * w +: 32]) begin
                               if (err[cop] < 6) $display("MISMATCH op %0d pair %0d word %0d got %h want %h", cop, npair, w,
                                                          ro_e[52 + 32 * w +: 32], exp_[cidx + npair][32 * w +: 32]);
                               err[cop] = err[cop] + 1;
                           end
                       nck[cop] = nck[cop] + 1; npair = npair + 1;
                   end
                   if (npair == cpair && wt > cpair + 30) begin pc = pc + 1; st = 0; end
                   else if (wt > 1000) begin $display("RDOUT TIMEOUT"); err[cop] = err[cop] + 1; pc = pc + 1; st = 0; end
               end
            3: begin
                   wt = wt + 1;
                   if (wt == 300) begin
                       $display("SLSL mut=%0d err SW=%0d QB=%0d RA=%0d RB=%0d QR=%0d MOE=%0d checked_pairs SW=%0d RA=%0d RB=%0d QR=%0d MOE=%0d xq=%0d rows=%0d fault=slice%b vp%b/vs%b/vq%b xg%b xr%b cap%b xf%b",
                                MUT, err[8], err[9], err[10], err[11], err[12], err[13], nck[8], nck[10], nck[11], nck[12], nck[13],
                                nxq, nrow, s_fault, fp, fs, fq, u_sl.f_xg, u_sl.f_xr, u_sl.f_cap, u_sl.f_xf);
                       if (s_fault == 1'b0 && err[8] + err[9] + err[10] + err[11] + err[12] + err[13] == 0 && nxq == 2 &&
                           nck[8] > 0 && nck[10] > 0 && nck[11] > 0 && nck[12] > 0 && nck[13] > 0) $display("PASS"); else $display("FAIL");
                       $finish;
                   end
               end
            default: ;
        endcase
        // vq XQ beats at the slice's W line pin: SW (quant2) first, then QB (z_quant)
        if (ro_w[0] && ro_w[3:1] == 3'd1) begin
            k = (nxq == 0) ? 8 : 9;
            if (ro_w[21 +: 532] !== xqe[nxq] || ro_w[20:13] !== xqi[nxq] || ro_w[8:4] !== 5'd7 || ro_w[12:9] !== SID) begin
                err[k] = err[k] + 1;
                $display("XQ MISMATCH beat %0d idx %h/%h hops %0d src %0d e0 %h/%h", nxq, ro_w[20:13], xqi[nxq], ro_w[8:4],
                         ro_w[12:9], ro_w[21 + 256 +: 10], xqe[nxq][256 +: 10]);
            end
            if (nxq == 0) gw_pend = 1'b1;
            nxq = nxq + 1;
        end
        if (cyc == 30000) begin $display("GLOBAL TIMEOUT"); $display("FAIL"); $finish; end
    end
endmodule
