`timescale 1ns/1ps
// One-stream (256-word) vs split (2 x 128-word) all-reduce gate, Verilator build
// (tools/qwen_tp4_ar256_verilator_gate.py).  Derived from tb_qwen_tp4_ar256.sv,
// which stays byte-identical: the four real ot_qwen_tp_seq_w12 sequencers
// (ENABLE_AR256=1), their VM word ports, the real ot_rom_oneshot_allreduce
// (rank-order binary32 fold, credits, links) and a stub core handshake.
// Added: DEPTH / LAT parameters (credit sizing), +EXPECT_FAULT (an arithmetic
// fault case must fault in both modes, at the same word), and a per-word
// write log for an off-line bit-exact comparison against tools/hdc_golden.fold.
module tb_qwen_tp4_ar256_vl #(
    parameter integer DEPTH = 1024,
    parameter integer LAT   = 339
);
    reg clk = 0, rst_n = 0, start = 0;
    always #5 clk = ~clk;
    localparam integer N = 4, FW = 512, TAGW = 34;
    integer split, inject_last, expect_fault, cyc = 0, first = -1, bad = 0, first_err = -1, last_write = -1;
    string vecdir;
    reg [FW-1:0] expected [0:255];
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
        reg [FW-1:0] vm_q;
        reg [63:0] desc_q;
        reg core_done = 0;
        wire core_start, desc_re, vm_re, vm_we;
        wire [5:0] desc_addr;
        wire [7:0] vm_ra, vm_wa;
        wire [FW-1:0] vm_wd;
        integer writes = 0, sends = 0, lasts = 0;
        string path;
        initial begin
            #1;
            path = $sformatf("%s/part_die%0d.hex", vecdir, g);
            $readmemh(path, mem);
        end
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
        always @(posedge clk) begin
            core_done <= core_start;
            if (desc_re) begin
                if (desc_addr == 0)
                    desc_q <= (split != 0) ? (64'd1 | (64'd128 << 10)) : 64'd1;   // count 0 = 256 words
                else if (split != 0 && desc_addr == 1)
                    desc_q <= 64'd1 | (64'd128 << 2) | (64'd128 << 10);
                else desc_q <= 64'd0;
            end
            if (vm_re) vm_q <= mem[vm_ra];
            if (iv[g] && ir[g]) begin
                sends = sends + 1;
                if (il[g]) lasts = lasts + 1;
            end
            if (oe[g] && first_err < 0) first_err = writes;
            if (vm_we) begin
                mem[vm_wa] <= vm_wd;
                if (vm_wa !== writes[7:0] || vm_wd !== expected[vm_wa]) bad = bad + 1;
                if (g == 0) $display("W %0d %h", vm_wa, vm_wd);
                writes = writes + 1;
                last_write = cyc;
            end
        end
    end endgenerate
    initial begin
        if (!$value$plusargs("VEC=%s", vecdir)) $fatal(1, "VEC required");
        if (!$value$plusargs("SPLIT=%d", split)) split = 0;
        if (!$value$plusargs("INJECT_LAST=%d", inject_last)) inject_last = 0;
        if (!$value$plusargs("EXPECT_FAULT=%d", expect_fault)) expect_fault = 0;
        $readmemh({vecdir, "/sum.hex"}, expected);
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
                // a non-finite sum: the collective faults (code[0]) on every die and the
                // sequencer latches it; the faulting word index is reported for comparison
                if (cfault != 4'b1111 || codes[0] != 1'b1 || sfault != 4'b1111)
                    $fatal(1, "expected arithmetic fault: cfault=%b codes=%h sfault=%b", cfault, codes, sfault);
            end else begin
                if (bad != 0 || cfault != 0) $fatal(1, "arithmetic mismatch=%0d fault=%b", bad, cfault);
                if (inject_last ? sfault != 4'b1111 : sfault != 0)
                    $fatal(1, "last protocol fault=%b inject=%0d", sfault, inject_last);
            end
            if (die[0].writes != 256 || die[1].writes != 256 || die[2].writes != 256 || die[3].writes != 256)
                $fatal(1, "write count");
            if (die[0].sends != 256 || die[1].sends != 256 || die[2].sends != 256 || die[3].sends != 256)
                $fatal(1, "send count");
            if (die[0].lasts != (split ? 2 : 1) || die[1].lasts != (split ? 2 : 1) ||
                die[2].lasts != (split ? 2 : 1) || die[3].lasts != (split ? 2 : 1))
                $fatal(1, "segment boundary count");
            $display("QWEN_AR256VL PASS split=%0d inject_last=%0d expect_fault=%0d depth=%0d lat=%0d cycles=%0d words=1024 lanes=16384 mismatches=%0d seq_fault=%b coll_fault=%b codes=%h first_err_word=%0d stalls=%0d",
                     split, inject_last, expect_fault, DEPTH, LAT, cyc-first, bad, sfault, cfault, codes, first_err, stalls);
            $finish;
        end
        if (cyc > 20000) $fatal(1, "timeout");
    end
endmodule
