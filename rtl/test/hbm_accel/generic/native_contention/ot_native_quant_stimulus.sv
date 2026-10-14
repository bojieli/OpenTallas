`timescale 1ps/1fs
// Bench-only producer stimulus and independent immutable quant oracle.
// Arithmetic is performed by the real qpin4 endpoint in the owned parent.
module ot_native_quant_stimulus(input wire clk,rst_n,go,
 output reg [4*683-1:0] rec=0,input wire [11:0] ret,
 output reg done=0,output integer cycles=0,output integer checked=0);
 reg [255:0] gin[0:7][0:127],gout[0:7][0:127];
 integer op[0:7],n[0:7],ab[0:7],ob[0:7],cost[0:7],blk[0:7];
 integer nret[0:3],cyc=0,t0=0,price=0,fd,nrec,scan;string dir,fn;
 reg loaded=0,started=0;reg [127:0] h;reg [255:0] da,dd;
 function automatic [255:0] desc(input integer base,nn);
  reg [255:0] d;begin d=0;d[1:0]=1;d[47:8]=40'(base);d[67:48]=20'(nn);d[87:68]=1;desc=d;end
 endfunction
 function automatic [255:0] preload_sector(input integer sec,input [255:0] fallback);
  begin preload_sector=fallback;for(integer k=0;k<8;k++)if(sec>=ab[k]/8&&sec<ab[k]/8+n[k]/8)preload_sector=gin[k][sec-ab[k]/8];end
 endfunction
 function automatic [31:0] expected_word(input integer wordidx,input [31:0] fallback);
  integer sec,w;begin sec=wordidx/8;w=wordidx%8;expected_word=fallback;
   for(integer k=0;k<8;k++)begin
    if(sec>=ab[k]/8&&sec<ab[k]/8+n[k]/8)expected_word=gin[k][sec-ab[k]/8][w*32+:32];
    if(sec>=ob[k]/8&&sec<ob[k]/8+n[k]/8)expected_word=gout[k][sec-ob[k]/8][w*32+:32];
   end
  end
 endfunction
 task automatic check_sector(input integer q,sec,input [255:0] data);
  begin for(integer k=0;k<8;k++)if(sec>=ob[k]/8&&sec<ob[k]/8+n[k]/8)begin
   if(data!==gout[k][sec-ob[k]/8])$fatal(1,"THREEPRODUCER quant golden mismatch q%0d rec%0d sector%0d",q,k,sec);
   checked=checked+8;
  end end
 endtask
 always @(posedge clk)cyc<=cyc+1;
 always @(negedge clk)if(started&&rst_n)for(integer q=0;q<4;q++)begin
  if(ret[q*3+2])$fatal(1,"THREEPRODUCER quant fault q%0d",q);
  if(ret[q*3+1])begin nret[q]++;cycles=cyc-t0;end
 end
 initial begin
  for(integer q=0;q<4;q++)nret[q]=0;
  if(!$value$plusargs("QDIR=%s",dir))$fatal(1,"THREEPRODUCER missing +QDIR");
  fd=$fopen({dir,"/recs.txt"},"r");if(!fd)$fatal(1,"THREEPRODUCER missing quant immutable vectors");
  scan=$fscanf(fd,"%d",nrec);if(scan!=1||nrec!=8)$fatal(1,"THREEPRODUCER quant record count");
  for(integer k=0;k<8;k++)begin
   scan=$fscanf(fd,"%d %d %d %d %d %d",op[k],n[k],ab[k],ob[k],cost[k],blk[k]);
   if(scan!=6||n[k]<=0||n[k]>1024)$fatal(1,"THREEPRODUCER malformed quant record");
   ab[k]=ab[k]%65536;ob[k]=ob[k]%65536;price+=cost[k];
   fn=$sformatf("%s/in_%0d.hex",dir,k);$readmemh(fn,gin[k],0,n[k]/8-1);
   fn=$sformatf("%s/out_%0d.hex",dir,k);$readmemh(fn,gout[k],0,n[k]/8-1);
  end
  $fclose(fd);if(price!=168)$fatal(1,"THREEPRODUCER quant immutable price changed");loaded=1;
  wait(rst_n&&go);@(negedge clk);t0=cyc;started=1;
  for(integer k=0;k<8;k++)begin
   while(!(ret[0]&&ret[3]&&ret[6]&&ret[9]))@(negedge clk);
   h=0;h[127:124]=4;h[123:118]=6'(op[k]);h[99:93]=7'b0010001;if(op[k]==6)h[71:64]=16;
   da=desc(ab[k],n[k]);dd=desc(ob[k],n[k]);
   for(integer q=0;q<4;q++)rec[q*683+:683]={21'(n[k]),21'(n[k]),dd,da,h,1'b1};
   @(negedge clk);for(integer q=0;q<4;q++)rec[q*683]=0;
  end
  while(nret[0]!=8||nret[1]!=8||nret[2]!=8||nret[3]!=8)begin @(negedge clk);if(cyc-t0>200000)$fatal(1,"THREEPRODUCER quant retirement timeout");end
  done=1;$display("THREEPRODUCER_QUANT_RETIRE records32 cycles%0d immutable_price168 ratio%0.9f",cycles,cycles/168.0);
 end
endmodule
