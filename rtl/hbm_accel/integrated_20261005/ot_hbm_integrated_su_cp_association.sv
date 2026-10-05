`timescale 1ns/1ps
// Qualified admission is distinct from the lifetime of an accepted executor.
// Shared grant owns all request/response debt. Live veto never cancels it.
module ot_hbm_integrated_su_cp_association #(parameter integer ENABLE=0)(
 input wire clk,por_n,raw_grant,qualified_owned,
 output wire exec_owned,new_request_permit,fault
);
 generate if(!ENABLE)begin:off
  assign exec_owned=raw_grant;
  assign new_request_permit=1'b1;
  assign fault=1'b0;
 end else begin:on
  reg associated_q,associated_n;
  wire rails_bad=associated_q==associated_n;
  wire associated=associated_q&&!associated_n;
  assign fault=raw_grant&&rails_bad;
  assign exec_owned=raw_grant&&!rails_bad&&(associated||qualified_owned);
  assign new_request_permit=raw_grant&&!rails_bad&&qualified_owned;
  always @(posedge clk or negedge por_n)begin
   if(!por_n)begin associated_q<=0;associated_n<=1;end
   else if(!raw_grant)begin associated_q<=0;associated_n<=1;end
   else if(qualified_owned&&!rails_bad)begin associated_q<=1;associated_n<=0;end
  end
 end endgenerate
endmodule
