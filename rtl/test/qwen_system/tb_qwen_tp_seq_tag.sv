`timescale 1ns/1ps
// Collective-tag bench (stream qwen-system 2026-10-08): ot_qwen_tp_seq_w12_fs vs its base ot_qwen_tp_seq_w12.
// The sequencer runs one 2-segment stage program (an all-reduce of 2 words, then END) per start, as a full-shape stage
// does, for 38 stages x positions {5, 261, 517, 8,191} with one token.  Every record's tag is collected.  PASS when the
// full-shape tag is unique for every (stage, position) of one segment and the wrapper's records, done and vector-memory
// writes are those of the base (same instance); the base's collisions are reported (the bug: stage alias + 256 wrap).
module tb_qwen_tp_seq_tag;
    localparam integer NW = 18, FW = 512, TAGW = 32, NS = 38;
    reg clk = 0, rst_n = 0;
    always #0.4166 clk = ~clk;
    reg start = 0; reg [NW-1:0] token = 18'h2A5A5, pos = 0; reg [5:0] stg = 0; reg [1:0] gen = 0;
    wire done, fault, core_start, desc_re, vm_re, vm_we, c_valid, c_last, c_mode, coll_busy;
    wire [NW-1:0] ntok, ctok, cpos; wire [31:0] nval; wire [11:0] pbase; wire [5:0] daddr;
    wire [7:0] vraddr, vwaddr; wire [FW-1:0] vwdata, c_data; wire [TAGW-1:0] c_tag;
    reg core_done = 1; reg [63:0] desc_q = 0; reg [FW-1:0] vm_rq = 0;
    reg r_valid = 0, r_last = 0; reg [FW-1:0] r_data = 0;
    ot_qwen_tp_seq_w12_fs #(.N(4), .NW(NW)) dut (.clk(clk), .rst_n(rst_n), .start(start), .token(token), .pos(pos),
        .tag_stage(stg), .tag_gen(gen), .done(done), .next_token(ntok), .next_val(nval), .fault(fault),
        .coll_busy(coll_busy), .core_start(core_start), .core_token(ctok), .core_pos(cpos), .core_done(core_done),
        .core_next_token(18'd7), .core_next_val(32'h3f80_0000), .core_fault(1'b0), .prog_base(pbase), .desc_re(desc_re),
        .desc_addr(daddr), .desc_q(desc_q), .vm_re(vm_re), .vm_raddr(vraddr), .vm_rq(vm_rq), .vm_we(vm_we),
        .vm_waddr(vwaddr), .vm_wdata(vwdata), .c_valid(c_valid), .c_ready(1'b1), .c_data(c_data), .c_last(c_last),
        .c_mode(c_mode), .c_tag(c_tag), .r_valid(r_valid), .r_data(r_data), .r_last(r_last), .r_rank(2'd0),
        .r_err(1'b0));
    // stage program: segment 0 an all-reduce of 2 VM words, segment 1 END
    integer cd = 0;
    always @(posedge clk) begin
        if (desc_re) desc_q <= (daddr == 0) ? 64'h0000_0000_0000_0805 : 64'd0;  // kind 1, vw 1, nw 2
        if (vm_re) vm_rq <= {16{vraddr, 24'h00c0de}};
        if (core_start) begin core_done <= 1'b0; cd <= 3; end
        else if (cd > 1) cd <= cd - 1;
        else if (cd == 1) begin core_done <= 1'b1; cd <= 0; end
        r_valid <= c_valid; r_data <= c_data; r_last <= c_last;   // the all-reduce result loops back
    end
    reg [TAGW-1:0] fs_tag [0:1023], b_tag [0:1023];
    integer n = 0, i, j, fs_coll = 0, b_coll = 0, writes = 0, dones = 0, p;
    always @(posedge clk) begin
        if (c_valid) begin fs_tag[n] <= c_tag; b_tag[n] <= dut.tag_b; n <= n + 1; end
        if (vm_we) writes = writes + 1;
    end
    integer ps [0:3];
    initial begin
        ps[0] = 5; ps[1] = 261; ps[2] = 517; ps[3] = 8191;
        repeat (4) @(posedge clk); rst_n = 1; repeat (2) @(posedge clk);
        for (p = 0; p < 4; p = p + 1)
            for (i = 0; i < NS; i = i + 1) begin
                @(posedge clk); start <= 1; pos <= ps[p]; stg <= i; gen <= 2'd1;
                @(posedge clk); start <= 0;
                @(posedge clk); while (!done) @(posedge clk);
                dones = dones + 1;
            end
        repeat (4) @(posedge clk);
        // two records a stage (2 words); compare record k of every (stage, position) pair
        for (i = 0; i < n; i = i + 1)
            for (j = i + 1; j < n; j = j + 1)
                if ((i % 2) == (j % 2)) begin
                    if (fs_tag[i] == fs_tag[j]) fs_coll = fs_coll + 1;
                    if (b_tag[i] == b_tag[j]) b_coll = b_coll + 1;
                end
        $display("TAG_RESULT pass=%0d records=%0d stages=%0d full_shape_tag_collisions=%0d base_tag_collisions=%0d vm_writes=%0d fault=%0d",
                 (fs_coll == 0 && n == 2 * dones && writes == 2 * dones && !fault), n, dones, fs_coll, b_coll, writes, fault);
        $finish;
    end
endmodule
