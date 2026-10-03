`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// Unit bench of ot_qwen_sys_kv_svc against ot_qwen_hbm_model_ack (WR_ACK = 1,
// refresh, FR-FCFS reordering, 4 pseudo-channels).  A scripted core runs
// NTOK tokens; each token: tok_start, a burst of random element writes
// (random words / lanes, including words of blocks not yet filled), then
// NOPS KV ops: kvd_v for a random block, wait kv_ok, read every word of the
// block through the latency-1 port with G lanes and compare with a reference
// model; then wait `drained`.  At the end the HBM image must equal the
// reference.  Negative runs: +TAG_FLIP=<n> corrupts the n-th response tag
// (fault_code[0] expected); +READ_INVALID reads a word of an unfilled block
// (fault_code[2] expected).
// ---------------------------------------------------------------------------
module tb_qwen_sys_kv_svc #(parameter integer PREFETCH = 0) (input wire clk);
    localparam integer W = 16, G = 4, AW = 24, KVWORDS = 512, LWB = 6, NPC = 4, LOT = 6, TAGW = 7;
    localparam integer SECTORS = 2 * KVWORDS + 2;
    reg rst_n = 0;
    integer cyc = 0, ntok = 12, nops = 6, nwr = 40, tag_flip = -1, rd_inv = 0;
    reg tok_start = 0, kvd_v = 0, kv_re = 0, kv_we = 0, boot_go = 0;
    reg [AW-1:0] kvd_wbase = 0, kv_waddr = 0;
    reg [G*AW-1:0] kv_raddr = 0;
    reg [31:0] kv_wdata = 0;
    wire kv_ok, drained, boot_done, boot_ok, fault;
    wire [5:0] fcode;
    wire [G*W*32-1:0] kv_q;
    wire h_req_v, h_req_rdy, h_req_we;
    wire [23:0] h_req_addr; wire [4:0] h_req_len; wire [TAGW-1:0] h_req_tag; wire [255:0] h_req_wdata;
    wire [NPC-1:0] h_rsp_v, h_rsp_rdy, h_rsp_wr;
    wire [NPC*TAGW-1:0] h_rsp_tag, h_rsp_tag_x;
    wire [NPC*4-1:0] h_rsp_beat;
    wire [NPC*256-1:0] h_rsp_data;
    wire [31:0] n_fill, n_wb, n_wait;
    ot_qwen_sys_kv_svc #(.W(W), .G(G), .AW(AW), .KVWORDS(KVWORDS), .LWB(LWB), .NPC(NPC), .LOT(LOT),
                         .BOOT_SECTOR(24'(SECTORS - 1)), .SCRUB_SECTORS(2 * KVWORDS), .PREFETCH(PREFETCH)) dut (
        .clk(clk), .rclk(clk), .rst_n(rst_n), .tok_start(tok_start), .kv_base(23'd0),
        .kvd_v(kvd_v), .kvd_wbase(kvd_wbase), .kv_ok(kv_ok),
        .kv_re(kv_re), .kv_raddr(kv_raddr), .kv_q(kv_q),
        .kv_we(kv_we), .kv_waddr(kv_waddr), .kv_wdata(kv_wdata), .drained(drained),
        .h_req_v(h_req_v), .h_req_rdy(h_req_rdy), .h_req_we(h_req_we), .h_req_addr(h_req_addr),
        .h_req_len(h_req_len), .h_req_tag(h_req_tag), .h_req_wdata(h_req_wdata),
        .h_rsp_v(h_rsp_v), .h_rsp_rdy(h_rsp_rdy), .h_rsp_tag(h_rsp_tag_x), .h_rsp_beat(h_rsp_beat),
        .h_rsp_data(h_rsp_data), .h_rsp_wr(h_rsp_wr),
        .boot_go(boot_go), .boot_done(boot_done), .boot_ok(boot_ok),
        .fault(fault), .fault_code(fcode), .n_fill_words(n_fill), .n_wb_sectors(n_wb), .n_kvok_wait(n_wait));
    ot_qwen_hbm_model_ack #(.NPC(NPC), .AW(24), .DW(256), .MEM_WORDS(SECTORS), .TAGW(TAGW), .LENW(5), .BEATW(4),
                            .CLK_PS(833), .PC_RDY(1), .PC_ROOM(16), .WR_ACK(1)) hbm (
        .clk(clk), .rst_n(rst_n), .req_v(h_req_v), .req_rdy(h_req_rdy), .pc_room(), .req_we(h_req_we),
        .req_addr(h_req_addr), .req_len(h_req_len), .req_tag(h_req_tag), .req_wdata(h_req_wdata),
        .rsp_v(h_rsp_v), .rsp_rdy(h_rsp_rdy), .rsp_tag(h_rsp_tag), .rsp_beat(h_rsp_beat), .rsp_data(h_rsp_data),
        .rsp_wr(h_rsp_wr));
    integer nrsp = 0;
    // corrupt the generation bit of one response on port 0
    assign h_rsp_tag_x = h_rsp_tag ^ ((tag_flip >= 0 && nrsp == tag_flip && h_rsp_v[0]) ? (1 << LOT) : 0);
    always @(posedge clk) if (h_rsp_v[0]) nrsp <= nrsp + 1;

    reg [31:0] ref_mem [0:KVWORDS*W-1];
    reg [63:0] lfsr = 64'h1234_5678_9ABC_DEF1;
    function automatic [63:0] nx(input [63:0] x);
        reg [63:0] y; begin y = x ^ (x << 13); y = y ^ (y >> 7); y = y ^ (y << 17); nx = y; end
    endfunction
    integer st = 0, tk = 0, op = 0, wi = 0, rk = 0, bad = 0, reads = 0, blk = 0, k, l, q;
    reg [AW-1:0] rq [0:G-1];
    reg rd_pend = 0, rd_pend2 = 0;
    reg [31:0] rd_exp [0:G*W-1];
    reg [31:0] rd_exp2 [0:G*W-1];
    reg [AW-1:0] rd_addr_d2 [0:G-1];
    reg [AW-1:0] rd_addr_d [0:G-1];
    integer wd;
    always @(posedge clk) begin
        cyc <= cyc + 1;
        if (cyc == 5) rst_n <= 1;
        tok_start <= 0; kvd_v <= 0; kv_re <= 0; kv_we <= 0; boot_go <= 0;
        // compare the read issued last cycle
        // kv_re/kv_raddr are registered here (edge E), sampled by the service at E+1, kv_q compared at E+2
        // (the expected words are captured when the read is issued: a later write must not move them)
        rd_pend2 <= rd_pend;
        for (q = 0; q < G; q = q + 1) begin
            rd_addr_d2[q] <= rd_addr_d[q];
            for (l = 0; l < W; l = l + 1) rd_exp2[q*W + l] <= rd_exp[q*W + l];
        end
        if (rd_pend2) for (q = 0; q < G; q = q + 1) for (l = 0; l < W; l = l + 1) begin
            if (kv_q[q*W*32 + 32*l +: 32] !== rd_exp2[q*W + l]) begin
                bad = bad + 1;
                if (bad < 5) $display("MISMATCH word=%0d lane=%0d got=%08x exp=%08x", rd_addr_d2[q], l,
                                      kv_q[q*W*32 + 32*l +: 32], rd_exp2[q*W + l]);
            end
        end
        rd_pend <= 1'b0;
        case (st)
            0: if (rst_n) begin boot_go <= 1; st <= 1; end
            1: if (boot_done) begin
                if (!boot_ok) begin $display("BOOT_FAIL"); $display("FAIL"); $finish; end
                st <= 2;
            end
            2: if (drained) begin tok_start <= 1; wi <= 0; op <= 0; st <= 3; end
            3: begin
                // element writes (one a cycle, as the stream unit writes)
                lfsr = nx(lfsr);
                kv_we <= 1; kv_waddr <= lfsr[8:0] * W + lfsr[12:9]; kv_wdata <= lfsr[63:32];
                ref_mem[lfsr[8:0] * W + lfsr[12:9]] = lfsr[63:32];
                if (wi == nwr - 1) st <= 4; else wi <= wi + 1;
            end
            4: begin
                lfsr = nx(lfsr);
                blk = lfsr[2:0];
                kvd_v <= 1; kvd_wbase <= (blk << LWB) + lfsr[8:4]; st <= 5;
            end
            5: st <= 6;
            6: if (kv_ok) begin rk <= 0; st <= 7; end
            7: begin
                // read the block G words a cycle
                kv_re <= 1; rd_pend <= 1;
                for (q = 0; q < G; q = q + 1) begin
                    kv_raddr[q*AW +: AW] <= (blk << LWB) + ((rk + q) % (1 << LWB));
                    rd_addr_d[q] <= (blk << LWB) + ((rk + q) % (1 << LWB));
                    for (l = 0; l < W; l = l + 1) rd_exp[q*W + l] <= ref_mem[((blk << LWB) + ((rk + q) % (1 << LWB)))*W + l];
                end
                reads = reads + G;
                if (rk + G >= (1 << LWB)) begin
                    // a few more writes interleaved with ops, then the next op
                    if (op == nops - 1) st <= 8; else begin op <= op + 1; st <= 9; end
                end else rk <= rk + G;
            end
            9: begin
                lfsr = nx(lfsr);
                kv_we <= 1; kv_waddr <= lfsr[8:0] * W + lfsr[12:9]; kv_wdata <= lfsr[63:32];
                ref_mem[lfsr[8:0] * W + lfsr[12:9]] = lfsr[63:32];
                st <= 4;
            end
            8: begin
                if (rd_inv && tk == 1) begin
                    // read a word of a block that is certainly not filled this token
                    wd = -1;
                    for (k = KVWORDS - 1; k >= 0; k = k - 1) if (!dut.valid[k]) wd = k;
                    kv_re <= 1; kv_raddr <= {G{wd[23:0]}}; st <= 12;
                end else if (tk == ntok - 1) st <= 10;
                else begin tk <= tk + 1; st <= 2; end
            end
            12: begin tk <= tk + 1; st <= 2; end
            10: if (drained) st <= 11;
            11: begin
                wd = 0;
                for (k = 0; k < KVWORDS * W; k = k + 1)
                    if (hbm.mem[2 * (k / W) + (k % W) / 8][32 * (k % 8) +: 32] !== ref_mem[k]) wd = wd + 1;
                $display("KVSVC tokens=%0d reads=%0d read_mismatches=%0d hbm_mismatches=%0d fills=%0d wb_sectors=%0d kvok_wait=%0d fault=%0d code=%b cycles=%0d",
                         ntok, reads, bad, wd, n_fill, n_wb, n_wait, fault, fcode, cyc);
                if (tag_flip >= 0) begin
                    if (fault && fcode[0]) $display("PASS"); else $display("FAIL");
                end else if (rd_inv) begin
                    if (fault && fcode[2]) $display("PASS"); else $display("FAIL");
                end else if (bad == 0 && wd == 0 && !fault) $display("PASS"); else $display("FAIL");
                $finish;
            end
            default: ;
        endcase
        if (tag_flip >= 0 && fault) begin
            $display("KVSVC tag-flip response %0d: fault=%0d code=%b at cycle %0d", tag_flip, fault, fcode, cyc);
            if (fcode[0]) $display("PASS"); else $display("FAIL");
            $finish;
        end
        if (cyc > 3000000) begin $display("TIMEOUT st=%0d tk=%0d", st, tk); $display("FAIL"); $finish; end
    end
    initial begin
        for (k = 0; k < KVWORDS * W; k = k + 1) ref_mem[k] = 32'd0;
        if (!$value$plusargs("NTOK=%d", ntok)) ntok = 12;
        if (!$value$plusargs("TAG_FLIP=%d", tag_flip)) tag_flip = -1;
        if ($test$plusargs("READ_INVALID")) rd_inv = 1;
    end
endmodule
