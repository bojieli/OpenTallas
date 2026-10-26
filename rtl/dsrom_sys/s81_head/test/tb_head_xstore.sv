`timescale 1ns/1ps
module tb_head_xstore;
 wire [7:0] load_index=8'd0;
 parameter integer MUT=0;
 reg ck=0;always #5 ck=~ck;
 reg rst_n=0,load_begin=0,load_v=0,issue=0;
 reg[511:0]load_d; wire go,xv,busy,done,fault;wire[255:0]xa,xb;
 ot_s81hd_xstore_replay #(.MUT_B_ADDR(MUT)) d(.*);
 reg[255:0] native_x[0:319];
 string xa_path,xb_path;
 initial begin
  if(!$value$plusargs("XA=%s",xa_path)||!$value$plusargs("XB=%s",xb_path))$fatal(1,"real head vectors required");
  $readmemh(xa_path,native_x,0,255);$readmemh(xb_path,native_x,256,319);
 end
 function automatic[255:0]word(input integer n);word=native_x[n];endfunction
 integer seen=0,cyc=0,g=-1,poses=0;
 always @(posedge ck)begin
  #1;cyc=cyc+1;
  if(go)begin g=cyc;seen=0;end
  if(xv)begin
   if(cyc!=g+5+seen)$fatal(1,"stream edge %0d expected%0d",cyc,g+5+seen);
   if(xa!==word(seen%256) || xb!==word(256+seen%64))$fatal(1,"actual source stream mismatch m=%0d",seen);
   seen=seen+1;
  end
  if(done)begin if(seen!=8269)$fatal(1,"length%0d",seen);poses=poses+1;end
 end
 task tick;@(negedge ck);endtask
 initial begin
  repeat(3)tick();rst_n=1;
  // A premature real command raises fault and never fabricates go.
  issue=1;tick();issue=0;tick();if(!fault||busy||go)$fatal(1,"early issue accepted");
  rst_n=0;tick();rst_n=1;load_begin=1;tick();load_begin=0;
  for(integer i=0;i<160;i++)begin load_v=1;load_d={word(2*i+1),word(2*i)};tick();end
  load_v=0;
  repeat(2)begin
   tick();issue=1;tick();issue=0;
   wait(done);tick();if(fault)$fatal(1,"fault on scheduled command");
  end
  if(poses!=2)$fatal(1,"missing position");
  $display("PASS head xstore 160 packed words,2 positions,16538 exact stream pairs,G+5,early rejection");$finish;
 end
 initial begin #200000;$fatal(1,"timeout");end
endmodule
