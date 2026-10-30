

module ot_hdc_inc_k__u1 #(
    parameter integer W = 24
) (
    input  wire [W-1:0] a,
    input  wire         inc,
    output wire [W-1:0] y,
    output wire         co
);
    localparam integer L = $clog2(W + 1);
    // t[i]: all of positions [0, i] are one, position 0 being the increment
    (* keep *) wire [W:0] t [0:L];
    assign t[0] = {a, inc};
    genvar l, i;
    generate
        for (l = 0; l < L; l = l + 1) begin : g_lv
            for (i = 0; i <= W; i = i + 1) begin : g_b
                if (i >= (1 << l)) begin : g_c
                    assign t[l + 1][i] = t[l][i] & t[l][i - (1 << l)];
                end else begin : g_p
                    assign t[l + 1][i] = t[l][i];
                end
            end
        end
    endgenerate
    assign y = a ^ t[L][W-1:0];
    assign co = t[L][W];
endmodule
