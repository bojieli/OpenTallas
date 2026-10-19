`ifndef SYNTHESIS
`timescale 1ns/1ps
module tb;
 parameter integer MUT=0;
 reg wc=0,rc=0;always #5 wc=~wc;
 integer phase=0;
 initial begin if(!$value$plusargs("PHASE=%d",phase))phase=0; #(5+phase);rc=1;forever #5 rc=~rc;end
 reg rst=0,wrst=0;reg[257:0]i=0;
 wire[1031:0]b;wire[43:0]v;wire[257:0]o;
 qfd_c_land_safe_w #(.W(258))w(wc,MUT?wrst:rst,i,b,v);
 qfd_c_land_safe_r #(.W(258))r(rc,rst,b,v,o);
 always@(posedge wc)wrst<=rst;
 integer cycle=0,j,write_epoch=0,read_epoch=0,errors=0,checks=0,slot;
 integer tags[0:3];reg written[0:3];real stamps[0:3];real age;
 reg[257:0]words[0:3],expected;
 always@(negedge wc)begin
  cycle=cycle+1;rst=(cycle>=12&&!(cycle>=300&&cycle<320)&&!(cycle>=650&&cycle<670));
  for(j=0;j<258;j=j+1)i[j]=$random;
 end
 always@(posedge wc)begin
  if(!w.g_slice[0].u.r2)begin write_epoch=0;for(j=0;j<4;j=j+1)written[j]=0;end
  else begin
   slot=write_epoch%4;tags[slot]=write_epoch;written[slot]=1;stamps[slot]=$realtime;words[slot]=i;write_epoch=write_epoch+1;
  end
 end
 integer rs;reg active;
 always@(posedge rc)begin
  rs=(read_epoch+2)%4;active=r.g_slice[0].u.warm&&v[rs];expected=active?words[rs]:0;
  if(active)begin
   checks=checks+1;age=($realtime-stamps[rs])/10.0;
   if(!written[rs]||tags[rs]!=(read_epoch-2)||age<1.599||age>2.401)begin
    errors=errors+1;if(errors<5)$display("EPOCH_BAD phase%0d mut%0d rc%0d slot%0d tag%0d age%0f",phase,MUT,read_epoch,rs,tags[rs],age);
   end
  end
  if(!r.g_slice[0].u.r2)read_epoch=0;else read_epoch=read_epoch+1;
  #0.1;
  if(o!==expected)begin errors=errors+1;if(errors<5)$display("EPOCH_DATA_BAD cycle%0d",cycle);end
  if(cycle>=1000)begin
   if(errors)$fatal(1,"SAFE_EPOCH_FAIL MUT%0d PHASE%0d errors%0d checks%0d",MUT,phase,errors,checks);
   $display("SAFE_EPOCH_PASS MUT%0d PHASE%0d checks%0d",MUT,phase,checks);$finish;
  end
 end
endmodule
`endif
