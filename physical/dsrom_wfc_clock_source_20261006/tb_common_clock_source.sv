`timescale 1ps/1fs
module tb_common_clock_source;
 reg pll_vco=0,por_n=0;wire f,s,fault;integer edge_n=0,checks=0;
 always #138.888889 pll_vco=~pll_vco;
 ot_dsrom_wfc_common_clock_source #(.ENABLE(1)) dut(pll_vco,por_n,f,s,fault);
 initial begin
  repeat(2)@(negedge pll_vco);por_n=1;
  for(integer k=0;k<25;k=k+1)begin
   @(posedge pll_vco);#1;
   if(f!==((k%3)==0||(k%3)==1)||s!==((k%4)==0||(k%4)==1)||fault)$fatal(1,"source edge mismatch k=%0d",k);
   checks++;
   @(negedge pll_vco);#1;if(f!==((k%3)==0)||s!==((k%4)==0||(k%4)==1)||fault)$fatal(1,"halfedge duty mismatch");
   checks++;
  end
  @(negedge pll_vco);dut.on.fn=dut.on.fn^2'b01;
  #1;if(!fault)$fatal(1,"counter mismatch failed open");
  @(negedge pll_vco);#1;if(f||s||!fault)$fatal(1,"fault did not stop source");
  repeat(3)begin @(negedge pll_vco);#1;if(f||s||!fault)$fatal(1,"sticky source failure");end
  @(negedge pll_vco);por_n=0;#1;if(f||s||fault)$fatal(1,"cold POR");
  $display("PASS_COMMON_SOURCE edges=%0d /3,/4 actual50pct duty aligned firstmasteredge; counterfault sticky stop coldPOR",checks);
  $finish;
 end
endmodule
