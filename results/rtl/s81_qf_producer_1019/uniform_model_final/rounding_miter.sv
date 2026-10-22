module rounding_miter(input [31:0] x, input [511:0] h,
output ok, output raw_ok, output header_ok, output bad_bind_ok);
function automatic [31:0] bf16(input [31:0] x);
        reg [32:0] s;
        begin s = {1'b0, x} + 33'h7FFF + {32'd0, x[16]}; bf16 = {s[31:16], 16'd0}; end
    endfunction
function automatic [31:0] fmt_d(input [31:0] x, input [15:0] row, input [1:0] fmt, input [15:0] rs, input lo32, input hi32);
        reg [32:0] rb;
        begin
            rb = {1'b0, x} + 33'h7FFF + {32'd0, x[16]};
            fmt_d = (fmt == 2'd1 || (fmt == 2'd0 && (row < rs ? lo32 : hi32))) ? x : {rb[31:16], 16'd0};
        end
    endfunction
wire [31:0] rounded = x + 32'h7fff + {31'd0,x[16]};
wire [31:0] golden = {rounded[31:16],16'd0};
wire [31:0] vs = bf16(x);
wire [31:0] cap = fmt_d(x,16'd0,2'd2,16'd0,1'b0,1'b0);
assign ok = vs == golden && cap == golden && vs[15:0] == 0 && cap[15:0] == 0;
assign raw_ok = x[31:16] == golden[31:16];
wire [1023:0] expanded;
wire [511:0] decoded;
genvar i;
generate for(i=0;i<32;i=i+1)begin:slot
assign expanded[32*i+:32] = {h[16*i+:16],16'd0};
assign decoded[16*i+:16] = expanded[32*i+16+:16];
end endgenerate
assign header_ok = decoded == h;
assign bad_bind_ok = expanded[511:0] == h;
endmodule
