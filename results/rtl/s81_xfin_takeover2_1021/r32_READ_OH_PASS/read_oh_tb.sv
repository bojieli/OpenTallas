`timescale 1ns/1ps
module read_oh_tb;
parameter integer TR=1;
localparam integer NV=80,NP=128,NB=(TR==3)?19:17,NG=(NB+2)/3;
reg[8:0] tag;reg fire;reg[TR*NV*2-1:0] owner;reg[TR*NP-1:0] nodes;
wire[NB-1:0] ar,as_,ab,ah,aj,br,bs,bb,bh,bj;wire[NB*5-1:0] aa,ba;
for(genvar g=0;g<NG;g=g+1)begin:g_group
 localparam integer C=(NB-3*g>=3)?3:NB-3*g;
 ot_s81dv_finish_readgroup #(.TREES(TR),.FIRST(3*g),.CNT(C)) u_old(.fire(fire),.tag(tag),.owner(owner),.ren(ar[g*3+:C]),.ra(aa[g*15+:C*5]),.sa(as_[g*3+:C]),.sb(ab[g*3+:C]),.ha(ah[g*3+:C]),.hb(aj[g*3+:C]));
 ot_s81dv_finish_readgroup_oh #(.TREES(TR),.FIRST(3*g),.CNT(C)) u_new(.nodes(nodes),.owner(owner),.ren(br[g*3+:C]),.ra(ba[g*15+:C*5]),.sa(bs[g*3+:C]),.sb(bb[g*3+:C]),.ha(bh[g*3+:C]),.hb(bj[g*3+:C]));
end
integer checks=0,bad=0,H,ca,cb;
initial begin
 fire=0;tag=0;owner=0;nodes=0;#1;
 if({ar,as_,ab,ah,aj,aa} !== {br,bs,bb,bh,bj,ba})$fatal(1,"IDLE");
 for(integer t=0;t<TR;t=t+1)for(integer n=1;n<NP;n=n+1)begin
 H=7-($clog2(n+1)-1);
 if((((2*n+1)<<(H-1))-NP)<NV)begin
 ca=g_group[0].u_old.ca_node(8'(n));cb=g_group[0].u_old.cb_node(8'(n));
 for(integer oa=0;oa<4;oa=oa+1)for(integer ob=0;ob<4;ob=ob+1)begin
  owner=0;if(ca>=128)owner[(t*NV+ca-128)*2+:2]=2'(oa);if(cb>=128)owner[(t*NV+cb-128)*2+:2]=2'(ob);
  tag={2'(t),7'(n)};fire=1;nodes=0;nodes[t*NP+n]=1;#1;checks=checks+1;
  if({ar,as_,ab,ah,aj,aa} !== {br,bs,bb,bh,bj,ba})begin bad=bad+1;if(bad<8)$display("BAD TR%0d n%0d t%0d oa%0d ob%0d",TR,n,t,oa,ob);end
 end
 end
 end
 $display("READ_OH TR=%0d checks=%0d bad=%0d",TR,checks,bad);
 if(bad)$fatal(1,"READ_OH_MISMATCH");$finish;
end
endmodule
