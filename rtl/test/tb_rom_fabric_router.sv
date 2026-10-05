`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// Random-traffic unit test of ot_rom_fabric_router.
//
// Every input injects NPKT packets of 1..MAXLEN flits to random destinations:
// unicast ids 0..NP-1, multicast group ids 8..15 (random sets of >= 2 ports,
// written through the configuration port after reset), an id with an empty set
// (20) and an id outside the table (40); both of the last two must be dropped.
// Senders are credit-based (BUF credits, one back per `in_credit` pulse) and
// inject at random; receivers take flits with random `out_ready`, including
// long stalls.  Checked on every flit and at the end:
//   * credits: a sender never sends without a credit, and whenever it holds a
//     credit the router has a free slot (`in_ready`); `overflow` stays low;
//   * integrity: every flit's payload is the function of (src, seq, index) it
//     was sent with;
//   * wormhole: an output never interleaves two packets, and a packet's flits
//     arrive in order with `last` on its final flit only;
//   * ordering: on every output, packets of one input arrive in sent order;
//   * delivery: every packet reaches exactly the ports of its set, once
//     (dropped packets reach none) and the router's drop count matches;
//   * progress: all traffic drains before a timeout.
// Prints ROUTER_TB ... and PASS / FAIL.
// ---------------------------------------------------------------------------
module tb_rom_fabric_router #(
    parameter integer NP = 5,
    parameter integer FW = 64,
    parameter integer BUF = 4,
    parameter integer NPKT = 300,
    parameter integer MAXLEN = 9,
    parameter integer SEED = 1,
    parameter integer READY_PCT = 70      // receiver readiness, percent
);
    localparam integer DESTS = 32;
    reg clk = 1'b0, rst_n = 1'b0;
    always #1 clk = ~clk;

    reg  [NP-1:0]    in_valid, in_last;
    reg  [NP*FW-1:0] in_data;
    wire [NP-1:0]    in_ready, in_credit;
    wire [NP-1:0]    out_valid, out_last;
    reg  [NP-1:0]    out_ready;
    wire [NP*FW-1:0] out_data;
    reg              cfg_we;
    reg  [7:0]       cfg_dest;
    reg  [NP-1:0]    cfg_mask;
    wire [31:0]      drops;
    wire             overflow;

    // unicast ids route to their port at reset; groups are written later
    function [DESTS*NP-1:0] init_table(input integer unused);
        integer d;
        begin
            init_table = {DESTS*NP{1'b0}};
            for (d = 0; d < NP; d = d + 1) init_table[d*NP + d] = 1'b1;
        end
    endfunction

    ot_rom_fabric_router #(.NP(NP), .FW(FW), .BUF(BUF), .DESTS(DESTS), .ROUTE_INIT(init_table(0))) dut (
        .clk(clk), .rst_n(rst_n),
        .in_valid(in_valid), .in_ready(in_ready), .in_credit(in_credit), .in_data(in_data), .in_last(in_last),
        .out_valid(out_valid), .out_ready(out_ready), .out_data(out_data), .out_last(out_last),
        .cfg_we(cfg_we), .cfg_dest(cfg_dest), .cfg_mask(cfg_mask), .drops(drops), .overflow(overflow));

    integer seed_v = SEED;
    function integer rnd(input integer unused);
        rnd = $random(seed_v);
    endfunction

    // -- routing sets as the testbench sees them -----------------------------------
    reg [NP-1:0] tset [0:63];
    integer s0, d0, b;
    function [NP-1:0] set_of(input integer dest);
        set_of = (dest < DESTS) ? tset[dest] : {NP{1'b0}};
    endfunction

    // -- flit format: [7:0] dest, [15:8] src, [31:16] seq, [39:32] len, [47:40] index,
    //    the rest a pattern of (src, seq, index)
    function [FW-1:0] flit(input integer dest, input integer src, input integer seq, input integer len,
                           input integer idx);
        reg [FW-1:0] f;
        integer w;
        begin
            f = {FW{1'b0}};
            for (w = 48; w < FW; w = w + 1) f[w] = ((src * 7919 + seq * 104729 + idx * 31 + w * 13) % 5) < 2;
            f[7:0] = dest; f[15:8] = src; f[31:16] = seq; f[39:32] = len; f[47:40] = idx;
            flit = f;
        end
    endfunction

    // -- senders ------------------------------------------------------------------------
    integer cred [0:NP-1];
    integer seq_i [0:NP-1];            // packet being / next to be sent
    integer idx_i [0:NP-1];            // next flit of it
    integer len_p [0:NP*NPKT-1];
    integer dst_p [0:NP*NPKT-1];
    reg [NP-1:0] exp_set [0:NP*NPKT-1];
    reg [NP-1:0] got_set [0:NP*NPKT-1];
    integer errors = 0, sent_flits = 0, recv_flits = 0, expect_drops = 0, mcast_pkts = 0;
    integer i, j, r;

    // -- receivers ----------------------------------------------------------------------
    integer cur_src [0:NP-1];          // -1: between packets
    integer cur_seq [0:NP-1];
    integer cur_idx [0:NP-1];
    integer cur_len [0:NP-1];
    integer last_seq [0:NP*NP-1];      // [output * NP + src]
    integer stall [0:NP-1];

    task fail(input [8*64-1:0] what, input integer a, input integer bb, input integer c);
        begin
            errors = errors + 1;
            if (errors < 20) $display("ERROR %0s %0d %0d %0d at %0t", what, a, bb, c, $time);
        end
    endtask

    integer cycle = 0, quiet = 0;
    reg done_send;
    reg [FW-1:0] o, e;
    initial begin
                for (d0 = 0; d0 < 64; d0 = d0 + 1) tset[d0] = 0;
        for (d0 = 0; d0 < NP; d0 = d0 + 1) tset[d0] = 1 << d0;
        for (d0 = 8; d0 < 16; d0 = d0 + 1) begin
            tset[d0] = 0;
            while ((tset[d0] & (tset[d0] - 1)) == 0) tset[d0] = rnd(0) & ((1 << NP) - 1);   // >= 2 ports
        end
        for (i = 0; i < NP; i = i + 1) begin
            cred[i] = BUF; seq_i[i] = 0; idx_i[i] = 0; cur_src[i] = -1; stall[i] = 0;
            for (j = 0; j < NP; j = j + 1) last_seq[i*NP + j] = -1;
        end
        for (i = 0; i < NP * NPKT; i = i + 1) begin
            r = rnd(0) & 1023;
            dst_p[i] = (r < 450) ? (rnd(0) & 32'h7fffffff) % NP :
                       (r < 950) ? 8 + (rnd(0) & 7) :
                       (r < 990) ? 20 : 40;
            len_p[i] = 1 + (rnd(0) & 32'h7fffffff) % MAXLEN;
            exp_set[i] = set_of(dst_p[i]);
            got_set[i] = 0;
            if (exp_set[i] == 0) expect_drops = expect_drops + 1;
            if ((exp_set[i] & (exp_set[i] - 1)) != 0) mcast_pkts = mcast_pkts + 1;
        end
        in_valid = 0; in_last = 0; in_data = 0; out_ready = 0; cfg_we = 0; cfg_dest = 0; cfg_mask = 0;
        repeat (4) @(posedge clk);
        rst_n = 1'b1;
        // groups and the empty id through the configuration port
        for (d0 = 8; d0 < 16; d0 = d0 + 1) begin
            @(negedge clk); cfg_we = 1; cfg_dest = d0; cfg_mask = tset[d0];
        end
        @(negedge clk); cfg_we = 1; cfg_dest = 20; cfg_mask = 0;
        @(negedge clk); cfg_we = 0;
    end

    // drive on the negative edge, check on the positive edge
    always @(negedge clk) if (rst_n && cycle > 16) begin   // after the table writes
        for (i = 0; i < NP; i = i + 1) begin
            in_valid[i] = 1'b0;
            if (seq_i[i] < NPKT && cred[i] > 0 && ((rnd(0) & 255) < 180)) begin
                j = i * NPKT + seq_i[i];
                in_valid[i] = 1'b1;
                in_data[i*FW +: FW] = flit(dst_p[j], i, seq_i[i], len_p[j], idx_i[i]);
                in_last[i] = (idx_i[i] == len_p[j] - 1);
            end
            // receivers: random readiness with occasional long stalls
            if (stall[i] > 0) begin
                stall[i] = stall[i] - 1; out_ready[i] = 1'b0;
            end else begin
                if ((rnd(0) & 1023) < 4) stall[i] = 20 + (rnd(0) & 63);
                out_ready[i] = ((rnd(0) & 32'h7fffffff) % 100) < READY_PCT;
            end
        end
    end

    always @(posedge clk) if (rst_n) begin
        cycle <= cycle + 1;
        for (i = 0; i < NP; i = i + 1) begin
            // credit accounting (the pulse and the send may coincide)
            if (in_credit[i]) cred[i] = cred[i] + 1;
            if (in_valid[i]) begin
                if (cred[i] <= 0) fail("send-without-credit", i, cred[i], 0);
                if (!in_ready[i]) fail("credit-but-full", i, cred[i], 0);
                cred[i] = cred[i] - 1;
                sent_flits = sent_flits + 1;
                if (idx_i[i] == len_p[i * NPKT + seq_i[i]] - 1) begin
                    idx_i[i] = 0; seq_i[i] = seq_i[i] + 1;
                end else idx_i[i] = idx_i[i] + 1;
            end
            if (cred[i] > BUF) fail("credit-overrun", i, cred[i], 0);
            // outputs
            if (out_valid[i] && out_ready[i]) begin
                recv_flits = recv_flits + 1;
                o = out_data[i*FW +: FW];
                if (cur_src[i] < 0) begin
                    // a header
                    if (o[47:40] != 0) fail("not-a-header", i, o[15:8], o[31:16]);
                    cur_src[i] = o[15:8]; cur_seq[i] = o[31:16]; cur_len[i] = o[39:32]; cur_idx[i] = 0;
                    j = cur_src[i] * NPKT + cur_seq[i];
                    if (!exp_set[j][i]) fail("wrong-port", i, cur_src[i], cur_seq[i]);
                    if (got_set[j][i]) fail("duplicate", i, cur_src[i], cur_seq[i]);
                    got_set[j][i] = 1'b1;
                    if (cur_seq[i] <= last_seq[i*NP + cur_src[i]]) fail("order", i, cur_src[i], cur_seq[i]);
                    last_seq[i*NP + cur_src[i]] = cur_seq[i];
                end else if (o[15:8] != cur_src[i] || o[31:16] != cur_seq[i] || o[47:40] != cur_idx[i]) begin
                    fail("interleaved", i, o[15:8], o[31:16]);
                end
                e = flit(o[7:0], cur_src[i], cur_seq[i], cur_len[i], cur_idx[i]);
                if (o !== e) fail("payload", i, cur_src[i], cur_seq[i]);
                if (out_last[i] != (cur_idx[i] == cur_len[i] - 1)) fail("last", i, cur_src[i], cur_seq[i]);
                if (out_last[i]) cur_src[i] = -1; else cur_idx[i] = cur_idx[i] + 1;
            end
        end
        if (overflow) fail("overflow", 0, 0, 0);
        done_send = 1'b1;
        for (i = 0; i < NP; i = i + 1) if (seq_i[i] < NPKT) done_send = 1'b0;
        quiet = (done_send && out_valid == 0) ? quiet + 1 : 0;
        if (quiet == 200 || cycle == 2000000) begin
            if (cycle == 2000000) fail("timeout", sent_flits, recv_flits, 0);
            for (j = 0; j < NP * NPKT; j = j + 1)
                if (got_set[j] != exp_set[j]) fail("delivery", j / NPKT, j % NPKT, got_set[j]);
            if (drops != expect_drops) fail("drops", drops, expect_drops, 0);
            $display("ROUTER_TB ports=%0d buf=%0d packets=%0d multicast_packets=%0d dropped=%0d sent_flits=%0d received_flits=%0d cycles=%0d errors=%0d",
                     NP, BUF, NP * NPKT, mcast_pkts, drops, sent_flits, recv_flits, cycle, errors);
            if (errors == 0) $display("PASS"); else $display("FAIL");
            $finish;
        end
    end
endmodule
