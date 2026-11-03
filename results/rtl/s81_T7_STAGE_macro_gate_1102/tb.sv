`timescale 1ns/1ps
// T7 attention staging SRAM_MACRO=1 vs SRAM_MACRO=0 gate (TOK-DS-4, 2026-11-02).
// Both instances use the unchanged ot_hdc_v41x_attn_staging at the T7 bound parameters D=32, NL=4, TROWS=640
// (DEPTH 160, ROWW 265, two 256x256 macros per lane). Clock 833 ps. Every edge, all 1060 rd_data bits are compared
// whenever the sampled rd_addr is < DEPTH (behavioural rows >= DEPTH do not exist: their read is undefined).
module tb;
localparam integer D = 32, NL = 4, TROWS = 640, DEPTH = 160, AW = 8, W = NL * (D / 32) * 265;
reg clk = 0;
always #0.4165 clk = ~clk;
reg  [NL-1:0] wr_en = 0;
reg  [AW-1:0] wr_addr = 0, rd_addr = 0;
reg  [W-1:0]  wr_data = 0;
wire [W-1:0]  q_ref, q_mac, q_m1, q_m2, q_m3, q_m4;
ot_hdc_v41x_attn_staging #(.D(D), .NL(NL), .TROWS(TROWS), .SRAM_MACRO(1'b0)) u_ref (clk, wr_en, wr_addr, wr_data, rd_addr, q_ref);
ot_hdc_v41x_attn_staging #(.D(D), .NL(NL), .TROWS(TROWS), .SRAM_MACRO(1'b1)) u_mac (clk, wr_en, wr_addr, wr_data, rd_addr, q_mac);
stg_mut1 #(.D(D), .NL(NL), .TROWS(TROWS), .SRAM_MACRO(1'b1)) u_m1 (clk, wr_en, wr_addr, wr_data, rd_addr, q_m1);
stg_mut2 #(.D(D), .NL(NL), .TROWS(TROWS), .SRAM_MACRO(1'b1)) u_m2 (clk, wr_en, wr_addr, wr_data, rd_addr, q_m2);
stg_mut3 #(.D(D), .NL(NL), .TROWS(TROWS), .SRAM_MACRO(1'b1)) u_m3 (clk, wr_en, wr_addr, wr_data, rd_addr, q_m3);
stg_mut4 #(.D(D), .NL(NL), .TROWS(TROWS), .SRAM_MACRO(1'b1)) u_m4 (clk, wr_en, wr_addr, wr_data, rd_addr, q_m4);
integer mutant = 0, i, j, seed = 1;
wire [W-1:0] obs = (mutant == 1) ? q_m1 : (mutant == 2) ? q_m2 : (mutant == 3) ? q_m3 : (mutant == 4) ? q_m4 : q_mac;
integer n_cmp = 0, n_coll = 0, n_oor_w = 0, n_oor_r = 0, n_wr = 0, n_nz = 0, n_slice1 = 0;
reg [AW-1:0] rd_s;
function automatic [AW-1:0] addr(input integer r);
    addr = (r % 10 == 0) ? AW'(DEPTH + ($urandom % (256 - DEPTH))) : AW'($urandom % DEPTH);
endfunction
initial begin
    if (!$value$plusargs("mutant=%d", mutant)) mutant = 0;
    // seed every row of every lane through the real write port
    for (i = 0; i < DEPTH; i = i + 1) begin
        @(negedge clk); wr_en = '1; wr_addr = AW'(i); rd_addr = 0;
        for (j = 0; j < W / 32 + 1; j = j + 1) wr_data[32*j +: 32] = $urandom;
    end
    for (i = 0; i < 4096; i = i + 1) begin
        @(negedge clk);
        wr_en = NL'($urandom); wr_addr = addr($urandom); rd_addr = addr($urandom);
        if ($urandom % 4 == 0) rd_addr = wr_addr;
        for (j = 0; j < W / 32 + 1; j = j + 1) wr_data[32*j +: 32] = $urandom;
        if (wr_en != 0 && rd_addr == wr_addr) n_coll = n_coll + 1;
        if (wr_en != 0 && wr_addr >= DEPTH) n_oor_w = n_oor_w + 1;
        if (wr_en != 0) n_wr = n_wr + 1;
        rd_s = rd_addr;
        @(posedge clk); #0.2;
        if (rd_s >= DEPTH) n_oor_r = n_oor_r + 1;
        else begin
            n_cmp = n_cmp + 1;
            if (q_ref != 0) n_nz = n_nz + 1;
            if (q_ref[W-1:256] != 0) n_slice1 = n_slice1 + 1;
            if (q_ref !== obs) begin
                $display("STAGE_MACRO_FAIL mutant=%0d edge=%0d rd_addr=%0d", mutant, i, rd_s); $fatal(1);
            end
        end
    end
    $display("STAGE_MACRO_PASS edges=4096 compared=%0d rdwr_collisions=%0d writes=%0d oor_writes=%0d oor_reads_skipped=%0d nonzero_reads=%0d", n_cmp, n_coll, n_wr, n_oor_w, n_oor_r, n_nz);
    $finish;
end
endmodule
