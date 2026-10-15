`timescale 1ns/1ps
module tb_dsfd_vm_static_scatter_lane;
 reg ck=0;always #5 ck=~ck;
 reg rn=0;reg [31:0] v=0,we=0;reg [447:0] row=0;reg [127:0] mask=0;
 reg [4095:0] data=0;reg [255:0] tag=0;
 wire [31:0] av,ae,bv,be;wire [287:0] aa,ba;wire [127:0] am,bm;
 wire [4095:0] ad,bd;wire [255:0] at,bt;wire af;wire [3:0] bf;
 dsfd_vm_static_scatter baseline(.ck(ck),.rst_n(rn),.i_v(v),.i_we(we),.i_row(row),.i_mask(mask),.i_data(data),.i_tag(tag),
 .o_v(av),.o_we(ae),.o_addr(aa),.o_mask(am),.o_data(ad),.o_tag(at),.fault(af));
 genvar l,k;generate for(l=0;l<4;l=l+1)begin:lane
 wire [7:0] lv,le;wire [71:0] la;wire [31:0] lm;wire [1023:0] ld;wire [63:0] lt;
 dsfd_vm_static_scatter_lane #(.LANE(l)) actual(.ck(ck),.rst_n(rn),.i_v(v[8*l+:8]),.i_we(we[8*l+:8]),
 .i_row(row[112*l+:112]),.i_mask(mask[32*l+:32]),.i_data(data[1024*l+:1024]),.i_tag(tag[64*l+:64]),
 .o_v(lv),.o_we(le),.o_addr(la),.o_mask(lm),.o_data(ld),.o_tag(lt),.fault(bf[l]));
 for(k=0;k<8;k=k+1)begin:bank
 assign bv[4*k+l]=lv[k];assign be[4*k+l]=le[k];assign ba[9*(4*k+l)+:9]=la[9*k+:9];
 assign bm[4*(4*k+l)+:4]=lm[4*k+:4];assign bd[128*(4*k+l)+:128]=ld[128*k+:128];assign bt[8*(4*k+l)+:8]=lt[8*k+:8];
 end end endgenerate
 integer cycle,j,w,a,b,mode=0,bad=0,checks=0;reg [4832:0] saved;
 initial begin
 if($value$plusargs("mode=%d",mode))begin end
 repeat(4)@(negedge ck);rn=1;
 for(cycle=0;cycle<1008;cycle=cycle+1)begin
  @(negedge ck);
  for(j=0;j<32;j=j+1)begin
   a=$urandom_range(0,511);b=(j%8+cycle)%8;
   row[14*j+:14]=(a<<5)|(((b^(a&7))&7)<<2)|(j/8);
   v[j]=cycle%7!=0;we[j]=(cycle+j)%3!=0;mask[4*j+:4]=(j+cycle)%16;tag[8*j+:8]=j+cycle;
   for(w=0;w<4;w=w+1)data[128*j+32*w+:32]=$random;
  end
  if(mode==1 && cycle==10)row[14+:14]=row[0+:14];
  if(mode==2 && cycle==10)row[1:0]=2;
  @(posedge ck);#1;
  if(cycle>4)begin
   checks=checks+1;
   if({av,ae,aa,am,ad,at,af}!=={bv,be,ba,bm,bd,bt,|bf})bad=bad+1;
   saved={bv,be,ba,bm,bd,bt,|bf};#1;
   if(saved!=={bv,be,ba,bm,bd,bt,|bf})bad=bad+1;
  end
 end
 if((mode==0 && (af || |bf)) || (mode!=0 && (!af || !(|bf))))bad=bad+1;
 if(bad)begin $display("TB_VM_SCATTER_LANE FAIL mode %0d checks %0d bad %0d",mode,checks,bad);$fatal;end
 $display("TB_VM_SCATTER_LANE PASS mode %0d checks %0d",mode,checks);$finish;
 end
endmodule
