`timescale 1ns/1ps
module tb_fifo_independent;
 reg ck=0;always #1 ck=~ck;
 reg wr;reg[2:0]wp=0,rp=0,nrp;reg[289:0]wd;
 wire[289:0]head;
 qkd_host_boot_fifo8_sram #(.W(290),.CACHE(1),.MUT(`MUT))dut(ck,wr,wp,wd,rp,nrp,head);
 reg[289:0]model[0:7];integer mw=0,mr=0,count=0,cyc,pushes=0,pops=0,full=0,empty=0,clears=0,both=0,j;reg pop;
 initial begin
  wr=0;wd=0;nrp=0;
  for(cyc=0;cyc<30000;cyc++)begin
   @(negedge ck);
   if(count!=0&&head!==model[mr])$fatal(1,"FIFO_MISMATCH cycle %0d count %0d",cyc,count);
   if(count==8)full++;if(count==0)empty++;
   // Independent consumer removes the current word; clear masks old memory/cache
   // exactly as the controllers' count reset does. Fill and drain epochs hit capacity.
   if(cyc%997==0)begin count=0;mw=0;mr=0;wp=0;rp=0;clears++;end
   pop=count!=0&&((cyc%128>=16&&cyc%128<32)||(cyc%128>=32&&$urandom%2));
   wr=count<8&&((cyc%128<16)||(cyc%128>=32&&$urandom%2));
   for(j=0;j<290;j+=1)wd[j]=$urandom%2;
   nrp=pop?rp+3'd1:rp;
   if(pop)begin mr=(mr+1)%8;count--;pops++;end
   if(wr)begin model[mw]=wd;mw=(mw+1)%8;count++;pushes++;end
   if(wr&&pop)both++;
   @(posedge ck);#0.01;
   rp=nrp;if(wr)wp=wp+3'd1;
  end
  $display("FIFO_INDEPENDENT_PASS cycles=%0d pushes=%0d pops=%0d full=%0d empty=%0d clear=%0d simultaneous=%0d",cyc,pushes,pops,full,empty,clears,both);$finish;
 end
endmodule
