`timescale 1ps/1fs
// Existing W18 /3,/4 clock plan's actual divider. Analog PLL is an IP input.
// Default OFF; cold POR only. Fast uses overlapping posedge/negedge pulses for 50% duty; slow is flop Q.
module ot_dsrom_wfc_common_clock_source #(parameter integer ENABLE=0)(
 input wire pll_vco,por_n, output wire clk_fast,clk_slow,clock_fault
);
 generate if(!ENABLE)begin:off
  assign clk_fast=0;assign clk_slow=0;assign clock_fault=0;
 end else begin:on
  reg [1:0] f=2,fn=1,s=3,sn=0;
  reg fq=0,fqn=1,fh=0,fhn=1,sq=0,sqn=1,failed=0,failed_n=1;
  wire bad=(f!=~fn)||(s!=~sn)||(f==3)||(fq==fqn)||(fh==fhn)||(sq==sqn)||(failed==failed_n);
  assign clock_fault=failed||bad;
  assign clk_fast=fq||fh;assign clk_slow=sq;
  always @(negedge pll_vco or negedge por_n)begin
   if(!por_n)begin fh<=0;fhn<=1;end
   else if(failed||bad)begin fh<=0;fhn<=1;end
   else begin fh<=fq;fhn<=!fq;end
  end
  always @(posedge pll_vco or negedge por_n)begin
   if(!por_n)begin
    f<=2;fn<=1;s<=3;sn<=0;fq<=0;fqn<=1;sq<=0;sqn<=1;failed<=0;failed_n<=1;
   end else if(failed||bad)begin
    failed<=1;failed_n<=0;fq<=0;fqn<=1;sq<=0;sqn<=1;
   end else begin
    f<=(f==2)?0:f+2'd1;fn<=~((f==2)?2'd0:f+2'd1);
    s<=s+2'd1;sn<=~(s+2'd1);
    fq<=(f==2);fqn<=!(f==2);
    sq<=(s==3||s==0);sqn<=!(s==3||s==0);
   end
  end
 end endgenerate
endmodule
