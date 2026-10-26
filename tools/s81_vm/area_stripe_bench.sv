`timescale 1ns/1ps
module tb #(parameter BASE=0);
 reg ck=0;always #5 ck=~ck;
 reg rst=0;reg [52:0] v=0;reg [741:0] row=0;reg [105:0] lane=0;
 reg [211:0] mask=0;reg [423:0] tag=0;reg [6783:0] data=0;
 reg [7:0] dv=0;reg [15:0] ds=0;
 wire [7:0] ov;wire [111:0] ore;wire [31:0] om;wire [63:0] ot;wire [1023:0] od;wire fault;
 s81_area_quarter #(.BASE(BASE)) dut(ck,ck,{8{ck}},rst,v,row,lane,mask,tag,data,dv,ds,ov,ore,om,ot,od,fault);
 reg [7:0] ev[0:511];reg [111:0] er[0:511];reg [31:0] em[0:511];
 reg [63:0] et[0:511];reg [1023:0] ed[0:511];
 reg [7:0] drainv[0:511];reg [15:0] drains[0:511];
 wire [23:0] cv;wire [47:0] cs;wire [335:0] cr;wire [95:0] cm;
 wire [3071:0] cd;wire [191:0] ct;wire df;
 reg [7:0] olddv=0;reg [15:0] oldds=0;
 wire [7:0] oldov,sf;wire [111:0] oldrow;wire [31:0] oldmask;
 wire [1023:0] olddata;wire [63:0] oldtag;
 dsfd_vm_static_wdispatch128 #(.NSRC(53),.NBANK(8),.BANK_BASE(BASE)) olddispatch(
 ck,rst,v,row,mask,data,tag,lane,lane,cv,cs,cr,cm,cd,ct,df);
 genvar ob;
 generate for(ob=0;ob<8;ob=ob+1)begin:oldbank
  wire sv;wire [13:0] sr;wire [3:0] sm;wire [127:0] sd;wire [7:0] st;wire unused_we;
  dsfd_vm_static_wstage128 oldstore(ck,rst,cv[3*ob+:3],cs[6*ob+:6],cr[42*ob+:42],
  cm[12*ob+:12],cd[384*ob+:384],ct[24*ob+:24],olddv[ob],oldds[2*ob+:2],sv,sr,sm,sd,st,sf[ob]);
  dsfd_vm_static_write_capture128 oldcapture(ck,rst,sv,sv,sr,sm,sd,st,
  oldov[ob],unused_we,oldrow[14*ob+:14],oldmask[4*ob+:4],olddata[128*ob+:128],oldtag[8*ob+:8]);
 end endgenerate
 integer cycle,s,b,l,t,n,mode,checked=0,active=0;reg [13:0] r;reg [127:0] word;
 task tick;begin @(posedge ck);#1;end endtask
 initial begin
  mode=0;if($value$plusargs("mode=%d",mode))begin end
  for(t=0;t<512;t=t+1)begin ev[t]=0;er[t]=0;em[t]=0;et[t]=0;ed[t]=0;drainv[t]=0;drains[t]=0;end
  repeat(4)tick();@(negedge ck);rst=1;repeat(3)tick();
  // Full source domain rotates through all53 inputs, including highest port52.
  // Sparse bursts reserve all24 slots, then drain each bank in lane order.
  for(cycle=0;cycle<220;cycle=cycle+1)begin
   @(negedge ck);v=0;row=0;mask=0;tag=0;data=0;lane=0;
   if(cycle<180 && (cycle%9==0 ||mode==4))begin
    for(n=0;n<(mode==4?8:24);n=n+1)begin
     s=(n+cycle)%53;b=mode==4?n:n/3;l=mode==4?0:n%3;
     r=((cycle/9)%16)*32+b; // row[7:5] changes hash; cancel it below.
     r[4:0]=(b+BASE)^{r[7:5],2'b00};
     word={32'(s),32'(cycle),32'(n),32'hcafe0000+32'(s)};
     v[s]=1;row[14*s+:14]=r;lane[2*s+:2]=l;
     mask[4*s+:4]=(s%15)+1;tag[8*s+:8]=cycle+s;data[128*s+:128]=word;
     t=cycle+5+l;
     ev[t][b]=1;er[t][14*b+:14]=r;em[t][4*b+:4]=(s%15)+1;
     et[t][8*b+:8]=cycle+s;ed[t][128*b+:128]=word;
     drainv[cycle+4+l][b]=1;drains[cycle+4+l][2*b+:2]=l;
     active=active+1;
    end
   end
   // Separate fail-closed checks: duplicate lane, invalid lane, empty drain.
   if(cycle==200 && mode==1)begin v[1:0]=3;row[13:0]=BASE;row[27:14]=BASE;lane[3:0]=0;end
   if(cycle==200 && mode==2)begin v[0]=1;row[13:0]=BASE;lane[1:0]=3;end
   dv=drainv[cycle];ds=drains[cycle];
   olddv=drainv[cycle+1];oldds=drains[cycle+1];
   if(cycle==200 && mode==3)begin dv[0]=1;ds[1:0]=2;end
   tick();
   if(mode==0 ||mode==4 ||cycle<200)begin
    if(oldov!==ev[cycle+2])$fatal(1,"old valid cycle%0d got%h expected%h",cycle,oldov,ev[cycle+2]);
    for(b=0;b<8;b=b+1)if(ev[cycle+2][b])begin
     if(oldrow[14*b+:14]!==er[cycle+2][14*b+:14] ||oldmask[4*b+:4]!==em[cycle+2][4*b+:4] ||
        oldtag[8*b+:8]!==et[cycle+2][8*b+:8] ||olddata[128*b+:128]!==ed[cycle+2][128*b+:128])
      $fatal(1,"old payload cycle%0d bank%0d",cycle,b);
    end
    if(df ||(|sf))$fatal(1,"old unexpected fault cycle%0d",cycle);
    if(ov!==ev[cycle])$fatal(1,"valid cycle%0d got%h expected%h",cycle,ov,ev[cycle]);
    for(b=0;b<8;b=b+1)if(ev[cycle][b])begin
     if(ore[14*b+:14]!==er[cycle][14*b+:14] ||om[4*b+:4]!==em[cycle][4*b+:4] ||
        ot[8*b+:8]!==et[cycle][8*b+:8] ||od[128*b+:128]!==ed[cycle][128*b+:128])
      $fatal(1,"payload cycle%0d bank%0d",cycle,b);
     checked=checked+1;
    end
    if(fault)$fatal(1,"unexpected fault cycle%0d",cycle);
   end
  end
  if(mode>=1 && mode<=3 && !fault)$fatal(1,"missing fault mode%0d",mode);
  if(checked!=active)$fatal(1,"lost records %0d/%0d",checked,active);
  @(negedge ck);rst=0;#1;if(fault ||ov)$fatal(1,"reset fails to clear fault/valid");
  $display("PASS full53sources banks8 slots3 records%0d mode%0d BASE%0d first_age5 II1_ports_preserved",checked,mode,BASE);$finish;
 end
endmodule
