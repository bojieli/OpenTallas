`timescale 1ps/1fs
// Contiguous quarter sector stream -> eight credit-flowed two-key lines.
// Return SRAM is indexed by (PC,j modulo DEPTH), allowing FR-FCFS reordering.
// Caller reserves DEPTH sector slots/PC before issuing, debits each accepted
// read's padded beats, and returns pop slots. No PHY response may be dropped.
// Behavioural storage is an exactness vehicle; physical banking/protection is pending.
module ot_hbm_index_lines #(parameter ENABLE=0,DEPTH=64,CRED=16)(
 input wire clk,rst_n,start,input wire[8:0] blocks,
 input wire[31:0] sector_v,input wire[383:0] sector_j,input wire[8191:0] sector_data,
 input wire[7:0] credit,
 output reg[8791:0] lines,output reg[63:0] pop,
 output reg done,output reg fault);
 localparam AW=$clog2(DEPTH);
 reg[255:0] mem[0:31][0:DEPTH-1];reg[DEPTH-1:0] valid[0:31];
 reg[5:0] credits[0:7];reg active;reg[10:0] line0,nlines;
 integer p,l,b,g,pc,j,slot,n,need;reg can;reg[31:0] used[0:31];
 reg[1087:0] assembled[0:7];
 always @*begin
  can=active&&!fault;for(p=0;p<32;p=p+1)used[p]=0;
  for(l=0;l<8;l=l+1)begin
   assembled[l]=0;
   if(credits[l]==0)can=0;
   if(line0+l<nlines)begin
    
    for(b=0;b<136;b=b+1)begin
     g=(line0+l)*136+b;pc=(g/32)%32;j=g/1024;slot=j%DEPTH;
     if(!valid[pc][slot])can=0;
     assembled[l][b*8+:8]=mem[pc][slot][(g%32)*8+:8];
    end
   end
  end
 end
 always @(posedge clk or negedge rst_n)begin
  if(!rst_n)begin active<=0;line0<=0;nlines<=0;lines<=0;pop<=0;done<=0;fault<=0;
   for(p=0;p<32;p=p+1)valid[p]<=0;
   for(l=0;l<8;l=l+1)credits[l]<=CRED;
  end else if(ENABLE!=0)begin
   lines<=0;pop<=0;done<=0;
   for(l=0;l<8;l=l+1)begin
    if(credit[l]&&credits[l]==CRED&&!can)fault<=1;
    credits[l]<=credits[l]+6'(credit[l])-6'(can);
   end
   if(start)begin
    if(active||blocks>342)fault<=1;
    else begin active<=blocks!=0;line0<=0;nlines<=11'(blocks)*4;done<=blocks==0;
     for(p=0;p<32;p=p+1)valid[p]<=0;
    end
   end
   for(p=0;p<32;p=p+1)if(sector_v[p])begin
    j=sector_j[p*12+:12];slot=j%DEPTH;
    // Padded final read beats are not part of the logical frame.
    if(!active)fault<=1;
    else if(j*32+p<((nlines*136+31)/32))begin
     if(valid[p][slot]||j*1024+p*32<line0*136)fault<=1;
     else begin valid[p][slot]<=1;mem[p][slot]<=sector_data[p*256+:256];end
    end
   end
   if(can)begin
    for(l=0;l<8;l=l+1)lines[l*1099+:1099]<={assembled[l],10'(line0+l),1'b1};
    // A boundary sector shared with the next group stays resident.
    for(p=0;p<32;p=p+1)begin
     n=0;
     for(j=0;j<DEPTH;j=j+1)begin
      slot=((line0*136)/1024+j)%DEPTH;
      g=(((line0*136)/1024+j)*32+p)*32;
      if(g>=((line0*136)/32)*32&&g+32<=((line0+8<nlines)?(line0+8)*136:nlines*136))begin valid[p][slot]<=0;n=n+1;end
     end
     pop[p*2+:2]<=2'(n);
    end
    if(line0+8>=nlines)begin active<=0;done<=1;end
    else line0<=line0+8;
   end
  end
 end
endmodule
