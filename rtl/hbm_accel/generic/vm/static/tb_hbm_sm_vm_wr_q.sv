`timescale 1ns/1ps
`default_nettype none
// Bench (H-NETLIST/smvm 2026-10-16): ot_hbm_sm_vm_wr_q + 8 real ot_vms_bank_static (NW shape RG/WG: wq0 = LG, wq1 = SM
// writer, wq2 idle) with the bench acting as the compiler: it derives every writer emission cycle from the fixed timing
// contract (wq slot 0 at rv+3, serial P-cycle server per SM, DEPTH rows) and programmes the VM calendar wslot from it;
// an LG competitor writes the SAME banks on every cycle the calendar leaves free.  SM result streams follow the SM's
// retire pattern (SUB=4 rows back to back, then a K-dependent gap; SM k staggered by its hop).  After the run every
// touched bank row is read back through rq group 0 and compared bit-exact to an independent address/value model.
// PASS needs: 0 mismatches, no bank schedule/decode fault, no writer fault.  -DMUT=1 (wrong row) / -DMUT=2 (late
// phase) must FAIL.
module tb_hbm_sm_vm_wr_q;
`ifndef MUT
`define MUT 0
`endif
    localparam integer Q = 2, NCYC = 6000, G_SM = 1, G_LG = 0;
    reg clk = 0, rst_n = 0;
    always #1 clk = ~clk;
    reg [7:0] rv, smf; reg [95:0] rrow; reg [2047:0] rdata; reg cmd_v; reg [25:0] cmd;
    wire [2247:0] wq_sm; wire busy, wfault;
    ot_hbm_sm_vm_wr_q #(.DEPTH(4), .MUT(`MUT)) dut(.clk(clk), .rst_n(rst_n), .quad(2'(Q)), .rv(rv), .rrow(rrow), .rdata(rdata),
        .cmd_v(cmd_v), .cmd(cmd), .sm_fault(smf), .sm_sched_fault(8'd0), .wq(wq_sm), .busy(busy), .fault(wfault));
    // banks
    reg [7:0] wslot_v, rslot_v; reg [2:0] wslot [0:7]; reg [0:0] rslot [0:7];
    reg [280:0] lgq [0:7]; reg [16:0] rqb [0:7];
    wire [256:0] rrb [0:7]; wire [17:0] bst [0:7]; wire [2:0] wqd [0:7];
    genvar b;
    generate for (b = 0; b < 8; b = b + 1) begin : g_b
        wire [275:0] eg; wire [265:0] pr; wire dd, kd, xd, x2d;
        ot_vms_bank_static #(.RG(1), .WG(3)) u_bank(.clk(clk), .rst_n(rst_n), .bid(3'(b)), .sid(2'(Q)),
            .rslot_v(rslot_v[b]), .rslot(rslot[b]), .wslot_v(wslot_v[b]), .wslot(wslot[b]),
            .rq(rqb[b]), .rr(rrb[b]), .wq({281'd0, wq_sm[b*281 +: 281], lgq[b]}), .wq_done(wqd[b]),
            .dq(281'd0), .dq_done(dd), .kq(281'd0), .kq_done(kd), .xq(276'd0), .xq_done(xd), .xq2(276'd0), .xq2_done(x2d),
            .eg(eg), .pq(285'd0), .pr(pr), .status(bst[b]));
    end endgenerate
    // ---------------- golden model ----------------
    reg [31:0] gold [0:7][0:2047][0:7];   // bank, row11 {mirror,row10}, word
    reg        gset [0:7][0:2047];
    function automatic [31:0] to_bf16(input [31:0] x, input en);
        reg [31:0] r;
        begin
            if (!en) to_bf16 = x;
            else if (&x[30:23] && |x[22:0]) to_bf16 = {x[31:16] | 16'h0040, 16'h0000};
            else begin r = x + 32'h0000_7FFF + x[16]; to_bf16 = {r[31:16], 16'h0000}; end
        end
    endfunction
    // ---------------- schedule (the compiler) ----------------
    reg [7:0] ev_rv [0:NCYC-1];
    reg [11:0] ev_row [0:NCYC-1][0:7];
    reg [255:0] ev_dat [0:NCYC-1][0:7];
    reg ev_cmd [0:NCYC-1]; reg [25:0] ev_cmdw [0:NCYC-1];
    reg [7:0] slot_sm [0:NCYC-1];        // bank k reserved for the SM writer at cycle c
    integer freec [0:7];
    integer c, k, i, p, op, nrows, gap, t, st, lastemit, mism, nwr, nlg, seed;
    reg [9:0] base, stride; reg [3:0] P; reg fmt, mir; reg [31:0] w; reg [10:0] row;
    initial begin
        seed = 7;
        for (c = 0; c < NCYC; c = c + 1) begin ev_rv[c] = 0; ev_cmd[c] = 0; slot_sm[c] = 0; end
        for (k = 0; k < 8; k = k + 1) for (i = 0; i < 2048; i = i + 1) gset[k][i] = 0;
        for (k = 0; k < 8; k = k + 1) freec[k] = 0;
        t = 20; lastemit = 0;
        for (op = 0; op < 5; op = op + 1) begin
            case (op)
                0: begin P = 1; fmt = 0; mir = 0; base = 10'd0;   stride = 10'd0;  end
                1: begin P = 4; fmt = 1; mir = 0; base = 10'd64;  stride = 10'd8;  end
                2: begin P = 2; fmt = 0; mir = 1; base = 10'd200; stride = 10'd3;  end
                3: begin P = 8; fmt = 1; mir = 0; base = 10'd300; stride = 10'd16; end
                4: begin P = 3; fmt = 0; mir = 0; base = 10'd700; stride = 10'd40; end
            endcase
            c = lastemit + 3; if (c < t) c = t;                // descriptor only while the writer is idle
            ev_cmd[c] = 1; ev_cmdw[c] = {fmt, mir, P, stride, base};
            t = c + 2;
            nrows = (op == 0) ? 24 : 16;
            for (k = 0; k < 8; k = k + 1) begin
                st = t + k;                                    // hop stagger of SM k
                for (i = 0; i < nrows; i = i + 1) begin
                    // SUB=4 retire burst, then a K-dependent gap (at least the P-cycle service of 4 rows)
                    if (i > 0 && i % 4 == 0) begin gap = 4 * P + 1 + ($urandom(seed) % 9); st = st + gap; end
                    else if (i > 0) st = st + 1;
                    ev_rv[st][k] = 1;
                    ev_row[st][k] = (i < 8) ? 12'(i) : 12'(40 + i);   // rows 0..7 and 48..; exercises r[11:3]
                    for (p = 0; p < 8; p = p + 1) begin
                        w = $urandom(seed);
                        if (i == 3 && p == 0) w = 32'h7F80_0001;        // NaN (quiet on BF16)
                        if (i == 5 && p == 1) w = 32'h3F80_8000;        // RNE tie
                        ev_dat[st][k][32*p +: 32] = w;
                    end
                    // timing contract: slot 0 at rv+3, serial server per SM
                    begin : srv
                        integer s0, e; s0 = st + 3; if (freec[k] > s0) s0 = freec[k];
                        for (p = 0; p < P; p = p + 1) begin
                            e = s0 + p; slot_sm[e][k] = 1;
                            row = {mir, 10'(base + p * stride + ev_row[st][k][11:3])};
                            gold[k][row][ev_row[st][k][2:0]] = to_bf16(ev_dat[st][k][32*p +: 32], fmt);
                            gset[k][row] = 1;
                            if (e > lastemit) lastemit = e;
                        end
                        freec[k] = s0 + P;
                    end
                end
            end
            t = lastemit + 1;
        end
        $display("schedule: last SM-writer emission at cycle %0d", lastemit);
    end
    // ---------------- drive ----------------
    integer cyc; reg [9:0] lgrow; reg [2:0] lgw; reg [31:0] lgv;
    integer rbk, rrw, phase_rd;
    reg [10:0] rd_row [0:7][0:9]; integer rdc [0:7];
    initial begin
        rv = 0; smf = 0; rrow = 0; rdata = 0; cmd_v = 0; cmd = 0; wslot_v = 0; rslot_v = 0; mism = 0; nwr = 0; nlg = 0;
        for (k = 0; k < 8; k = k + 1) begin lgq[k] = 0; rqb[k] = 0; wslot[k] = 0; rslot[k] = 0; end
        repeat (4) @(posedge clk); rst_n = 1;
        for (cyc = 0; cyc < NCYC; cyc = cyc + 1) begin
            @(negedge clk);
            rv = ev_rv[cyc]; cmd_v = ev_cmd[cyc]; cmd = ev_cmdw[cyc];
            for (k = 0; k < 8; k = k + 1) begin
                rrow[12*k +: 12] = ev_row[cyc][k]; rdata[256*k +: 256] = ev_dat[cyc][k];
                lgq[k] = 0; wslot_v[k] = 0; wslot[k] = 0;
                if (slot_sm[cyc][k]) begin wslot_v[k] = 1; wslot[k] = 3'(G_SM); nwr = nwr + 1; end
                else if (cyc > 10 && cyc < lastemit && ($urandom(seed) % 3) == 0) begin
                    // LG competitor on the free calendar cycles, own rows 960..1023 of the same banks
                    lgrow = 10'(960 + ($urandom(seed) % 64)); lgw = 3'($urandom(seed)); lgv = $urandom(seed);
                    lgq[k] = {1'b1, 1'b0, 2'(Q), lgrow, 3'(k), {8{lgv}}, 8'd1 << lgw};
                    wslot_v[k] = 1; wslot[k] = 3'(G_LG);
                    gold[k][{1'b0, lgrow}][lgw] = lgv; gset[k][{1'b0, lgrow}] = 1; nlg = nlg + 1;
                end
            end
        end
        // read back every touched row through read group 0
        repeat (8) @(negedge clk);
        for (k = 0; k < 8; k = k + 1) wslot_v[k] = 0;
        for (i = 0; i < 2048 + 8; i = i + 1) begin
            @(negedge clk);
            for (k = 0; k < 8; k = k + 1) begin
                rslot_v[k] = 0; rqb[k] = 0;
                if (i < 2048 && gset[k][i]) begin
                    rslot_v[k] = 1; rslot[k] = 0;
                    rqb[k] = {1'b1, i[10], i[10] ? 2'b00 : 2'(Q), i[9:0], 3'(k)};
                end
            end
        end
        repeat (10) @(negedge clk);
        for (k = 0; k < 8; k = k + 1) if (bst[k][17]) begin mism = mism + 1; $display("bank %0d FAULT (schedule/decode)", k); end
        if (wfault) begin mism = mism + 1; $display("writer FAULT"); end
        // status path: an SM fault pulse must reach the sticky writer fault in 2 edges
        @(negedge clk); smf = 8'h08; @(negedge clk); smf = 0; @(negedge clk);
        if (!wfault) begin mism = mism + 1; $display("SM fault did not reach the writer fault"); end
        $display("SM writes %0d, LG writes %0d, rows checked %0d", nwr, nlg, nchk);
        for (k = 0; k < 8; k = k + 1) for (i = 0; i < 2048; i = i + 1) if (gset[k][i]) nexp = nexp + 1;
        if (nchk != nexp) begin mism = mism + 1; $display("rows checked %0d != touched %0d", nchk, nexp); end
        if (mism == 0 && nchk > 0) $display("TB_HBM_SM_VM_WR_Q PASS MUT=%0d", `MUT);
        else $display("TB_HBM_SM_VM_WR_Q FAIL MUT=%0d mismatches+faults=%0d", `MUT, mism);
        $finish;
    end
    // response checker: rr arrives 6 edges after the request is presented (bank header)
    reg [10:0] pipe_row [0:7][0:15]; reg pipe_v [0:7][0:15];
    integer nchk = 0, nexp = 0, j;
    always @(posedge clk) begin
        for (k = 0; k < 8; k = k + 1) begin
            for (j = 15; j > 0; j = j - 1) begin pipe_v[k][j] <= pipe_v[k][j-1]; pipe_row[k][j] <= pipe_row[k][j-1]; end
            pipe_v[k][0] <= rst_n && rslot_v[k] && rqb[k][16];
            pipe_row[k][0] <= {rqb[k][15], rqb[k][12:3]};
        end
    end
    always @(negedge clk) if (rst_n) begin
        for (k = 0; k < 8; k = k + 1) if (rrb[k][256]) begin
            if (!pipe_v[k][6]) begin mism = mism + 1; $display("bank %0d unexpected response", k); end
            else begin
                nchk = nchk + 1;
                for (j = 0; j < 8; j = j + 1)
                    if (rrb[k][32*j +: 32] !== gold[k][pipe_row[k][6]][j] && !(gold[k][pipe_row[k][6]][j] === 32'bx && rrb[k][32*j +: 32] == 0)) begin
                        if (mism < 10) $display("MISMATCH bank %0d row %0d word %0d: got %h want %h", k, pipe_row[k][6], j,
                            rrb[k][32*j +: 32], gold[k][pipe_row[k][6]][j]);
                        mism = mism + 1;
                    end
            end
        end
    end
endmodule
`default_nettype wire
