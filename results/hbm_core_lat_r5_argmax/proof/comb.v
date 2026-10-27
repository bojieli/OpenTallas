// P3: the R4 32-bit expression vs the R5 19-bit + sign-extension, all inputs free
module p3(input wire [17:0] o_idx, input wire [2:0] ab, input wire z, output wire ok, output wire eq_hi);
    wire [31:0] old_v = {14'd0, o_idx} - (z ? 32'd0 : {29'd0, ab});
    wire [18:0] new_r = {1'b0, o_idx} - (z ? 19'd0 : {16'd0, ab});
    wire [31:0] new_v = {{13{new_r[18]}}, new_r};
    assign ok = old_v == new_v;
    assign eq_hi = (old_v[31:18] == {14{old_v[18]}});
endmodule
