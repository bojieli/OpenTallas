`timescale 1ns/1ps
// S81-SLICE vs bench (helper S81-SLICE-SU): ONE beat leaf's SU path = real ot_s81sl_vp (leaf store + command port) +
// ot_s81sl_vs + ot_s81sl_vsw (hub SW lane) + the closed hub RA lane pair (dsfd_su_t_rxsf -> dsfd_su_t_rxsb) +
// ot_s81sl_vq (act-quant of the vs stream), on one layer's 1M-token SU cases (tools/s81_slice/vs_gold.py: every case's
// golden asserted against the hub executor's check).  Everything goes through vp's ports: the leaf-store image through
// the row-pair write port, each SU op as a vp command (ops 8..13 -> vs), every result read back with vp RDOUT and
// compared word for word; the vq XQ beats (SW -> quant2, QB z_quant) are compared with the golden act-quant.
// Prints VSOP (per op: vp command pin -> last vs result output, in cycles) and SLVS (per-op mismatch counts) + PASS/FAIL.
// Negative controls: -GMUT=1..6, 9 (ot_s81sl_vs MUT; 9 = SW wr takes w1 from the wrong word) must FAIL.
module tb_s81sl_vs #(parameter integer MUT = 0, parameter integer BEAT = 37);
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
    wire s_v; wire [159:0] s_d; wire x_rv, x_qv, x_wv; wire [9:0] x_ra, x_wa; wire [7:0] x_wm; wire [255:0] x_qd, x_wd;
    wire u_v, um_v, um_q, um_b; wire [2:0] u_i; wire [255:0] u; wire [7:0] um_i;
    wire swv, swvi, swfi; wire [255:0] swd; wire [31:0] sww, swl; wire [63:0] swri;
    wire rav, ravi, rafi, rfv, rff; wire [31:0] rax, rfmx; wire [30:0] rfu, rfu2, rari;
    ot_s81sl_vp u_p (.clk(clk), .rst_n(rst_n), .c_v(c_v), .c_d(c_d), .sw_v(sw_v), .sw_a(sw_a), .sw_m(sw_m), .sw_d(sw_d),
        .cw_v(2'b00), .cw_a(24'd0), .cw_d(64'd0), .lo_v(lo_v), .lo_d(lo_d),
        .s_v(s_v), .s_d(s_d), .x_rv(x_rv), .x_ra(x_ra), .x_qv(x_qv), .x_qd(x_qd), .x_wv(x_wv), .x_wa(x_wa), .x_wm(x_wm), .x_wd(x_wd),
        .hw_v(), .hw_j(), .hw_hf(), .hw_d(), .hr_v(), .hr_j(), .hr_hf(), .hq_v(1'b0), .hq_d(256'd0),
        .n_go(), .n_pre(), .m_v(), .m_q(), .m_b(), .m_i(), .wl_v(), .wl_i(), .wl_d(), .fault(fp));
    ot_s81sl_vs #(.MUT(MUT)) u_s (.clk(clk), .rst_n(rst_n), .s_v(s_v), .s_d({s_d[159:64], s_d[62], s_d[60:0]}),
        .x_rv(x_rv), .x_ra(x_ra), .x_qv(x_qv), .x_qd(x_qd), .x_wv(x_wv), .x_wa(x_wa), .x_wm(x_wm), .x_wd(x_wd),
        .u_v(u_v), .u_i(u_i), .u(u), .um_v(um_v), .um_q(um_q), .um_b(um_b), .um_i(um_i),
        .sw_v(swv), .sw_d(swd), .sw_w(sww), .sw_lim(swl), .sw_vi(swvi), .sw_ri(swri), .sw_fi(swfi),
        .ra_v(rav), .ra_x(rax), .ra_vi(ravi), .ra_ri(rari), .ra_fi(rafi), .fault(fs));
    ot_s81sl_vsw u_w (.clk(clk), .rst_n(rst_n), .i_v(swv), .i_d(swd), .i_w(sww), .i_lim(swl), .o_v(swvi), .o_d(swri), .o_f(swfi));
    dsfd_su_t_rxsf u_rf (.ck(clk), .rst(rst_n), .i_v(rav), .i_x(rax), .o_v(rfv), .o_u(rfu), .o_u2(rfu2), .o_mx(rfmx), .o_f(rff));
    dsfd_su_t_rxsb u_rb (.ck(clk), .rst(rst_n), .i_v(rfv), .i_u(rfu), .i_u2(rfu2), .i_mx(rfmx), .i_f(rff), .o_v(ravi), .o_r(rari), .o_f(rafi));
    localparam [3:0] SID = BEAT / 5; localparam [2:0] KL = BEAT % 5;
    wire xf_v, xf_s; wire [275:0] xf;
    ot_s81sl_vq u_q (.clk(clk), .rst_n(rst_n), .y_v(1'b0), .y_i(3'd0), .y(128'd0), .u_v(u_v), .u_i(u_i), .u(u),
        .sid(SID), .k(KL), .m_v(1'b0), .m_q(1'b0), .m_b(1'b0), .m_i(8'd0), .um_v(um_v), .um_q(um_q), .um_b(um_b), .um_i(um_i),
        .xf_v(xf_v), .xf_s(xf_s), .xf(xf), .fault(fq));

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
                   idl = (wt > 6 && !u_s.busy) ? idl + 1 : 0;
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
                       if (err[8] + err[9] + err[10] + err[11] + err[12] + err[13] == 0 && nxq == 3 && !fp && !fs && !fq &&
                           nck[8] > 0 && nck[10] > 0 && nck[11] > 0 && nck[12] > 0 && nck[13] > 0) $display("PASS"); else $display("FAIL");
                       $finish;
                   end
               end
            default: ;
        endcase
        if (st == 0 && cyc == 0) wt = 0;
        // vq XQ beats: SW (quant2) first, then QB (z_quant)
        if (xo_v) begin
            k = (nxq <= 1) ? 8 : 9;      // xq beats: SW quant2, SW wr (TOK-S81-GAPS), then QB
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
