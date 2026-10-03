`timescale 1ns/1ps
module tb_dsrom_credit_root;
 reg clk=0,rst_n=0;always #5 clk=~clk;
 reg iv=0; reg [31:0] it;wire ready,credit,rv,re,fault,quiet;
 wire [15:0] row,bf;wire[2:0]pos;wire[31:0]fp,pq,ph,blocked;
 ot_v41_ret_credit_root dut(.clk(clk),.rst_n(rst_n),.i_v(iv),.i_t(it),.i_d(32'h3f800000),.i_e(1'b0),
 .i_ready(ready),.i_credit(credit),.r_v(rv),.r_row(row),.r_pos(pos),.r_fp32(fp),.r_bf16(bf),.r_e(re),
 .fault(fault),.quiet(quiet),.peak_q(pq),.peak_held(ph),.blocked_cycles(blocked));
 integer sent=0,got=0,cycle=0,rr,ll;reg [128:0]seen=0;
 function[31:0]tag(input integer r,input integer l);tag={3'd0,16'(r),5'(l),3'd0,5'd2};endfunction
 always @(posedge clk) if(rst_n)begin
  cycle=cycle+1;if(iv && ready)sent=sent+1;
  if(fault)$fatal(1,"root fault");
  if(rv)begin
   if(fp!=32'h40000000 || bf!=16'h4000 || re || pos!=0 || row>128 || seen[row])$fatal(1,"root exactness");
   seen[row]=1;got=got+1;
  end
  if(got==129)begin
   if(ph!=128 || blocked==0)$fatal(1,"held full scenario not exercised");
   $display("RESULT root count=%0d cycles=%0d peak_q=%0d peak_held=%0d blocked=%0d",got,cycle,pq,ph,blocked);$finish;
  end
 end
 always @(negedge clk) if(rst_n)begin
  iv=sent<258;
  // 129 unmatched lefts fill held128, then all right siblings. The unmatched
  // 129th queued entry must not hide the sibling of row0 arriving behind it.
  rr=sent<129 ? sent : sent-129;ll=sent<129 ? 0 : 1;it=tag(rr,ll);
 end
 initial begin #22;rst_n=1;end
 initial begin repeat(2048)@(posedge clk);$fatal(1,"held sibling deadlock");end
endmodule
