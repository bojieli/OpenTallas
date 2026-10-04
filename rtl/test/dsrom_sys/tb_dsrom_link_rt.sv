`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// tb_dsrom_link_rt: self-checking scoreboard for ot_dsrom_link_rt (and, with
// -DDUT_ORIG, the original ot_rom_pkg_link as a latency reference).
//
// Payload of flit i is a pure function of (seed, i) (16 x 32-bit hashed
// words); `last` is a hash of i, giving random message lengths.  The
// scoreboard compares the r-th output handshake with flit r, so a lost,
// duplicated, reordered or corrupted flit, or a wrong `last`, is a mismatch.
// After the N-th flit the bench idles and fails on any extra output.  A
// watchdog fails the run when no flit is delivered for STALL cycles.
//
// Compile-time: -DCH= -DDYN= -DCRED= -DSEQW= -DEFWD= -DEREV= (link params).
// Run-time plusargs: +n= +seed= +chsel= (DYNAMIC_DELAY delay) +gap= (percent
// of cycles in_valid idles between flits) +bpm= (0: out_ready back-pressure
// sweep 0/30/70 %; 1: heavy 70/90 %; 2: none) +case=<name>.
// Prints one LINKRT_SUMMARY line.
// ---------------------------------------------------------------------------
`ifndef CH
`define CH 8
`endif
`ifndef DYN
`define DYN 0
`endif
`ifndef CRED
`define CRED 32
`endif
`ifndef SEQW
`define SEQW 8
`endif
`ifndef EFWD
`define EFWD 0
`endif
`ifndef EREV
`define EREV 0
`endif
module tb_dsrom_link_rt;
    localparam integer FB = 64;
    localparam integer W  = FB * 8;
    localparam integer NMAX = 65536;

    reg clk = 1'b0;
    reg rst_n = 1'b0;
    always #1 clk = ~clk;

    integer N, seed, chsel, gap, bpm;
    reg [8*32-1:0] casename;
    reg  [15:0] chcyc;
    reg         in_valid, in_last, out_ready;
    reg  [W-1:0] in_data;
    wire        in_ready, out_valid, out_last;
    wire [W-1:0] out_data;
    wire [31:0] credit_stalls;
    wire        fault;
    wire [3:0]  fault_code;
    wire [31:0] st_tx, st_rx, st_crc, st_nak, st_rep, st_to, st_retx, st_occ;

`ifdef DUT_ORIG
    ot_rom_pkg_link #(.FLIT_BYTES(FB), .TX_STAGES(2), .CHANNEL_CYCLES(`CH), .RX_STAGES(2),
                      .CREDITS(`CRED), .DYNAMIC_DELAY(`DYN)) dut (
        .clk(clk), .rst_n(rst_n), .channel_cycles(chcyc),
        .in_valid(in_valid), .in_ready(in_ready), .in_data(in_data), .in_last(in_last),
        .out_valid(out_valid), .out_ready(out_ready), .out_data(out_data), .out_last(out_last),
        .credit_stalls(credit_stalls));
    assign fault = 1'b0; assign fault_code = 4'd0;
    assign st_tx = 0; assign st_rx = 0; assign st_crc = 0; assign st_nak = 0;
    assign st_rep = 0; assign st_to = 0; assign st_retx = 0; assign st_occ = 0;
`else
    ot_dsrom_link_rt #(.FLIT_BYTES(FB), .TX_STAGES(2), .CHANNEL_CYCLES(`CH), .RX_STAGES(2),
                       .CREDITS(`CRED), .DYNAMIC_DELAY(`DYN), .SEQW(`SEQW),
                       .ERR_PERIOD_FWD(`EFWD), .ERR_PERIOD_REV(`EREV), .ERR_OFFSET(5),
                       .LINK_CLASS((`CH > 32) ? 1 : 0)) dut (
        .clk(clk), .rst_n(rst_n), .channel_cycles(chcyc),
        .in_valid(in_valid), .in_ready(in_ready), .in_data(in_data), .in_last(in_last),
        .out_valid(out_valid), .out_ready(out_ready), .out_data(out_data), .out_last(out_last),
        .credit_stalls(credit_stalls),
        .fault(fault), .fault_code(fault_code),
        .st_flits_tx(st_tx), .st_flits_rx_ok(st_rx), .st_crc_err(st_crc), .st_naks(st_nak),
        .st_replays(st_rep), .st_timeouts(st_to), .st_retx_flits(st_retx), .st_max_replay_occ(st_occ));
`endif

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
        integer j;
        begin
            for (j = 0; j < W / 32; j = j + 1)
                gen_data[j*32 +: 32] = mix((i * 16 + j) ^ mix(seed));
        end
    endfunction
    function automatic gen_last(input integer i);
        gen_last = (mix(i ^ 32'h5bd1e995 ^ mix(seed + 7)) % 5) == 0;
    endfunction
    function automatic [31:0] rnd(input integer c, input integer salt);
        rnd = mix(c * 3 + salt * 32'h9e3779b9 + mix(seed));
    endfunction

    integer cyc, sent, rcvd, mism, extra, last_prog, stall_lim, bp, ov_idx;
    integer acc_cyc [0:NMAX-1];
    integer lat, lat_first, lat_min, lat_max, first_out, last_out;
    real    lat_sum;
    integer done_cyc;
    reg     finished;

    initial begin
        if (!$value$plusargs("n=%d", N)) N = 2000;
        if (!$value$plusargs("seed=%d", seed)) seed = 1;
        if (!$value$plusargs("chsel=%d", chsel)) chsel = `CH;
        if (!$value$plusargs("gap=%d", gap)) gap = 20;
        if (!$value$plusargs("bpm=%d", bpm)) bpm = 0;
        if (!$value$plusargs("case=%s", casename)) casename = "unnamed";
        if (N > NMAX) N = NMAX;
        chcyc = chsel[15:0];
        stall_lim = 40 * `CH + 20000;
        in_valid = 0; in_last = 0; in_data = 0; out_ready = 0;
        cyc = 0; sent = 0; rcvd = 0; mism = 0; extra = 0; last_prog = 0;
        lat_first = -1; lat_min = 1 << 30; lat_max = 0; lat_sum = 0.0;
        first_out = -1; last_out = -1; ov_idx = -1; done_cyc = -1; finished = 0;
        repeat (5) @(posedge clk);
        rst_n = 1'b1;
    end

    always @(posedge clk) if (rst_n && !finished) begin
        cyc = cyc + 1;
        // ---- input side ----
        if (in_valid && in_ready) begin
            if (sent < NMAX) acc_cyc[sent] = cyc;
            sent = sent + 1;
        end
        if (!(in_valid && !in_ready)) begin
            if (sent < N && (rnd(cyc, 1) % 100) >= gap) begin
                in_valid <= 1'b1; in_data <= gen_data(sent); in_last <= gen_last(sent);
            end else begin
                in_valid <= 1'b0;
            end
        end
        // ---- output side ----
        if (out_valid && ov_idx != rcvd) begin
            ov_idx = rcvd;
            if (rcvd < N && rcvd < NMAX) begin
                lat = cyc - acc_cyc[rcvd];
                if (rcvd == 0) lat_first = lat;
                if (lat < lat_min) lat_min = lat;
                if (lat > lat_max) lat_max = lat;
                lat_sum = lat_sum + lat;
            end
        end
        if (out_valid && out_ready) begin
            if (rcvd >= N) begin
                extra = extra + 1;
            end else begin
                if (out_data !== gen_data(rcvd) || out_last !== gen_last(rcvd)) begin
                    if (mism < 5) $display("MISMATCH case=%0s idx=%0d last=%b/%b", casename, rcvd, out_last, gen_last(rcvd));
                    mism = mism + 1;
                end
                if (first_out < 0) first_out = cyc;
                last_out = cyc;
            end
            rcvd = rcvd + 1;
            last_prog = cyc;
        end
        if (bpm == 2) bp = 0;
        else if (bpm == 1) bp = (rcvd < N / 2) ? 70 : 90;
        else bp = (rcvd < N / 3) ? 0 : (rcvd < 2 * N / 3) ? 30 : 70;
        out_ready <= (rnd(cyc, 2) % 100) >= bp;

        if (rcvd >= N && done_cyc < 0) done_cyc = cyc;
        if ((done_cyc >= 0 && cyc - done_cyc > 4 * `CH + 600) || (cyc - last_prog > stall_lim)) begin
            finished = 1;
            report();
            $finish;
        end
    end

    task report;
        reg pass;
        real rate;
        begin
            pass = (mism == 0) && (rcvd == N) && (extra == 0) && !fault && (sent == N);
            rate = (last_out > first_out && rcvd > 1) ? (rcvd - 1.0) / (last_out - first_out) : 0.0;
            $display("LINKRT_SUMMARY case=%0s result=%0s n=%0d sent=%0d rcvd=%0d mism=%0d extra=%0d stalled=%0d fault=%0d fault_code=%0d cycles=%0d lat_first=%0d lat_min=%0d lat_max=%0d lat_avg=%0.2f rate=%0.4f credit_stalls=%0d st_flits_tx=%0d st_flits_rx_ok=%0d st_crc_err=%0d st_naks=%0d st_replays=%0d st_timeouts=%0d st_retx_flits=%0d st_max_replay_occ=%0d ch=%0d dyn=%0d chsel=%0d credits=%0d seqw=%0d efwd=%0d erev=%0d gap=%0d bpm=%0d seed=%0d",
                casename, pass ? "PASS" : "FAIL", N, sent, rcvd, mism, extra, (cyc - last_prog > stall_lim),
                fault, fault_code, cyc, lat_first, lat_min, lat_max,
                (rcvd > 0) ? lat_sum / ((rcvd < N) ? rcvd : N) : 0.0, rate, credit_stalls,
                st_tx, st_rx, st_crc, st_nak, st_rep, st_to, st_retx, st_occ,
                `CH, `DYN, chsel, `CRED, `SEQW, `EFWD, `EREV, gap, bpm, seed);
        end
    endtask
endmodule
