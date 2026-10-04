`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// tb_dsrom_1m_hop: the DS-ROM S81 stage hop and token return through the
// measured link endpoint ot_dsrom_link_rt (no change to the link RTL).
//
// One message of +bytes= payload bytes is cut into ceil(bytes / FB) flits of
// FB bytes (the last flit zero-padded), offered back to back from the first
// cycle after reset (in_valid held high), on an idle link with out_ready = 1.
// Leg 1 is the board link (CHANNEL_CYCLES = CH: the vendor PHY + FEC +
// flight budget as a delay line).  With CHU > 0 a second ot_dsrom_link_rt
// (in-package UCIe fan-out, CHANNEL_CYCLES = CHU) is chained cut-through
// behind leg 1 (leg1.out -> leg2.in, leg1.out_ready = leg2.in_ready).
//
// Payload word w of the message is a hash of (seed, w) for 4w < bytes and 0
// beyond; every delivered flit is compared with its expected value and its
// `last` bit (bit-exact, in order, exactly once).
//
// Cycle convention (that of tb_dsrom_link_rt): the counter advances on every
// posedge after reset; an event is stamped with the counter value of the edge
// at which the bench samples it.  first_flit = first cycle the final out_valid
// is high - first input handshake cycle; last_flit = cycle of the last output
// handshake - first input handshake cycle.
//
// Compile-time: -DFB= -DCH= -DCRED= -DSEQW= -DCHU= -DCREDU= -DSEQWU=
// Plusargs: +bytes= +seed= +case=
// Prints one HOP_SUMMARY line.
// ---------------------------------------------------------------------------
`ifndef FB
`define FB 64
`endif
`ifndef CH
`define CH 156
`endif
`ifndef CRED
`define CRED 512
`endif
`ifndef SEQW
`define SEQW 10
`endif
`ifndef CHU
`define CHU 0
`endif
`ifndef CREDU
`define CREDU 64
`endif
`ifndef SEQWU
`define SEQWU 8
`endif
module tb_dsrom_1m_hop;
    localparam integer FB = `FB;
    localparam integer W  = FB * 8;
    localparam integer NW = W / 32;

    reg clk = 1'b0;
    reg rst_n = 1'b0;
    always #1 clk = ~clk;

    integer BYTES, N, seed;
    reg [8*32-1:0] casename;
    reg  [15:0] chcyc = 16'd0;
    reg         in_valid, in_last;
    reg  [W-1:0] in_data;
    wire        in_ready;
    wire        l1_v, l1_last, l1_rdy;
    wire [W-1:0] l1_d;
    wire        out_valid, out_last;
    wire [W-1:0] out_data;
    wire [31:0] cs1, cs2;
    wire        f1, f2;
    wire [3:0]  fc1, fc2;
    wire [31:0] tx1, rx1, crc1, nak1, rep1, to1, retx1, occ1;
    wire [31:0] tx2, rx2, crc2, nak2, rep2, to2, retx2, occ2;

    ot_dsrom_link_rt #(.FLIT_BYTES(FB), .TX_STAGES(2), .CHANNEL_CYCLES(`CH), .RX_STAGES(2),
                       .CREDITS(`CRED), .SEQW(`SEQW), .LINK_CLASS(1)) u_board (
        .clk(clk), .rst_n(rst_n), .channel_cycles(chcyc),
        .in_valid(in_valid), .in_ready(in_ready), .in_data(in_data), .in_last(in_last),
        .out_valid(l1_v), .out_ready(l1_rdy), .out_data(l1_d), .out_last(l1_last),
        .credit_stalls(cs1), .fault(f1), .fault_code(fc1),
        .st_flits_tx(tx1), .st_flits_rx_ok(rx1), .st_crc_err(crc1), .st_naks(nak1),
        .st_replays(rep1), .st_timeouts(to1), .st_retx_flits(retx1), .st_max_replay_occ(occ1));

    generate if (`CHU > 0) begin : g_fan
        ot_dsrom_link_rt #(.FLIT_BYTES(FB), .TX_STAGES(2), .CHANNEL_CYCLES(`CHU), .RX_STAGES(2),
                           .CREDITS(`CREDU), .SEQW(`SEQWU), .LINK_CLASS(0)) u_ucie (
            .clk(clk), .rst_n(rst_n), .channel_cycles(chcyc),
            .in_valid(l1_v), .in_ready(l1_rdy), .in_data(l1_d), .in_last(l1_last),
            .out_valid(out_valid), .out_ready(1'b1), .out_data(out_data), .out_last(out_last),
            .credit_stalls(cs2), .fault(f2), .fault_code(fc2),
            .st_flits_tx(tx2), .st_flits_rx_ok(rx2), .st_crc_err(crc2), .st_naks(nak2),
            .st_replays(rep2), .st_timeouts(to2), .st_retx_flits(retx2), .st_max_replay_occ(occ2));
    end else begin : g_nofan
        assign l1_rdy = 1'b1;
        assign out_valid = l1_v;
        assign out_data = l1_d;
        assign out_last = l1_last;
        assign cs2 = 0; assign f2 = 1'b0; assign fc2 = 4'd0;
        assign tx2 = 0; assign rx2 = 0; assign crc2 = 0; assign nak2 = 0;
        assign rep2 = 0; assign to2 = 0; assign retx2 = 0; assign occ2 = 0;
    end endgenerate

    function automatic [31:0] mix(input [31:0] x0);
        reg [31:0] x;
        begin
            x = x0;
            x = x ^ (x >> 16); x = x * 32'h7feb352d;
            x = x ^ (x >> 15); x = x * 32'h846ca68b;
            x = x ^ (x >> 16);
            mix = x;
        end
    endfunction
    function automatic [W-1:0] gen_data(input integer i);
        integer j, w;
        begin
            for (j = 0; j < NW; j = j + 1) begin
                w = i * NW + j;
                gen_data[j*32 +: 32] = (4 * w < BYTES) ? mix(w ^ mix(seed)) : 32'd0;
            end
        end
    endfunction

    integer cyc, sent, rcvd, mism, extra, first_in, last_in, first_ov, first_out, last_out, l1_first_ov, l1_last_out;
    integer done_cyc;
    reg finished;

    initial begin
        if (!$value$plusargs("bytes=%d", BYTES)) BYTES = 40976;
        if (!$value$plusargs("seed=%d", seed)) seed = 1;
        if (!$value$plusargs("case=%s", casename)) casename = "unnamed";
        N = (BYTES + FB - 1) / FB;
        in_valid = 0; in_last = 0; in_data = 0;
        cyc = 0; sent = 0; rcvd = 0; mism = 0; extra = 0;
        first_in = -1; last_in = -1; first_ov = -1; first_out = -1; last_out = -1;
        l1_first_ov = -1; l1_last_out = -1; done_cyc = -1; finished = 0;
        repeat (5) @(posedge clk);
        rst_n = 1'b1;
    end

    always @(posedge clk) if (rst_n && !finished) begin
        cyc = cyc + 1;
        // ---- input: back to back, held valid ----
        if (in_valid && in_ready) begin
            if (first_in < 0) first_in = cyc;
            last_in = cyc;
            sent = sent + 1;
        end
        if (!(in_valid && !in_ready)) begin
            if (sent < N) begin
                in_valid <= 1'b1; in_data <= gen_data(sent); in_last <= (sent == N - 1);
            end else begin
                in_valid <= 1'b0; in_last <= 1'b0;
            end
        end
        // ---- leg-1 observation ----
        if (l1_v && l1_first_ov < 0) l1_first_ov = cyc;
        if (l1_v && l1_rdy) l1_last_out = cyc;
        // ---- output ----
        if (out_valid && first_ov < 0) first_ov = cyc;
        if (out_valid) begin
            if (rcvd >= N) begin
                extra = extra + 1;
            end else begin
                if (out_data !== gen_data(rcvd) || out_last !== (rcvd == N - 1)) begin
                    if (mism < 5) $display("MISMATCH case=%0s idx=%0d last=%b", casename, rcvd, out_last);
                    mism = mism + 1;
                end
                if (first_out < 0) first_out = cyc;
                last_out = cyc;
            end
            rcvd = rcvd + 1;
        end
        if (rcvd >= N && done_cyc < 0) done_cyc = cyc;
        if ((done_cyc >= 0 && cyc - done_cyc > 4 * (`CH + `CHU) + 600) || cyc > 200000) begin
            finished = 1;
            report();
            $finish;
        end
    end

    task report;
        reg pass;
        begin
            pass = (mism == 0) && (rcvd == N) && (extra == 0) && !f1 && !f2 && (sent == N);
            $display("HOP_SUMMARY case=%0s result=%0s bytes=%0d flits=%0d fb=%0d ch=%0d chu=%0d credits=%0d seqw=%0d credits_u=%0d seqw_u=%0d sent=%0d rcvd=%0d mism=%0d extra=%0d fault1=%0d fault2=%0d first_in=%0d last_in=%0d first_flit=%0d last_flit=%0d leg1_first_flit=%0d leg1_last_flit=%0d out_span=%0d in_span=%0d credit_stalls1=%0d credit_stalls2=%0d retx1=%0d retx2=%0d crc1=%0d crc2=%0d max_replay_occ1=%0d max_replay_occ2=%0d seed=%0d",
                casename, pass ? "PASS" : "FAIL", BYTES, N, FB, `CH, `CHU, `CRED, `SEQW, `CREDU, `SEQWU,
                sent, rcvd, mism, extra, f1, f2, first_in, last_in,
                first_ov - first_in, last_out - first_in, l1_first_ov - first_in, l1_last_out - first_in,
                last_out - first_out, last_in - first_in, cs1, cs2, retx1, retx2, crc1, crc2, occ1, occ2, seed);
        end
    endtask
endmodule
