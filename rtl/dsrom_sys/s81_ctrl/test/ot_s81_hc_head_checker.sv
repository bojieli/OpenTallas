`timescale 1ns/1ps
// Every engine edge, not only command accepts: the physical snapshot may
// describe a blocked head and must keep data, valid and acceptance aligned.
module ot_s81_hc_head_checker(input wire clk,rst_n,
 input wire source_valid,source_accept,input wire [83:0] source_d,
 input wire pin_valid,pin_accept,input wire [83:0] pin_d);
 reg v,a;reg [83:0] d;integer checked=0,accepted=0,loads=0,stores=0;
 always @(posedge clk or negedge rst_n)
  if(!rst_n)begin v<=0;a<=0;d<=0;end
  else begin v<=source_valid;a<=source_accept;d<=source_d;end
 always @(negedge clk)if(rst_n)begin
  if(pin_valid!==v || pin_accept!==a || pin_d!==d)$fatal(1,"actual HC face snapshot lost alignment");
  checked=checked+1;
  if(pin_accept)begin accepted=accepted+1;
   if(pin_d[29:27]==0)loads=loads+1;
   if(pin_d[29:27]==1)stores=stores+1;
  end
 end
 final $display("HC_HEAD_PIN_CHECK checked=%0d accepted=%0d loads=%0d stores=%0d",checked,accepted,loads,stores);
endmodule
bind ot_s81_hc_cseq ot_s81_hc_head_checker hc_head_pin_check(
 .clk(sk),.rst_n(rs_n),.source_valid(head_valid),.source_accept(head_accept),.source_d(head_d),
 .pin_valid(n_head_valid),.pin_accept(n_head_accept),.pin_d(n_head_d));
