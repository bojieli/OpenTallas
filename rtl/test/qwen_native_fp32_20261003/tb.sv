`timescale 1ns/1ps
module tb;
 reg clk=0;always #5 clk=~clk;
 reg rst_n=0;
 reg [3:0] valid=0,ad=0,mu=0,di=0,sq=0,canon=15,ready=0;
 reg [127:0] a=0,b=0;
 wire [3:0] ir,ov,pe;
 wire [127:0] y;wire [7:0] err;
 ot_qwen_native_fp32_lanes #(.OPT(1)) dut(clk,rst_n,valid,ir,ad,mu,di,sq,a,b,canon,ov,ready,y,err,pe);
 wire [3:0] off_ready,off_valid,off_pe;wire [127:0] off_y;wire [7:0] off_err;
 ot_qwen_native_fp32_lanes off(clk,rst_n,valid,off_ready,ad,mu,di,sq,a,b,canon,off_valid,ready,off_y,off_err,off_pe);
 integer file,rc,n,l,k,op,cz,er,delta,count=0;
 reg [31:0] aa,bb,yy;
 reg [127:0] expected,held_y;reg [7:0] expected_error,held_err;
 integer expected_latency[0:3];reg [3:0] observed;
 reg [1023:0] filename;
 task clear_input;begin valid=0;ad=0;mu=0;di=0;sq=0;end endtask
 initial begin
  if(!$value$plusargs("VECTORS=%s",filename))$fatal(1,"vectors required");
  file=$fopen(filename,"r");if(!file)$fatal(1,"no vectors");
  repeat(2)@(negedge clk);rst_n=1;
  // Invalid operation masks rejected BEFORE accepting/mutating any lane.
  valid=15;ad=15;mu=15;#1;
  if(ir!=0||pe!=15)$fatal(1,"invalid mask admitted");
  @(negedge clk);clear_input();
  for(n=0;n<128;n=n+1)begin
   expected=0;expected_error=0;canon=0;ready=0;observed=0;
   for(l=0;l<4;l=l+1)begin
    rc=$fscanf(file,"%h %h %h %h %h %h\n",op,aa,bb,cz,yy,er);
    if(rc!=6)$fatal(1,"vector truncated");
    a[32*l+:32]=aa;b[32*l+:32]=bb;canon[l]=cz;
    expected[32*l+:32]=yy;expected_error[2*l+:2]=er;
    ad[l]=(op==0);mu[l]=(op==1);di[l]=(op==2);sq[l]=(op==3);
    expected_latency[l]=(op<2)?5:31;
   end
   valid=15;#1;if(ir!=15)$fatal(1,"idle lanes not ready");
   @(posedge clk);#1;clear_input();a=128'hdeadbeef12345678800000007f800000;b=0;canon=~canon;
   if(off_ready||off_valid||off_y||off_err||off_pe)$fatal(1,"default off active");
   for(delta=1;delta<=34;delta=delta+1)begin
    @(posedge clk);#1;
    for(l=0;l<4;l=l+1)begin
     if(ov[l]!=(delta>=expected_latency[l]))$fatal(1,"latency lane%0d edge%0d",l,delta);
     if(ov[l])begin
      if(y[32*l+:32]!==expected[32*l+:32]||err[2*l+:2]!==expected_error[2*l+:2])
       $fatal(1,"RNE lane%0d wave%0d got%h/%h expected%h/%h",l,n,y[32*l+:32],err[2*l+:2],expected[32*l+:32],expected_error[2*l+:2]);
      observed[l]=1;
     end
    end
    if(ir!=0)$fatal(1,"reserved seat reissued before output accepted");
   end
   if(observed!=15)$fatal(1,"missing completion");
   held_y=y;held_err=err;
   repeat(3)begin @(posedge clk);#1;if(ov!=15||y!==held_y||err!==held_err)$fatal(1,"held result changed");end
   @(negedge clk);ready=15;
   @(posedge clk);#1;if(ov!=0)$fatal(1,"output not retired");
   @(negedge clk);ready=0;count=count+4;
  end
  // Reset flushes an in-flight long operation; no stale result after release.
  valid=15;sq=15;a={4{32'h40000000}};#1;if(ir!=15)$fatal(1,"reset test not idle");
  @(posedge clk);#1;clear_input();
  @(negedge clk);rst_n=0;
  @(negedge clk);rst_n=1;
  repeat(36)begin @(posedge clk);#1;if(ov!=0)$fatal(1,"stale result after reset");end
  $display("PASS FP32 vectors=%0d held/invalid/defaultoff/reset",count);$finish;
 end
endmodule
