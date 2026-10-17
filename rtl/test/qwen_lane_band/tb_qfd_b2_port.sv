`timescale 1ns/1ps
// Actual 16-lane hardened result-port source: post-scale, rows, masks, write
// addresses and argmax, against BANDF1 at its original physical position.
// Inputs are ideal stimuli at the port's declared ROM-column/tree boundaries.
module tb_qfd_b2_port;
 parameter integer MUT=0;
 reg ck=0;always #5 ck=~ck;
 reg rst_n=0,v=0;
 reg [4:0] oldp,newp;
 reg [1023:0] colq=0;
 reg [511:0] lv=0;
 reg [112:0] tag=0;
 wire ow,nw,oo,no,of,nf;
 wire [23:0] oa,na;wire [15:0] om,nm;
 wire [511:0] od,nd;wire [50:0] oh,nh;
 qfd_slab_port_leaf u_old(.ck(ck),.ck_mul0(ck),.ck_mul1(ck),.ck_mul2(ck),.ck_mul3(ck),.rst_n(rst_n),
   .pt_id(oldp),.colq(colq),.lv_in(lv),.a_v_e2(v),.a_f_e2(tag),.o_we(ow),.o_addr(oa),.o_mask(om),.o_data(od),.o_ov(oo),.am(oh),.fault(of));
 qfd_slab_port_leaf_b2 u_new(.ck(ck),.ck_mul0(ck),.ck_mul1(ck),.ck_mul2(ck),.ck_mul3(ck),.rst_n(rst_n),
   .pt_id(newp),.colq(colq),.lv_in(lv),.a_v_e2(v),.a_f_e2(tag),.o_we(nw),.o_addr(na),.o_mask(nm),.o_data(nd),.o_ov(no),.am(nh),.fault(nf));
 integer s,g,c,l,n,seed=11,checks=0,writes=0,heads=0,ops=0;
 reg checking=0;
 function automatic integer pos(input integer split,group,bits);
  integer top,count;
  begin top=7+bits;if(split<=top)begin count=1<<(top-split);pos=(group/count)*(1<<bits)+group%count;end else pos=group;end
 endfunction
 task automatic step;
  begin
   @(negedge ck);
   if(checking)begin
    if({ow,oo,of}!=={nw,no,nf})$fatal(1,"port strobes s%0d g%0d old%0b%0b%0b new%0b%0b%0b",s,g,ow,oo,of,nw,no,nf);
    if(ow)begin
     if({oa,om,od}!=={na,nm,nd})$fatal(1,"port result s%0d g%0d oldaddr%0d newaddr%0d oldmask%h newmask%h",s,g,oa,na,om,nm);
     writes=writes+1;
    end
    if(oh[50]!==nh[50] || (oh[50] && oh!==nh))$fatal(1,"port argmax s%0d g%0d old%h new%h",s,g,oh,nh);
    if(oh[50])heads=heads+1;
    checks=checks+1;
   end
  end
 endtask
 initial begin
  oldp=0;newp=0;
  repeat(4)step();rst_n=1;repeat(32)step();checking=1;
  for(s=7;s<=11;s=s+1)for(g=0;g<(3072>>s);g=g+1)for(c=0;c<3;c=c+1)begin
   oldp=5'(pos(s,g,3));newp=5'(MUT==1?pos(s,g,3):pos(s,g,2));
   for(l=0;l<16;l=l+1)begin
    lv[32*l+:32]={1'($random(seed)),8'(120+l%8),23'($random(seed))};
    colq[16*l+:16]=16'h3f00+16'(l%3*128);
   end
   repeat(12)step();
   tag={1'b1,1'b1,1'b0,1'b0,4'(s),24'd77,24'd13,19'd0,19'd0,19'(g*128+(c==0?16:c==1?5:0))};
   v=1;step();v=0;repeat(31)step();ops=ops+1;
  end
  if(ops!=138 || writes!=138 || heads<92)$fatal(1,"port coverage ops%0d writes%0d heads%0d",ops,writes,heads);
  $display("PASS b2 native16-lane port result+argmax same edges, ops%0d writes%0d heads%0d checks%0d",ops,writes,heads,checks);$finish;
 end
endmodule
