`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// ABI 3.0 engine-datapath fault codes and shared helpers.
//
// One code per way a datapath can refuse.  The golden side of the correlation
// derives the expected code from the EngineError the functional simulator
// actually raised -- its trap class plus the message it carries -- so a
// refusal is compared as a refusal *of the same kind*, not merely as "both
// stopped".  tools/build_abi3_engine_vectors.py publishes the code, the trap
// class and the golden message for every negative case.
// ---------------------------------------------------------------------------
package ot_a3_engine_pkg;
    localparam [7:0] ERR_NONE              = 8'd0;
    // BF16 NaN or infinity, or a reserved E4M3FN / E8M0 encoding
    localparam [7:0] ERR_OPERAND_NONFINITE = 8'd1;
    // a product left the binary32 range
    localparam [7:0] ERR_PRODUCT_RANGE     = 8'd2;
    // an accumulation or an elementwise sum left the binary32 range
    localparam [7:0] ERR_ACCUMULATE_RANGE  = 8'd3;
    // a gather or scatter index lies outside the extent it addresses
    localparam [7:0] ERR_INDEX_RANGE       = 8'd4;
    // a token may not be selected from a NaN or infinite logit
    localparam [7:0] ERR_SELECT_NONFINITE  = 8'd5;
    // block scale application left the binary32 range
    localparam [7:0] ERR_SCALE_RANGE       = 8'd6;
    // a degenerate or unsupported extent
    localparam [7:0] ERR_SHAPE             = 8'd7;

    // Engine family and subopcode identifiers, transcribed from
    // runtime/abi3/constants.py.  The engine array dispatches on the pair.
    localparam [7:0] FAMILY_DMA       = 8'h10;
    localparam [7:0] FAMILY_TENSOR    = 8'h20;
    localparam [7:0] FAMILY_VECTOR    = 8'h30;
    localparam [7:0] FAMILY_SELECTION = 8'h70;

    localparam [7:0] DMA_GATHER       = 8'h02;
    localparam [7:0] DMA_SCATTER      = 8'h03;
    localparam [7:0] TENSOR_MATMUL    = 8'h00;
    localparam [7:0] VECTOR_ADD       = 8'h03;
    localparam [7:0] SELECTION_ARGMAX = 8'h00;

    // Order-preserving key for a finite binary32 comparison.  Sign-magnitude
    // is not monotone as an unsigned integer, so the sign decides: a negative
    // code inverts, a non-negative code sets the top bit.  Signed zero is
    // canonicalised first, because +0.0 and -0.0 compare equal and must
    // therefore key equal -- the tie rule for token selection depends on it.
    function automatic [31:0] order_key;
        input [31:0] code;
        reg [31:0] canonical;
        begin
            canonical = (code[30:0] == 31'b0) ? 32'b0 : code;
            order_key = canonical[31] ? ~canonical : (canonical | 32'h8000_0000);
        end
    endfunction
endpackage
