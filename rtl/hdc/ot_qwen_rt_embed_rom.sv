`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// Qwen3-8B INT8 embedding ROM of the REAL_MEM runtime die (default-off; used only by
// rtl/test/qwen_rom_runtime/ot_qwen_rom_rt_die_w12_rm.sv with EMBED_ROM = 1).
//
// The core's INT8_EMBED port (rtl/hdc/ot_hdc_core_vector_weight.sv): code word a = token*64 +
// element/64 holds 64 signed INT8 codes (512 bits), returned the cycle after embed_code_re
// (held otherwise); the token's BF16 row scale is returned the cycle after embed_scale_re.
// Full vocabulary: 151,936 x 64 code words and 151,936 scales.
//
// Physical organisation (not instantiated in simulation): 2 x 2,374 ot_rom_4096x266_m8 code
// macros (a pair per 4,096 words) + 3 scale macros, the only ROM depth whose SS clk->q (739 ps)
// + setup fits the 833 ps cycle -- so the one-cycle registered read below IS that macro's read
// contract.  The simulation model stores the contents as plain arrays (instantiating 4,751
// via-mask macro models per die made the die model ~10x larger to compile; the scale and code
// ROMs of the run ARE instantiated macro models).  Contents are preloaded by the host.  An
// address past the vocabulary faults (sticky) instead of reading zero.
// ---------------------------------------------------------------------------
module ot_qwen_rt_embed_rom #(
    parameter integer ROWS = 151936,
    parameter integer AW = 24,
    parameter integer NW = 18
) (
    input  wire          clk,
    input  wire          rst_n,
    input  wire          code_re,
    input  wire [AW-1:0] code_addr,
    output reg  [511:0]  code_q,
    input  wire          scale_re,
    input  wire [NW-1:0] scale_addr,
    output reg  [15:0]   scale_q,
    output reg           fault
);
    reg [511:0] codes  [0:ROWS*64-1] /*verilator public_flat_rw*/;
    reg [15:0]  scales [0:ROWS-1]    /*verilator public_flat_rw*/;
    always @(posedge clk) begin
        if (code_re && code_addr < ROWS * 64) code_q <= codes[code_addr];
        if (scale_re && scale_addr < ROWS) scale_q <= scales[scale_addr];
    end
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) fault <= 1'b0;
        else if ((code_re && code_addr >= ROWS * 64) || (scale_re && scale_addr >= ROWS)) fault <= 1'b1;
    end
endmodule
