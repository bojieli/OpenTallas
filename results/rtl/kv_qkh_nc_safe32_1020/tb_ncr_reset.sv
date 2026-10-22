`timescale 1ns/1ps
// Independent startup values via --x-initial unique. Compare public valid-qualified arithmetic,
// and asynchronous output reset before any clock. Never assume old/new unreset data twins.
module tb_ncr_reset;
 reg clk=0;always #1 clk=~clk;
 reg rst_n=0,v=0;reg[31:0]a=0,b=0;
 wire[31:0]y0,y1;wire[1:0]e0,e1;wire vo0,vo1;
 ot_hdc_fp32_add_lat_nr #(.LAT(7)) old(.clk(clk),.rst_n(rst_n),.valid_in(v),.a(a),.b(b),.y(y0),.err(e0),.valid_out(vo0));
 ot_hdc_fp32_add_lat_ncr #(.LAT(7)) dut(.clk(clk),.rst_n(rst_n),.rst_y(rst_n),.valid_in(v),.a(a),.b(b),.y(y1),.err(e1),.valid_out(vo1));
 integer errors=0,checked=0,pulses=0,firsts=0,seen=0,k=0,cycle=0;
 task automatic check;
 begin
  checked++;
  if(vo0!==vo1)begin errors++;if(errors<5)$display("valid mismatch cycle%0d",cycle);end
  if(vo0)begin
   if(!seen)begin firsts++;seen=1;end
   if(y0!==y1||e0!==e1)begin errors++;if(errors<5)$display("data mismatch cycle%0d %h/%h %h/%h",cycle,y0,y1,e0,e1);end
  end
  if(dut.x_swap !== {7{dut.x_swap[0]}})errors++;
  if(dut.lz_oh!==(27'd1<<dut.lz))errors++;
  if(dut.w_sub_dist!=={4{dut.w_sub}})errors++;
  if(dut.rnd_c_dist!=={2{dut.rnd_c}})errors++;
  if(dut.u_byp_dist!=={4{dut.u_byp}})errors++;
  for(integer j=0;j<4;j++)if(!$onehot(dut.bypass_wp[j]))errors++;
 end endtask
 initial begin
  // Long reset first; unreset datapath registers start independently and converge only by sampling.
  repeat(2)@(negedge clk);
  #0.25;rst_n=1;v=1;
  for(k=0;k<4000;k++)begin
   @(negedge clk);a=$urandom;b=$urandom;v=($urandom%4)!=0;
   if(k%13==0)a=0;if(k%17==0)b=32'h7f800001;if(k%19==0)b=a^32'h80000000;
   if(k%37==0)begin
    #0.2;rst_n=0;seen=0;pulses++;
    #0.1;if(y0!==0||y1!==0||vo0!==0||vo1!==0||e0!==0||e1!==0)begin errors++;$display("offphase reset failure");end
    #0.1;rst_n=1;v=1;
   end
   @(posedge clk);#0.25;cycle++;check();
  end
  $display("NCR_RESET %s checks=%0d offphase=%0d first_valid_after_reset=%0d errors=%0d scope=valid_qualified_data_plus_immediate_reset_and_copy_convergence",errors?"FAIL":"PASS",checked,pulses,firsts,errors);
  if(errors)$fatal(1,"NCR reset mismatch");$finish;
 end
endmodule
