module comparison(input wire[2:0] rc,input wire signed[31:0] K,
output wire ok, output wire truncated_ok);
wire old_cmp = rc == K-1;
wire new_cmp = 32'(rc) == K-1;
wire bad_cmp = rc == 3'(K-1);
assign ok=old_cmp==new_cmp;
assign truncated_ok=old_cmp==bad_cmp;
endmodule
