module tb;
 import ot_gpu_w6_secded_pkg::*;
 import ot_hbrom_secded_pipeline_pkg::*;
 reg[63:0]d;reg[71:0]code,broken,first;integer trial,a,b,tests;
 initial begin
  tests=0;
  for(trial=0;trial<4;trial=trial+1)begin
   d={$random,$random};first=encode64(d)&{1'b0,{71{1'b1}}};code={^first[70:0],first[70:0]};
   if(code!==encode64(d))$fatal(1,"split encode mismatch");
   if(correct72(code,check72(code))!==decode64(code))$fatal(1,"clean mismatch");
   for(a=0;a<72;a=a+1)begin
    broken=code^(72'b1<<a);
    if(correct72(broken,check72(broken))!==decode64(broken))$fatal(1,"single mismatch");
    for(b=a+1;b<72;b=b+1)begin
     broken=code^(72'b1<<a)^(72'b1<<b);
     if(correct72(broken,check72(broken))!==decode64(broken))$fatal(1,"double mismatch");
     tests=tests+1;
    end
   end
  end
  $display("PASS split codec:4 payloads,288singlefaults,%0d doublefaults",tests);$finish;
 end
endmodule
