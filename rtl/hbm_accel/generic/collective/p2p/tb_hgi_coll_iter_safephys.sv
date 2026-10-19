`timescale 1ns/1ps
module tb_hgi_coll_iter_safephys #(parameter integer MUT=0);
 reg clk=0;always #5 clk=~clk;
 reg[31:0]it=0,it_late=0;reg[15:0]a=0,v=0,b=0,c=0,d=0;reg[7:0]k=0;
 wire[223:0]old_o,new_o;
 always @(posedge clk)it_late<=it;
 ot_hgi_coll_iter_mul ref_i(.clk(clk),.iteration(it),.s_idx(a),.s_vm(v),.s_iaddr(b),.s_del(c),.s_rgx(d),.s_lk(k),.m_idx(old_o[223:208]),.m_vm(old_o[207:192]),.m_iaddr_l(old_o[191:160]),.m_del_l(old_o[159:128]),.m_rgx_l(old_o[127:96]),.m_iaddr_h(old_o[95:80]),.m_del_h(old_o[79:64]),.m_rgx_h(old_o[63:48]),.m_lk_l(old_o[47:24]),.m_lk_h(old_o[23:0]));
 ot_hgi_coll_iter_mul_safephys dut(.clk(clk),.iteration(MUT==1?it_late:it),.s_idx(a),.s_vm(v),.s_iaddr(b),.s_del(c),.s_rgx(MUT==2?{d[15:8],8'd0}:d),.s_lk(k),.m_idx(new_o[223:208]),.m_vm(new_o[207:192]),.m_iaddr_l(new_o[191:160]),.m_del_l(new_o[159:128]),.m_rgx_l(new_o[127:96]),.m_iaddr_h(new_o[95:80]),.m_del_h(new_o[79:64]),.m_rgx_h(new_o[63:48]),.m_lk_l(new_o[47:24]),.m_lk_h(new_o[23:0]));
 reg[223:0]expected[0:513];integer checked=0;
 function automatic[223:0]gold(input[31:0]iv,input[15:0]aa,vv,bb,cc,dd,input[7:0]kk);
 reg[63:0]pa,pv,pb,pc,pd,pl,ph;
 begin pa=64'(iv)*64'(aa);pv=64'(iv)*64'(vv);pb=64'(iv)*64'(bb);pc=64'(iv)*64'(cc);pd=64'(iv)*64'(dd);pl=64'(iv[15:0])*64'(kk);ph=64'(iv[31:16])*64'(kk);gold={pa[15:0],pv[15:0],pb[31:0],pc[31:0],pd[31:0],48'd0,pl[23:0],ph[23:0]};end
 endfunction
 initial begin
  for(integer j=0;j<514;j++)begin
   @(negedge clk);
   if(j>=512)begin it=0;a=0;v=0;b=0;c=0;d=0;k=0;end
   else begin
    it=$urandom;a=16'($urandom);v=16'($urandom);b=16'($urandom);c=16'($urandom);d=16'($urandom);k=8'($urandom);
    if(j<4)begin it=j==0?32'd0:j==1?32'hffffffff:j==2?32'h10001:32'h80000000;a=16'hffff;v=16'hffff;b=16'hffff;c=16'hffff;d=16'hffff;k=8'hff;end
   end
   expected[j]=gold(it,a,v,b,c,d,k);
   @(posedge clk);#1;
   if(j>=2)begin
    if(new_o!==old_o||new_o!==expected[j-2])$fatal(1,"COLL_ITER_SAFE_FAIL j=%0d old=%h new=%h expected=%h",j,old_o,new_o,expected[j-2]);
    checked++;
   end
  end
  $display("COLL_ITER_SAFE_PASS cases=%0d independent unsigned truncation +sameedge baseline",checked);$finish;
 end
endmodule
