`timescale 1ns/1ps
module ot_sram_1r1w_512x256_m1_r2c2(input clk,r_ce_in,input[8:0]r_addr_in,output reg[255:0]rd_out,
 input w_ce_in,input[8:0]w_addr_in,input[255:0]wd_in,w_mask_in,
 input[1:0]rr_en,input[17:0]rr_addr,input[1:0]cr_en,input[15:0]cr_sel);
 reg[255:0]mem[0:511];integer i;
 initial for(i=0;i<512;i=i+1)mem[i]=0;
 always @(posedge clk)begin
  if(r_ce_in)rd_out<=mem[r_addr_in];
  if(w_ce_in)mem[w_addr_in]<=(mem[w_addr_in]&~w_mask_in)|(wd_in&w_mask_in);
 end
endmodule
module tb;
 reg clk=0;always #5 clk=~clk;
 reg rst=0,dv=0,rspv=0,ready=0;wire dr,reqv,sv,idle,fault;
 reg[23:0]lines;reg[9:0]rsptag;reg[1087:0]rspdata;
 wire[31:0]addr;wire[9:0]tag;wire[1087:0]sd;wire[9:0]outstanding;
 ot_hbrom_bulk_copy_protected #(.PROTECT(1))dut(clk,rst,dv,dr,32'd100,lines,
 reqv,1'b1,addr,tag,rspv,rsptag,rspdata,sv,ready,sd,outstanding,idle,fault);
 integer qtag[0:2047],qidx[0:2047];integer wp,rp,got,cycle,phase,total,tmp;
 reg inj,holdoff;reg[1087:0]held;reg heldv;
 function automatic[1087:0]pattern(input integer index);
  integer j;begin for(j=0;j<34;j=j+1)pattern[j*32+:32]=(index*32'h13579b+j*32'h9e3779b9)^32'ha5610123;end
 endfunction
 always @(posedge clk)if(rst)begin
  if(outstanding>512)$fatal(1,"outstanding credit overflow");
  if(reqv)begin qtag[wp]=tag;qidx[wp]=addr-100;wp=wp+1;end
  if(sv&&ready)begin
   if(sd!==pattern(got))$fatal(1,"data/order phase%0d index%0d",phase,got);
   got=got+1;
  end
  if(heldv&&!fault&&(sd!==held||!sv))$fatal(1,"unstable stalled output");
  heldv=sv&&!ready&&!fault;held=sd;
 end
 initial begin
  for(phase=0;phase<3;phase=phase+1)begin
   rst=0;dv=0;rspv=0;ready=0;wp=0;rp=0;got=0;cycle=0;inj=0;heldv=0;
   total=(phase==0)?1100:32;lines=total;
   repeat(3)@(negedge clk);rst=1;dv=1;
   @(negedge clk);dv=0;
   while((phase<2&&got<total)||(phase==2&&!fault))begin
    cycle=cycle+1;
    rspv=0;
    if((phase!=0||cycle>520)&&rp<wp && ((rp%2)==1 || rp+1<wp))begin
     if((rp%2)==0)begin
      tmp=qtag[rp];qtag[rp]=qtag[rp+1];qtag[rp+1]=tmp;
      tmp=qidx[rp];qidx[rp]=qidx[rp+1];qidx[rp+1]=tmp;
     end
     rspv=1;rsptag=qtag[rp];rspdata=pattern(qidx[rp]);rp=rp+1;
    end
    if(phase==0)begin
     if(cycle==520&&wp!=512)$fatal(1,"512outstanding bound not reached %0d",wp);
     ready=cycle>1200&&(cycle%7!=0&&cycle%7!=1);
    end
    else begin
     if(rp==total&&!inj)begin
      // All returns are queued; allow encoding/commit before SRAM fault.
      if(cycle>total+20)begin
       if(phase==1)dut.g_protected.core.g_protected.primary.g_lookahead.g_sram.g_m2.g_grp[0].g_mb[0].u_ring.mem[10][0]=~dut.g_protected.core.g_protected.primary.g_lookahead.g_sram.g_m2.g_grp[0].g_mb[0].u_ring.mem[10][0];
       else begin
        dut.g_protected.core.g_protected.primary.g_lookahead.g_sram.g_m2.g_grp[0].g_mb[0].u_ring.mem[10][1:0]=dut.g_protected.core.g_protected.primary.g_lookahead.g_sram.g_m2.g_grp[0].g_mb[0].u_ring.mem[10][1:0]^2'b11;
       end
       inj=1;ready=1;
      end
     end
    end
    @(negedge clk);
   end
   rspv=0;repeat(5)@(negedge clk);
   if(phase<2&&fault)$fatal(1,"unexpected fault");
   if(phase==2&&(sv||reqv||dr))$fatal(1,"side effect after fault");
   $display("phase%0d PASS got%0d cycles%0d",phase,got,cycle);
  end
  $display("PASS full1024ring512outstanding:1100linewrap,outoforder,stalls,single correction,double failstop");$finish;
 end
endmodule
