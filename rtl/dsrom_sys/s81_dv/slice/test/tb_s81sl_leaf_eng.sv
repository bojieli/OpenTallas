`timescale 1ns/1ps
// RTL-BUILD-S81 (2026-10-18): Engram mix through ONE ot_s81sl_leaf (the beat leaf exactly as ot_s81sl_slice wires it:
// vp + vn + vq + vs + vsw + RA pair + ve).  Fixtures: tools/s81_dv/ve_golden.py (hdc_golden_v41 chunk8: one beat x 4
// copies; p = the 12 beat partials, y = bf16(h + gate*v)).  Only the leaf's ports are driven:
//   row writes (sw_*): h at rows 0.. (vn half-row layout); the Engram K / W / V region of the compiler row map
//   (results/arch/s81_dv_1016/eng/kv_rowmap.json, L1 A0 = 704): K_j at A0 + 16 j, W_j at A0 + 64 + 16 j, V at A0 + 128
//   vp HLOAD 0 (h -> vn), vp HSTORE 300 (vn -> leaf store: the real h source of op 14)
//   vs op 14 REDUCE (a0 300, a1 A0, n 64)  -> e_* triples checked against p
//   gates on g_* (the eg values of the fixture), vs op 14 ADD (a0 A0, a1 400, n 32)
//   vp HLOAD 400 (results -> vn h store), vp HSTORE 500, vp RDOUT 500 x 16 -> lo checked against y.
// -GMUT=7 / 8 (vs MUT: wrong gate copy / K as W) must FAIL.
module tb_s81sl_leaf_eng #(parameter integer MUT = 0,
    // S81-PLAN R3 (10-25): ot_s81sl_leaf core<->core station depths (0 = the pre-R3 leaf)
    parameter integer CS_HI_D = 0, parameter integer CS_HI_GS = 0, parameter integer CS_HO_D = 0, parameter integer CS_HO_GS = 0, parameter integer CS_VNI_D = 0, parameter integer CS_VNO_D = 0, parameter integer CS_Y_D = 0, parameter integer CS_U_D = 0, parameter integer CS_SW_D = 0, parameter integer CS_SWR_D = 0, parameter integer CS_RA_D = 0, parameter integer CS_RAR_D = 0, parameter integer CS_VE_D = 0, parameter integer CS_VER_D = 0, parameter integer CS_PVS_D = 0, parameter integer CS_VSP_D = 0, parameter integer CS_H_G = 4);
    localparam [9:0] A0 = 10'd704;
    reg clk = 1'b0;
    always #0.5 clk = ~clk;
    reg [31:0] hm [0:255], km [0:255], wm [0:255], vm [0:63], gm [0:3], pm [0:11], ym [0:255];
    reg [1023:0] dir;
    reg rst_n = 1'b0, c_v = 1'b0, sw_v = 1'b0, g_v = 1'b0;
    reg [159:0] c_d = 0; reg [9:0] sw_a = 0; reg [255:0] sw_d = 0; reg [7:0] sw_m = 0; reg [1:0] g_c = 0; reg [31:0] g_d = 0;
    wire lo_v; wire [255:0] lo_d; wire xf_v, xf_s; wire [275:0] xf; wire p_v, f_lf, e_v; wire [31:0] p_d; wire [1:0] e_c;
    wire [95:0] e_d;
    ot_s81sl_leaf #(.AQ_XMEM(2), .VS_MUT(MUT), .CS_HI_D(CS_HI_D), .CS_HI_GS(CS_HI_GS), .CS_HO_D(CS_HO_D), .CS_HO_GS(CS_HO_GS), .CS_VNI_D(CS_VNI_D), .CS_VNO_D(CS_VNO_D), .CS_Y_D(CS_Y_D), .CS_U_D(CS_U_D), .CS_SW_D(CS_SW_D), .CS_SWR_D(CS_SWR_D), .CS_RA_D(CS_RA_D), .CS_RAR_D(CS_RAR_D), .CS_VE_D(CS_VE_D), .CS_VER_D(CS_VER_D), .CS_PVS_D(CS_PVS_D), .CS_VSP_D(CS_VSP_D), .CS_H_G(CS_H_G)) u_lf (.clk(clk), .rst_n(rst_n), .sid(4'd3), .k(3'd2),
        .c_v(c_v), .c_d(c_d), .sw_v(sw_v), .sw_a(sw_a), .sw_m(sw_m), .sw_d(sw_d),
        .cw_v(2'b00), .cw_a(24'd0), .cw_d(64'd0), .lo_v(lo_v), .lo_d(lo_d), .rb_v(1'b0), .rb_d(32'd0),
        .p_v(p_v), .p_d(p_d), .xf_v(xf_v), .xf_s(xf_s), .xf(xf), .e_v(e_v), .e_c(e_c), .e_d(e_d),
        .g_v(g_v), .g_c(g_c), .g_d(g_d), .fault(f_lf));
    integer cyc = 0, i, j, e, bad = 0, np = 0, nlo = 0, t_r = 0, t_rl = 0, t_a = 0, t_al = 0;
    always @(posedge clk) cyc <= cyc + 1;
    // h half row i (vn layout): copy j element 4 i + e at bits (4 j + e) * 16
    function automatic [255:0] hrow(input integer hi, input integer src);   // src 0 = h fixture, 1 = y fixture
        integer jj, ee; reg [255:0] r;
        begin
            r = 256'd0;
            for (jj = 0; jj < 4; jj = jj + 1) for (ee = 0; ee < 4; ee = ee + 1)
                r[(4 * jj + ee) * 16 +: 16] = (src == 0) ? hm[64 * jj + 4 * hi + ee][31:16] : ym[64 * jj + 4 * hi + ee][31:16];
            hrow = r;
        end
    endfunction
    task automatic cmd(input [3:0] op, input [9:0] a0, input [9:0] a1, input [7:0] n, input [127:0] imm);
        begin @(negedge clk); c_v = 1'b1; c_d = {imm, n, a1, a0, op}; @(negedge clk); c_v = 1'b0; end
    endtask
    task automatic wrow(input [9:0] a, input [255:0] d);
        begin @(negedge clk); sw_v = 1'b1; sw_a = a; sw_m = 8'hFF; sw_d = d; @(negedge clk); sw_v = 1'b0; end
    endtask
    task automatic vs_wait;
        begin repeat (8) @(negedge clk); while (u_lf.u_vs.busy) @(negedge clk); repeat (4) @(negedge clk); end
    endtask
    // beat partial triples
    always @(posedge clk) if (e_v) begin
        t_rl <= cyc;
        if (e_c !== np[1:0] || e_d[31:0] !== pm[3 * np] || e_d[63:32] !== pm[3 * np + 1] || e_d[95:64] !== pm[3 * np + 2]) begin
            bad = bad + 1;
            if (bad < 6) $display("PARTIAL MISMATCH copy %0d/%0d hh %h/%h kk %h/%h dd %h/%h", e_c, np, e_d[31:0], pm[3 * np],
                                  e_d[63:32], pm[3 * np + 1], e_d[95:64], pm[3 * np + 2]);
        end
        np = np + 1;
    end
    always @(posedge clk) if (u_lf.u_vs.x_wv && u_lf.u_vs.op == 4'd14) t_al <= cyc;
    reg rd_on = 1'b0;
    always @(posedge clk) if (lo_v && rd_on) begin
        if (lo_d !== hrow(nlo, 1)) begin
            bad = bad + 1;
            if (bad < 6) $display("OUT MISMATCH half row %0d got %h want %h", nlo, lo_d, hrow(nlo, 1));
        end
        nlo = nlo + 1;
    end
    initial begin
        if (!$value$plusargs("dir=%s", dir)) $fatal(1, "dir required");
        $readmemh({dir, "/h.mem"}, hm); $readmemh({dir, "/k.mem"}, km); $readmemh({dir, "/w.mem"}, wm);
        $readmemh({dir, "/v.mem"}, vm); $readmemh({dir, "/g.mem"}, gm); $readmemh({dir, "/p.mem"}, pm);
        $readmemh({dir, "/y.mem"}, ym);
        repeat (4) @(negedge clk); rst_n = 1'b1; repeat (10) @(negedge clk);
        for (i = 0; i < 16; i = i + 1) wrow(2 * i, hrow(i, 0));
        for (j = 0; j < 4; j = j + 1) for (i = 0; i < 8; i = i + 1) begin
            wrow(A0 + 16 * j + 2 * i, {km[64 * j + 8 * i + 7], km[64 * j + 8 * i + 6], km[64 * j + 8 * i + 5], km[64 * j + 8 * i + 4],
                                      km[64 * j + 8 * i + 3], km[64 * j + 8 * i + 2], km[64 * j + 8 * i + 1], km[64 * j + 8 * i]});
            wrow(A0 + 64 + 16 * j + 2 * i, {wm[64 * j + 8 * i + 7], wm[64 * j + 8 * i + 6], wm[64 * j + 8 * i + 5], wm[64 * j + 8 * i + 4],
                                      wm[64 * j + 8 * i + 3], wm[64 * j + 8 * i + 2], wm[64 * j + 8 * i + 1], wm[64 * j + 8 * i]});
        end
        for (i = 0; i < 8; i = i + 1)
            wrow(A0 + 128 + 2 * i, {vm[8 * i + 7], vm[8 * i + 6], vm[8 * i + 5], vm[8 * i + 4], vm[8 * i + 3], vm[8 * i + 2],
                               vm[8 * i + 1], vm[8 * i]});
        repeat (4) @(negedge clk);
        cmd(4'd3, 10'd0, 10'd0, 8'd0, 128'd0); repeat (40) @(negedge clk);          // HLOAD h -> vn
        cmd(4'd4, 10'd300, 10'd0, 8'd0, 128'd0); repeat (40) @(negedge clk);        // HSTORE vn -> rows 300..
        t_r = cyc + 1;
        cmd(4'd14, 10'd300, A0, 8'd64, 128'd0); vs_wait;                         // REDUCE
        for (j = 0; j < 4; j = j + 1) begin @(negedge clk); g_v = 1'b1; g_c = j; g_d = gm[j]; end
        @(negedge clk); g_v = 1'b0; repeat (4) @(negedge clk);
        t_a = cyc + 1;
        cmd(4'd14, A0, 10'd400, 8'd32, {97'd0, 1'b1, 30'd0}); vs_wait;          // ADD (imm[30])
        cmd(4'd3, 10'd400, 10'd0, 8'd0, 128'd0); repeat (40) @(negedge clk);        // HLOAD results -> vn
        cmd(4'd4, 10'd500, 10'd0, 8'd0, 128'd0); repeat (40) @(negedge clk);        // HSTORE vn -> rows 500..
        rd_on = 1'b1;
        cmd(4'd6, 10'd500, 10'd0, 8'd16, 128'd0); repeat (60) @(negedge clk);       // RDOUT 16 pairs
        $display("LEAFENG mut=%0d partials=%0d half_rows=%0d mismatches=%0d fault=%b vp%b vs%b reduce_cmd_to_last_partial=%0d add_cmd_to_last_write=%0d",
                 MUT, np, nlo, bad, f_lf, u_lf.f_vp, u_lf.f_vs, t_rl - t_r, t_al - t_a);
        if (bad == 0 && np == 4 && nlo == 16 && !f_lf) $display("PASS"); else $display("FAIL");
        $finish;
    end
    initial begin #200000; $display("GLOBAL TIMEOUT"); $display("FAIL"); $finish; end
endmodule
