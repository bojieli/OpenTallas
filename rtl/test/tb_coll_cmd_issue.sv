`timescale 1ns/1ps
// Actual PW calendar completeness: omission of either half must fault without moving issue.
module tb_coll_cmd_issue;
 reg clk=0; always #5 clk=~clk;
 reg rst_n=0,pw_v=0,start=0,cmd_free=1;
 reg [9:0] pw_addr=0; reg [63:0] pw_data=0;
 wire cmd_v,cmd_mode,active,done,fault,image_ready; wire[15:0]cmd_words; wire[31:0]cmd_tag;
 integer omit=0,seen=0,elapsed=0,issued=-1,reload=0,round_i;
 ot_coll_cmd_issue #(.DEPTH(2),.BASE(100)) dut(.*);
 task wr(input[9:0]a,input[63:0]d);
  @(negedge clk);pw_v=1;pw_addr=a;pw_data=d;
  @(negedge clk);pw_v=0;
 endtask
 always @(posedge clk) if(start) elapsed<=0; else if(active) begin
  elapsed<=elapsed+1;
  if(cmd_v)begin seen<=seen+1;issued<=elapsed;
   if(cmd_words!==16'd256 || cmd_mode!==1'b0) $fatal(1,"descriptor");
   if(omit!=2 && cmd_tag!==32'h12345678) $fatal(1,"tag");
  end
 end
 initial begin
  if($value$plusargs("OMIT=%d",omit))begin end
  if($value$plusargs("RELOAD=%d",reload))begin end
  repeat(3)@(negedge clk);rst_n=1;
  for(round_i=0;round_i<=reload;round_i=round_i+1)begin
  if(round_i!=0)begin wr(0,0);seen=0;issued=-1;end
  if(omit!=1)wr(100,(64'd256<<32)|8);
  if(omit!=2)wr(101,64'h12345678);
  wr(102,(64'd1<<49)|12);wr(103,0);
  wr(104,(64'h434c<<48)|(64'd2<<32)|12);
  if(image_ready !== (omit==0))$fatal(1,"image readiness omit=%0d ready=%b",omit,image_ready);
  @(negedge clk);start=1;@(negedge clk);start=0;
  wait(done);@(negedge clk);
  if(fault !== (omit!=0)) $fatal(1,"completeness omit=%0d fault=%b",omit,fault);
  if(omit!=1 && (seen!=1 || issued!=8))$fatal(1,"timeline seen=%0d issued=%0d",seen,issued);
  $display("ISSUER PASS omit=%0d fault=%b issued=%0d round=%0d",omit,fault,issued,round_i);
  end
  $finish;
 end
 initial begin #2000;$fatal(1,"timeout");end
endmodule
