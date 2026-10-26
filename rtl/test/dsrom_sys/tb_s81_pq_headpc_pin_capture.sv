`timescale 1ns/1ps
module tb_s81_pq_headpc_pin_capture;
 reg clk=0;always #5 clk=~clk;
 reg rst_n=0;reg consume=0;reg[9:0]aqi=0;reg[15:0]h0=0;reg[1:0]sv=0;reg[1023:0]rd=0;
 wire[255:0]q0,q1;wire[9:0]e0,e1;wire fault;
 ot_s81_pq_qb_headpc_native dut(.clk(clk),.rst_n(rst_n),.consume(consume),.aqi_d(aqi),.h_b0(h0),.h_b1(16'd0),.hw_sv(sv),.rd_data(rd),.aq_e(20'd0),.aq_p(10'd0),.hq0(q0),.hq1(q1),.he0(e0),.he1(e1),.fault(fault));
 function automatic[255:0] word(input integer bank,input integer cycle);
  reg[31:0]x;begin x=32'h12340000 ^ (bank*32'h551100) ^ cycle;word={8{x}};end
 endfunction
 integer b,i,k,checks=0;reg[255:0]previous;
 initial begin
  repeat(8)@(negedge clk);rst_n=1;repeat(8)@(negedge clk);
  // Actual loader pins write metadata row0 of all four banks, including parity.
  aqi={1'b1,8'd0,1'b0};repeat(4)@(negedge clk);
  aqi={1'b1,8'd8,1'b0};repeat(4)@(negedge clk);
  aqi=0;repeat(8)@(negedge clk);consume=1;sv=1;
  for(b=0;b<4;b=b+1)begin
   h0=(b==0?0:b==1?1:b==2?8:9);
   for(i=0;i<64;i=i+1)begin
    for(k=0;k<4;k=k+1)rd[256*k+:256]=word(k,i);
    @(posedge clk);#1;
    if(i>=8)begin
     if(q0!==previous || e0!==0 || fault)$fatal(1,"PINREAD_CAPTURE FAIL bank%0d edge%0d got%h expected%h fault%b",b,i,q0,previous,fault);
     checks=checks+256;
    end
    previous=word(b,i);@(negedge clk);
   end
  end
  $display("PINREAD_CAPTURE PASS checked_bits=%0d banks=4 independent_data_edges=256",checks);$finish;
 end
endmodule
