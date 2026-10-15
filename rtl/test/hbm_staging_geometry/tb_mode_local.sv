`timescale 1ns/1ps
module tb_mode_local;
 parameter integer MUT=0;
 reg clk=0;always #0.4165 clk=~clk;
 reg rst_n=0,ms=0,pv=0,re=0;reg[1:0]we=0,rm=3;reg[8:0]wa=0,ra=0;reg[8479:0]data=0;
 wire[8479:0]oldq,newq;wire[8191:0]codes;wire[287:0]meta;wire rp,fault;
 reg[4239:0]gold[0:1][0:319];reg[8479:0]expected;reg[31:0]rng=32'hbe4f8319;
 integer cycles=0,bitchecks=0,elemchecks=0;
 ot_hdc_v41x_attn_staging #(.D(512),.NL(2),.TROWS(640),.SRAM_MACRO(1)) baseline(.clk(clk),.wr_en(we),.wr_addr(wa),.wr_data(data),.rd_addr(ra),.rd_data(oldq));
 ot_hbm_attn_staging_mode_local #(.MUT(MUT)) dut(.clk(clk),.rst_n(rst_n),.mode_set(ms),.job_pv(pv),.wr_en(we),.wr_addr(wa),.wr_data(data),.rd_en(re),.rd_mask(rm),.rd_addr(ra),.rd_data(newq),.local_codes(codes),.local_metadata(meta),.rd_pv(rp),.fault(fault));
 function automatic[17:0]elem(input[264:0]g,input integer x);
 begin if(g[264])elem={1'b0,1'b1,4'b0,g[4*x+:4],g[128+8*(x/16)+:8]};
 else elem={1'b0,1'b0,g[8*x+:8],g[263:256]};end endfunction
 function automatic[17:0]local_elem(input[127:0]h,input[8:0]m,input integer x);
 begin if(m[8])local_elem={1'b0,1'b1,4'b0,h[4*x+:4],h[71:64]};
 else local_elem={1'b0,1'b0,h[8*x+:8],m[7:0]};end endfunction
 task tick(input[1:0]w,input integer a,input integer r,input ren);
 reg[264:0]g;reg[127:0]h;reg[8:0]m;
 begin
  @(negedge clk);we=w;wa=9'(a);ra=9'(r);re=ren;
  for(integer k=0;k<265;k=k+1)begin rng=rng^(rng<<13);rng=rng^(rng>>17);rng=rng^(rng<<5);data[k*32+:32]=rng;end
  expected={gold[1][r],gold[0][r]};
  @(posedge clk);#0.001;
  if(ren)begin
   if(oldq!==expected)$fatal(1,"baseline mismatch cycle%0d",cycles);
   if(newq!==expected)$fatal(1,"mode raw scoreboard mismatch cycle%0d MUT%0d pv%0d",cycles,MUT,pv);
   if(rp!==pv)$fatal(1,"mode phase misaligned");
   bitchecks=bitchecks+8480;
   if(pv)for(integer t=0;t<32;t=t+1)for(integer l=0;l<2;l=l+1)begin
    g=expected[l*4240+(t/2)*265+:265];h=codes[t*256+l*128+:128];m=meta[l*144+(t/2)*9+:9];
    for(integer x=0;x<16;x=x+1)begin
     if(elem(g,(t%2)*16+x)!==local_elem(h,m,x))$fatal(1,"PV local decode mismatch tile%0d lane%0d dim%0d",t,l,x);
     elemchecks=elemchecks+1;
    end
   end
  end
  for(integer l=0;l<2;l=l+1)if(w[l])gold[l][a]=data[l*4240+:4240];
  if(fault)$fatal(1,"unexpected guardfault cycle%0d",cycles);
  cycles=cycles+1;
 end endtask
 task setmode(input v);
 begin @(negedge clk);ms=1;pv=v;we=0;re=0;@(posedge clk);#0.001;@(negedge clk);ms=0;end endtask
 task resetguard;
 begin @(negedge clk);rst_n=0;we=0;re=0;ms=0;@(posedge clk);#0.001;@(negedge clk);rst_n=1;end endtask
 initial begin
  for(integer l=0;l<2;l=l+1)for(integer a=0;a<320;a=a+1)gold[l][a]=0;
  resetguard();
  for(integer job=0;job<4;job=job+1)begin
   setmode(job%2);
   for(integer a=0;a<320;a=a+1)tick(3,a,0,0);
   for(integer a=319;a>=0;a=a-1)tick(0,0,a,1);
   for(integer a=0;a<320;a=a+1)tick(a%2?1:2,a,a,1);
   for(integer a=0;a<320;a=a+1)tick(0,0,a,1);
  end
  // Exact residency guard: mode change must not silently reinterpret old K/V.
  setmode(!pv);@(negedge clk);re=1;ra=0;we=0;@(posedge clk);#0.001;
  if(!fault)$fatal(1,"missing stale-mode residency fault");
  @(negedge clk);re=0;@(posedge clk);#0.001;if(!fault)$fatal(1,"fault notsticky");
  resetguard();@(negedge clk);ms=1;we=1;@(posedge clk);#0.001;if(!fault)$fatal(1,"missing mode/write fault");
  resetguard();@(negedge clk);we=1;wa=320;@(posedge clk);#0.001;if(!fault)$fatal(1,"missing rangefault");
  $display("PASS mode actual34SRAM baseline+flat cycles=%0d bitchecks=%0d local_elemchecks=%0d guards=3 MUT=%0d",cycles,bitchecks,elemchecks,MUT);$finish;
 end
endmodule
