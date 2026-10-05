`timescale 1ns/1ps
module tb #(parameter integer WORDS = 266);
    reg clk = 0;
    always #5 clk = ~clk;
    localparam integer WA = 15, FW = 512, DST = 101;
    reg rst_n = 0, start = 0, started = 0;
    reg [WA-1:0] dst = DST, n = WORDS;
    wire in_ready, out_valid, out_last, done, fault;
    wire [3:0] out_we;
    wire [4*WA-1:0] out_addr;
    wire [4*FW-1:0] out_data;
    reg [4*FW-1:0] in_data;
    integer cyc = 0, sent = 0, writes = 0, stalls = 0, holds = 0, last_seen = 0;
    reg [FW-1:0] vm [0:2047];
    reg [2047:0] written = 0;
    wire in_valid = started && sent < WORDS;
    wire in_last = sent == WORDS - 1;
    wire out_ready = (cyc % 47) < 34;

    function automatic [FW-1:0] payload(input integer rank, input integer idx);
        reg [FW-1:0] p;
        integer j;
        begin
            for (j = 0; j < FW/32; j = j + 1)
                p[32*j +: 32] = (32'(rank) << 24) | (32'(idx) << 8) | 32'(j);
            return p;
        end
    endfunction
    always_comb begin
        for (integer r = 0; r < 4; r = r + 1)
            in_data[r*FW +: FW] = payload(r, sent);
    end
    ot_chip_v41x_coll_transpose_related_vm #(.WA(WA), .FW(FW), .OUT_PIPE(1), .ELASTIC_PIPE(1)) dut (
        .clk(clk), .rst_n(rst_n), .start(start), .dst(dst), .n(n),
        .in_ready(in_ready), .in_valid(in_valid), .in_data(in_data), .in_last(in_last),
        .out_ready(out_ready), .out_valid(out_valid), .out_we(out_we),
        .out_addr(out_addr), .out_data(out_data), .out_last(out_last),
        .done(done), .fault(fault));

    always @(posedge clk) if (rst_n) begin : tick
        integer a, rank, idx, wc;
        wc = 0;
        cyc <= cyc + 1;
        if (in_valid && in_ready) begin
            if ($isunknown(in_data)) $fatal(1,"fixture offered unknown input");
            sent <= sent + 1;
        end
        if (in_valid && !in_ready) stalls <= stalls + 1;
        if (out_valid && !out_ready) holds <= holds + 1;
        if (out_last && out_ready) last_seen <= last_seen + 1;
        for (integer k = 0; k < 4; k = k + 1) if (out_we[k] && out_ready) begin
            a = out_addr[k*WA +: WA];
            rank = (a - DST) / WORDS;
            idx = (a - DST) % WORDS;
            if (a < DST || a >= DST + 4*WORDS || rank < 0 || rank > 3 || idx < 0 || idx >= WORDS)
                $fatal(1, "transpose address out of range %0d", a);
            if (out_data[k*FW +: FW] !== payload(rank, idx))
                $fatal(1, "transpose data mismatch rank=%0d idx=%0d", rank, idx);
            if (written[a]) $fatal(1, "transpose duplicate address %0d", a);
            written[a] <= 1;
            vm[a] <= out_data[k*FW +: FW];
            wc = wc + 1;
        end
        writes <= writes + wc;
    end

    initial begin
        repeat (5) @(negedge clk);
        rst_n = 1;
        @(negedge clk); start = 1;
        @(negedge clk); start = 0; started = 1;
        wait (done || fault);
        @(negedge clk);
        if (fault) $fatal(1, "transpose fault");
        if (sent != WORDS || writes != 4*WORDS || last_seen != 1) begin
            for(integer z=DST;z<DST+4*WORDS;z=z+1)if(!written[z])$display("MISSING addr=%0d rank=%0d index=%0d",z,(z-DST)/WORDS,(z-DST)%WORDS);
            $fatal(1, "transpose counts sent=%0d writes=%0d last=%0d", sent, writes, last_seen);
        end
        for (integer r = 0; r < 4; r = r + 1)
            for (integer i = 0; i < WORDS; i = i + 1)
                if (!written[DST + r*WORDS + i] || vm[DST + r*WORDS + i] !== payload(r, i))
                    $fatal(1, "transpose final VM rank=%0d idx=%0d", r, i);
        if (WORDS >= 32 && (stalls == 0 || holds == 0))
            $fatal(1, "transpose backpressure unexercised");
        $display("TRANSPOSE_PASS words=%0d writes=%0d stalls=%0d holds=%0d cycles=%0d", WORDS, writes, stalls, holds, cyc);
        $finish;
    end
    initial begin #1000000; $fatal(1, "transpose timeout"); end
endmodule
