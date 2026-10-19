`timescale 1ns/1ps
module tb_predecode;
  reg clk=0; always #5 clk=~clk;
  reg [23:0] tm=0, tq=0;
  wire [8:0] ix=tm[22:14], sx=tm[13] ? tm[12:4] : ~tm[12:4];
  wire [23:0] pd, sd;
  for(genvar g=0;g<3;g=g+1) for(genvar v=0;v<8;v=v+1) begin
    assign pd[8*g+v]=ix[3*g+:3]==v;
    assign sd[8*g+v]=sx[3*g+:3]==v;
  end
  wire [32:0] c0, e0; wire [22:0] c1,e1; wire [12:0] c2,e2; wire [13:0] sq,es;
  wire [12:0] dm=tq[13] ? tq[12:0] : ~tq[12:0];
  ot_hdc_sk_recip_rom ref_rom(.i(tq[22:14]),.c0(e0),.c1(e1),.c2(e2));
  ot_hdc_sk_sq_rom ref_sq(.dmh(dm[12:4]),.sq(es));
  ot_hdc_skp_decode_c0lo a(clk,pd,c0[16:0]);
  ot_hdc_skp_decode_c0hi b(clk,pd,c0[32:17]);
  ot_hdc_skp_decode_c1 c(clk,pd,c1);
  ot_hdc_skp_decode_c2 d(clk,pd,c2);
  ot_hdc_skp_decode_sq e(clk,sd,sq);
  always @(posedge clk) tq<=tm;
  integer errs=0;
  initial begin
    for(integer i=0;i<2048;i=i+1) begin
      @(negedge clk); tm={1'b1,9'(i),1'(i>>9),9'(i*73),4'b1010};
      @(posedge clk); #1;
      if({c0,c1,c2,sq} !== {e0,e1,e2,es}) begin
        errs=errs+1; if(errs<4) $display("PREDECODE mismatch i=%0d",i);
      end
    end
    if(errs) $fatal(1,"PREDECODE FAIL errors=%0d",errs);
    $display("PREDECODE PASS cases=2048 all512 seed/square addresses both polarities same-edge");
    $finish;
  end
endmodule
