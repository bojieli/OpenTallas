`timescale 1ns/1ps
// TOK-DS/ENTRY (2026-10-25): actual S81 entry mechanism cut, one slice, one beat leaf.
//   entry pin (ot_s81sl_rstopt ri_w / ri_e / vi, +PORT=0/1/2) -> ot_s81sl_xrt1 (production C1 control plane master)
//   -> ot_s81sl_rly W594 / W667, D 4 (the slice leaf <-> centre glue: production c1x_k8_cap5r_lp = DLK 1 + one landed
//   crossing of +3 edges on leaves 0/1/3/4, DLK 4 on leaf 2: 4 edges on every leaf under one clock)
//   -> ot_s81sl_vp (leaf store: 2 x ot_sram_1r1w_512x128_m4_r2c2).
// Stimulus = the real entry image rows of one (sid, leaf) (tools/s81_dv/layer_prog/entry_inputs.py on the die + fixture),
// written by the gate as memh: target-5 row writes at the two-edge entry_boot cadence, then the slice/leaf's own VP HLOAD,
// GAIN and an RDOUT of the delayed-pre row.  Measured per write: entry pin edge -> SRAM w_ce_in edge (store commit);
// HLOAD pin -> last vp hw_v; GAIN pin -> last vp wl_v.  Data is checked exactly at every commit (wd_in vs the image row),
// and read back through the VP's own read path (HLOAD hw_d, GAIN wl_d, RDOUT lo_d) against the image rows.
// +MUT=1 flips one payload data bit (bit +MUTB of the row data) of write +MUTI at the entry pin: must FAIL.
// One common bench clock (phase 0); die route phases / regional clocks are outside this cut.
module tb_entry_vp;
    localparam integer W = 1104, V = 276, MAXW = 64;
    reg clk = 0; always #0.5 clk = ~clk;
    reg rst_n = 0;
    integer port = 0, mut = 0, muti = 13, mutb = 5, nw = 0, leaf = 0, sid_i = 0, cyc = 0, bad = 0, i, j, r, k;
    reg [3:0] sid = 4'd0;
    reg [W-1:0] wbeat [0:MAXW-1];          // entry-image CTL beats (header + 186-b payload), one per row write
    reg [143:0] wexp [0:MAXW-1];           // {row 16, data 128}
    reg [W-1:0] cbeat [0:2];               // HLOAD, GAIN, RDOUT CTL beats of this slice / leaf
    reg [15:0] cargs [0:2];                // HLOAD a0, GAIN a0, RDOUT a0
    reg [W-1:0] line = 0;
    reg drv_v = 0; integer drv_i = -1;     // which write is on the pin this edge (-1 = none, 100+k = command k)
    integer pin_at [0:MAXW-1]; integer commit_at [0:MAXW-1]; integer ncommit [0:MAXW-1];
    integer cpin [0:2]; integer hw_n = 0, hw_last = -1, wl_n = 0, wl_last = -1, lo_n = 0, lo_last = -1, stray = 0;

    // ---------------------------------------------------------------- DUT chain
    wire [W-1:0] ri_w = (port == 0) ? line : {W{1'b0}};
    wire [W-1:0] ri_e = (port == 1) ? line : {W{1'b0}};
    wire [V-1:0] vi   = (port == 2) ? line[V-1:0] : {V{1'b0}};
    wire [W-1:0] ro_e, ro_w, dl_e, dl_w, ci_b; wire [V-1:0] vo, dl_vb; wire [2:0] ci_dir;
    wire dl_ev, dl_wv, dl_vv, f_rs, f_xr, f_vp;
    wire [172:0] nx_wi, nx_ei; wire [2:0] g_v3, g_fam; wire [20:0] g_idx; wire [3071:0] g_d3;
    ot_s81sl_rstopt u_rs (.clk(clk), .rst_n(rst_n), .sid(sid), .ri_w(ri_w), .ri_e(ri_e), .ro_e(ro_e), .ro_w(ro_w),
        .vi(vi), .vo(vo), .xf_v(5'd0), .xf_s(5'd0), .xf({5*V{1'b0}}), .nx_wi(nx_wi), .nx_ei(nx_ei),
        .nx_eo(173'd0), .nx_wo(173'd0), .g_v(g_v3), .g_fam(g_fam), .g_idx(g_idx), .g_d(g_d3),
        .dl_ev(dl_ev), .dl_e(dl_e), .dl_wv(dl_wv), .dl_w(dl_w), .dl_vv(dl_vv), .dl_vb(dl_vb),
        .ci_dir(ci_dir), .ci_b(ci_b), .fault(f_rs));
    wire [4:0] c_v, sw_v, lo_v_x; wire [159:0] c_d; wire [49:0] sw_a; wire [39:0] sw_m; wire [1279:0] sw_d, lo_d_x;
    wire rb_v; wire [31:0] rb_d; wire gv; wire [1:0] gc; wire [31:0] gd;
    wire x_go, x_mode, x_sv, is_v, cfg_v; wire [31:0] x_eps, x_scale, x_s; wire [7:0] x_si; wire [159:0] is_d, cfg_d;
    ot_s81sl_xrt1 u_xr (.clk(clk), .rst_n(rst_n), .sid(sid), .dl_ev(dl_ev), .dl_e(dl_e), .dl_wv(dl_wv), .dl_w(dl_w),
        .dl_vv(dl_vv), .dl_vb(dl_vb), .ci_dir(ci_dir), .ci_b(ci_b), .c_v(c_v), .c_d(c_d), .sw_v(sw_v), .sw_a(sw_a),
        .sw_m(sw_m), .sw_d(sw_d), .lo_v(lo_v_x), .lo_d(lo_d_x), .p_v(5'd0), .p_d(160'd0), .rb_v(rb_v), .rb_d(rb_d),
        .e_v(5'd0), .e_c(10'd0), .e_d(480'd0), .eg_v(1'b0), .eg_c(2'd0), .eg_d(32'd0), .g_v(gv), .g_c(gc), .g_d(gd),
        .x_go(x_go), .x_mode(x_mode), .x_eps(x_eps), .x_scale(x_scale), .x_sv(x_sv), .x_si(x_si), .x_s(x_s),
        .x_rbv(1'b0), .x_rbd(32'd0), .is_v(is_v), .is_d(is_d), .cfg_v(cfg_v), .cfg_d(cfg_d), .fault(f_xr));
    // leaf <-> centre glue of the selected leaf: exact production bundle layouts (ot_s81sl_slice_c1x dn_x<k> / up_l<k>)
    reg [2:0] lf = 3'd0;
    wire [593:0] dn_x = {c_v[lf], c_d, sw_v[lf], sw_a[10 * lf +: 10], sw_m[8 * lf +: 8], sw_d[256 * lf +: 256],
                         2'd0, 24'd0, 64'd0, rb_v, rb_d, gv, gc, gd};   // cw_* = capture (not in this cut): idle
    wire [593:0] dn_l;
    ot_s81sl_rly #(.W(594), .D(4)) u_dn (.clk(clk), .d(dn_x), .q(dn_l));
    wire lo_v; wire [255:0] lo_d; wire [666:0] up_x;
    ot_s81sl_rly #(.W(667), .D(4)) u_up (.clk(clk), .d({lo_v, lo_d, 410'd0}), .q(up_x));
    assign lo_v_x = {4'd0, up_x[666]} << lf; assign lo_d_x = {1024'd0, up_x[665:410]} << (256 * lf);
    wire s_v, x_qv, hw_v, hw_hf, hr_v, hr_hf, n_go, m_v, m_q, m_b, wl_v;
    wire [159:0] s_d; wire [255:0] x_qd, hw_d, wl_d; wire [2:0] hw_j, hr_j, wl_i; wire [127:0] n_pre; wire [7:0] m_i;
    ot_s81sl_vp u_vp (.clk(clk), .rst_n(rst_n), .c_v(dn_l[593]), .c_d(dn_l[592:433]), .sw_v(dn_l[432]),
        .sw_a(dn_l[431:422]), .sw_m(dn_l[421:414]), .sw_d(dn_l[413:158]), .cw_v(dn_l[157:156]), .cw_a(dn_l[155:132]),
        .cw_d(dn_l[131:68]), .lo_v(lo_v), .lo_d(lo_d), .s_v(s_v), .s_d(s_d), .x_rv(1'b0), .x_ra(10'd0), .x_qv(x_qv),
        .x_qd(x_qd), .x_wv(1'b0), .x_wa(10'd0), .x_wm(8'd0), .x_wd(256'd0), .hw_v(hw_v), .hw_j(hw_j), .hw_hf(hw_hf),
        .hw_d(hw_d), .hr_v(hr_v), .hr_j(hr_j), .hr_hf(hr_hf), .hq_v(1'b0), .hq_d(256'd0), .n_go(n_go), .n_pre(n_pre),
        .m_v(m_v), .m_q(m_q), .m_b(m_b), .m_i(m_i), .wl_v(wl_v), .wl_i(wl_i), .wl_d(wl_d), .fault(f_vp));

    // ---------------------------------------------------------------- expected leaf-store rows (image; unwritten = 0)
    function automatic [127:0] row_exp(input integer row);
        integer q; begin
            row_exp = 128'd0;
            for (q = 0; q < nw; q = q + 1) if (wexp[q][143:128] == row) row_exp = wexp[q][127:0];
        end
    endfunction
    function automatic integer row_idx(input integer row);
        integer q; begin
            row_idx = -1;
            for (q = 0; q < nw; q = q + 1) if (wexp[q][143:128] == row) row_idx = q;
        end
    endfunction

    // ---------------------------------------------------------------- monitors (sample at the posedge, as rdpair_leaf4)
    always @(posedge clk) begin
        cyc <= cyc + 1;
        if (drv_v && drv_i >= 0 && drv_i < MAXW) pin_at[drv_i] = cyc;
        if (drv_v && drv_i >= 100) cpin[drv_i - 100] = cyc;
        if (rst_n) begin
            for (k = 0; k < 2; k = k + 1)
                if ((k == 0 && u_vp.u_b0.w_ce_in) || (k == 1 && u_vp.u_b1.w_ce_in)) begin
                    r = 2 * ((k == 0) ? u_vp.u_b0.w_addr_in : u_vp.u_b1.w_addr_in) + k;
                    j = row_idx(r);
                    if (j < 0) begin stray = stray + 1; $display("STRAY commit row %0d cyc %0d", r, cyc); end
                    else begin
                        commit_at[j] = cyc; ncommit[j] = ncommit[j] + 1;
                        if (((k == 0) ? u_vp.u_b0.w_mask_in : u_vp.u_b1.w_mask_in) !== {128{1'b1}} ||
                            ((k == 0) ? u_vp.u_b0.wd_in : u_vp.u_b1.wd_in) !== wexp[j][127:0]) begin
                            bad = bad + 1; $display("COMMIT DATA MISMATCH row %0d", r);
                        end
                    end
                end
            if (hw_v) begin
                hw_n = hw_n + 1; hw_last = cyc; r = cargs[0] + 2 * (2 * hw_j + hw_hf);
                if (hw_d !== {row_exp(r + 1), row_exp(r)}) begin bad = bad + 1; $display("HLOAD DATA MISMATCH rows %0d/%0d", r, r + 1); end
            end
            if (wl_v) begin
                wl_n = wl_n + 1; wl_last = cyc; r = cargs[1] + 2 * wl_i;
                if (wl_d !== {row_exp(r + 1), row_exp(r)}) begin bad = bad + 1; $display("GAIN DATA MISMATCH rows %0d/%0d", r, r + 1); end
            end
            if (lo_v) begin
                lo_n = lo_n + 1; lo_last = cyc; r = cargs[2];
                if (lo_d !== {row_exp(r + 1), row_exp(r)}) begin bad = bad + 1; $display("RDOUT DATA MISMATCH rows %0d/%0d", r, r + 1); end
            end
            // only the selected leaf may see commands / row writes
            if (((c_v | sw_v) & ~(5'd1 << lf)) != 5'd0) begin bad = bad + 1; $display("WRONG LEAF c_v %b sw_v %b", c_v, sw_v); end
        end
    end
    task tick(input integer n); repeat (n) @(negedge clk); endtask
    task drive(input [W-1:0] b, input integer idx);
        begin line = b; drv_v = 1; drv_i = idx; tick(1); line = 0; drv_v = 0; drv_i = -1; end
    endtask

    integer maxc;
    initial begin
        void'($value$plusargs("PORT=%d", port)); void'($value$plusargs("MUT=%d", mut));
        void'($value$plusargs("MUTI=%d", muti)); void'($value$plusargs("MUTB=%d", mutb));
        void'($value$plusargs("NW=%d", nw)); void'($value$plusargs("LEAF=%d", leaf)); void'($value$plusargs("SID=%d", sid_i));
        if (port < 0 || port > 2 || nw < 1 || nw > MAXW || leaf < 0 || leaf > 4) $fatal(1, "ENTRY_VP FAIL bad arguments");
        sid = sid_i[3:0]; lf = leaf[2:0];
        $readmemh("writes.memh", wbeat); $readmemh("expect.memh", wexp); $readmemh("cmds.memh", cbeat);
        $readmemh("cargs.memh", cargs);
        for (i = 0; i < MAXW; i = i + 1) begin pin_at[i] = -1; commit_at[i] = -1; ncommit[i] = 0; end
        for (i = 0; i < 3; i = i + 1) cpin[i] = -1;
        if (port == 2) for (i = 0; i < nw; i = i + 1) if (wbeat[i][W-1:V] != 0) $fatal(1, "ENTRY_VP FAIL V beat wider than 276");
        tick(32); rst_n = 1; tick(32);
        // entry_boot cadence: one target-5 row write every two edges
        for (i = 0; i < nw; i = i + 1) begin
            if (mut == 1 && i == muti) drive(wbeat[i] ^ ({{W-1{1'b0}}, 1'b1} << (21 + 26 + 14 + mutb)), i);
            else drive(wbeat[i], i);
            tick(1);
        end
        tick(40);
        drive(cbeat[0], 100);                       // HLOAD a0
        tick(60);
        drive(cbeat[1], 101);                       // GAIN a0
        tick(60);
        drive(cbeat[2], 102);                       // RDOUT a0, n 1: the delayed-pre row
        tick(60);
        maxc = 0;
        for (i = 0; i < nw; i = i + 1) begin
            if (ncommit[i] != 1 || pin_at[i] < 0) begin bad = bad + 1; $display("ROW %0d commits %0d", wexp[i][143:128], ncommit[i]); end
            else begin
                $display("AGE T5 i=%0d row=%0d pin=%0d commit=%0d age=%0d", i, wexp[i][143:128], pin_at[i], commit_at[i],
                         commit_at[i] - pin_at[i]);
                if (commit_at[i] - pin_at[i] > maxc) maxc = commit_at[i] - pin_at[i];
            end
        end
        if (hw_n != 16 || wl_n != 8 || lo_n != 1 || stray != 0) begin
            bad = bad + 1; $display("COUNTS hw %0d wl %0d lo %0d stray %0d", hw_n, wl_n, lo_n, stray);
        end
        if (f_rs || f_xr || f_vp) begin bad = bad + 1; $display("FAULT rstopt %b xrt %b vp %b", f_rs, f_xr, f_vp); end
        $display("AGE HLOAD pin=%0d last_hw=%0d age=%0d", cpin[0], hw_last, hw_last - cpin[0]);
        $display("AGE GAIN pin=%0d last_wl=%0d age=%0d", cpin[1], wl_last, wl_last - cpin[1]);
        $display("AGE RDOUT pin=%0d lo=%0d age=%0d", cpin[2], lo_last, lo_last - cpin[2]);
        $display("ENTRY_VP port=%0d sid=%0d leaf=%0d nw=%0d mut=%0d bad=%0d max_t5=%0d", port, sid_i, leaf, nw, mut, bad, maxc);
        if (bad) $fatal(1, "ENTRY_VP FAIL");
        $display("ENTRY_VP PASS");
        $finish;
    end
    initial begin tick(4000); $fatal(1, "ENTRY_VP FAIL finite static calendar exceeded"); end
endmodule
