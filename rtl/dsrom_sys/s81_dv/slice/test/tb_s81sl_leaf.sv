`timescale 1ns/1ps
// S81-TILES5 slice bench (10-17): the vs bench's 1M-token SU cases (tools/s81_slice/vs_gold.py) driven through ONE
// ot_s81sl_leaf -- the beat leaf exactly as ot_s81sl_slice wires it (vp + vn + vq AQ_XMEM 2 + vs + vsw + RA lane pair) --
// so the slice's vq u / um seam, the vp vs seam and vq's SRAM-ring wait line are checked end to end: every SU result
// read back by vp RDOUT, the vq XQ beats (SW -> quant2, QB z_quant) against the golden act-quant.  Only the leaf's
// ports are driven.  Negative controls: -GMUT=1..6 (vs MUT through VS_MUT) must FAIL.  Derived from tb_s81sl_vs.
module tb_s81sl_leaf #(parameter integer MUT = 0, parameter integer BEAT = 37, parameter integer XMEM = 2);
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
    reg rst_n = 1'b0, c_v = 1'b0, sw_v = 1'b0;
    reg [159:0] c_d = 0; reg [9:0] sw_a = 0; reg [255:0] sw_d = 0; reg [7:0] sw_m = 0;
    wire lo_v; wire [255:0] lo_d; wire fp, fs, fq;
    localparam [3:0] SID = BEAT / 5; localparam [2:0] KL = BEAT % 5;
    wire xf_v, xf_s; wire [275:0] xf; wire p_v, f_lf; wire [31:0] p_d;
    // the slice's beat leaf exactly as ot_s81sl_slice instantiates it (vq AQ_XMEM = the slice default 2)
    ot_s81sl_leaf #(.AQ_XMEM(XMEM), .VS_MUT(MUT)) u_lf (.clk(clk), .rst_n(rst_n), .sid(SID), .k(KL),
        .c_v(c_v), .c_d(c_d), .sw_v(sw_v), .sw_a(sw_a), .sw_m(sw_m), .sw_d(sw_d),
        .cw_v(2'b00), .cw_a(24'd0), .cw_d(64'd0), .lo_v(lo_v), .lo_d(lo_d), .rb_v(1'b0), .rb_d(32'd0),
        .p_v(p_v), .p_d(p_d), .xf_v(xf_v), .xf_s(xf_s), .xf(xf),
        .e_v(), .e_c(), .e_d(), .g_v(1'b0), .g_c(2'd0), .g_d(32'd0), .fault(f_lf));   // ENG ports: idle in this SU bench
    wire u_v = u_lf.u_v, x_wv = u_lf.x_wv;
    assign fp = u_lf.f_vp; assign fs = u_lf.f_vs; assign fq = u_lf.f_vq;

    // vq fragments -> ring beats (as the ring stop)
    reg [1103:0] xo = 0; reg [1:0] frn = 0; reg xo_v = 0;
    always @(posedge clk) begin
        xo_v <= 1'b0;
        if (xf_v) begin
            if (xf_s) begin xo[275:0] <= xf; frn <= 2'd1; end
            else begin xo[276 * frn +: 276] <= xf; frn <= frn + 2'd1; if (frn == 2'd3) xo_v <= 1'b1; end
        end
    end
    integer idl = 0, cyc = 0, pc = 0, st = 0, t0 = 0, tl = 0, nxq = 0, k, w, wt = 0, nchk = 0, npair = 0, cidx = 0, cpair = 0;
    integer err [8:13]; integer nck [8:13]; integer cop = 0;
    initial for (k = 8; k < 14; k = k + 1) begin err[k] = 0; nck[k] = 0; end
    // the last vs result output (write port / vq stream) of the running op
    always @(posedge clk) if (x_wv || u_v) tl <= cyc;
    always @(posedge clk) begin
        cyc <= cyc + 1;
        c_v <= 1'b0; sw_v <= 1'b0;
        if (cyc == 3) rst_n <= 1'b1;
        if (cyc >= 10 && cyc < 522 && (imgv[2 * (cyc - 10)] || imgv[2 * (cyc - 10) + 1])) begin
            sw_v <= 1'b1; sw_a <= 2 * (cyc - 10); sw_d <= {img[2 * (cyc - 10) + 1], img[2 * (cyc - 10)]};
            sw_m <= {{4{imgv[2 * (cyc - 10) + 1]}}, {4{imgv[2 * (cyc - 10)]}}};
        end
        // program sequencer: st 0 fetch, 1 wait for vs idle, 2 wait for the RDOUT pairs
        if (cyc >= 540) case (st)
            0: if (prog[pc][191:188] == 4'd1) begin
                   c_v <= 1'b1; c_d <= prog[pc][159:0]; cop = prog[pc][187:184]; t0 = cyc; st = 1; wt = 0; idl = 0;
               end else if (prog[pc][191:188] == 4'd2) begin
                   cop = prog[pc][187:184]; cidx = prog[pc][183:170]; cpair = prog[pc][167:160];
                   c_v <= 1'b1; c_d <= {128'd0, cpair[7:0], 10'd0, prog[pc][9:0], 4'd6}; npair = 0; st = 2; wt = 0;
               end else if (prog[pc][191:188] == 4'd0) st = 3;
            1: begin
                   wt = wt + 1;
                   idl = (wt > 6 && !u_lf.u_vs.busy) ? idl + 1 : 0;
                   if (idl == 6) begin
                       $display("VSOP op=%0d cmd=%0d cycles_cmd_to_last_result=%0d", cop, t0, tl - t0);
                       pc = pc + 1; st = 0;
                   end else if (wt > 3000) begin $display("TIMEOUT op %0d", cop); err[cop] = err[cop] + 1; pc = pc + 1; st = 0; end
               end
            2: begin
                   wt = wt + 1;
                   if (lo_v) begin
                       for (w = 0; w < 8; w = w + 1)
                           if (expm[cidx + npair][w] && lo_d[32 * w +: 32] !== exp_[cidx + npair][32 * w +: 32]) begin
                               if (err[cop] < 6) $display("MISMATCH op %0d pair %0d word %0d got %h want %h", cop, npair, w,
                                                          lo_d[32 * w +: 32], exp_[cidx + npair][32 * w +: 32]);
                               err[cop] = err[cop] + 1;
                           end
                       nck[cop] = nck[cop] + 1; npair = npair + 1;
                   end
                   if (npair == cpair && wt > cpair + 8) begin pc = pc + 1; st = 0; end
                   else if (wt > 1000) begin $display("RDOUT TIMEOUT"); err[cop] = err[cop] + 1; pc = pc + 1; st = 0; end
               end
            3: begin
                   wt = wt + 1;
                   if (wt == 300) begin
                       $display("SLVS mut=%0d err SW=%0d QB=%0d RA=%0d RB=%0d QR=%0d MOE=%0d checked_pairs SW=%0d RA=%0d RB=%0d QR=%0d MOE=%0d xq=%0d fault=vp%b/vs%b/vq%b",
                                MUT, err[8], err[9], err[10], err[11], err[12], err[13], nck[8], nck[10], nck[11], nck[12], nck[13],
                                nxq, fp, fs, fq);
                       if (f_lf == 1'b0 && err[8] + err[9] + err[10] + err[11] + err[12] + err[13] == 0 && nxq == 3 && !fp && !fs && !fq &&
                           nck[8] > 0 && nck[10] > 0 && nck[11] > 0 && nck[12] > 0 && nck[13] > 0) $display("PASS"); else $display("FAIL");
                       $finish;
                   end
               end
            default: ;
        endcase
        if (st == 0 && cyc == 0) wt = 0;
        // vq XQ beats: SW (quant2) first, then QB (z_quant)
        if (xo_v) begin
            k = (nxq == 0) ? 8 : 9;
            if (xo[3:1] !== 3'd1 || xo[21 +: 532] !== xqe[nxq] || xo[20:13] !== xqi[nxq]) begin
                err[k] = err[k] + 1;
                $display("XQ MISMATCH beat %0d kind %0d idx %h/%h e0 %h/%h e1 %h/%h", nxq, xo[3:1], xo[20:13], xqi[nxq],
                         xo[21 + 256 +: 10], xqe[nxq][256 +: 10], xo[21 + 522 +: 10], xqe[nxq][522 +: 10]);
            end
            nxq = nxq + 1;
        end
        if (cyc == 20000) begin $display("GLOBAL TIMEOUT"); $display("FAIL"); $finish; end
    end
endmodule
