`timescale 1ns/1ps
// RTL-BUILD-S81 (2026-10-18): the in-slice Engram mix of one V4.1 layer on ONE real ot_s81sl_slice (C1, sid SID): 5 beat
// leaves (vp + vn + vq + vs op 14 + ve), xr (ENG collector, CTL target 1 mode ENG, gate fan-out), xfin (mode ENG: the
// 12-vector exchange + finish) and eg (scalar finish).  The other 15 slices are represented by their golden exchange
// flits (NX beats on the tier line, injected at the W port); everything else enters through the slice's real ports:
// RD beats (leaf-store rows), CTL beats (vp / vs commands, xfin go).  Fixtures: tools/s81_slice/eng_slice_gold.py
// (Model.engram_layer statements, chunk8).  Checked: xfin's 12 copy sums, eg's 4 gates, the 5 leaves' 4 x 64 results
// (read back through vn: HLOAD, HSTORE, RDOUT) bit exact.  -GVS_MUT=7 / 8 (vs ENG negative controls) must FAIL.
module tb_s81sl_slice_eng #(parameter integer VS_MUT = 0, parameter integer SID = 3);
    reg clk = 1'b0;
    always #0.5 clk = ~clk;
    reg [255:0] img [0:4][0:87];
    reg [255:0] im0 [0:87], im1 [0:87], im2 [0:87], im3 [0:87], im4 [0:87];
    reg [167:0] flit [0:179]; reg [3:0] fvm [0:179];
    reg [31:0] sumg [0:11], gateg [0:3], par [0:1]; reg [255:0] yg [0:79];
    reg [1023:0] dir;
    reg rst_n = 1'b0;
    reg [1103:0] ri_w = 0;
    wire [1103:0] ro_e, ro_w; wire [512:0] bo; wire [275:0] vo; wire [4*1104-1:0] xc; wire [15:0] ck_line, ck_xc; wire [1:0] ck_v;
    wire [7:0] ck_rt; wire fault;
    ot_s81sl_slice #(.HB(0), .VS_MUT(VS_MUT)) u_dut (.clk(clk), .rst_n(rst_n), .sid(SID[3:0]), .ri_w(ri_w), .ri_e(1104'd0), .ro_e(ro_e),
        .ro_w(ro_w), .vi(276'd0), .vo(vo), .bi(1104'd0), .bo(bo), .xc(xc), .rt(560'd0), .ck_line(ck_line), .ck_v(ck_v),
        .ck_xc(ck_xc), .ck_rt(ck_rt), .fault(fault));
    integer cyc = 0, i, k, b, bad = 0, ng = 0, ns = 0, nlo = 0, rdk = 0, t_r = 0, t_g = 0, t_a = 0, t_w = 0;
    always @(posedge clk) cyc <= cyc + 1;
    // ---- beat builders (tier line, from the W neighbour, hops 1 = deliver here)
    function automatic [1103:0] ctl(input [4:0] tgt, input [4:0] lm, input [159:0] body);
        reg [1103:0] x;
        begin x = 0; x[0] = 1'b1; x[3:1] = 3'd0; x[8:4] = 5'd1; x[12:9] = SID - 1; x[21 +: 16] = 16'd1 << SID;
              x[37 +: 5] = tgt; x[42 +: 5] = lm; x[47 +: 160] = body; ctl = x; end
    endfunction
    function automatic [9:0] prow(input integer p);
        prow = (p < 16) ? 2 * p : 704 + 2 * (p - 16);       // h rows, then the Engram region (L1 A0 = 704)
    endfunction
    task automatic send(input [1103:0] x);
        begin @(negedge clk); ri_w = x; @(negedge clk); ri_w = 0; end
    endtask
    task automatic vcmd(input [4:0] lm, input [3:0] op, input [9:0] a0, input [9:0] a1, input [7:0] n, input [127:0] imm);
        begin send(ctl(5'd0, lm, {imm, n, a1, a0, op})); end
    endtask
    // ---- probes: xfin sums, eg gates at the leaves, leaf RDOUT rows
    wire [4:0] lov = {u_dut.lf[4].u_lf.lo_v, u_dut.lf[3].u_lf.lo_v, u_dut.lf[2].u_lf.lo_v, u_dut.lf[1].u_lf.lo_v,
                      u_dut.lf[0].u_lf.lo_v};
    wire [255:0] lod [0:4];
    assign lod[0] = u_dut.lf[0].u_lf.lo_d; assign lod[1] = u_dut.lf[1].u_lf.lo_d; assign lod[2] = u_dut.lf[2].u_lf.lo_d;
    assign lod[3] = u_dut.lf[3].u_lf.lo_d; assign lod[4] = u_dut.lf[4].u_lf.lo_d;
    always @(posedge clk) begin
        if (u_dut.xe_v) begin
            if (u_dut.xe_hh !== sumg[u_dut.xe_c] || u_dut.xe_kk !== sumg[4 + u_dut.xe_c] || u_dut.xe_dd !== sumg[8 + u_dut.xe_c]) begin
                bad = bad + 1;
                $display("SUM MISMATCH copy %0d hh %h/%h kk %h/%h dd %h/%h", u_dut.xe_c, u_dut.xe_hh, sumg[u_dut.xe_c],
                         u_dut.xe_kk, sumg[4 + u_dut.xe_c], u_dut.xe_dd, sumg[8 + u_dut.xe_c]);
            end
            ns = ns + 1;
        end
        if (u_dut.gv_l[0]) begin
            if (u_dut.gd_l[31:0] !== gateg[u_dut.gc_l[1:0]]) begin
                bad = bad + 1; $display("GATE MISMATCH copy %0d %h/%h", u_dut.gc_l[1:0], u_dut.gd_l[31:0], gateg[u_dut.gc_l[1:0]]);
            end
            ng = ng + 1; t_g <= cyc;
        end
        if (|lov) begin
            if (lov != (5'd1 << rdk) || lod[rdk] !== yg[16 * rdk + (nlo % 16)]) begin
                bad = bad + 1;
                if (bad < 8) $display("OUT MISMATCH leaf %0d half row %0d got %h want %h", rdk, nlo % 16, lod[rdk], yg[16 * rdk + (nlo % 16)]);
            end
            nlo = nlo + 1;
        end
        if (u_dut.lf[0].u_lf.u_vs.x_wv && u_dut.lf[0].u_lf.u_vs.op == 4'd14) t_w <= cyc;
    end
    initial begin
        if (!$value$plusargs("dir=%s", dir)) $fatal(1, "dir required");
        $readmemh({dir, "/img_0.mem"}, im0); $readmemh({dir, "/img_1.mem"}, im1); $readmemh({dir, "/img_2.mem"}, im2);
        $readmemh({dir, "/img_3.mem"}, im3); $readmemh({dir, "/img_4.mem"}, im4);
        $readmemh({dir, "/flit.mem"}, flit); $readmemh({dir, "/fv.mem"}, fvm); $readmemh({dir, "/sum.mem"}, sumg);
        $readmemh({dir, "/gate.mem"}, gateg); $readmemh({dir, "/par.mem"}, par); $readmemh({dir, "/y.mem"}, yg);
        for (i = 0; i < 88; i = i + 1) begin img[0][i] = im0[i]; img[1][i] = im1[i]; img[2][i] = im2[i]; img[3][i] = im3[i];
                                               img[4][i] = im4[i]; end
        repeat (6) @(negedge clk); rst_n = 1'b1; repeat (40) @(negedge clk);
        // leaf-store rows: RD beats of 4 row pairs, leaves interleaved
        for (b = 0; b < 22; b = b + 1) for (k = 0; k < 5; k = k + 1) begin
            @(negedge clk);
            ri_w = 0; ri_w[0] = 1'b1; ri_w[3:1] = 3'd4; ri_w[8:4] = 5'd1; ri_w[12:9] = SID - 1; ri_w[21 +: 16] = 16'd1 << SID;
            ri_w[37 +: 3] = k; ri_w[40 +: 10] = prow(4 * b); ri_w[50 +: 2] = 2'd3;
            for (i = 0; i < 4; i = i + 1) ri_w[52 + 256 * i +: 256] = img[k][4 * b + i];
            @(negedge clk); ri_w = 0; repeat (2) @(negedge clk);
        end
        repeat (20) @(negedge clk);
        vcmd(5'h1F, 4'd3, 10'd0, 10'd0, 8'd0, 128'd0); repeat (60) @(negedge clk);       // HLOAD h -> vn
        vcmd(5'h1F, 4'd4, 10'd300, 10'd0, 8'd0, 128'd0); repeat (60) @(negedge clk);     // HSTORE vn -> 300
        send(ctl(5'd1, 5'd0, {64'd0, par[1], 31'd0, 1'b1, par[0]})); repeat (8) @(negedge clk);   // xfin go, ENG
        t_r = cyc + 1;
        vcmd(5'h1F, 4'd14, 10'd300, 10'd704, 8'd64, 128'd0);                              // op 14 REDUCE, 5 leaves
        // the 15 other slices' flits (in each source's injection order), one a cycle on the line
        for (i = 0; i < 180; i = i + 1) begin
            @(negedge clk);
            ri_w = 0; ri_w[0] = 1'b1; ri_w[3:1] = 3'd3; ri_w[8:4] = 5'd1; ri_w[12:9] = flit[i][163:160];
            ri_w[20:13] = flit[i][167:160]; ri_w[21 +: 160] = flit[i][159:0];
        end
        @(negedge clk); ri_w = 0;
        while (ng < 4 && cyc < t_r + 5000) @(negedge clk);
        repeat (8) @(negedge clk);
        t_a = cyc + 1;
        vcmd(5'h1F, 4'd14, 10'd704, 10'd400, 8'd32, {97'd0, 1'b1, 30'd0});              // op 14 ADD
        repeat (150) @(negedge clk);
        vcmd(5'h1F, 4'd3, 10'd400, 10'd0, 8'd0, 128'd0); repeat (60) @(negedge clk);     // HLOAD results -> vn
        vcmd(5'h1F, 4'd4, 10'd500, 10'd0, 8'd0, 128'd0); repeat (60) @(negedge clk);     // HSTORE vn -> 500
        for (k = 0; k < 5; k = k + 1) begin
            rdk = k; vcmd(5'd1 << k, 4'd6, 10'd500, 10'd0, 8'd16, 128'd0); repeat (40) @(negedge clk);
        end
        $display("SLICEENG vs_mut=%0d sums=%0d gates=%0d half_rows=%0d mismatches=%0d fault=%b reduce_cmd_to_last_gate=%0d add_cmd_to_last_write=%0d",
                 VS_MUT, ns, ng, nlo, bad, fault, t_g - t_r, t_w - t_a);
        if (bad == 0 && ns == 4 && ng == 4 && nlo == 80 && !fault) $display("PASS"); else $display("FAIL");
        $finish;
    end
    initial begin #400000; $display("GLOBAL TIMEOUT"); $display("FAIL"); $finish; end
endmodule
