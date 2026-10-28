module fill_faces_miter(input wire [511:0] native, output wire mismatch);
wire [273:0] w={native[392:256],native[136:0]};
wire [237:0] e={native[511:393],native[255:137]};
wire [511:0] recovered;
ot_hbm_vmdel_fill_faces u(w,e,recovered);
assign mismatch=|(native^recovered);
endmodule
