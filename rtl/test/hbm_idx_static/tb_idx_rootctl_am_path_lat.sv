`timescale 1ns/1ps
`default_nettype none
// HBM-BANKLAT-IDX 2026-10-19: ARGMAX path at the d4g GEN2c BUDGET (results/arch/hbm_banklat_1019/idx_budget.json):
// hb_idx__ctl = ot_hbm_idx_rootctl_static_am #(VM_RT 65, CR_RT 36, SEL_LAT 30) -> argmax_m -> LAR relay stages ->
// hb_argmax = ot_hbm_argmax_static_sw_vm_r2 #(VMX 77 = 5 + 65 + 4 + 3, ACK 52 = 13 + faces pin 1 + cq 19 + cr 19), its
// vm_rq -> LAQ relay stages -> argmax_rq. From tb_idx_rootctl_am_path (same stimulus and exact checks vs the CURRENT
// ot_hbm_idx_rootctl_static -> ot_hbm_argmax_static_sw_vm reference on RD 7 / ACKD 11): the DUT's VM model answers
// RD = 7 + CTL_M edges after the share's vm_rq port (bank 6 + pin 1 + rq4/rr4 lanes), its hub echo reaches cr
// ACKD = ACK_M - 2 edges after cq. Same requests / writes (payload + cq_seq) / done-fault-nan events in order, each class
// at ONE constant offset; TIES 0/1/2 as the source bench. Mutants: VMX_P 5 (the as-built r2 on GEN2c lanes),
// VMX_P 76, ACK_P 51.
module tb_idx_rootctl_am_path_lat;
`ifndef TIES
`define TIES 0
`endif
`ifndef AMMUT
`define AMMUT 0
`endif
`ifndef NREC
`define NREC 300
`endif
`ifndef MUT
`define MUT 0
`endif
`ifndef CTL_M
`define CTL_M 65
`endif
`ifndef LAQ
`define LAQ 4
`endif
`ifndef LAR
`define LAR 3
`endif
`ifndef ACK_M
`define ACK_M 52
`endif
`ifndef VMX_P
`define VMX_P (5 + `CTL_M + `LAQ + `LAR)
`endif
`ifndef ACK_P
`define ACK_P `ACK_M
`endif
    localparam integer RD = 7, ACKD = 11, RD1 = 7 + `CTL_M, ACKD1 = `ACK_M - 2, PD = 128;
    reg clk = 0, rst_n = 0; always #1 clk = ~clk;
    reg go = 0, mode = 0, a_mirror = 0; reg [17:0] imm_a = 0, a_base = 0, n = 0, o_base = 0; reg [15:0] o_is = 0;
    reg drop_rr = 0, drop_ack = 0;
    // ---------------- reference
    reg [2055:0] rr0 = 0; reg [273:0] cr0 = 0;
    wire [135:0] rq0, rqs0; wire [2055:0] arr0; wire [337:0] cq0; wire [1:0] s0; wire b0, d0, f0, n0, sf0;
    `define RC_IDLE .program_we(1'b0), .program_addr(8'd0), .program_data(256'd0), .start(1'b0), .length(12'd0), \
        .sel_op(), .sel_pass(), .sel_addr(), .link_flush(), .link_emit(), .link_group(), .link_clear(), .selected_v(4'hF), \
        .ingest_v(), .tree_ev(4'h0), .qfault(4'h0), .sf(1'b0), .lf(1'b0), .done(), .fault(), .topk_go(1'b0), .topk_k(4'd0), \
        .topk_order(1'b0), .topk_n(20'd0), .topk_m(20'd0), .topk_a_mirror(1'b0), .topk_a_base(18'd0), .topk_a_str(18'd0), \
        .topk_o_mirror(1'b0), .topk_o_base(18'd0), .topk_o_str(18'd0), .topk_has_r(1'b0), .topk_r_base(18'd0), .topk_r_str(18'd0), \
        .cq(), .cq_seq(), .cr(274'd0), .topk_busy(), .topk_done(), .topk_fault(), .index_rq(136'd0), .index_rr()
    ot_hbm_idx_rootctl_static rc0(.clk_program(clk), .clk_program_mem(clk), .clk_sel(clk), .clk_topk(clk), .clk_pair({4{clk}}),
        .rst_n(rst_n), `RC_IDLE, .argmax_rq(rq0), .argmax_rr(arr0), .vm_rq(rqs0), .vm_rr(rr0), .share_fault(sf0));
    ot_hbm_argmax_static_sw_vm #(.TP(192)) ref_(.clk(clk), .rst_n(rst_n), .die_id(8'd3), .go(go), .mode(mode), .imm_a(imm_a),
        .a_mirror(a_mirror), .a_base(a_base), .n(n), .o_base(o_base), .o_is(o_is), .vm_rq(rq0), .vm_rr(arr0),
        .cq(cq0), .cq_seq(s0), .cr(cr0), .busy(b0), .done(d0), .fault(f0), .nan_flag(n0));
    // ---------------- r2 + merge chain
    reg [2055:0] bank1 = 0; reg [273:0] cr1 = 0;
    wire [135:0] rq1, rqs; wire [263:0] am; wire [337:0] cq1; wire [1:0] s1; wire b1, d1, f1, n1, sf;
    // die lanes between hb_argmax and hb_idx__ctl (register stages, power up 0)
    reg [135:0] aq [0:15]; reg [263:0] ar [0:15]; wire [263:0] am_c; wire [135:0] rq1_l;
    initial for (integer d = 0; d < 16; d = d + 1) begin aq[d] = 0; ar[d] = 0; end
    always @(posedge clk) begin aq[0] <= rq1; ar[0] <= am_c; for (integer d = 1; d < 16; d = d + 1) begin aq[d] <= aq[d-1]; ar[d] <= ar[d-1]; end end
    assign rq1_l = (`LAQ == 0) ? rq1 : aq[`LAQ-1];
    assign am = (`LAR == 0) ? am_c : ar[`LAR-1];
    ot_hbm_idx_rootctl_static_am #(.AMMUT(`AMMUT), .VM_RT(`CTL_M), .CR_RT(36), .SEL_LAT(30)) rc1(.clk(clk), .rst_n(rst_n), `RC_IDLE, .argmax_rq(rq1_l), .argmax_m(am_c),
        .vm_rq(rqs), .vm_rr(bank1), .share_fault(sf));
    ot_hbm_argmax_static_sw_vm_r2 #(.TP(192), .MUT(`MUT), .VMX(`VMX_P), .ACK(`ACK_P)) dut(.clk(clk), .rst_n(rst_n), .die_id(8'd3), .go(go), .mode(mode),
        .imm_a(imm_a), .a_mirror(a_mirror), .a_base(a_base), .n(n), .o_base(o_base), .o_is(o_is), .vm_rq(rq1),
        .vm_rr(am), .cq(cq1), .cq_seq(s1), .cr(cr1), .busy(b1), .done(d1), .fault(f1), .nan_flag(n1));
    // ---------------- VM + client models (same function for both sides)
    function automatic [255:0] sdat(input [15:0] q, input integer l);
        integer k; reg [31:0] h; begin
            for (k = 0; k < 8; k = k + 1) begin h = {q, 3'(l), 3'(k)} * 32'h9E3779B1 ^ 32'h5bd1e995;
                sdat[32*k +: 32] = (`TIES == 2) ? 32'h3FC0_0000 : (`TIES == 1) ? (h[13] ? 32'h4000_0000 : 32'h3F80_0000) : (h & 32'hBFFF_FFFF); end
        end endfunction
    reg [16:0] p0 [0:PD-1][0:7]; reg [16:0] p1 [0:PD-1][0:7]; reg [16:0] c0 [0:PD-1]; reg [16:0] c1 [0:PD-1]; integer t, k;
    initial for (t = 0; t < PD; t = t + 1) begin c0[t] = 0; c1[t] = 0; for (k = 0; k < 8; k = k + 1) begin p0[t][k] = 0; p1[t][k] = 0; end end
    always @(posedge clk) begin
        for (t = PD-1; t > 0; t = t - 1) begin c0[t] <= c0[t-1]; c1[t] <= c1[t-1]; for (k = 0; k < 8; k = k + 1) begin p0[t][k] <= p0[t-1][k]; p1[t][k] <= p1[t-1][k]; end end
        for (k = 0; k < 8; k = k + 1) begin p0[0][k] <= {rqs0[17*k+16], rqs0[17*k +: 16]}; p1[0][k] <= {rqs[17*k+16], rqs[17*k +: 16]}; end
        c0[0] <= {cq0[337], cq0[15:0]}; c1[0] <= {cq1[337], cq1[15:0]};
    end
    always @(negedge clk) begin
        for (k = 0; k < 8; k = k + 1) begin
            rr0[257*k +: 256] = sdat(p0[RD-1][k][15:0], k); rr0[257*k+256] = p0[RD-1][k][16] && !drop_rr;
            bank1[257*k +: 256] = sdat(p1[RD1-1][k][15:0], k); bank1[257*k+256] = p1[RD1-1][k][16] && !drop_rr;
        end
        cr0 = 0; cr0[273] = c0[ACKD-1][16] && !drop_ack; cr0[272:257] = c0[ACKD-1][15:0]; cr0[256] = c0[ACKD-1][16];
        cr1 = 0; cr1[273] = c1[ACKD1-1][16] && !drop_ack; cr1[272:257] = c1[ACKD1-1][15:0]; cr1[256] = c1[ACKD1-1][16];
    end
    // ---------------- transaction logs
    integer cyc = 0; always @(posedge clk) cyc <= cyc + 1;
    reg [400:0] lq0 [0:65535]; reg [400:0] lq1 [0:65535]; integer tq0 [0:65535]; integer tq1 [0:65535]; integer nq0 = 0, nq1 = 0;
    reg [400:0] lw0 [0:8191]; reg [400:0] lw1 [0:8191]; integer tw0 [0:8191]; integer tw1 [0:8191]; integer nw0 = 0, nw1 = 0;
    reg [2:0] le0 [0:4095]; reg [2:0] le1 [0:4095]; integer te0 [0:4095]; integer te1 [0:4095]; integer ne0 = 0, ne1 = 0;
    always @(posedge clk) if (rst_n) begin
        for (k = 0; k < 8; k = k + 1) begin
            if (rq0[17*k+16]) begin lq0[nq0] = {k[2:0], rq0[17*k +: 16]}; tq0[nq0] = cyc; nq0 = nq0 + 1; end
            if (rq1[17*k+16]) begin lq1[nq1] = {k[2:0], rq1[17*k +: 16]}; tq1[nq1] = cyc; nq1 = nq1 + 1; end
        end
        if (cq0[337]) begin lw0[nw0] = {s0, cq0}; tw0[nw0] = cyc; nw0 = nw0 + 1; end
        if (cq1[337]) begin lw1[nw1] = {s1, cq1}; tw1[nw1] = cyc; nw1 = nw1 + 1; end
        if (d0 || f0) begin le0[ne0] = {d0, f0, n0}; te0[ne0] = cyc; ne0 = ne0 + 1; end
        if (d1 || f1) begin le1[ne1] = {d1, f1, n1}; te1[ne1] = cyc; ne1 = ne1 + 1; end
    end
    integer w, errs = 0, oq = -999, ow = -999, oe = -999, nrec_vm = 0, ndone = 0, i;
    task automatic rec(input m);
        begin
            @(negedge clk);
            mode = m; imm_a = $urandom % 40000; a_mirror = $urandom % 2; n = 1 + $urandom % 200;
            a_base = {(($urandom % 8) == 0) ? 2'd1 : 2'd0, 16'($urandom)}; o_base = {2'd0, 16'($urandom % 60000)};
            o_is = $urandom % 64; go = 1;
            @(negedge clk) go = 0;
        end
    endtask
    initial begin
        repeat (6) @(negedge clk); rst_n = 1; repeat (6) @(negedge clk);
        for (w = 0; w < `NREC; w = w + 1) begin
            drop_rr = ($urandom % 12) == 0; drop_ack = !drop_rr && ($urandom % 12) == 0;
            rec(($urandom % 8) == 0);
            repeat (3) @(negedge clk);
            while (b0 || b1) @(negedge clk);
            repeat (2) @(negedge clk);
        end
        repeat (40 + 2 * `CTL_M + `ACK_M) @(negedge clk);
        if (nq0 != nq1 || nw0 != nw1 || ne0 != ne1) begin errs = errs + 1; $display("COUNT q %0d/%0d w %0d/%0d e %0d/%0d", nq0, nq1, nw0, nw1, ne0, ne1); end
        for (i = 0; i < nq0 && i < nq1; i = i + 1) begin
            if (lq0[i] !== lq1[i]) begin errs = errs + 1; if (errs < 5) $display("RQ %0d differs", i); end
            if (oq == -999) oq = tq1[i] - tq0[i]; else if (tq1[i] - tq0[i] != oq) begin errs = errs + 1; if (errs < 5) $display("RQ offset %0d", i); end
        end
        for (i = 0; i < nw0 && i < nw1; i = i + 1) begin
            // a killed write (zero byte mask: fault path) carries an unspecified payload; compare everything else
            if ((lw0[i][47:16] == 0 && lw1[i][47:16] == 0) ? ({lw0[i][339:304], lw0[i][47:0]} !== {lw1[i][339:304], lw1[i][47:0]}) : (lw0[i] !== lw1[i])) begin
                errs = errs + 1; if (errs < 5) $display("WRITE %0d differs mask %h/%h", i, lw0[i][47:16], lw1[i][47:16]); end
            if (ow == -999) ow = tw1[i] - tw0[i]; else if (tw1[i] - tw0[i] != ow) begin errs = errs + 1; if (errs < 5) $display("WRITE offset %0d", i); end
        end
        for (i = 0; i < ne0 && i < ne1; i = i + 1) begin
            if (le0[i] !== le1[i]) begin errs = errs + 1; if (errs < 5) $display("EVENT %0d differs %b/%b", i, le0[i], le1[i]); end
            if (le0[i][2]) ndone = ndone + 1;
            // an illegal record (incl. every STREAM record) faults at E_CHK: only the go pin register (+1) applies
            if (le0[i][1] && !le0[i][2] && te1[i] - te0[i] == 1) ;
            else if (oe == -999) oe = te1[i] - te0[i]; else if (te1[i] - te0[i] != oe) begin errs = errs + 1; if (errs < 5) $display("EVENT offset %0d", i); end
        end
        $display("ARGMAX_LAT CTL_M=%0d VMX_P=%0d ACK_P=%0d ACK_M=%0d MUT=%0d requests %0d writes %0d events %0d (done %0d) offsets rq %0d write %0d event %0d share_fault %b/%b ties %0d errors %0d",
                 `CTL_M, `VMX_P, `ACK_P, `ACK_M, `MUT, nq0, nw0, ne0, ndone, oq, ow, oe, sf0, sf, `TIES, errs);
        if (errs == 0 && ndone > `NREC / 3 && nw0 > 0 && !sf0 && !sf) $display("IDX_AM_PATH_LAT PASS"); else $display("IDX_AM_PATH_LAT FAIL");
        $finish;
    end
endmodule
`default_nettype wire
