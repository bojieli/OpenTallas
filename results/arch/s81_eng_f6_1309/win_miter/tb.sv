`timescale 1ns/1ps
module tb;
reg ck=0,rn=0,v=0,en=0;always #1 ck=~ck;
reg[9:0]user=0;reg[20:0]tok=0,pos=0;
reg vd=0,ed=0;reg[9:0]ud=0;reg[20:0]td=0,pd=0;
always@(posedge ck or negedge rn)if(!rn)vd<=0;else vd<=v;
always@(posedge ck)begin ed<=en;ud<=user;td<=tok;pd<=pos;end
wire wv0,wv1,f0,f1;wire[2:0]slot0,slot1;wire[67:0]ids0,ids1;
ot_s81eng_win_n32_ref refm(ck,rn,2'b11,ed,vd,ud,td,pd,wv0,slot0,ids0,f0);
ot_s81eng_win_n32 dut(ck,rn,2'b11,en,v,user,tok,pos,wv1,slot1,ids1,f1);
for(genvar bank=0;bank<8;bank=bank+1)begin:gm
 initial begin
  #0.1;
  for(integer row=0;row<512;row=row+1)for(integer sub=0;sub<8;sub=sub+1)for(integer w=0;w<4;w=w+1)begin
   for(integer bitn=0;bitn<17;bitn=bitn+1)begin
    dut.u_map.m[bank].rom.arr[row][8*(17*w+bitn)+sub]=(((row*8+sub)*17+bank*127+w*1027)&65535)>>bitn&1;
    refm.u_map.m[bank].rom.arr[row][8*(17*w+bitn)+sub]=(((row*8+sub)*17+bank*127+w*1027)&65535)>>bitn&1;
   end
  end
 end
end
integer cyc=0,seed=1,mis=0,nv=0,hit=0;
initial begin if($value$plusargs("seed=%d",seed))begin end repeat(8)@(negedge ck);rn=1;
 for(cyc=0;cyc<40000;cyc=cyc+1)begin
  @(negedge ck);
  if(cyc>5)begin
   if({wv0,slot0,ids0,f0}!=={wv1,slot1,ids1,f1})begin mis=mis+1;if(mis<5)$display("WIN_DIFF cyc%0d v%b/%b slot%h/%h ids%h/%h f%b/%b",cyc,wv0,wv1,slot0,slot1,ids0,ids1,f0,f1);end
   if(wv1)nv=nv+1;if(dut.h_hit)hit=hit+1;
  end
  rn=(cyc%8192>5);v=($random(seed)&7)!=0;en=($random(seed)&7)!=0;
  user=$random(seed)&3;tok=$random(seed)&131071;pos=$random(seed)&1023;
 end
 $display("WIN_MITER %s mis=%0d valid=%0d forward=%0d",(mis==0&&nv>100&&hit>10)?"PASS":"FAIL",mis,nv,hit);$finish;
end
endmodule
