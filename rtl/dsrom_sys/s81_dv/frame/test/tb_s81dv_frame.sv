// tb_s81dv_frame: exact frame bench of the S81-DV frame master (FRAME = col_h9 / col_h10), tools/s81_dv/frame_bench.py.
// Driver = the die's own x path: ot_v41_spine_pq_static_w17w10 (PQ 1, R 1, its phase / stream ROMs and a vector
// memory, +OT_ROM_DIR) -> f_bus -> dsfd_pq_lx (+DSFD_PQ_STATIC_X2 +DSFD_PQ_HAS_BF_X2: the packed static lane word xw)
// -> the ot_s81sl_slice x-chain word {xw[1100:565], xw[0], mk, xw[564:0], mk} (mk = released reset marker) -> x.
// All frame clocks (clk, cr, cr_s, xk[3:0]) are the one bench clock.  Prints RET <edge> <ri word hex> for every valid
// return root word (rd[1]), XO_MISMATCH if xo != x one edge later, FAULT on frame status / lane encoder fault, END.
`timescale 1ns/1ps
`ifndef FRAME
`define FRAME col_h9
`endif
module tb_s81dv_frame;
    localparam integer VAW = 14;
    // go >= CW + 1 + GSLACK edges (6-bit spine counter: GSLACK <= 37) after the op's cfg broadcast (spine schedule parameter, default 6 in the vehicle):
    // the frame's elements must also finish the PQ shadow replay of the load before the op's go_e (measured here)
    localparam integer GSLACK = `ifdef TB_GSLACK `TB_GSLACK `else 36 `endif;
    reg clk = 1'b0;
    always #0.5 clk = ~clk;
    reg rst_n = 1'b0;
    reg go = 1'b0;
    integer T, K, OPS, PH, edge_n = 0;   // PH: the field phase the spine runs (+PH, default 0; TOK-S81-GAPS/XS multi-phase fields)
    // ---------------- spine + vector memory (as ot_v41_fieldtop_pq_static_w17w10)
    reg [31:0] vm [0:(1 << VAW) - 1];
    reg [8*1024-1:0] rom_dir;
    integer ii;
    initial begin
        for (ii = 0; ii < (1 << VAW); ii = ii + 1) vm[ii] = 32'd0;
        if ($value$plusargs("OT_ROM_DIR=%s", rom_dir)) $readmemh({rom_dir, "/vm.hex"}, vm);
        if (!$value$plusargs("T=%d", T)) T = 3000;
        if (!$value$plusargs("K=%d", K)) K = 2048;
        if (!$value$plusargs("OPS=%d", OPS)) OPS = 8;
        if (!$value$plusargs("PH=%d", PH)) PH = 0;
    end
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
    // ---------------- the die lane encoder and the slice x-chain word
    wire [1100:0] xw, xe_unused; wire lx_fault;
    dsfd_pq_lx u_lx (.ck(clk), .rst(rst_n), .f_bus(f_bus), .f_fault(1'b0), .xws(3'b000), .xes(3'b000), .xw(xw),
                     .xe(xe_unused), .f_fault_c(lx_fault));
    reg [7:0] mkq;                                   // released reset marker, 8 edges after the frame reset release
    always @(posedge clk or negedge rst_n) if (!rst_n) mkq <= 8'd0; else mkq <= {mkq[6:0], 1'b1};
    wire mk = mkq[7];
    // Compiler schedule (ledger row FIELD.CFG7_SEQ_PINREG, cfg7 contract lc -> go_e +4 edges at PINREG 1): the frame's
    // sequencers re-issue go to the elements 4 edges later than the PINREG-0 pair loader the spine's go -> beat
    // spacing was set for, so the x producer sends every beat (x0 / x1 / x2 payload and its xs_v) XDLY edges later than
    // the cc fields of the same op; the word valid is cfg | go of the current word or the delayed beat's xs_v.
    localparam integer XDLY = `ifdef TB_XDLY `TB_XDLY `else 4 `endif;
    reg [1100:0] xwd [0:XDLY];
    integer di;
    always @(*) xwd[0] = xw;
    always @(posedge clk) for (di = XDLY; di > 0; di = di - 1) xwd[di] <= xwd[di - 1];
    wire [1100:0] xs = xwd[XDLY];
    // TOK-S81-GAPS/XS2: a BF16 word (dsfd_pq_lx bv: go_bf = xw[565], xb_v = xw[569]; its payload replaces x0 / x1) is
    // valid too -- the delayed BF beat and the delayed go_bf (the BF front samples it with the sequencer's go_e, +4 like
    // the beats).  q-only words are unchanged (xw[565] = xw[569] = 0).
    wire [1100:0] xw2 = {xs[1100:565], xw[564:550], xs[549:1], xw[550] | xw[551] | xs[283] | xs[565] | xs[569]};
    wire [1103:0] x = {xw2[1100:565], xw2[0], mk, xw2[564:0], mk};
    // ---------------- DUT
    wire [1103:0] xo; wire [3:0] xok; wire [69:0] ret;
`ifdef TB_FWD_GATE
    // LANDFIX-SQ/F (10-18): the die's forwarded lane, as LANDING-CONTRACT L2 builds it -- the source's hop-0 clock gate
    // opens on the source edge G = the frame's regional reset release (2-flop sync of rst_n, the same edge as the
    // dsfd_cfifo_crs4 rsync), and the lane (ck_f AND data) reaches the frame TB_LDLY whole periods later (dL = LDLY x T).
    // With the gate, the landing's write epoch is source-relative, so ret must not move with LDLY inside the window
    // (E - D) T < dL < E T (E = LK, D = 4).  Without TB_FWD_GATE: xk = the free-running bench clock (old form).
    localparam integer LDLY = `ifdef TB_LDLY `TB_LDLY `else 0 `endif;
    reg [1:0] gsy; always @(posedge clk or negedge rst_n) if (!rst_n) gsy <= 2'b00; else gsy <= {gsy[0], 1'b1};
    reg [1103:0] xl_ [0:LDLY]; reg gl_ [0:LDLY];
    integer li;
    always @(*) begin xl_[0] = x; gl_[0] = gsy[1]; end
    always @(posedge clk) for (li = LDLY; li > 0; li = li - 1) begin xl_[li] <= xl_[li - 1]; gl_[li] <= gl_[li - 1]; end
    reg gen_l = 1'b0; always @(negedge clk) gen_l <= gl_[LDLY];       // ICG: enable latched while clk is low
    wire xkg = clk & gen_l;
    wire [1103:0] xin = xl_[LDLY];
    `FRAME #(.INSTANCE("f")) dut (.clk(clk), .cr(clk), .cr_s(clk), .rst_n(rst_n), .x(xin), .xk({4{xkg}}), .xo(xo), .xok(xok),
                                  .ret(ret));
`else
    wire [1103:0] xin = x;
    `FRAME #(.INSTANCE("f")) dut (.clk(clk), .cr(clk), .cr_s(clk), .rst_n(rst_n), .x(x), .xk({4{clk}}), .xo(xo), .xok(xok),
                                  .ret(ret));
`endif
`ifdef TB_DEBUG
    always @(posedge clk) if (rst_n && edge_n < 400) begin
        if (dut.u_cf.xflt || dut.u_cf.sti != 2'b00 || dut.u_cf.flt)
            $display("DBG edge %0d cf xflt %b fa %b fb %b mk %b/%b sti %b flt %b", edge_n, dut.u_cf.xflt, dut.u_cf.fa_,
                     dut.u_cf.fb_, dut.u_cf.oa_[0], dut.u_cf.ob_[0], dut.u_cf.sti, dut.u_cf.flt);
        if (x[1] || x[2]) $display("DBG edge %0d x v=%b go=%b cfg=%b ph=%0d", edge_n, x[1], x[551], x[552], x[562:553]);
    end
`endif
    // ---------------- checks / capture
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
`ifdef SEAM_REF
    // S81-P7 10-23 (tools/s81_dv/frame_seam_bench.sh): a REFERENCE banded frame (the vgch twin: D=4 landings across the
    // band seams, lockstep- and frame-bench proven) runs on the same framed traffic, and every band-seam output of the
    // DUT is compared with the reference landing output, every edge.  The frame-level ret/xo checks alone are blind to
    // seam timing when the traffic has slack (x landed long before go); this makes each seam an observed contract.
    `include "seam_ref.svh"
`endif
    initial begin
        #5.2 rst_n = 1'b1;
        repeat (3) @(posedge clk);
        live = 1'b1;
        repeat (60) @(posedge clk);
        @(negedge clk) go = 1'b1;
        @(negedge clk) go = 1'b0;
        repeat (T) @(posedge clk);
        $display("END edges=%0d ret_words=%0d xo_checked=%0d fault=%0d spine_fault=%b", edge_n, nret, xo_checked, nflt,
                 sp_fault);
        $finish;
    end
endmodule
`ifdef TB_PVTRACE
// diagnostic: every element return word at the element pv port (edge = the RET edge numbering)
module tb_s81dv_pvtrace (input wire clk, input wire [1:0] pv, input wire [31:0] prow, input wire [9:0] pseg,
                         input wire [9:0] pnseg);
    always @(posedge clk) if (|pv) $display("PV %0d %m %b rows %0d %0d seg %0d %0d n %0d", tb_s81dv_frame.edge_n, pv,
                                            prow[15:0], prow[31:16], pseg[4:0], pseg[9:5], pnseg[4:0]);
endmodule
bind ot_v41_rom_elem_q_qxpq_w10 tb_s81dv_pvtrace u_pvt (.clk(clk), .pv(pv), .prow(prow), .pseg(pseg), .pnseg(pnseg));
`endif
`ifdef TB_BFTRACE
// TOK-S81-GAPS/XS2 measurement probe (simulation only): every BF core's walker availability edge with the identity a
// static programme must present (the tools/s81/bf_programme_compile.py trace: G = core go, I = available, off = core
// cycles since go) on the RET edge numbering, every programmed issue the core rejects (programme_bad: the sticky
// programme_fault cause), and every BF column partial (the frame return tree leaf e<k>{w,e}.r = dsfd_bf_col r[0]).
module tb_bf_issue_trace (input wire fclk, input wire go, input wire go_bf, input wire ia, input wire [13:0] a_ctr,
                          input wire [14:0] op, input wire [2:0] ws, input wire wh, input wire [3:0] wc, input wire pi,
                          input wire pbad);
    integer cyc = 0, g = -1;
    always @(posedge fclk) begin
        cyc = cyc + 1;
        if (go) begin g = cyc; $display("BFG %m %0d %0d %0d", tb_s81dv_frame.edge_n, cyc, go_bf); end
        if (ia) $display("BFI %m %0d %0d %0d %0d %0d %0d %0d %0d %0d", tb_s81dv_frame.edge_n, cyc, cyc - g, a_ctr, op, ws,
                         wh, wc, go_bf);
        if (pi && pbad) $display("BFP_BAD %m edge %0d", tb_s81dv_frame.edge_n);
    end
endmodule
bind ot_v41_bf_front_core_roots tb_bf_issue_trace u_bft (.fclk(fclk), .go(go), .go_bf(go_bf), .ia(issue_available),
    .a_ctr(a_ctr), .op(programme_operand), .ws(w_s), .wh(w_h), .wc(w_cnt), .pi(prog_issue_u), .pbad(programme_bad));
module tb_bf_pvtrace (input wire clk, input wire pv, input wire [15:0] prow, input wire [4:0] pseg, input wire [4:0] pnseg);
    always @(posedge clk) if (pv) $display("BFPV %0d %m rows %0d seg %0d n %0d", tb_s81dv_frame.edge_n, prow, pseg, pnseg);
endmodule
bind ot_v41_bf_col tb_bf_pvtrace u_bfpv (.clk(clk), .pv(pv), .prow(prow), .pseg(pseg), .pnseg(pnseg));
`endif
