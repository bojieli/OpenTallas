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
