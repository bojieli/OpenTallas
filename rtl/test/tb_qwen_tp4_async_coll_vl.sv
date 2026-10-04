`timescale 1ns/1ps
// Asynchronous (cut-through) all-reduce gate, Verilator build
// (tools/qwen_tp4_async_coll_verilator_gate.py).  Four sequencers, their VM
// word ports and the real ot_rom_oneshot_allreduce (rank-order binary32 fold,
// credits, LAT-cycle links), with a stub core that WRITES the all-reduce
// region through ME result ports on a schedule (sched.hex) while it "runs",
// and reports END DONE_LAG cycles after its last write.  Before the writes the
// region holds stale words (stale_die*.hex), so a word sent before the engine
// wrote it gives a wrong sum.
//   LEGACY = 1: the sequencer is ot_qwen_tp_seq_w12 (byte-identical reference)
//   LEGACY = 0: ot_qwen_tp_seq_async_w12, ASYNC_COLL = 1; +CUT=1 sets descriptor
//               bit 20 (cut-through), +CUT=0 runs the legacy path of the same RTL
// Descriptor 0: all-reduce of +NWORDS words at +VW (count 0 = 256); descriptor 1: END.
// Prints every result write ("W addr data") for an off-line comparison against
// tools/hdc_golden.fold and between modes.
module tb_qwen_tp4_async_coll_vl #(
    parameter integer DEPTH  = 256,
    parameter integer LAT    = 339,
    parameter integer LEGACY = 0,
    parameter integer SB_PIPE = 0,
    parameter integer NP     = 12,
    parameter integer TMAX   = 1024
);
    reg clk = 0, rst_n = 0, start = 0;
    always #5 clk = ~clk;
    localparam integer N = 4, FW = 512, TAGW = 34;
    integer cut, inject_last, expect_fault, vw0, nwords, done_lag, cyc = 0, first = -1;
    string vecdir;
    reg [FW-1:0] expected [0:255];
    // schedule: per cycle offset t and port p, {we, word[23:0], mask[15:0]}
    reg [40:0] sched [0:TMAX*NP-1];
    integer last_ev;
    wire [N-1:0] done, sfault, cfault, iv, ir, il, im, ov, ol, oe;
    wire [N*FW-1:0] idata, odata;
    wire [N*TAGW-1:0] tags;
    wire [N*2-1:0] ranks;
    wire [N*3-1:0] codes;
    wire [31:0] stalls;
    ot_rom_oneshot_allreduce #(.N(N), .LANES(16), .TAGW(TAGW),
        .DEPTH(DEPTH), .LAT(LAT)) coll (
        .clk(clk), .rst_n(rst_n), .in_valid(iv), .in_ready(ir),
        .in_data(idata), .in_last(il), .in_mode(im), .in_tag(tags),
        .out_valid(ov), .out_data(odata), .out_last(ol), .out_rank(ranks),
        .out_err(oe), .fault(cfault), .fault_code(codes), .link_stalls(stalls));
    genvar g;
    generate for (g = 0; g < N; g = g + 1) begin : die
        reg [FW-1:0] mem [0:255];
        reg [FW-1:0] part [0:255];
        reg [FW-1:0] vm_q;
        reg [63:0] desc_q;
        reg core_done = 0, running = 0;
        integer t0 = 0, starts = 0, writes = 0, sends = 0, lasts = 0, first_send = -1, done_cyc = -1,
                last_write = -1, bad = 0, first_err = -1, me_words = 0;
        wire core_start, desc_re, vm_re, vm_we;
        wire [5:0] desc_addr;
        wire [7:0] vm_ra, vm_wa;
        wire [FW-1:0] vm_wd;
        wire [31:0] t = cyc - t0;
        reg  [NP-1:0] me_we;
        reg  [NP*24-1:0] me_addr;
        reg  [NP*16-1:0] me_mask;
        integer p, l;
        always @(*) begin
            for (p = 0; p < NP; p = p + 1) begin
                me_we[p] = running && starts == 1 && t < TMAX && sched[t*NP + p][40];
                me_addr[p*24 +: 24] = sched[(t < TMAX ? t : 0)*NP + p][39:16];
                me_mask[p*16 +: 16] = sched[(t < TMAX ? t : 0)*NP + p][15:0];
            end
        end
        string path;
        initial begin
            #1;
            path = $sformatf("%s/part_die%0d.hex", vecdir, g);
            $readmemh(path, part);
            path = $sformatf("%s/stale_die%0d.hex", vecdir, g);
            $readmemh(path, mem);
        end
        if (LEGACY != 0) begin : s
            ot_qwen_tp_seq_w12 #(.ENABLE_AR256(1), .N(N), .NW(18), .TAGW(TAGW), .QWEN_FULLSHAPE(1)) seq (
                .clk(clk), .rst_n(rst_n), .start(start), .token(18'd151935), .pos(18'd0),
                .done(done[g]), .next_token(), .next_val(), .fault(sfault[g]), .coll_busy(),
                .core_start(core_start), .core_token(), .core_pos(), .core_done(core_done),
                .core_next_token(18'd0), .core_next_val(32'h0), .core_fault(1'b0),
                .prog_base(), .desc_re(desc_re), .desc_addr(desc_addr), .desc_q(desc_q),
                .vm_re(vm_re), .vm_raddr(vm_ra), .vm_rq(vm_q),
                .vm_we(vm_we), .vm_waddr(vm_wa), .vm_wdata(vm_wd),
                .c_valid(iv[g]), .c_ready(ir[g]), .c_data(idata[g*FW +: FW]),
                .c_last(il[g]), .c_mode(im[g]), .c_tag(tags[g*TAGW +: TAGW]),
                .r_valid(ov[g]), .r_data(odata[g*FW +: FW]),
                .r_last(ol[g] ^ (inject_last != 0 && ov[g])),
                .r_rank(ranks[g*2 +: 2]), .r_err(oe[g]));
        end else begin : s
            ot_qwen_tp_seq_async_w12 #(.ENABLE_AR256(1), .ASYNC_COLL(1), .SB_PIPE(SB_PIPE), .NP(NP), .MAW(24),
                .N(N), .NW(18), .TAGW(TAGW), .QWEN_FULLSHAPE(1)) seq (
                .clk(clk), .rst_n(rst_n), .start(start), .token(18'd151935), .pos(18'd0),
                .done(done[g]), .next_token(), .next_val(), .fault(sfault[g]), .coll_busy(),
                .core_start(core_start), .core_token(), .core_pos(), .core_done(core_done),
                .core_next_token(18'd0), .core_next_val(32'h0), .core_fault(1'b0),
                .prog_base(), .desc_re(desc_re), .desc_addr(desc_addr), .desc_q(desc_q),
                .vm_re(vm_re), .vm_raddr(vm_ra), .vm_rq(vm_q),
                .vm_we(vm_we), .vm_waddr(vm_wa), .vm_wdata(vm_wd),
                .c_valid(iv[g]), .c_ready(ir[g]), .c_data(idata[g*FW +: FW]),
                .c_last(il[g]), .c_mode(im[g]), .c_tag(tags[g*TAGW +: TAGW]),
                .r_valid(ov[g]), .r_data(odata[g*FW +: FW]),
                .r_last(ol[g] ^ (inject_last != 0 && ov[g])),
                .r_rank(ranks[g*2 +: 2]), .r_err(oe[g]),
                .me_we(me_we), .me_addr(me_addr), .me_mask(me_mask));
        end
        integer w;
        always @(posedge clk) begin
            // stub core: segment 1 (the all-reduce segment) writes the region on the schedule and
            // reports END done_lag cycles after its last write; segment 2 (END) is done at once
            if (core_start) begin
                running <= 1'b1; t0 <= cyc + 1; starts <= starts + 1; core_done <= 1'b0;
            end else if (running) begin
                if ((starts == 1 && t == last_ev + done_lag) || (starts != 1 && t == 2)) begin
                    core_done <= 1'b1; running <= 1'b0; if (starts == 1) done_cyc <= cyc;
                end
            end
            for (w = 0; w < NP; w = w + 1)
                if (me_we[w] && me_addr[w*24 +: 24] < 256) begin
                    for (l = 0; l < 16; l = l + 1)
                        if (me_mask[w*16 + l])
                            mem[me_addr[w*24 +: 8]][l*32 +: 32] <= part[me_addr[w*24 +: 8]][l*32 +: 32];
                    me_words = me_words + 1;
                end
            if (desc_re) begin
                if (desc_addr == 0)
                    desc_q <= 64'd1 | (64'(vw0) << 2) | (64'(nwords & 255) << 10) | (64'(cut) << 20);
                else desc_q <= 64'd0;
            end
            if (vm_re) vm_q <= mem[vm_ra];
            if (iv[g] && ir[g]) begin
                sends = sends + 1;
                if (first_send < 0) first_send = cyc;
                if (il[g]) lasts = lasts + 1;
            end
            if (oe[g] && first_err < 0) first_err = writes;
            if (vm_we) begin
                mem[vm_wa] <= vm_wd;
                if (vm_wa !== 8'(vw0 + writes) || vm_wd !== expected[vm_wa]) bad = bad + 1;
                if (g == 0) $display("W %0d %h", vm_wa, vm_wd);
                writes = writes + 1;
                last_write = cyc;
            end
        end
    end endgenerate
    integer k;
    initial begin
        if (!$value$plusargs("VEC=%s", vecdir)) $fatal(1, "VEC required");
        if (!$value$plusargs("CUT=%d", cut)) cut = 0;
        if (!$value$plusargs("VW=%d", vw0)) vw0 = 0;
        if (!$value$plusargs("NWORDS=%d", nwords)) nwords = 256;
        if (!$value$plusargs("DONE_LAG=%d", done_lag)) done_lag = 30;
        if (!$value$plusargs("INJECT_LAST=%d", inject_last)) inject_last = 0;
        if (!$value$plusargs("EXPECT_FAULT=%d", expect_fault)) expect_fault = 0;
        $readmemh({vecdir, "/sum.hex"}, expected);
        $readmemh({vecdir, "/sched.hex"}, sched);
        last_ev = 0;
        for (k = 0; k < TMAX * NP; k = k + 1) if (sched[k][40] && k / NP > last_ev) last_ev = k / NP;
        repeat (4) @(negedge clk);
        rst_n = 1;
        @(negedge clk); start = 1;
        @(negedge clk); start = 0;
    end
    always @(negedge clk) begin
        cyc = cyc + 1;
        if (start && first < 0) first = cyc;
        if (&done) begin
            if (expect_fault != 0) begin
                if (cfault != 4'b1111 || codes[0] != 1'b1 || sfault != 4'b1111)
                    $fatal(1, "expected arithmetic fault: cfault=%b codes=%h sfault=%b", cfault, codes, sfault);
            end else begin
                if (die[0].bad + die[1].bad + die[2].bad + die[3].bad != 0 || cfault != 0)
                    $fatal(1, "arithmetic mismatch=%0d fault=%b", die[0].bad + die[1].bad + die[2].bad + die[3].bad, cfault);
                if (inject_last ? sfault != 4'b1111 : sfault != 0)
                    $fatal(1, "last protocol fault=%b inject=%0d", sfault, inject_last);
            end
            if (die[0].writes != nwords || die[1].writes != nwords || die[2].writes != nwords || die[3].writes != nwords)
                $fatal(1, "write count");
            if (die[0].sends != nwords || die[1].sends != nwords || die[2].sends != nwords || die[3].sends != nwords)
                $fatal(1, "send count");
            if (die[0].lasts != 1 || die[1].lasts != 1 || die[2].lasts != 1 || die[3].lasts != 1)
                $fatal(1, "segment boundary count");
            $display("QWEN_ASYNCVL PASS legacy=%0d cut=%0d inject_last=%0d expect_fault=%0d depth=%0d lat=%0d cycles=%0d core_done=%0d first_send=%0d last_write=%0d words=%0d mismatches=%0d seq_fault=%b coll_fault=%b codes=%h first_err_word=%0d stalls=%0d",
                     LEGACY, cut, inject_last, expect_fault, DEPTH, LAT, cyc-first, die[0].done_cyc-first,
                     die[0].first_send-first, die[0].last_write-first, nwords,
                     die[0].bad + die[1].bad + die[2].bad + die[3].bad, sfault, cfault, codes,
                     die[0].first_err, stalls);
            $finish;
        end
        if (cyc > 40000) $fatal(1, "timeout");
    end
endmodule
