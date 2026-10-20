`timescale 1ns/1ps
module tb_guard_fifo_sram;
 reg ck=0,rst_n=0,push=0,pop=0;
 reg[63:0]din=0;always #5 ck=~ck;
 wire valid,rv,overflow,ro,underflow,ru;
 wire[63:0]dout,rd;wire[7:0]count,rc;
 wire lv,lrv,lo,lro,lu,lru;wire[7:0]ld,lrd,lc,lrc;
 qkd_host_guard_fifo #(.W(64),.SRAM_FIFO(1)) dut(
 .ck(ck),.rst_n(rst_n),.push(push),.din(din),.pop(pop),
 .valid(valid),.dout(dout),.count(count),.overflow(overflow),.underflow(underflow));
 qkd_host_guard_fifo_ref #(.W(64)) ref_fifo(
 .ck(ck),.rst_n(rst_n),.push(push),.din(din),.pop(pop),
 .valid(rv),.dout(rd),.count(rc),.overflow(ro),.underflow(ru));
 // W8 remains the original 1024-bit implementation even with global opt-in.
 qkd_host_guard_fifo #(.W(8),.SRAM_FIFO(1)) legacy(
 .ck(ck),.rst_n(rst_n),.push(push),.din(din[7:0]),.pop(pop),
 .valid(lv),.dout(ld),.count(lc),.overflow(lo),.underflow(lu));
 qkd_host_guard_fifo_ref #(.W(8)) legacy_ref(
 .ck(ck),.rst_n(rst_n),.push(push),.din(din[7:0]),.pop(pop),
 .valid(lrv),.dout(lrd),.count(lrc),.overflow(lro),.underflow(lru));
 reg[63:0]queue[0:127];integer qw=0,qr=0,qn=0;
 integer cycles=0,accepted=0,retired=0,fulls=0,empties=0,simultaneous=0;
 integer full_simultaneous=0,resets=0,overflows=0,underflows=0;
 reg[63:0]rng=64'h6584d2e30a91bc7f;
 task check;
 begin
 if({valid,count,overflow,underflow}!=={rv,rc,ro,ru})
   $fatal(1,"cycle %0d control got %b/%d/%b/%b ref %b/%d/%b/%b",cycles,valid,count,overflow,underflow,rv,rc,ro,ru);
 if(valid && dout!==rd)$fatal(1,"cycle %0d data got %h ref %h",cycles,dout,rd);
 if({lv,lc,lo,lu}!=={lrv,lrc,lro,lru} || (lv && ld!==lrd))
   $fatal(1,"W8 legacy changed cycle %0d",cycles);
 end endtask
 task tick(input reg ipush,input reg ipop,input reg reset);
 reg take,put;
 begin
 @(negedge ck);
 rng=rng^(rng<<13);rng=rng^(rng>>7);rng=rng^(rng<<17);
 push=ipush;pop=ipop;din=rng;rst_n=!reset;
 #1;check();
 take=pop&&rv;put=push&&(rc<128||take);
 if(reset)begin qw=0;qr=0;qn=0;resets=resets+1;end
 else begin
   if(rc==128)fulls=fulls+1;
   if(rc==0)empties=empties+1;
   if(ro)overflows=overflows+1;
   if(ru)underflows=underflows+1;
   if(take && put)begin simultaneous=simultaneous+1;
      if(rc==128)full_simultaneous=full_simultaneous+1;end
   if(take)begin
      if(qn==0 || rd!==queue[qr])$fatal(1,"independent queue mismatch cycle %0d",cycles);
      qr=(qr+1)%128;qn=qn-1;retired=retired+1;
   end
   if(put)begin queue[qw]=din;qw=(qw+1)%128;qn=qn+1;accepted=accepted+1;end
 end
 @(posedge ck);#1;cycles=cycles+1;check();
 if(count!==qn)$fatal(1,"count mismatch cycle %0d got %0d expected %0d",cycles,count,qn);
 end endtask
 integer i;
 initial begin
 tick(0,0,1);tick(0,0,0);
 // Fill every entry, reject overflow, replace at full, drain and underflow.
 for(i=0;i<140;i=i+1)tick(1,0,0);
 for(i=0;i<512;i=i+1)tick(1,1,0);
 for(i=0;i<150;i=i+1)tick(0,1,0);
 // Warm resets interrupt both storage occupancy and every prefetch stage.
 for(i=0;i<20;i=i+1)begin
   tick(1,0,0);tick(1,1,0);tick(1,0,0);tick(1,1,0);
   tick(0,0,1);tick(0,1,0);
 end
 while(cycles<100000)begin
   if(cycles%997==0)tick(0,0,1);
   else if(cycles%2048<192)tick(1,0,0);
   else if(cycles%2048<384)tick(0,1,0);
   else tick(rng[0]||rng[2],rng[1]||rng[3],0);
 end
 for(i=0;i<140;i=i+1)tick(0,1,0);
 if(accepted<10000||retired<10000||fulls==0||empties==0||simultaneous==0||full_simultaneous==0||resets<100||overflows==0||underflows==0)
   $fatal(1,"coverage missing");
 $display("PASS cycles=%0d accepted=%0d retired=%0d full=%0d empty=%0d simultaneous=%0d full_simultaneous=%0d resets=%0d overflow=%0d underflow=%0d zero_added_edges=1",cycles,accepted,retired,fulls,empties,simultaneous,full_simultaneous,resets,overflows,underflows);
 $finish;
 end
endmodule
