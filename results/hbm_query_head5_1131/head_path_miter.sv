`timescale 1ns/1ps
// Extracted actual native head path. Exact reverse source-delta check establishes
// every non-head source byte is unchanged. Existing caller reset window is4;
// these data registers have no reset and capture on every edge in both sources.
module miter;
 parameter MUT=0;
 reg clk=0;always #1 clk=~clk;
 reg[4:0] emit_head=0;
 reg[4:0] eh_r; // Unchanged native input register precedes the two changed output widths.
 reg[7:0] old_c_head,old_ql_head;
 reg[4:0] new_c_head,new_ql_head;
 wire[7:0] restored=(MUT==1)?{3'b001,new_ql_head}:{3'b000,new_ql_head};
 always @(posedge clk)begin
  eh_r<=emit_head;
  old_c_head<={3'b000,eh_r};old_ql_head<=old_c_head;
  new_c_head<=(MUT==2)?{eh_r[3],eh_r[3:0]}:eh_r;
  new_ql_head<=new_c_head;
 end
 integer i,j,k,n=0;
 task tick(input[4:0] h);
 begin @(negedge clk);emit_head=h;@(posedge clk);#0.1;
  n=n+1;
  if(n>4 && old_ql_head!==restored)begin
   $display("DIFF cycle=%0d old=%h restored=%h MUT=%0d",n,old_ql_head,restored,MUT);$fatal(1);
  end
 end endtask
 initial begin
  repeat(4)tick(0);
  for(i=0;i<32;i=i+1)for(j=0;j<32;j=j+1)for(k=0;k<32;k=k+1)begin tick(i[4:0]);tick(j[4:0]);tick(k[4:0]);end
  tick(0);tick(0);
  $display("PASS H32 native3stage path triples=32768 captures=%0d caller_zeroextension8to5 MUT=%0d",n,MUT);$finish;
 end
endmodule
