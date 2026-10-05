`timescale 1ns/1ps
// ROUTE.EXPERT_DISPATCH: the (group, slot) repeat, the expert side channel, and
// the bound check that must refuse BEFORE writing anything.
module tb_a3_expert_dispatch;
    localparam MAX_SLOTS = 8;
    reg clk = 0, rst_n = 0, start = 0;
    reg [31:0] cfg_groups, cfg_slots, cfg_width, cfg_experts;
    reg [31:0] cfg_id_base, cfg_token_base, cfg_out_base, cfg_expert_out_base;
    reg        cfg_has_expert_out;
    wire id_rd_en; wire [31:0] id_rd_addr; reg [31:0] id_rd_data;
    wire tok_rd_en; wire [31:0] tok_rd_addr; reg [31:0] tok_rd_data;
    wire out_we; wire [31:0] out_addr, out_data;
    wire eout_we; wire [31:0] eout_addr, eout_data;
    wire busy, done; wire [7:0] error_code;
    wire [31:0] out_count, rejected_ids;

    reg [31:0] idmem  [0:63];
    reg [31:0] tokmem [0:255];
    reg [31:0] omem   [0:255];
    reg [31:0] emem   [0:63];
    integer j, errors = 0, writes, ewrites;

    ot_a3_route_expert_dispatch #(.MAX_SLOTS(MAX_SLOTS)) dut (
        .clk(clk), .rst_n(rst_n), .start(start),
        .cfg_groups(cfg_groups), .cfg_slots(cfg_slots), .cfg_width(cfg_width),
        .cfg_experts(cfg_experts), .cfg_id_base(cfg_id_base),
        .cfg_token_base(cfg_token_base), .cfg_out_base(cfg_out_base),
        .cfg_has_expert_out(cfg_has_expert_out),
        .cfg_expert_out_base(cfg_expert_out_base),
        .id_rd_en(id_rd_en), .id_rd_addr(id_rd_addr), .id_rd_data(id_rd_data),
        .tok_rd_en(tok_rd_en), .tok_rd_addr(tok_rd_addr), .tok_rd_data(tok_rd_data),
        .out_we(out_we), .out_addr(out_addr), .out_data(out_data),
        .eout_we(eout_we), .eout_addr(eout_addr), .eout_data(eout_data),
        .busy(busy), .done(done), .error_code(error_code),
        .out_count(out_count), .rejected_ids(rejected_ids)
    );

    always #1 clk = ~clk;
    always @(posedge clk) begin
        if (id_rd_en)  id_rd_data  <= idmem[id_rd_addr[5:0]];
        if (tok_rd_en) tok_rd_data <= tokmem[tok_rd_addr[7:0]];
    end
    always @(posedge clk) begin
        if (out_we)  begin omem[out_addr[7:0]] <= out_data;  writes  = writes + 1; end
        if (eout_we) begin emem[eout_addr[5:0]] <= eout_data; ewrites = ewrites + 1; end
    end

    task go; begin
        writes = 0; ewrites = 0;
        for (j = 0; j < 256; j = j + 1) omem[j] = 32'hdead_beef;
        for (j = 0; j < 64; j = j + 1)  emem[j] = 32'hdead_beef;
        @(negedge clk); start = 1; @(negedge clk); start = 0;
        wait (done); @(negedge clk);
    end endtask

    initial begin
        // token row g holds 1000*g + column
        for (j = 0; j < 256; j = j + 1) tokmem[j] = 0;
        for (j = 0; j < 3; j = j + 1) begin
            tokmem[j*4 + 0] = 1000*j + 0; tokmem[j*4 + 1] = 1000*j + 1;
            tokmem[j*4 + 2] = 1000*j + 2; tokmem[j*4 + 3] = 1000*j + 3;
        end
        // 3 groups x 2 slots of expert ids, all inside a bound of 12
        idmem[0] = 5; idmem[1] = 7;
        idmem[2] = 0; idmem[3] = 11;
        idmem[4] = 3; idmem[5] = 9;
        repeat (4) @(negedge clk); rst_n = 1; repeat (2) @(negedge clk);

        cfg_groups = 3; cfg_slots = 2; cfg_width = 4; cfg_experts = 12;
        cfg_id_base = 0; cfg_token_base = 0; cfg_out_base = 0;
        cfg_has_expert_out = 1; cfg_expert_out_base = 0;
        go;
        if (error_code !== 8'd0) begin
            $display("FAIL error=%0d", error_code); errors = errors + 1; end
        if (out_count !== 24 || writes !== 24) begin
            $display("FAIL count=%0d writes=%0d expected 24", out_count, writes);
            errors = errors + 1; end
        // output row g*slots+s is a copy of token row g
        for (j = 0; j < 6; j = j + 1) begin
            if (omem[j*4+0] !== 1000*(j/2) + 0 || omem[j*4+1] !== 1000*(j/2) + 1 ||
                omem[j*4+2] !== 1000*(j/2) + 2 || omem[j*4+3] !== 1000*(j/2) + 3) begin
                $display("FAIL row %0d = %0d %0d %0d %0d, expected group %0d",
                         j, omem[j*4+0], omem[j*4+1], omem[j*4+2], omem[j*4+3], j/2);
                errors = errors + 1;
            end
        end
        // the expert side channel, in the same (group, slot) order
        if (ewrites !== 6) begin
            $display("FAIL expert writes=%0d expected 6", ewrites); errors=errors+1; end
        for (j = 0; j < 6; j = j + 1)
            if (emem[j] !== idmem[j]) begin
                $display("FAIL expert[%0d]=%0d expected %0d", j, emem[j], idmem[j]);
                errors = errors + 1; end

        // -- an ID outside the bound must refuse, and write NOTHING ---------
        idmem[3] = 12;                     // the bound is 12, so 12 is outside
        go;
        if (error_code === 8'd0) begin
            $display("FAIL an out-of-bound expert ID was accepted"); errors=errors+1; end
        if (rejected_ids !== 1) begin
            $display("FAIL rejected_ids=%0d expected 1", rejected_ids); errors=errors+1; end
        if (writes !== 0) begin
            $display("FAIL refused dispatch wrote %0d elements; the check must precede the walk", writes); errors=errors+1; end
        idmem[3] = 11;

        // -- slots beyond MAX_SLOTS is a shape refusal ----------------------
        cfg_slots = MAX_SLOTS + 1;
        go;
        if (error_code === 8'd0) begin
            $display("FAIL slots > MAX_SLOTS accepted"); errors=errors+1; end
        cfg_slots = 2;

        // -- no expert side channel: the rows still land, nothing else does --
        cfg_has_expert_out = 0;
        go;
        if (error_code !== 8'd0 || writes !== 24) begin
            $display("FAIL without expert out: error=%0d writes=%0d",
                     error_code, writes); errors=errors+1; end
        if (ewrites !== 0) begin
            $display("FAIL wrote %0d expert ids with the channel unbound", ewrites);
            errors=errors+1; end

        if (errors == 0)
            $display("PASS: expert_dispatch, (group,slot) repeat, expert channel, bound refusal writes nothing, II=1");
        else $display("FAIL: %0d errors", errors);
        $finish;
    end
endmodule
