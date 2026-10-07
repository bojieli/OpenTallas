`timescale 1ns/1ps
// Exact lockstep gate of ot_s81ph_vm_mem (CLAUDE S81-PH VM) against a behavioural array VM with the same ports:
// every op takes effect in (issue cycle, port) order, reads return L = QD + 6 cycles later on their port.
// Directed: same-cycle W->R and R->W on one row, back-to-back RAW across ports, all ports on distinct banks, one
// bank saturated to QD, masked writes; then random traffic over a small row pool (hazards) and the full array.
// The bench schedules within the stall-free contract (<= QD outstanding per bank, the DUT's queue arithmetic
// mirrored); +OVF instead floods one bank and requires the overflow fault (fail closed).
// Plusargs: +CYCLES=n +SEED=n +OVF.  Defines: NP, NB, QD (defaults 8 / 32 / 4).
`ifndef NP
`define NP 8
`endif
`ifndef NB
`define NB 32
`endif
`ifndef QD
`define QD 4
`endif
module tb_ot_s81ph_vm_mem;
    localparam integer NP = `NP, NB = `NB, QD = `QD, RQ = (QD + 2 <= 8) ? 8 : 16;
`ifdef TILED
    // CLAUDE S81-PH vm v2: the 4-tile bank-group chain dsfd_vm_mem (rtl/dsrom_sys/s81_ph/vm/dsfd_vm_bg.sv), fixed
    // read latency L + 8 (2-cycle request and read-data hops between tiles, pin registers)
    localparam integer BB = $clog2(NB), RA = BB + 9, L = QD + 14, NR = NB * 512;
`else
    localparam integer BB = $clog2(NB), RA = BB + 9, L = QD + 6, NR = NB * 512;
`endif
    reg clk = 0, rst_n = 0;
    reg [NP-1:0] i_v = 0, i_we = 0;
    reg [NP*RA-1:0] i_row = 0;
    reg [NP*16-1:0] i_mask = 0;
    reg [NP*512-1:0] i_d = 0;
    wire [NP-1:0] o_v;
    wire [NP*512-1:0] o_d;
    wire fault;
    wire [2:0] fault_code;
    wire [$clog2(QD):0] max_occ;
`ifdef TILED
    dsfd_vm_mem #(.NP(NP), .NB(NB), .QD(QD), .RQ(RQ)) dut (.clk(clk), .rst_n(rst_n), .i_v(i_v), .i_we(i_we),
`else
    ot_s81ph_vm_mem #(.NP(NP), .NB(NB), .QD(QD), .RQ(RQ)) dut (.clk(clk), .rst_n(rst_n), .grp(1'b0), .i_v(i_v), .i_we(i_we),
`endif
        .i_row(i_row), .i_mask(i_mask), .i_d(i_d), .o_v(o_v), .o_d(o_d), .fault(fault), .fault_code(fault_code),
        .max_occ(max_occ));
    always #0.5555 clk = ~clk;

    reg [511:0] mem [0:NR-1];
    reg [NP-1:0] ev [0:L];
    reg [511:0] ed [0:L][0:NP-1];
    integer cyc = 0, ncheck = 0, nbad = 0, nops = 0, nrd = 0, nwr = 0, i, p, b, seed, cycles, ovf, phase;
    // stall-free gating: mirror of the DUT bank-queue arithmetic
    integer occ_m [0:NB-1];
    integer pend [0:NB-1];
    initial begin
        for (i = 0; i < NR; i = i + 1) mem[i] = 512'd0;
        for (i = 0; i <= L; i = i + 1) ev[i] = 0;
        for (b = 0; b < NB; b = b + 1) begin occ_m[b] = 0; pend[b] = 0; end
    end
    function automatic [511:0] r512(input integer s);
        reg [511:0] x; integer k;
        for (k = 0; k < 16; k = k + 1) x[32*k +: 32] = $urandom;
        r512 = x;
    endfunction
    // reference: apply this cycle's ops in port order at the capture edge
    always @(posedge clk) if (rst_n) begin
        ev[cyc % (L + 1)] = 0;
        for (p = 0; p < NP; p = p + 1) if (i_v[p]) begin
            if (i_we[p]) begin
                for (i = 0; i < 16; i = i + 1)
                    if (i_mask[p*16 + i]) mem[i_row[p*RA +: RA]][32*i +: 32] = i_d[p*512 + 32*i +: 32];
            end else begin
                ev[cyc % (L + 1)][p] = 1'b1;
                ed[cyc % (L + 1)][p] = mem[i_row[p*RA +: RA]];
            end
        end
    end
    // compare L edges later
    always @(posedge clk) if (rst_n) begin
        #0.1;
        if (cyc >= L) for (p = 0; p < NP; p = p + 1) begin
            if (o_v[p] !== ev[(cyc - L) % (L + 1)][p]) begin
                nbad = nbad + 1;
                if (nbad < 10) $display("MISMATCH valid cyc %0d port %0d dut %b ref %b", cyc, p, o_v[p], ev[(cyc - L) % (L + 1)][p]);
            end else if (o_v[p]) begin
                ncheck = ncheck + 1;
                if (o_d[p*512 +: 512] !== ed[(cyc - L) % (L + 1)][p]) begin
                    nbad = nbad + 1;
                    if (nbad < 10) $display("MISMATCH data cyc %0d port %0d", cyc, p);
                end
            end
        end
        cyc = cyc + 1;
    end
    // drive one cycle of ops (called at negedge); gate to the contract unless ovf
    reg [NP-1:0] g_v, g_we;
    reg [RA-1:0] g_row [0:NP-1];
    reg [15:0] g_m [0:NP-1];
    reg [511:0] g_d [0:NP-1];
    task automatic issue;
        integer oa, cntb [0:NB-1], bb_;
        begin
            // occupancy after the coming edge (pushes of the previously issued ops)
            for (bb_ = 0; bb_ < NB; bb_ = bb_ + 1) begin
                oa = occ_m[bb_] - (occ_m[bb_] > 0) + pend[bb_];
                if (oa > QD) oa = QD;
                occ_m[bb_] = oa; cntb[bb_] = 0;
            end
            for (p = 0; p < NP; p = p + 1) if (g_v[p]) begin
                bb_ = g_row[p][BB-1:0];
                if (!ovf && occ_m[bb_] - (occ_m[bb_] > 0) + cntb[bb_] + 1 > QD) g_v[p] = 1'b0;
                else cntb[bb_] = cntb[bb_] + 1;
            end
            for (bb_ = 0; bb_ < NB; bb_ = bb_ + 1) pend[bb_] = cntb[bb_];
            for (p = 0; p < NP; p = p + 1) begin
                i_v[p] = g_v[p]; i_we[p] = g_we[p]; i_row[p*RA +: RA] = g_row[p]; i_mask[p*16 +: 16] = g_m[p];
                i_d[p*512 +: 512] = g_d[p];
                if (g_v[p]) begin nops = nops + 1; if (g_we[p]) nwr = nwr + 1; else nrd = nrd + 1; end
            end
        end
    endtask
    task automatic clr; for (p = 0; p < NP; p = p + 1) begin g_v[p] = 0; g_we[p] = 0; g_row[p] = 0; g_m[p] = 16'hffff; g_d[p] = 0; end endtask
    task automatic op(input integer pp, input integer we, input integer row, input [15:0] m);
        begin g_v[pp] = 1; g_we[pp] = we; g_row[pp] = row; g_m[pp] = m; g_d[pp] = r512(0); end
    endtask
    task automatic step; begin issue(); @(negedge clk); clr(); end endtask
    integer pool [0:63];
    initial begin
        if (!$value$plusargs("SEED=%d", seed)) seed = 20261006;
        if (!$value$plusargs("CYCLES=%d", cycles)) cycles = 20000;
        ovf = $test$plusargs("OVF");
        void'($urandom(seed));
        for (i = 0; i < 64; i = i + 1) pool[i] = $urandom % NR;
        clr();
        repeat (3) @(negedge clk);
        rst_n = 1;
        repeat (3) @(negedge clk);                 // the DUT's 2-flop reset release
        if (ovf) begin
            for (i = 0; i < 4; i = i + 1) begin for (p = 0; p < NP; p = p + 1) op(p, 1, p * NB, 16'hffff); step(); end
            repeat (2 * L) step();
            $display("OVF fault=%b code=%b -> %s", fault, fault_code, (fault && fault_code[0]) ? "PASS_OVF" : "FAIL_OVF");
            $finish;
        end
        // D1: same-cycle write->read (p0 W, p1 R) and read->write (p2 R, p3 W) on one row each
        op(0, 1, 5, 16'hffff); op(1, 0, 5, 0); op(2, 0, 7, 0); op(3, 1, 7, 16'hffff); step();
        op(0, 1, 5, 16'h00f0); op(5, 0, 5, 0); op(4, 0, 7, 0); op(6, 1, 7, 16'h0f0f); step();
        // D2: back-to-back RAW across ports
        for (i = 0; i < 8; i = i + 1) begin op(i % NP, 1, 9 + NB, 16'h1 << i); op((i + 1) % NP, 0, 9 + NB, 0); step(); end
        // D3: all ports busy on distinct banks
        for (i = 0; i < 16; i = i + 1) begin for (p = 0; p < NP; p = p + 1) op(p, i[0], (p + i) % NB + NB * i, 16'hffff); step(); end
        // D4: one bank saturated (QD ops a cycle, mixed R/W on two rows)
        for (i = 0; i < 12; i = i + 1) begin for (p = 0; p < NP; p = p + 1) op(p, (p + i) % 2, 3 + NB * (p % 2), $urandom); step(); end
        repeat (L) step();
        // random: phase 0 hazards over the pool, phase 1 whole array
        for (i = 0; i < cycles; i = i + 1) begin
            phase = (i * 2) / cycles;
            for (p = 0; p < NP; p = p + 1) if ($urandom % 100 < 70)
                op(p, $urandom % 2, phase == 0 ? pool[$urandom % 64] : $urandom % NR,
                   ($urandom % 4 == 0) ? 16'hffff : $urandom);
            step();
        end
        repeat (L + 4) step();
        $display("RESULT ops=%0d reads=%0d writes=%0d checked=%0d mismatches=%0d fault=%b code=%b max_occ=%0d L=%0d",
                 nops, nrd, nwr, ncheck, nbad, fault, fault_code, max_occ, L);
        $display("%s", (nbad == 0 && !fault && ncheck > 0) ? "PASS" : "FAIL");
        $finish;
    end
endmodule
