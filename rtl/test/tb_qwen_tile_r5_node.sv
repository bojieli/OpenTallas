`timescale 1ns/1ps
// q13 spec r5 leaf 2 boundary bench: the W12 ROM tile (ot_qwen_rom_tile_w12, NK form, production parameters) with the
// tree node as the hardened-leaf wrapper ot_qwen_tile_node (NDH 1) against the same tile flat (NDH 0), same inputs:
//   n_y, n_vy, t_out, t_vout equal on EVERY cycle (the leaf is a pure re-hierarchy of the node's data and valid);
//   fault == the flat tile's engine fault | its node fault ONE cycle later (the leaf's fault pin register).
// Stimulus: random finite / special FP32 words on n_a / n_b with random n_va, random instruction words with sparse go.
// BMUT 2 (the leaf's a input with lanes 0 / 1 swapped at the seam) must FAIL.
// q14: t_out / t_vout come from the leaf's feed-through pin registers (the TOREG registers moved into the leaf); BMUT 3
// (the leaf's t_d input with lanes 0 / 1 swapped at the seam) must FAIL.
module ot_rom_4096x266_m8 (input wire clk, input wire ce_in, input wire [11:0] addr_in, output reg [265:0] rd_out);
    always @(posedge clk) if (ce_in) rd_out <= {22{addr_in ^ 12'h5a5}} ^ {{8{addr_in, 21'h1f3a5c}}, 2'b01};
endmodule
module tb_qwen_tile_r5_node;
    parameter integer N = 60000, BMUT = 0, SEED = 1;
    localparam integer NW = 18, IBW = 3*NW + 13*24 + 13;
    reg clk = 0, rst_n = 0;
    always #1 clk = ~clk;
    reg [15:0] tile_id = 16'h0003;
    reg ib_go = 0; reg [IBW-1:0] ib = 0; reg [127:0] xl = 0;
    reg [511:0] n_a = 0, n_b = 0; reg n_va = 0;
    wire [511:0] f_t, h_t, f_y, h_y; wire f_tv, h_tv, f_vy, h_vy, f_fault, h_fault;
`define TILE(NAME, ND, BM, T, TV, Y, VY, F) \
    ot_qwen_rom_tile_w12 #(.NW(18), .GT(6144), .SMIN(7), .CODE_BANKS(5), .KV_VB(131072), .KV_NH(2), .MEM_EXTRA(1), \
        .ACC_LAT(7), .TREE_LAT(7), .MUL_LAT(8), .FAST_ISSUE(1), .KV_PREP(4), .ROM_PIPE(1), .ROM_ARELAY(2), .ROM_CAP2(1), \
        .ROM_CAPX(2), .LRST(3), .ARPB(1), .MPR(1), .HIER(2), .HIER_HARD(1), .ANR(1), .TOREG(1), .TIDR(1), .LRR(1), .XTX(2), \
        .KV_SLICE(0), .NDH(ND), .BMUT(BM)) NAME (.clk(clk), .rst_n(rst_n), .tile_id(tile_id), .ib_go(ib_go), .ib(ib), .xl(xl), \
        .t_out(T), .t_vout(TV), .n_a(n_a), .n_b(n_b), .n_va(n_va), .n_y(Y), .n_vy(VY), .fault(F), \
        .kvw_ce(1'b0), .kvw_addr(7'd0), .kvw_data(512'd0), .kvw_mask(512'd0));
    `TILE(u_flat, 0, 0, f_t, f_tv, f_y, f_vy, f_fault)
    `TILE(u_hard, 1, BMUT, h_t, h_tv, h_y, h_vy, h_fault)
    reg nf_q;
    always @(posedge clk or negedge rst_n) if (!rst_n) nf_q <= 1'b0; else nf_q <= u_flat.u_logic.node_fault;
    wire f_ref = u_flat.u_logic.me_fault | nf_q;
    integer seed, i, cyc = 0, errors = 0, n_vy = 0, n_nz = 0, n_go = 0, n_flt = 0;
    function automatic [31:0] fpw(input [31:0] h);
        begin
            case (h[31:28])
                4'd0: fpw = 32'd0;
                4'd1: fpw = {h[0], 31'd0};
                4'd2: fpw = {h[0], 8'hff, 23'd0};                       // infinity (raises the node fault)
                default: fpw = {h[27], 8'd100 + {2'd0, h[26:21]} % 8'd56, h[22:0]};
            endcase
        end
    endfunction
    always @(negedge clk) if (rst_n) begin
        cyc = cyc + 1;
        if (f_y !== h_y || f_vy !== h_vy || f_t !== h_t || f_tv !== h_tv) begin
            if (errors < 10) $display("FAIL cyc=%0d data/valid differ vy %b/%b", cyc, f_vy, h_vy);
            errors = errors + 1;
        end
        if (h_fault !== f_ref) begin
            if (errors < 10) $display("FAIL cyc=%0d fault %b != ref %b", cyc, h_fault, f_ref);
            errors = errors + 1;
        end
        if (f_vy) begin n_vy = n_vy + 1; if (f_y != 512'd0) n_nz = n_nz + 1; end
        if (nf_q) n_flt = n_flt + 1;
    end
    initial begin
        seed = SEED;
        repeat (4) @(posedge clk);
        rst_n = 1;
        repeat (8) @(posedge clk);      // q14: the leaf's reset relay releases 3 edges after the pin; the tile is idle after reset
        for (i = 0; i < N; i = i + 1) begin
            @(posedge clk); #0.1;
            n_va = ($urandom(seed) % 4) != 0; seed = seed + 1;
            begin : g_w
                integer l;
                for (l = 0; l < 16; l = l + 1) begin
                    n_a[32*l +: 32] = fpw($urandom(seed)); seed = seed + 1;
                    n_b[32*l +: 32] = fpw($urandom(seed)); seed = seed + 1;
                end
                for (l = 0; l < 4; l = l + 1) begin xl[32*l +: 32] = fpw($urandom(seed) | 32'h30000000); seed = seed + 1; end
            end
            ib_go = ($urandom(seed) % 700) == 0; seed = seed + 1;
            if (ib_go) begin
                n_go = n_go + 1;
                ib = 0;
                ib[IBW-1 -: NW] = 1 + $urandom(seed) % 512; seed = seed + 1;           // nout
                ib[IBW-NW-1 -: NW] = 1;                                                // tiles
                ib[IBW-2*NW-1 -: NW] = 1 + $urandom(seed) % 4; seed = seed + 1;        // k
            end
        end
        repeat (40) @(posedge clk);
        if (errors == 0 && n_vy > 1000 && n_nz > 1000)
            $display("PASS tile_r5_node cycles=%0d checks=%0d node_results=%0d nonzero=%0d go=%0d fault_cycles=%0d", cyc, cyc, n_vy, n_nz, n_go, n_flt);
        else $display("FAIL tile_r5_node errors=%0d node_results=%0d nonzero=%0d", errors, n_vy, n_nz);
        $finish;
    end
endmodule
