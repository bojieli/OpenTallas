`timescale 1ns/1ps
module tb(input wire ck);
 parameter integer MUT=0;
 reg [3:0] rst_n=0;
 reg wn=0,rn=0;reg [1:0] wa=0,ra=0;reg [1023:0] wd=0;
 wire[1023:0] q;
 ot_qfd_head_fifo4_sram #(.MUT(MUT)) dut(.clk(ck),.ck_pm0(ck),.ck_pm1(ck),.rst_leaf_n(rst_n),
 .write_next(wn),.read_run_next(rn),.write_addr_next(wa),.read_addr_2next(ra),.write_data(wd),.read_data(q));
 reg [1023:0] mem[0:3];reg [3:0] valid=0;
 integer c=0,n=0,k;
 function automatic wf(input integer e);wf=(e%5!=2);endfunction
 function automatic[1:0] wr(input integer e);wr=e%4;endfunction
 function automatic[1:0] rd(input integer e);rd=(e%3==0)?((e+1)%4):((e-1)%4);endfunction
 function automatic[1023:0] data(input integer e);
  integer j;reg[31:0] v;
  begin v=32'h1234567 ^ e;for(j=0;j<32;j=j+1)begin v=1664525*v+1013904223;data[32*j+:32]=v;end end
 endfunction
 always @(negedge ck)begin
  c=c+1;
  if(c<8)begin rst_n=0;wn=0;rn=0;end
  else begin rst_n=15;wn=wf(c+1);wa=wr(c+1);ra=rd(c+2);rn=1;end
  wd=data(c);
 end
 always @(posedge ck)begin
  if(c>=11 && valid[rd(c)])begin
   n=n+1;
   if(q !== mem[rd(c)])begin $display("FQ4_SRAM_FAIL MUT=%0d edge=%0d row=%0d checks=%0d",MUT,c,rd(c),n);$finish;end
  end
  if(c>=9 && wf(c))begin mem[wr(c)]<=data(c);valid[wr(c)]<=1;end
  if(c==1000)begin $display("FQ4_SRAM_PASS MUT=%0d checks=%0d",MUT,n);$finish;end
 end
endmodule
