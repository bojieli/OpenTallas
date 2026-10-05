`timescale 1ns/1ps
// Static producer wiring view: instantiate in the source's known format path.
// No run-time format mux or state. The compiler emits beats from this same map.
module ot_hbm_accel_activation_pack #(
    parameter integer NC = 8,
    parameter integer FORMAT = 0, // 0 BF16, 1 FP8, 2 FP4, source-selected at elaboration
    parameter integer XMAP = 0    // default-off; original fragment layout bypass
) (
    input wire [NC*3152-1:0] source_fragment,
    output wire [NC*3152-1:0] packed_fragment
);
    generate if (FORMAT < 0 || FORMAT > 2) begin : g_bad_format
        initial $fatal(1, "Unsupported activation packing format");
    end endgenerate
    genvar bit_index;
    generate for (bit_index=0; bit_index<NC*3152; bit_index=bit_index+1) begin : g_bit
        if (!XMAP) begin : g_original
            assign packed_fragment[bit_index] = source_fragment[bit_index];
        end else if (FORMAT==0) begin : g_bf16
            if (bit_index<NC*1024)
                assign packed_fragment[bit_index] = source_fragment[(bit_index/1024)*3152+2128+bit_index%1024];
            else assign packed_fragment[bit_index] = 1'b0;
        end else begin : g_block
            localparam integer HALF = bit_index/(NC*1064);
            localparam integer COL = (bit_index%(NC*1064))/1064;
            localparam integer IN_HALF = bit_index%1064;
            if ((FORMAT==1 && HALF==0) || (FORMAT==2 && HALF<2))
                assign packed_fragment[bit_index] = source_fragment[COL*3152+HALF*1064+IN_HALF];
            else assign packed_fragment[bit_index] = 1'b0;
        end
    end endgenerate
endmodule
