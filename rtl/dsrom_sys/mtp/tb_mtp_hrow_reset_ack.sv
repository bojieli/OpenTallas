`timescale 1ns/1ps
module tb_mtp_hrow_reset_ack;
 reg ck=0,leaf_ck=0,run_leaf=1,rst=0;
 always #5 ck=~ck;
 always #5 if(run_leaf) leaf_ck=~leaf_ck; else leaf_ck=0;
 wire rn,ca,ra;wire[2078:0]o;reg[2078:0]i=0;
 dsfd_die_rstsync #(.RESET_ACK(1)) u_rs(.ck(ck),.rst(rst),.rn(rn),.rst_ack(ca));
 dsfd_hrow_r2079 u_r(.ck(leaf_ck),.rn(rn),.i(i),.o(o),.reset_epoch_n(rst),.rst_ack(ra));
 task bad(input string s);begin $display("ACK_BAD %s rn=%b ca=%b ra=%b",s,rn,ca,ra);$fatal(1);end endtask
 initial begin
   #21;rst=1;#60;
   if(!ca||!ra)bad("initial actual consumer release");
   @(negedge ck);run_leaf=0;#1;rst=0;#20;rst=1;#60;
   if(ra)bad("stopped leaf clock acknowledged");
   // Conditioner completed its reset while leaf was stopped: no low local RN
   // was sampled by this leaf in the new epoch. Resuming must not repair it.
   run_leaf=1;#60;if(ra)bad("missed epoch local reset witness");
   @(negedge ck);rst=0;#21;rst=1;#60;
   if(!ra||!ca)bad("valid reset repair");
   i[0]=1;i[1039]=1;i[1054]=1;#20;
   if(!ra||!o[0]||!o[1039]||!o[1054])bad("payload flags incorrectly gate ACK");
   rst=0;#1;if(ra||ca)bad("raw epoch did not clear ACK");
   $display("PASS actual stopped relay/conditioner clocks and epoch witness");$finish;
 end
endmodule
module tb_mtp_hrow_reset_ack_full;
 reg ck=0,rst=0;always #5 ck=~ck;
 wire[39:0]a;wire[26:0]b,c;
 dsfd_mtp_hrow_td #(.HARD_RELAYS(1),.DISTRIBUTED_RST(1),.UT(2)) dut(
 .ck(ck),.rst(rst),.f_hp0(515'b0),.f_hp1(515'b0),.f_hp2(515'b0),
 .f_vrq(25'b0),.f_clr(11'b0),.rst_ack_leaf(a),.rst_ack_relay(b),.rst_ack_conditioner(c));
 initial begin
 #21;rst=1;#120;
 if(!(&{a,b,c}))begin $display("ACK_BAD full94 release %h %h %h",a,b,c);$fatal(1);end
 rst=0;#1;
 if(|{a,b,c})begin $display("ACK_BAD full94 epoch clear");$fatal(1);end
 #20;rst=1;#120;
 if(!(&{a,b,c}))begin $display("ACK_BAD full94 second epoch");$fatal(1);end
 $display("PASS all94 genuine HROW ACK outputs and second epoch");$finish;
 end
endmodule
