// tb_s81dv_frame_xs (TOK-S81-GAPS/XS2b 10-19): the S81-DV frame driven by the SLICE X STREAMER ot_s81sl_xs.
// The frame bench tb_s81dv_frame.sv drives the frame from the w17w10 PQ spine (+ dsfd_pq_lx, the XDLY payload splice);
// every frame return-plan constant was measured there.  Here the frame's x comes from ot_s81sl_xs running the compiled
// slice programme of tools/s81_dv/layer_prog/xs_calendar.py (calendar action / time ROMs, phase / stream ROMs, is_d
// issuer words, ring all-gather beats), and the spine path of the original bench runs alongside as the REFERENCE:
//   LOCKSTEP  every edge the xs frame word must equal the reference frame word D edges earlier (D = +D, compiled):
//             every bit, except the q payload (x0 / x1) of words whose q valid is low on both sides (cfg / go-only
//             and invalid words carry each producer's stale stream fields there; dsfd_pq_lx qualifies them by qv);
//   RET       the frame's return words (RET <edge>) -- the check (xs_calendar.py check) wants the plan's words at
//             plan edge + D, values exact against the golden segment tree;
//   FAULT     xs sticky fault, frame status, lane encoder.
// Gathered beats carry the x exactly as the owning slice's quantiser hands it to the ring: the q family is the
// production act-quant output the spine holds (u_sp.qb / eb: 2 blocks {q 256, e 10} a beat), the BF16 family the RNE
// words (u_sp.bb); the bench injects them only after the spine has loaded them.
`timescale 1ns/1ps
`ifndef FRAME
`define FRAME col_h9
`endif
module tb_s81dv_frame_xs;
    localparam integer VAW = 14;
    localparam integer GSLACK = `ifdef TB_GSLACK `TB_GSLACK `else 36 `endif;
    localparam integer NIT = 8192;
    reg clk = 1'b0;
    always #0.5 clk = ~clk;
    reg rst_n = 1'b0;
    reg go = 1'b0;
    integer T, K, OPS, PH, D, edge_n = 0;
    reg [31:0] vm [0:(1 << VAW) - 1];
    reg [160:0] pis [0:NIT-1];          // {is_v, is_d}
    reg [26:0]  pg  [0:NIT-1];          // {idx 3x7, fam 3, v 3}
    reg [8*1024-1:0] rom_dir;
    integer ii;
    initial begin
        for (ii = 0; ii < (1 << VAW); ii = ii + 1) vm[ii] = 32'd0;
        for (ii = 0; ii < NIT; ii = ii + 1) begin pis[ii] = 161'd0; pg[ii] = 27'd0; end
        if ($value$plusargs("OT_ROM_DIR=%s", rom_dir)) begin
            $readmemh({rom_dir, "/vm.hex"}, vm);
            $readmemh({rom_dir, "/xs_is.hex"}, pis);
            $readmemh({rom_dir, "/xs_g.hex"}, pg);
        end
        if (!$value$plusargs("T=%d", T)) T = 3000;
        if (!$value$plusargs("K=%d", K)) K = 2048;
        if (!$value$plusargs("OPS=%d", OPS)) OPS = 8;
        if (!$value$plusargs("PH=%d", PH)) PH = 0;
        if (!$value$plusargs("D=%d", D)) D = 0;
    end
    // ================================================================ REFERENCE: spine + lane encoder (as tb_s81dv_frame)
    wire x_re; wire [VAW-1:0] x_addr; reg [64*32-1:0] x_q;
    integer k;
    always @(posedge clk) if (x_re) for (k = 0; k < 64; k = k + 1) x_q[32*k +: 32] <= vm[x_addr + VAW'(k)];
    wire [1633:0] f_bus;
    wire sp_ready, sp_idle, sp_fault;
    wire [0:0] w_we; wire [VAW-1:0] w_addr; wire [31:0] w_data; wire [31:0] phase_cycles; wire ev_go, ev_end; wire [1:0] ev_tag;
    ot_v41_spine_pq_static_w17w10 #(.PHW(10), .SAW(14), .R(1), .VAW(VAW), .VRD(64), .KMAX(6144), .BST(2), .PQ(1), .GSLACK(GSLACK)) u_sp (
        .clk(clk), .rst_n(rst_n), .go(go), .i_ph(PH[9:0]), .i_np(3'd0), .i_xbase({VAW{1'b0}}), .i_xps(VAW'(K)),
        .i_obase({VAW{1'b0}}), .i_ops(VAW'(OPS)), .i_fmt(2'd0), .ready(sp_ready), .idle(sp_idle), .x_re(x_re),
        .x_addr(x_addr), .x_q(x_q), .w_we(w_we), .w_addr(w_addr), .w_data(w_data),
        .f_cfg_go(), .f_cfg_ph(), .f_cfg_np(), .f_go(), .f_go_bf(), .f_go_tag(), .f_xs_v(), .f_xs_p(), .f_xs_b(), .f_xs_sv(),
        .f_xs_q0(), .f_xs_e0(), .f_xs_q1(), .f_xs_e1(), .f_xs_pos(), .f_xb_pos(), .f_xb_v(), .f_xb_b(), .f_xb_sv(), .f_xb_u(),
        .f_xb_d(), .f_bus(f_bus), .r_v(1'b0), .r_row(16'd0), .r_pos(3'd0), .r_fp32(32'd0), .r_bf16(16'd0), .r_e(1'b0),
        .f_fault(1'b0), .fault(sp_fault), .phase_cycles(phase_cycles), .ev_go(ev_go), .ev_end(ev_end), .ev_tag(ev_tag));
    wire [1100:0] xw, xe_unused; wire lx_fault;
    dsfd_pq_lx u_lx (.ck(clk), .rst(rst_n), .f_bus(f_bus), .f_fault(1'b0), .xws(3'b000), .xes(3'b000), .xw(xw),
                     .xe(xe_unused), .f_fault_c(lx_fault));
    localparam integer XDLY = `ifdef TB_XDLY `TB_XDLY `else 4 `endif;
    reg [1100:0] xwd [0:XDLY];
    integer di;
    always @(*) xwd[0] = xw;
    always @(posedge clk) for (di = XDLY; di > 0; di = di - 1) xwd[di] <= xwd[di - 1];
    wire [1100:0] xs_ref = xwd[XDLY];
    wire [1100:0] xw_ref = {xs_ref[1100:565], xw[564:550], xs_ref[549:1], xw[550] | xw[551] | xs_ref[283]};
    // ================================================================ DUT x source: the slice x streamer
    reg         is_v; reg [159:0] is_d;
    reg  [2:0]  g_v, g_fam; reg [20:0] g_idx; reg [3071:0] g_d;
    wire        xsw_v; wire [1100:0] xsw; wire xs_fault;
    ot_s81sl_xs u_xs (.clk(clk), .rst_n(rst_n), .g_v(g_v), .g_fam(g_fam), .g_idx(g_idx), .g_d(g_d), .is_v(is_v),
                      .is_d(is_d), .xw_v(xsw_v), .xw_d(xsw), .fault(xs_fault));
    // inputs of the posedge whose edge number (edge_n before it) is n are set on the negedge before it
    integer s, l, gb;
    always @(negedge clk) begin
        {is_v, is_d} = (edge_n < NIT && rst_n) ? pis[edge_n] : 161'd0;
        g_v = 3'd0; g_fam = 3'd0; g_idx = 21'd0; g_d = '0;
        if (edge_n < NIT && rst_n) begin
            g_v = pg[edge_n][2:0]; g_fam = pg[edge_n][5:3]; g_idx = pg[edge_n][26:6];
            for (s = 0; s < 3; s = s + 1) if (g_v[s]) begin
                gb = g_idx[7*s +: 7];
                if (g_fam[s]) begin
                    for (l = 0; l < 64; l = l + 1) g_d[1024*s + 16*l +: 16] = u_sp.bb[64*gb + l];
                end else begin
                    g_d[1024*s +: 256] = u_sp.qb[2*gb];       g_d[1024*s + 256 +: 10] = u_sp.eb[2*gb];
                    g_d[1024*s + 266 +: 256] = u_sp.qb[2*gb + 1]; g_d[1024*s + 522 +: 10] = u_sp.eb[2*gb + 1];
                end
            end
        end
    end
    // ---------------- the slice x-chain word from the xs
    reg [7:0] mkq;
    always @(posedge clk or negedge rst_n) if (!rst_n) mkq <= 8'd0; else mkq <= {mkq[6:0], 1'b1};
    wire mk = mkq[7];
    wire [1103:0] x = {xsw[1100:565], xsw[0], mk, xsw[564:0], mk};
    // ================================================================ DUT frame (as tb_s81dv_frame)
    wire [1103:0] xo; wire [3:0] xok; wire [69:0] ret;
`ifdef TB_FWD_GATE
    localparam integer LDLY = `ifdef TB_LDLY `TB_LDLY `else 0 `endif;
    reg [1:0] gsy; always @(posedge clk or negedge rst_n) if (!rst_n) gsy <= 2'b00; else gsy <= {gsy[0], 1'b1};
    reg [1103:0] xl_ [0:LDLY]; reg gl_ [0:LDLY];
    integer li;
    always @(*) begin xl_[0] = x; gl_[0] = gsy[1]; end
    always @(posedge clk) for (li = LDLY; li > 0; li = li - 1) begin xl_[li] <= xl_[li - 1]; gl_[li] <= gl_[li - 1]; end
    reg gen_l = 1'b0; always @(negedge clk) gen_l <= gl_[LDLY];
    wire xkg = clk & gen_l;
    wire [1103:0] xin = xl_[LDLY];
    `FRAME #(.INSTANCE("f")) dut (.clk(clk), .cr(clk), .cr_s(clk), .rst_n(rst_n), .x(xin), .xk({4{xkg}}), .xo(xo), .xok(xok),
                                  .ret(ret));
`else
    wire [1103:0] xin = x;
    `FRAME #(.INSTANCE("f")) dut (.clk(clk), .cr(clk), .cr_s(clk), .rst_n(rst_n), .x(x), .xk({4{clk}}), .xo(xo), .xok(xok),
                                  .ret(ret));
`endif
    // ================================================================ lockstep: xs word (edge e) vs reference (edge e - D)
    reg [1100:0] refw [0:NIT-1];
    reg [1100:0] mk_;
    // compared bits: everything, except the q payload x0 / x1 ([282:1], [549:284]) of a word whose q valid (x0 msb, bit
    // 283) is low on both sides -- dsfd_pq_lx qualifies that payload by qv; cfg / go-only words (valid = cfg | go) carry
    // each producer's stale stream fields there (the spine's held bt_* registers, the xs's held head fields)
    function automatic [1100:0] qmask(input [1100:0] a, input [1100:0] b);
        qmask = {1101{1'b1}};
        if (!a[283] && !b[283]) begin qmask[282:1] = '0; qmask[549:284] = '0; end
    endfunction
    integer bi, nb, e_, cmp = 0, mism = 0, vref = 0, vxs = 0, first_bad = -1, xs_fault_at = -1, first_ref = -1, first_xs = -1;
    always @(negedge clk) if (rst_n && edge_n > 0 && edge_n <= NIT) begin
        e_ = edge_n - 1;                                  // the word after posedge e_
        refw[e_] = xw_ref;
        if (xw_ref[0]) begin vref = vref + 1; if (first_ref < 0) first_ref = e_; end
        if (xsw[0]) begin vxs = vxs + 1; if (first_xs < 0) first_xs = e_; end
        if (xs_fault && xs_fault_at < 0) xs_fault_at = e_;
        if (xsw_v !== xsw[0]) begin mism = mism + 1; $display("XSL_MISMATCH edge %0d xw_v != xw_d[0]", e_); end
        if (e_ - D >= 0) begin
            cmp = cmp + 1;
            mk_ = qmask(refw[e_ - D], xsw);
            if ((refw[e_ - D] & mk_) !== (xsw & mk_)) begin
                mism = mism + 1;
                if (first_bad < 0) first_bad = e_;
                if (mism <= 6) $display("XSL_MISMATCH xs edge %0d ref edge %0d valid %b/%b cc %h/%h", e_, e_ - D, xsw[0],
                                        refw[e_ - D][0], xsw[564:550], refw[e_ - D][564:550]);
                if (mism <= 2) begin
                    nb = 0;
                    for (bi = 0; bi < 1101; bi = bi + 1)
                        if (mk_[bi] && refw[e_ - D][bi] !== xsw[bi] && nb < 12) begin
                            $display("XSL_BIT edge %0d bit %0d xs %b ref %b", e_, bi, xsw[bi], refw[e_ - D][bi]); nb = nb + 1; end
                end
            end
        end else if (xsw[0]) begin
            mism = mism + 1;
            $display("XSL_MISMATCH xs edge %0d valid before the reference window", e_);
        end
    end
    // ================================================================ checks / capture (as tb_s81dv_frame)
    reg [1103:0] x_d; reg live = 1'b0; integer xo_checked = 0, nret = 0, nflt = 0;
    always @(posedge clk) begin
        x_d <= xin;
        if (rst_n) edge_n <= edge_n + 1;
        if (live) begin
            if (xo !== x_d) begin
                if (xo_checked < 1000000) $display("XO_MISMATCH edge %0d", edge_n);
            end
            xo_checked <= xo_checked + 1;
        end
        if (rst_n && ret[1]) begin $display("RET %0d %017h", edge_n, ret[67:2]); nret <= nret + 1; end
        if (rst_n && edge_n > 20 && (ret[69] || lx_fault) && nflt < 4) begin
            $display("FAULT edge %0d status %b lx %b", edge_n, ret[69:68], lx_fault); nflt <= nflt + 1; end
    end
    initial begin
        #5.2 rst_n = 1'b1;
        repeat (3) @(posedge clk);
        live = 1'b1;
        repeat (60) @(posedge clk);
        @(negedge clk) go = 1'b1;
        @(negedge clk) go = 1'b0;
        repeat (T) @(posedge clk);
        @(negedge clk);
        $display("XSL_LOCKSTEP D=%0d compared=%0d mismatch=%0d valid_ref=%0d valid_xs=%0d first_ref=%0d first_xs=%0d xs_fault_at=%0d",
                 D, cmp, mism, vref, vxs, first_ref, first_xs, xs_fault_at);
        $display("END edges=%0d ret_words=%0d xo_checked=%0d fault=%0d spine_fault=%b xs_fault=%b", edge_n, nret, xo_checked,
                 nflt, sp_fault, xs_fault);
        $finish;
    end
endmodule
