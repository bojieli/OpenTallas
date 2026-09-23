`timescale 1ns/1ps
// Scoreboarded testbench for ot_rom_striped_expert_reader.
//
// For every selection it checks, in both layouts, that each selected expert
// word arrives exactly once with the stored value and that nothing else
// arrives.  It prints one CASE line per run with the cycle count, words read
// and dedicated-bank serialisations; tools/rtl_rom_striped_bank_campaign.py
// checks those counts against the closed-form schedules.
module tb_rom_striped_expert_reader;
    localparam integer BANKS = 8, WORD_BITS = 32, EXPERTS = 48, EXPERT_WORDS = 64;
    localparam integer MAX_SELECT = 6, LAT = 2, RANDOM_CASES = 24;
    localparam integer EW = $clog2(EXPERTS), WW = $clog2(EXPERT_WORDS), SW = $clog2(MAX_SELECT + 1);

    reg clk = 0, rst_n = 0, striped = 1, start = 0;
    reg [SW-1:0] select_count;
    reg [MAX_SELECT*EW-1:0] select_ids;
    wire busy, done;
    wire [BANKS-1:0] lane_valid;
    wire [BANKS*WORD_BITS-1:0] lane_data;
    wire [BANKS*EW-1:0] lane_expert;
    wire [BANKS*WW-1:0] lane_word;
    wire [31:0] read_cycles, words_read, bank_conflicts;

    ot_rom_striped_expert_reader #(
        .BANKS(BANKS), .WORD_BITS(WORD_BITS), .EXPERTS(EXPERTS),
        .EXPERT_WORDS(EXPERT_WORDS), .MAX_SELECT(MAX_SELECT), .SENSE_LATENCY(LAT)
    ) dut (
        .clk(clk), .rst_n(rst_n), .striped(striped), .start(start),
        .select_count(select_count), .select_ids(select_ids), .busy(busy),
        .lane_valid(lane_valid), .lane_data(lane_data), .lane_expert(lane_expert),
        .lane_word(lane_word), .done(done), .read_cycles(read_cycles),
        .words_read(words_read), .bank_conflicts(bank_conflicts)
    );

    always #5 clk = ~clk;

    function automatic [WORD_BITS-1:0] weight_value(input integer e, input integer w);
        weight_value = (e * 32'h9E37_79B1) ^ (w * 32'h85EB_CA77) ^ 32'hC2B2_AE3D;
    endfunction

    integer seen [0:EXPERTS-1][0:EXPERT_WORDS-1];
    reg selected [0:EXPERTS-1];
    integer errors = 0, total_errors = 0, cases = 0;

    task automatic run_case(input integer mode, input integer k, input [MAX_SELECT*EW-1:0] ids, input [255:0] label);
        integer e, w, b, j, lane_e, lane_w;
        begin
            for (e = 0; e < EXPERTS; e = e + 1) begin
                selected[e] = 0;
                for (w = 0; w < EXPERT_WORDS; w = w + 1) seen[e][w] = 0;
            end
            for (j = 0; j < k; j = j + 1) selected[ids[j*EW +: EW]] = 1;
            errors = 0;
            striped = mode[0];
            select_count = k;
            select_ids = ids;
            @(negedge clk) start = 1;
            @(negedge clk) start = 0;
            while (!done) begin
                @(posedge clk); #1;
                for (b = 0; b < BANKS; b = b + 1)
                    if (lane_valid[b]) begin
                        lane_e = lane_expert[b*EW +: EW];
                        lane_w = lane_word[b*WW +: WW];
                        if (!selected[lane_e]) errors = errors + 1;
                        else if (lane_data[b*WORD_BITS +: WORD_BITS] !== weight_value(lane_e, lane_w)) errors = errors + 1;
                        else seen[lane_e][lane_w] = seen[lane_e][lane_w] + 1;
                    end
            end
            for (e = 0; e < EXPERTS; e = e + 1)
                if (selected[e])
                    for (w = 0; w < EXPERT_WORDS; w = w + 1)
                        if (seen[e][w] != 1) errors = errors + 1;
            total_errors = total_errors + errors;
            cases = cases + 1;
            $display("CASE label=%0s mode=%0s k=%0d ids=%0h cycles=%0d words=%0d serialised=%0d errors=%0d",
                     label, mode[0] ? "striped" : "dedicated", k, ids, read_cycles, words_read, bank_conflicts, errors);
            repeat (2) @(posedge clk);
        end
    endtask

    function automatic [MAX_SELECT*EW-1:0] pack(input integer a0, input integer a1, input integer a2,
                                                input integer a3, input integer a4, input integer a5);
        pack = 0;
        pack[0*EW +: EW] = a0; pack[1*EW +: EW] = a1; pack[2*EW +: EW] = a2;
        pack[3*EW +: EW] = a3; pack[4*EW +: EW] = a4; pack[5*EW +: EW] = a5;
    endfunction

    integer m, r, j, cand, dup, seed;
    reg [MAX_SELECT*EW-1:0] rand_ids;
    initial begin
        seed = 20260923;
        repeat (3) @(posedge clk);
        rst_n = 1;
        repeat (2) @(posedge clk);
        for (m = 1; m >= 0; m = m - 1) begin
            // Six experts in six different dedicated banks: the best case for dedicated.
            run_case(m, 6, pack(0, 1, 2, 3, 4, 5), "spread");
            // Pairs sharing a bank.
            run_case(m, 6, pack(0, 8, 1, 9, 2, 10), "paired");
            // All six in one dedicated bank: the concentrated route.
            run_case(m, 6, pack(0, 8, 16, 24, 32, 40), "concentrated");
            // A single expert.
            run_case(m, 1, pack(7, 0, 0, 0, 0, 0), "single");
        end
        for (r = 0; r < RANDOM_CASES; r = r + 1) begin
            rand_ids = 0;
            for (j = 0; j < MAX_SELECT; j = j + 1) begin
                dup = 1;
                while (dup) begin
                    cand = $unsigned($random(seed)) % EXPERTS;
                    dup = 0;
                    for (m = 0; m < j; m = m + 1)
                        if (rand_ids[m*EW +: EW] == cand) dup = 1;
                end
                rand_ids[j*EW +: EW] = cand;
            end
            run_case(1, 6, rand_ids, "random");
            run_case(0, 6, rand_ids, "random");
        end
        $display("SUMMARY cases=%0d errors=%0d", cases, total_errors);
        $finish;
    end

    initial begin
        #10000000;
        $display("SUMMARY cases=%0d errors=timeout", cases);
        $finish;
    end
endmodule
