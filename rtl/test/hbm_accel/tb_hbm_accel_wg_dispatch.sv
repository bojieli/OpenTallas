`timescale 1ps/1fs
module tb_hbm_accel_wg_dispatch;
 reg clk=0,rst_n=0;always #5 clk=~clk;
 reg tv=0;reg [53:0] ids;wire tr,v,busy,fault,keep,last;
 wire [2:0] k;wire [5:0] j,n;reg ready=0;
 ot_hbm_accel_wg_dispatch #(.ENABLE(1)) dut (.clk(clk),.rst_n(rst_n),.task_valid(tv),.ids(ids),.task_ready(tr),
 .desc_valid(v),.desc_ready(ready),.desc_slot(k),.desc_j0(j),.desc_n(n),.desc_keep(keep),.desc_last(last),.busy(busy),.fault(fault));
 integer f,rc,ek,ej,en,e_keep,patterns,seen=0,cycles=0;
 reg [53:0] expids;string path;integer mut=0;
 always @(negedge clk) begin cycles=cycles+1;ready=(cycles%5!=0);end
 initial begin
  if(!$value$plusargs("VECTORS=%s",path))$fatal(1,"reference required");
  void'($value$plusargs("mut=%d",mut));f=$fopen(path,"r");if(!f)$fatal(1,"reference open");
  repeat(2)@(negedge clk);rst_n=1;
  rc=$fscanf(f,"%d\n",patterns);if(rc!=1)$fatal(1,"reference header");
  for(integer p=0;p<patterns;p=p+1)begin
   rc=$fscanf(f,"%h\n",expids);if(rc!=1)$fatal(1,"IDs");
   @(negedge clk);ids=expids;if(mut!=0)ids[17:9]=ids[8:0];tv=1;
   @(posedge clk);if(!tr)$fatal(1,"task backpressure");
   @(negedge clk);tv=0;
   if(mut!=0)begin repeat(2)@(posedge clk);if(!fault||v)$fatal(1,"duplicate accepted");
    $display("DUPLICATE_REJECTED_NO_DESCRIPTOR");$finish;end
   for(integer d=0;d<42;d=d+1)begin
    rc=$fscanf(f,"%d %d %d %d\n",ek,ej,en,e_keep);if(rc!=4)$fatal(1,"descriptor reference");
    do @(posedge clk);while(!(v&&ready));
    if(int'(k)!=ek||int'(j)!=ej||int'(n)!=en||int'(keep)!=e_keep||last!=(d==41)||fault)
      $fatal(1,"DESCRIPTOR mismatch pattern=%0d d=%0d actual=%0d,%0d,%0d,%0d reference=%0d,%0d,%0d,%0d",p,d,k,j,n,keep,ek,ej,en,e_keep);
    seen++;
   end
   @(negedge clk);
  end
  $display("DISPATCH_PASS patterns=%0d accepted_descriptors=%0d",patterns,seen);$finish;
 end
endmodule
