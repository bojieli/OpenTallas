
// Leading-zero count of a 32-bit word as a tree (n = 32 for zero).
module ot_hdc_lzc32 (
    input  wire [31:0] x,
    output wire [5:0]  n
);
    // Level L holds 32 >> L groups; group k covers bits [(k+1)*2^L-1 : k*2^L],
    // with a valid bit (any one) and the count of leading zeros below 2^L.
    reg [31:0]     v, vn;
    reg [32*5-1:0] c, cn;
    integer L, k;
    always @* begin
        v = x;
        c = {(32*5){1'b0}};
        vn = 32'd0;
        cn = {(32*5){1'b0}};
        for (L = 0; L < 5; L = L + 1) begin
            vn = 32'd0;
            cn = {(32*5){1'b0}};
            for (k = 0; k < (16 >> L); k = k + 1) begin
                vn[k] = v[2*k+1] | v[2*k];
                cn[5*k +: 5] = v[2*k+1] ? c[5*(2*k+1) +: 5] : (c[5*(2*k) +: 5] | (5'd1 << L));
            end
            v = vn;
            c = cn;
        end
    end
    assign n = v[0] ? {1'b0, c[4:0]} : 6'd32;
endmodule
