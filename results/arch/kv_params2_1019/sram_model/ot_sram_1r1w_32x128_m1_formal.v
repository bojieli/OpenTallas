// KV-PARAMS2 10-19: SAT model of ot_sram_1r1w_32x128_m1 (tools/mem_compiler/sram_gen.py v1.0 behaviour, MUX 1, no
// spares, faults off, OT_MEM_NO_INIT): one clk; registered read when r_ce_in (rd_out holds otherwise); masked write when
// w_ce_in (mask 1 writes); same-address read in the write cycle returns the OLD word; no reset, no power-up content.
module ot_sram_1r1w_32x128_m1 (
    input  wire         clk,
    input  wire         r_ce_in,
    input  wire [4:0]   r_addr_in,
    output reg  [127:0] rd_out,
    input  wire         w_ce_in,
    input  wire [4:0]   w_addr_in,
    input  wire [127:0] wd_in,
    input  wire [127:0] w_mask_in
);
    reg [127:0] arr [0:31];
    always @(posedge clk) begin
        if (r_ce_in) rd_out <= arr[r_addr_in];
        if (w_ce_in) arr[w_addr_in] <= (arr[w_addr_in] & ~w_mask_in) | (wd_in & w_mask_in);
    end
endmodule
