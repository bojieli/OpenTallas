`timescale 1ns/1ps
module tb_qbank #(parameter integer ALIGN=0,MUT=0);
 reg ck=0;always #5 ck=~ck;
 reg rst_n=0;reg[547:0]dd=0;reg lcv=0;reg[5:0]stage=0;reg qs=0;reg[4:0]beat=0;
 wire[547:0]ddo;wire lcvo;wire[5:0]sto;wire v,full,committed,bad;wire[4:0]ob;wire[511:0]row;
 qfd_native59_qbank #(.MUT(MUT),.QB_MUT(0),.QB_ALIGN(ALIGN),.QB_LOCAL32(0),.QB_LOCAL_MUT(0)) dut
 (.ck(ck),.rst_n(rst_n),.dd_i(dd),.layer_context_v(lcv),.command_stage(stage),.q_slot(qs),.q_slot_beat(beat),
 .dd_o(ddo),.lcv_o(lcvo),.stage_o(sto),.qb_v(v),.qb_beat(ob),.qb_row(row),.qb_full(full),.qb_committed(committed),.qb_bad(bad));
 integer cyc=0,got=0,err=0,checks=0,gap=1;bit checking=0;
 function automatic[31:0] val(input integer e);val=32'(e)*32'h9e3779b1+32'h3f800007;endfunction
 task tick;begin @(posedge ck);#1;end endtask
 task drive;begin @(negedge ck);end endtask
 always @(posedge ck)begin
  #1;cyc++;
  if(checking&&v)begin
   if(ob!==5'(got))begin err++;$display("QB_MISMATCH beat_order got=%0d expected=%0d",ob,got);end
   for(integer j=0;j<16;j++)begin checks++;if(row[32*j+:32]!==val(16*got+j))begin
    if(err<8)$display("QB_MISMATCH cycle=%0d beat=%0d lane=%0d row=%h expected=%h ALIGN=%0d GAP=%0d",cyc,ob,j,row[32*j+:32],val(16*got+j),ALIGN,gap);
    err++;
   end end
   if(!full||!committed||bad)begin err++;$display("QB_MISMATCH flags full=%b committed=%b bad=%b",full,committed,bad);end
   got++;
  end
 end
 initial begin
  if($value$plusargs("GAP=%d",gap));repeat(4)tick();drive();rst_n=1;repeat(12)tick();
  drive();lcv=1;stage=1;tick();drive();lcv=0;repeat(8)tick();
  for(integer n=0;n<64;n++)begin
   drive();dd=0;dd[547:545]=3'b100;dd[544:537]=8'hff;
   for(integer w=0;w<8;w++)begin integer e;e=((8*n+w)*37+11)%512;dd[345+24*w+:24]=24'(e);dd[89+32*w+:32]=val(e);end
   tick();
  end
  drive();dd=0;repeat(12)tick();
  if(!committed||bad)begin $display("QB_FAIL before_read committed=%b bad=%b",committed,bad);$fatal;end
  checking=1;
  for(integer b=0;b<32;b++)begin drive();qs=1;beat=5'(b);tick();
   for(integer g=1;g<gap;g++)begin drive();qs=0;tick();end
  end
  drive();qs=0;repeat(12)tick();checking=0;
  if(got!=32)begin err++;$display("QB_MISMATCH output_count=%0d",got);end
  if(err)begin $display("QB_FAIL ALIGN=%0d GAP=%0d got=%0d checks=%0d errors=%0d",ALIGN,gap,got,checks,err);$fatal;end
  $display("QB_PASS ALIGN=%0d LOCAL32=0 GAP=%0d rows=%0d checks=%0d",ALIGN,gap,got,checks);$finish;
 end
endmodule
