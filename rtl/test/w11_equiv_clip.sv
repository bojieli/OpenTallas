module clip_gold(input [31:0] x, input [31:0] imm, output [31:0] y);
    function automatic [31:0] okey(input [31:0] v); okey = v[31] ? ~v : {1'b1, v[30:0]}; endfunction
    function automatic [31:0] fmin(input [31:0] a, input [31:0] b); fmin = (okey(a) <= okey(b)) ? a : b; endfunction
    function automatic [31:0] fmax(input [31:0] a, input [31:0] b); fmax = (okey(a) >= okey(b)) ? a : b; endfunction
    assign y = fmin(fmax(x, {1'b1, imm[30:0]}), imm);
endmodule
module clip_gate(input [31:0] x, input [31:0] imm, output [31:0] y);
    function automatic [31:0] okey(input [31:0] v); okey = v[31] ? ~v : {1'b1, v[30:0]}; endfunction
    wire [31:0] lo = {1'b1, imm[30:0]};
    wire ge_lo = okey(x) >= okey(lo);
    wire le_hi = okey(x) <= okey(imm);
    wire lohi = okey(lo) <= okey(imm);
    assign y = ge_lo ? (le_hi ? x : imm) : (lohi ? lo : imm);
endmodule
// A' = min(relu(rnd?(A)), imm3): the lane's original chained form and its side-by-side form
module prea_gold(input [31:0] x, input [31:0] imm, input arnd, input arelu, input amin, output [31:0] y);
    function automatic [31:0] okey(input [31:0] v); okey = v[31] ? ~v : {1'b1, v[30:0]}; endfunction
    function automatic [31:0] fmin(input [31:0] a, input [31:0] b); fmin = (okey(a) <= okey(b)) ? a : b; endfunction
    function automatic [31:0] bf16(input [31:0] v); bf16 = (v + 32'h7FFF + {31'd0, v[16]}) & 32'hFFFF0000; endfunction
    wire [31:0] a_r = arnd ? bf16(x) : x;
    wire [31:0] a_l = (arelu && a_r[31]) ? 32'd0 : a_r;
    assign y = amin ? fmin(a_l, imm) : a_l;
endmodule
module prea_gate(input [31:0] x, input [31:0] imm, input arnd, input arelu, input amin, output [31:0] y);
    function automatic [31:0] okey(input [31:0] v); okey = v[31] ? ~v : {1'b1, v[30:0]}; endfunction
    function automatic [31:0] pre_a(input [31:0] v, input relu, input amn, input [31:0] im);
        reg zero, le_v, le_0;
        begin
            zero = relu && v[31];
            le_v = okey(v) <= okey(im);
            le_0 = okey(32'd0) <= okey(im);
            pre_a = !amn ? (zero ? 32'd0 : v) : zero ? (le_0 ? 32'd0 : im) : (le_v ? v : im);
        end
    endfunction
    wire [31:0] t = {x[31:16], 16'd0};
    wire [31:0] u = {x[31:16] + 16'd1, 16'd0};
    wire up = x[15] & ((|x[14:0]) | x[16]);
    assign y = !arnd ? pre_a(x, arelu, amin, imm) : up ? pre_a(u, arelu, amin, imm) : pre_a(t, arelu, amin, imm);
endmodule
