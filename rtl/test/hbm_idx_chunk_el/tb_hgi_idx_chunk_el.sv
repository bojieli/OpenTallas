`timescale 1ns/1ps
// hgi-1010/g2: the chunk ELEMENT (hb strap) in lockstep with the proven parameterised chunk (HB = 8c), 4 chunks of a
// 32-head engine: random q-loads of heads 0..39 (heads >= 32 belong to no chunk), random key beats (NKT 4, random kv),
// every output compared every cycle.  Throughput: a key beat every cycle in the stream phase must give a chunk sum beat
// every cycle (c_v count == k_v count, constant latency).  +MUT_HB: element 1 strapped hb 9 -> must FAIL.
module tb_hgi_idx_chunk_el;
    localparam integer NB = 4, NKT = 4, FPL = 7, FML = 5, QL = 5, KW = NKT * NB * 136;
    reg clk = 0; always #0.4165 clk = ~clk;
    reg rst_n = 0, ql_v = 0, k_v = 0; reg [7:0] ql_head = 0; reg [NB*128-1:0] ql_codes = 0; reg [NB*8-1:0] ql_sc = 0;
    reg [15:0] ql_w = 0; reg [NKT-1:0] k_kv = 0; reg [KW-1:0] k_key = 0;
    integer mut = 0, errors = 0, nk = 0, nc = 0, i, j, c, seed = 5;
    initial begin if (!$value$plusargs("SEED=%d", seed)) seed = 5; $display("SEED=%0d", seed); end  // runtime seed (+SEED=<n> overrides): Verilator 5.050 drops a declaration initialiser read only by $random (tools/seed_init_lint.py)
    wire [3:0] rv, ev; wire [4*NKT-1:0] rkv, ekv, rf, ef; wire [4*NKT*32-1:0] rs, es;
    genvar g;
    for (g = 0; g < 4; g = g + 1) begin : g_c
        ot_hdc_v41x_idx_chunk_l #(.NB(NB), .NKT(NKT), .HB(8 * g), .FPL(FPL), .FML(FML), .QL(QL)) u_r (.clk(clk), .rst_n(rst_n),
            .ql_v(ql_v), .ql_head(ql_head), .ql_codes(ql_codes), .ql_sc(ql_sc), .ql_w(ql_w), .k_v(k_v), .k_kv(k_kv), .k_key(k_key),
            .c_v(rv[g]), .c_kv(rkv[NKT*g +: NKT]), .c_sum(rs[NKT*32*g +: NKT*32]), .c_fault(rf[NKT*g +: NKT]));
        wire [7:0] hb = (g == 1 && mut != 0) ? 8'd9 : 8'(8 * g);
        ot_hdc_v41x_idx_chunk_el #(.NB(NB), .NKT(NKT), .FPL(FPL), .FML(FML), .QL(QL)) u_e (.clk(clk), .rst_n(rst_n), .hb(hb),
            .ql_v(ql_v), .ql_head(ql_head), .ql_codes(ql_codes), .ql_sc(ql_sc), .ql_w(ql_w), .k_v(k_v), .k_kv(k_kv), .k_key(k_key),
            .c_v(ev[g]), .c_kv(ekv[NKT*g +: NKT]), .c_sum(es[NKT*32*g +: NKT*32]), .c_fault(ef[NKT*g +: NKT]));
    end
    always @(posedge clk) if (rst_n) begin
        if (rv !== ev || (rv[0] && (rkv !== ekv || rs !== es || rf !== ef))) begin
            if (errors < 5) $display("ERR t=%0t chunk outputs differ: v %b/%b sum %h / %h", $time, rv, ev, rs[127:0], es[127:0]);
            errors = errors + 1;
        end
        if (k_v) nk = nk + 1;
        if (rv[0]) nc = nc + 1;
    end
    function automatic [31:0] rnd; begin rnd = $random(seed); end endfunction
    // FP4 E2M1 codes (any nibble) with a modest UE8M0-style scale so sums stay finite most of the time
    task automatic qload(input [7:0] h);
        begin
            @(negedge clk); ql_v = 1; ql_head = h;
            for (j = 0; j < NB * 4; j = j + 1) ql_codes[32 * j +: 32] = rnd();
            for (j = 0; j < NB; j = j + 1) ql_sc[8 * j +: 8] = 8'd120 + (rnd() & 8'd15);
            ql_w = {1'b0, 8'd120 + (rnd() & 8'd7), 7'(rnd())};
            @(negedge clk); ql_v = 0;
        end
    endtask
    initial begin
        if ($test$plusargs("MUT_HB")) mut = 1;
        repeat (4) @(negedge clk); rst_n = 1; repeat (2) @(negedge clk);
        for (c = 0; c < 3; c = c + 1) begin                          // 3 tokens: reload all heads, then a key stream
            for (i = 0; i < 40; i = i + 1) qload((i * 7 + c) % 40);
            repeat (4) @(negedge clk);
            for (i = 0; i < 200; i = i + 1) begin
                @(negedge clk); k_v = (c == 0) ? 1'b1 : ((rnd() & 3) != 0); k_kv = rnd();
                for (j = 0; j < KW / 32 + 1; j = j + 1) k_key[32 * j +: 32] = rnd();
                for (j = 0; j < NKT * NB; j = j + 1) k_key[(j / NB) * NB * 136 + NB * 128 + 8 * (j % NB) +: 8] = 8'd118 + (rnd() & 8'd15);
            end
            @(negedge clk); k_v = 0; repeat (FPL * 12 + QL + FML + 20) @(negedge clk);
        end
        $display("summary: %0d key beats in, %0d chunk beats out, %0d mismatching cycles", nk, nc, errors);
        if (errors == 0 && nk == nc && nk > 0) $display("HGI_IDX_CHUNK_EL PASS (lockstep, 4 chunks, tput 1 beat/cycle)");
        else $display("HGI_IDX_CHUNK_EL FAIL");
        $finish;
    end
endmodule
