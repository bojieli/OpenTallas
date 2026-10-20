`timescale 1ns/1ps
module tb_reset_edges;
 reg ck=0,rst_n=0,start=0;always #1 ck=~ck;
 (* keep="true" *) reg land0,land1;
 always @(posedge ck)land0<=rst_n;
 always @(posedge ck)land1<=land0;
 wire [255:0] plain,farm;
 ot_rst_relay_bounded32 #(.REGIONS(256)) u_plain(.clk(ck),.rst_n_in(rst_n),.rst_n(plain));
 ot_rst_relay_bounded32 #(.REGIONS(256)) u_ship(.clk(ck),.rst_n_in(land1),.rst_n(farm));
 // Exact pin/control reset sensitivity and start_q->active first-command path
 // from R10 and legacy; valid calendar, inactive and no fault preconditions.
 reg q0,q1,q2,a0,a1,a2;
 always @(posedge ck or negedge rst_n)if(!rst_n)q0<=0;else q0<=start;
 always @(posedge ck or negedge plain[0])if(!plain[0])q1<=0;else q1<=start;
 always @(posedge ck or negedge farm[0])if(!farm[0])q2<=0;else q2<=start;
 always @(posedge ck or negedge rst_n)if(!rst_n)a0<=0;else if(q0)a0<=1;
 always @(posedge ck or negedge plain[0])if(!plain[0])a1<=0;else if(q1)a1<=1;
 always @(posedge ck or negedge farm[0])if(!farm[0])a2<=0;else if(q2)a2<=1;
 initial begin
  repeat(8)@(negedge ck);rst_n=1;start=1;
  $display("EDGE land0 land1 plain_leaf ship_roots ship_second ship_leaf legacy_q plain_q ship_q legacy_active plain_active ship_active");
  for(integer e=1;e<=7;e=e+1)begin
   @(negedge ck);
   $display("%0d %b %b %b %b %b %b %b %b %b %b %b %b",e,land0,land1,plain[0],u_ship.data_root[0],u_ship.region[0].second,farm[0],q0,q1,q2,a0,a1,a2);
   if(q0!==(e>=1)||q1!==(e>=4)||q2!==(e>=6)||a0!==(e>=2)||a1!==(e>=5)||a2!==(e>=7))$fatal(1,"RESET_EDGE FAIL edge=%0d",e);
  end
  $display("RESET_EDGE PASS release-beforeE1 pin1/4/6 accept2/5/7 delta_shipping_vs_legacy5 vs_plain2");$finish;
 end
endmodule
