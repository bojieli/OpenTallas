// Smallest paired landing with independent source/destination clocks.
module landing_vehicle #(parameter W=1095,D=4,K=2,PHYSICAL=0)(
 input wire ck_w,ck_r,rst_w,rst_r,input wire[W-1:0] i,
 output wire[W-1:0] o
);
 localparam AW=$clog2(D),C=(W+23)/24;
 wire[W*D-1:0] bank;
 generate if(PHYSICAL==0) begin:g_generic
  wire[D*(AW+1)-1:0] epo;wire[D-1:0] vld;
  ot_pl_land_w #(.W(W),.D(D)) w(.ck(ck_w),.rsi(rst_w),.i(i),.bank(bank),.epo(epo),.vld(vld));
  ot_pl_land_r #(.W(W),.D(D),.K(K)) r(.ck(ck_r),.rsi(rst_r),.bank(bank),.epo(epo),.vld(vld),.o(o));
 end else begin:g_physical
  wire[C*D-1:0] vld;
  ot_pl_land_phys_chunk_w #(.W(W),.D(D)) w(.ck(ck_w),.rsi(rst_w),.i(i),.bank(bank),.vld(vld));
  ot_pl_land_phys_chunk_r #(.W(W),.D(D),.K(K)) r(.ck(ck_r),.rsi(rst_r),.bank(bank),.vld(vld),.o(o));
 end endgenerate
endmodule
