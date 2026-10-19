`timescale 1ns/1ps
module tb;
 reg wc=0,rc=0,wrst=1,rrst=1,we=1,re=1;
 reg [3:0] k=0;reg [452:0] din=0;
 wire [452:0] so;wire [9:0] fo;wire sv,sf,fv,ff;
 qfd_d8_mechanism #(.W(10),.ENABLE(1)) f(wc,rc,wrst,rrst,we,re,k[0],k[1],k[2],k[3],din[9:0],fo,fv,ff);
 qfd_d8_mechanism #(.W(453),.SRAM(1),.ENABLE(1)) s(wc,rc,wrst,rrst,we,re,k[0],k[1],k[2],k[3],din,so,sv,sf);
 // Arbitrary complete payload memories and returned macro registers; no DUT memory init.
 initial for(integer i=0;i<8;i++) f.ff.rows[i]={$urandom,$urandom};
 for(genvar b=0;b<8;b++)begin
  initial begin
   for(integer i=0;i<32;i++)s.sram.banks[b].mem.arr[i]={$urandom,$urandom};
   s.sram.banks[b].mem.rd_out={$urandom,$urandom};
  end
 end
 integer ws=0,rs=0,wa=0,ra=0,warm=0,checks=0,accepted=0,rejects=0;
 integer stamp[0:7];reg [452:0] history[0:7];
 reg pending=0;reg [452:0] pendingdata=0;reg pendingvalid=0;
 reg lastsv=0;reg [452:0] lastso=0;
 reg [452:0] consumed=0;reg consumedvalid=0;
 always @(posedge rc)begin consumed<=so;consumedvalid<=sv;end
 task reset_all;
 begin
  wrst=1;rrst=1;#2;
  if(fv||sv||fo!=0||so!=0)$fatal(1,"ASYNC_RESET");
  ws=0;rs=0;wa=0;ra=0;warm=0;pending=0;pendingvalid=0;pendingdata=0;lastsv=0;lastso=0;
  for(integer i=0;i<8;i++)stamp[i]=-100000;
  wrst=0;rrst=0;#2;
 end endtask
 task wstep;
 begin
  #2;
  for(integer b=0;b<453;b++)din[b]=((wa*37+b*13+(wa>>(b%7)))%11)<5;
  if(ws>=2 && we)begin stamp[wa%8]=wa;history[wa%8]=din;wa=wa+1;end
  wc=1;#1;wc=0;ws=ws+1;
 end endtask
 task rstep;
 integer target,slot;reg ok;reg [452:0] data;reg allwritten;
 begin
  #3;
  if(rs<2)begin ok=0;data=0;end
  else begin
   target=ra-k;slot=((target%8)+8)%8;allwritten=1;
   for(integer i=0;i<8;i++)if(stamp[i]<0)allwritten=0;
   ok=re && allwritten && warm>=((k==0)?16:k) && ((stamp[slot]&15)==(target&15));
   data=ok?history[slot]:0;
   // Absolute identity is distinct from four-bit equality; stale alias is rejected as a lifecycle violation.
   if(ok && stamp[slot]!=target)begin rejects++;$display("LIFECYCLE_REJECT target=%0d actual=%0d K=%0d",target,stamp[slot],k);end
  end
  rc=1;#1;
  checks++;
  if(consumedvalid!==lastsv || (lastsv && consumed!==lastso))$fatal(1,"CONSUMER_NBA");
  if(fv!==ok || (ok && fo!==data[9:0]))$fatal(1,"FF_IDENTITY K=%0d R=%0d",k,ra);
  if(sv!==(pending && pendingvalid) || (sv && so!==pendingdata))$fatal(1,"SRAM_IDENTITY K=%0d R=%0d",k,ra);
  if(ok)accepted++;
  lastsv=sv;lastso=so;
  if(rs>=2)begin pending=re;pendingvalid=ok;pendingdata=data;if(re)begin ra++;if(warm<16)warm++;end end
  else begin pending=0;pendingvalid=0;end
  rc=0;rs++;
 end endtask
 initial begin
  for(integer phase=0;phase<3;phase++)begin
   for(integer kk=0;kk<16;kk++)begin
    k=kk;reset_all();
    // Both orderings retain native posedge publication and preedge read semantics.
    for(integer n=0;n<96;n++)begin
     if(phase==1)begin rstep();wstep();end else begin wstep();#(phase);rstep();end
     if(n==40)begin // stop receiver while producer advances, then invalidate before restart
      for(integer j=0;j<21;j++)wstep();reset_all();
     end
     if(n==65)begin // pending read invalidation while both clocks stop
      wrst=1;#3;if(sv||fv)$fatal(1,"PENDING_RESET");reset_all();
     end
     if(n==80)begin // stop producer; reads are allowed to reject, then a joint cold epoch
      we=0;for(integer j=0;j<5;j++)rstep();we=1;reset_all();
     end
    end
   end
  end
  if(accepted<100)$fatal(1,"HOLLOW");
  $display("PASS fullW10 fullW453 K0..15 phases3 checks=%0d accepted=%0d lifecycle_rejects=%0d",checks,accepted,rejects);
  $finish;
 end
endmodule
