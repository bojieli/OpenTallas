`timescale 1ns/1ps
// qwen-rtl-finish 2026-10-07: the banked vector memory (ot_qfd_sp_vector_memory) against the token bench's behavioural
// VM semantics (rtl/test/qwen_rom_runtime/ot_qwen_rom_rt_die_w12_stream4.sv: every x seat read at the edge after the
// descriptor, XVM extra registers, engine-gated by me_en, ELEMS-bounded), with the x seats expanded by ot_qfd_vm_xroot.
// Random tuples: S = 2^split (SMIN..SMAX), stride d from the supported set with (S-1)*d < BMAX*BEAT, held >= B edges
// (or a fresh contiguous tuple every edge), gaps, engine pauses (me_en low 1/8); row writes every other cycle into the
// half not being read (the halves swap after a quiet window); row reads of the read half.  Compared: all x seats every
// cycle; every row-read answer; no x_fault / x_hazard.  MUT = 1 (shift one lane off): must FAIL.
module tb_qfd_vector_memory;
    parameter integer ELEMS = 16384, NRB = 16, SMIN = 3, SMAX = 7, XVM = 12, BMAX = 4, MUT = 0, CYCLES = 30000, SEED = 5;
    parameter integer ND = 9;
    parameter [ND*8-1:0] DSET = {8'd16, 8'd12, 8'd8, 8'd6, 8'd4, 8'd3, 8'd2, 8'd1, 8'd0};
    localparam integer AW = 24, NX = 1 << SMAX, BEAT = (NRB - 1) * 16, HALF = ELEMS / 2;
    reg clk = 0, rst_n = 0;
    always #0.5 clk = ~clk;
    integer seed;
    reg me_en, x_dv, w_v, r_v;
    reg [AW-1:0] x_dc, x_dcs;
    reg [3:0] x_dsp;
    reg [AW-5:0] w_row, r_row;
    reg [15:0] w_mask;
    reg [511:0] w_data;
    wire [NX*32-1:0] d_xq;
    wire r_rdy, r_qv, x_fault, x_hazard;
    wire [511:0] r_q;
    ot_qfd_sp_vector_memory #(.ELEMS(ELEMS), .NRB(NRB), .AW(AW), .SMIN(SMIN), .SMAX(SMAX), .XVM(XVM), .BMAX(BMAX),
        .ND(ND), .DSET(DSET), .MUT(MUT)) dut (
        .clk(clk), .rst_n(rst_n), .me_en(me_en), .x_dv(x_dv), .x_dc(x_dc), .x_dcs(x_dcs), .x_dsp(x_dsp), .x_q(d_xq),
        .w_v(w_v), .w_row(w_row), .w_mask(w_mask), .w_data(w_data), .r_v(r_v), .r_rdy(r_rdy), .r_row(r_row),
        .r_qv(r_qv), .r_q(r_q), .x_fault(x_fault), .x_hazard(x_hazard));
    // ---- reference ----
    wire [NX-1:0] vx_re;
    wire [NX*AW-1:0] vx_addr;
    ot_qfd_vm_xroot #(.AW(AW), .GT(NX * 4), .TG(4), .SMAX(SMAX), .XVM(XVM)) u_xr (.clk(clk), .rst_n(rst_n),
        .x_dv(x_dv), .x_dc(x_dc), .x_dcs(x_dcs), .x_dsp(x_dsp), .x_re(vx_re), .x_addr(vx_addr), .x_q({NX*32{1'b0}}), .xl0());
    reg [31:0] vm [0:ELEMS-1];
    reg [NX*32-1:0] xp_q [0:XVM-1];
    reg [NX-1:0]    xp_v [0:XVM-1];
    reg [NX*32-1:0] r_xq;
    integer vi, xs, l;
    always @(posedge clk) begin : ref_vm
        reg [31:0] a; reg [NX*32-1:0] rq;
        if (me_en) begin
            rq = 0;
            for (vi = 0; vi < NX; vi = vi + 1)
                if (vx_re[vi]) begin a = vx_addr[vi*AW +: AW]; rq[vi*32 +: 32] = (a < ELEMS) ? vm[a] : 32'd0; end
            for (vi = 0; vi < NX; vi = vi + 1) if (xp_v[XVM-1][vi]) r_xq[vi*32 +: 32] <= xp_q[XVM-1][vi*32 +: 32];
            for (xs = XVM - 1; xs > 0; xs = xs - 1) begin xp_q[xs] <= xp_q[xs-1]; xp_v[xs] <= xp_v[xs-1]; end
            xp_q[0] <= rq; xp_v[0] <= vx_re;
        end
        if (w_v) for (l = 0; l < 16; l = l + 1) if (w_mask[l] && {w_row, 4'h0} + l < ELEMS) vm[{w_row, 4'h0} + l] <= w_data[32*l +: 32];
    end
    // row-read expectations (the read half is static while it is read)
    reg [511:0] rexp [0:63]; reg [5:0] rw_p, rr_p;
    integer bad, rbad, rows_read, tuples, cyc, first_bad, started, i, k;
    always @(posedge clk) if (rst_n) begin
        if (r_v && r_rdy) begin
            for (l = 0; l < 16; l = l + 1) rexp[rw_p][32*l +: 32] <= ({r_row, 4'h0} + l < ELEMS) ? vm[{r_row, 4'h0} + l] : 32'd0;
            rw_p <= rw_p + 1'b1;
        end
        if (r_qv) begin
            if (r_q !== rexp[rr_p]) rbad = rbad + 1;
            rr_p <= rr_p + 1'b1; rows_read = rows_read + 1;
        end
    end
    // ---- stimulus ----
    function integer dset(input integer i); dset = DSET[i*8 +: 8]; endfunction
    integer hold, side, quiet, s, d, b, span, ntup, since, pend;
    reg [AW-1:0] base;
`ifdef DBG
    always @(posedge clk) if (rst_n && cyc < 26 && cyc > 14) $display("edge cyc %0d me_en %0d x_dv %0d dc %0d nt %0d same %0d hnew %b bi_v %0d bi_j %0d", cyc, me_en, x_dv, x_dc, dut.nt, dut.same, dut.h_new, dut.bi_v, dut.bi_j);
    reg xf_d; always @(posedge clk) begin xf_d <= x_fault; if (rst_n && dut.me_en && (dut.bi_n > 1 || (dut.nt && (dut.bq >= BMAX || !(|dut.din))))) $display("fault cond cyc %0d bq=%0d din=%b dsp=%0d dcs=%0d bi_n=%0d nt=%0d hnew=%b b3=%0d b4=%0d b2=%0d", cyc, dut.bq, dut.din, x_dsp, x_dcs, dut.bi_n, dut.nt, dut.h_new, dut.h_b[3], dut.h_b[4], dut.h_b[2]); end
`endif
    initial begin
        seed = SEED; bad = 0; rbad = 0; rows_read = 0; tuples = 0; first_bad = -1; started = -1;
        rw_p = 0; rr_p = 0;
        for (i = 0; i < ELEMS; i = i + 1) vm[i] = 0;
        for (i = 0; i < XVM; i = i + 1) begin xp_v[i] = 0; xp_q[i] = 0; end
        r_xq = 0;
        me_en = 1; x_dv = 0; x_dc = 0; x_dcs = 1; x_dsp = SMIN; w_v = 0; r_v = 0; w_row = 0; r_row = 0; w_mask = 0; w_data = 0;
        hold = 0; side = 0; quiet = 0; ntup = 0; since = 100; pend = 0;
        repeat (4) @(negedge clk); rst_n = 1;
        // preload through the row write port (the reference takes the same writes)
        for (i = 0; i < ELEMS / 16; i = i + 1) begin
            @(negedge clk); w_v = 1; w_row = i; w_mask = 16'hffff;
            for (l = 0; l < 16; l = l + 1) w_data[32*l +: 32] = $random(seed);
        end
        @(negedge clk); w_v = 0;
        for (cyc = 0; cyc < CYCLES; cyc = cyc + 1) begin
            @(negedge clk);
            if (started >= 0 && cyc > started && d_xq !== r_xq) begin
                bad = bad + 1; if (first_bad < 0) first_bad = cyc;
`ifdef DBG
                if (bad < 3) for (k = 0; k < NX; k = k + 1) if (d_xq[k*32 +: 32] !== r_xq[k*32 +: 32] && k < 4)
                    $display("cyc %0d seat %0d dut %h ref %h", cyc, k, d_xq[k*32 +: 32], r_xq[k*32 +: 32]);
`endif
            end
            me_en = ($random(seed) & 7) != 0;
            // row write into the other half, row read of this half
            w_v = $random(seed) & 1;
            w_row = (((side ? 0 : HALF) + (($random(seed) & 32'h7fffffff) % HALF)) >> 4);
            w_mask = $random(seed); w_data = {16{$random(seed)}};
            r_v = (($random(seed) & 3) == 0) && quiet == 0;
            r_row = (((side ? HALF : 0) + (($random(seed) & 32'h7fffffff) % HALF)) >> 4);
            // the x descriptor changes only on engine edges (it is the engine's registered state)
            if (me_en) begin
                if (hold > 0) hold = hold - 1;
                since = since + 1;
                if (hold == 0) begin
                    if (quiet > 0) begin
                        quiet = quiet - 1; x_dv = 0;
                        if (quiet == 0) side = !side;
                    end else if (($random(seed) & 15) == 0) begin
                        x_dv = 0; hold = 1;
                    end else if (ntup > 40 && ($random(seed) & 7) == 0) begin
                        x_dv = 0; quiet = XVM + 4; ntup = 0; pend = 0;
                    end else if (pend && since < b) begin
                        // a new tuple with b beats may come only b engine edges after the previous new tuple (the
                        // tree top holds the op's go on x_rdy for that): keep the current descriptor meanwhile
                    end else begin
                      if (!pend) begin
                        s = SMIN + (($random(seed) & 32'h7fffffff) % (SMAX - SMIN + 1));
                        if (($random(seed) & 3) == 0) d = 1;
                        else begin
                            d = dset(($random(seed) & 32'h7fffffff) % ND);
                            while (((1 << s) - 1) * d >= BMAX * BEAT) d = dset(($random(seed) & 32'h7fffffff) % 5);
                        end
                        span = ((1 << s) - 1) * d;
                        b = span / BEAT + 1;
                        base = (side ? HALF : 0) + (($random(seed) & 32'h7fffffff) % (HALF - span - 1));
                        if (($random(seed) & 31) == 0 && side) base = ELEMS - span / 2;   // runs past the end: zeros
                      end
                      if (since < b) pend = 1;
                      else begin
                        pend = 0; since = 0;
                        x_dv = 1; x_dc = base; x_dcs = d; x_dsp = s;
`ifdef DBG
                        if (tuples < 14) $display("cyc %0d tuple base=%0d d=%0d s=%0d b=%0d me_en=%0d", cyc, base, d, s, b, me_en);
`endif
                        hold = b + (($random(seed) & 3) == 0 ? ($random(seed) & 7) : 0);
                        tuples = tuples + 1; ntup = ntup + 1;
                        if (started < 0) started = cyc + XVM + 3;
                      end
                    end
                end
            end
        end
        if (bad == 0 && rbad == 0 && !x_fault && !x_hazard && tuples > 1000 && rows_read > 1000)
            $display("PASS qfd_vector_memory NRB=%0d BEAT=%0d SMAX=%0d XVM=%0d tuples=%0d row_reads=%0d cycles=%0d", NRB, BEAT, SMAX, XVM, tuples, rows_read, CYCLES);
        else
            $display("FAIL qfd_vector_memory x_mismatch_cycles=%0d first=%0d row_mismatch=%0d x_fault=%0d x_hazard=%0d tuples=%0d rows=%0d", bad, first_bad, rbad, x_fault, x_hazard, tuples, rows_read);
        $finish;
    end
endmodule
