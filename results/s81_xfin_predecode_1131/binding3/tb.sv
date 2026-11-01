`timescale 1ps/1fs
module tb;
reg clk=0;always #416.5 clk=~clk;
reg rst_n=0,go=0;reg[2:0]f_v=0;reg[5:0]f_t=0;reg[23:0]f_base=0;reg[479:0]f_d=0;
wire vo,vn,vm,fo,fn,fm;wire[31:0]ho,ko,do_,hn,kn,dn,hm,km,dm;
eng_old #(.NV(5),.P(3),.K(5),.LA(6)) old(.clk(clk),.rst_n(rst_n),.go(go),.f_v(f_v),.f_t(f_t),.f_base(f_base),.f_d(f_d),.r_v(vo),.r_hh(ho),.r_kk(ko),.r_dd(do_),.fault(fo));
eng_new #(.NV(5),.P(3),.K(5),.LA(6)) candidate(.clk(clk),.rst_n(rst_n),.go(go),.f_v(f_v),.f_t(f_t),.f_base(f_base),.f_d(f_d),.r_v(vn),.r_hh(hn),.r_kk(kn),.r_dd(dn),.fault(fn));
eng_mut #(.NV(5),.P(3),.K(5),.LA(6)) mutant(.clk(clk),.rst_n(rst_n),.go(go),.f_v(f_v),.f_t(f_t),.f_base(f_base),.f_d(f_d),.r_v(vm),.r_hh(hm),.r_kk(km),.r_dd(dm),.fault(fm));
integer roots=0,mut_errors=0,cycles=0,b,t,k,base_count,waited,tree;
always @(negedge clk) if(rst_n) begin
 cycles=cycles+1;
 if({vo,ho,ko,do_,fo} !== {vn,hn,kn,dn,fn}) begin $display("FAIL lockstep cycle%0d",cycles);$fatal;end
 if(fo) begin $display("FAIL unexpected fault cycle%0d",cycles);$fatal;end
 if(vo)roots=roots+1;
 if(vo!==vm || fo!==fm || (vo && {ho,ko,do_}!=={hm,km,dm}))mut_errors=mut_errors+1;
end
initial begin
 if($bits(candidate.wr_onehot)!=24 || $bits(mutant.wr_onehot)!=24) $fatal(1,"wrong selected source");
 repeat(8)@(negedge clk);rst_n=1;repeat(8)@(negedge clk);
 for(b=0;b<16;b=b+1)begin
  base_count=roots;go=1;@(negedge clk);go=0;repeat(8)@(negedge clk);
  for(t=0;t<3;t=t+1)begin
   tree=(b%2)?2-t:t;f_v=1;f_t=tree;f_base=0;
   for(k=0;k<15;k=k+1)f_d[k*32+:32]=32'h3f800000+(b<<12)+(tree<<9)+(k<<6);
   @(negedge clk);f_v=0;@(negedge clk);
  end
  waited=0;
  while(roots==base_count && waited<400)begin @(negedge clk);waited=waited+1;end
  if(roots!=base_count+1)$fatal(1,"missing root batch%0d",b);
  repeat(8)@(negedge clk);
 end
 if(roots!=16 || mut_errors==0)$fatal(1,"bad root/mutant counts");
 $display("PASS bound_real_child NV5 LA6 batches16 roots%0d cycles%0d mutant_errors%0d source_witness24",roots,cycles,mut_errors);$finish;
end
endmodule
