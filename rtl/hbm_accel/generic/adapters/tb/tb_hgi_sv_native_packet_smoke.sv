`timescale 1ps/1fs
module tb_hgi_sv_native_packet_smoke;
 reg clk=0,vclk=0,rst_n=0;always #416.666625 clk=~clk;always #555.5555 vclk=~vclk;
 reg[337:0]su_q=0,bench_q=0;wire[273:0]su_r,bench_r;wire[420:0]fault;wire[3:0]released;
 ot_hgi_sv_native_vm_fixture dut(.clk(clk),.vclk(vclk),.rst_n(rst_n),
  .rg_req(1'b0),.wg_req(1'b0),.rg_gnt(),.wg_gnt(),.rq(512'b0),.rq_cr(),.rr(),
  .wq(8960'b0),.wcredit(),.wdone(),.su_q(su_q),.bench_q(bench_q),.su_r(su_r),.bench_r(bench_r),.fault(fault),.released(released));
 integer errors=0,checks=0;
 task packet(input bit wr,input integer sector,input[255:0]data,input[31:0]mask,output[255:0]answer);
  integer t;
  @(negedge clk);bench_q={1'b1,wr,27'(sector),5'b0,data,mask,16'h0be0};
  @(negedge clk);bench_q[337]=0;
  t=0;while(!bench_r[273]&&t<10000)begin @(negedge clk);t++;end
  if(t==10000||bench_r[272:257]!=16'h0be0||bench_r[256]!=wr)begin errors++;$display("ERR packet sector%0d wr%0d t%0d response%h",sector,wr,t,bench_r);end
  answer=bench_r[255:0];@(negedge clk);
 endtask
 function automatic[255:0]pattern(input integer sector);
  for(integer w=0;w<8;w++)pattern[w*32+:32]=32'ha5000000+32'(sector*8+w);
 endfunction
 initial begin
  reg[255:0]answer,gold;integer sector;
  repeat(8)@(negedge clk);rst_n=1;repeat(16)@(negedge clk);
  for(integer q=0;q<4;q++)for(integer l=0;l<32;l++)begin
   sector=q*8192+32*17+l;gold=pattern(sector);
   packet(1,sector,gold,32'hffffffff,answer);
   packet(0,sector,0,0,answer);checks++;
   if(answer!==gold)begin errors++;$display("ERR native packet globalS%0d got%h want%h",sector,answer,gold);end
   packet(1,sector,~gold,32'h000f000f,answer);
   gold[31:0]=~gold[31:0];gold[159:128]=~gold[159:128];
   packet(0,sector,0,0,answer);checks++;
   if(answer!==gold)begin errors++;$display("ERR native masked packet globalS%0d",sector);end
  end
  repeat(200)@(negedge clk);
  if(|fault||released!=4'hf)begin errors++;$display("ERR native fault%h released%h",fault,released);end
  if(errors==0)$display("SV_NATIVE_PACKET PASS checks=%0d",checks);else $display("SV_NATIVE_PACKET FAIL errors=%0d",errors);
  $finish;
 end
 always @(posedge clk)if(rst_n&&|fault)begin $display("SV_NATIVE_PACKET FAIL native_fault=%h",fault);$finish;end
endmodule
