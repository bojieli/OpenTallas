`timescale 1ns/1ps
module tb_dsfd_vm_static_direct_scatter;
 parameter integer PIPE=0; // PIPE=1: b8_out pin stage, every output/fault one edge later than the baseline
 reg ck=0;always #5 ck=~ck;
 reg rn=0;reg [31:0] v=0,we=0;reg [447:0] row=0;reg [127:0] mask=0;
 reg [4095:0] data=0;reg [255:0] tag=0;
 wire [31:0] av,ae,bv,be;wire [287:0] aa,ba;wire [127:0] am,bm;
 wire [4095:0] ad,bd;wire [255:0] at,bt;wire af;wire [3:0] bf;
 wire [31:0] av0,ae0;wire [287:0] aa0;wire [127:0] am0;wire [4095:0] ad0;wire [255:0] at0;wire af0;
 dsfd_vm_static_scatter baseline(.ck(ck),.rst_n(rn),.i_v(v),.i_we(we),.i_row(row),.i_mask(mask),.i_data(data),.i_tag(tag),
 .o_v(av0),.o_we(ae0),.o_addr(aa0),.o_mask(am0),.o_data(ad0),.o_tag(at0),.fault(af0));
 // baseline aligned to the b8_out output edge (PIPE extra edges)
 reg [31:0] av1,ae1;reg [287:0] aa1;reg [127:0] am1;reg [4095:0] ad1;reg [255:0] at1;reg af1=0;
 always @(posedge ck)begin av1<=av0;ae1<=ae0;aa1<=aa0;am1<=am0;ad1<=ad0;at1<=at0;af1<=af0;end
 assign av=PIPE?av1:av0;assign ae=PIPE?ae1:ae0;assign aa=PIPE?aa1:aa0;assign am=PIPE?am1:am0;
 assign ad=PIPE?ad1:ad0;assign at=PIPE?at1:at0;assign af=PIPE?af1:af0;
 genvar g,k;generate for(g=0;g<4;g=g+1)begin:group
 wire [7:0] cv,cwe;wire [111:0] cr;wire [31:0] cm;wire [1023:0] cd;wire [63:0] ct;
 for(k=0;k<8;k=k+1)begin:record_capture
 localparam integer B=8*g+k,J=8*(B%4)+B/4;
 dsfd_vm_static_write_capture128 actual(.ck(ck),.rst_n(rn),.i_v(v[J]),.i_we(we[J]),.i_row(row[14*J+:14]),
 .i_mask(mask[4*J+:4]),.i_data(data[128*J+:128]),.i_tag(tag[8*J+:8]),
 .o_v(cv[k]),.o_we(cwe[k]),.o_row(cr[14*k+:14]),.o_mask(cm[4*k+:4]),.o_data(cd[128*k+:128]),.o_tag(ct[8*k+:8]));
 end
 dsfd_vm_static_scatter_b8_out #(.BANK_BASE(8*g),.PIPE(PIPE)) actual_output(.ck(ck),.rst_n(rn),.i_v(cv),.i_we(cwe),
 .i_row(cr),.i_mask(cm),.i_data(cd),.i_tag(ct),.o_v(bv[8*g+:8]),.o_we(be[8*g+:8]),.o_addr(ba[72*g+:72]),
 .o_mask(bm[32*g+:32]),.o_data(bd[1024*g+:1024]),.o_tag(bt[64*g+:64]),.fault(bf[g]));
 end endgenerate
 integer cycle,j,w,a,b,mode=0,bad=0,checks=0;reg [4832:0] saved;reg af_d=0;
 initial begin
 if($value$plusargs("mode=%d",mode))begin end
 repeat(4)@(negedge ck);rn=1;
 for(cycle=0;cycle<1008;cycle=cycle+1)begin
  @(negedge ck);
  for(j=0;j<32;j=j+1)begin
   a=$urandom_range(0,511);b=j%8;
   row[14*j+:14]=(a<<5)|(((b^(a&7))&7)<<2)|(j/8);
   v[j]=cycle%7!=0;we[j]=(cycle+j)%3!=0;mask[4*j+:4]=(j+cycle)%16;tag[8*j+:8]=j+cycle;
   for(w=0;w<4;w=w+1)data[128*j+32*w+:32]=$random;
  end
  if(mode==1 && cycle==10)row[14+:14]=row[0+:14];
  if(mode==2 && cycle==10)row[1:0]=2;
  @(posedge ck);#1;
  if(cycle>4)begin
   checks=checks+1;
   // valid / fault exactly; we, address, mask, data and tag of every VALID bank exactly (payload is meaningful
   // only with o_v: the consumer writes only on valid).  Mode 2 (wrong lane) keeps the same valid set as the
   // baseline on every cycle, so its valid suppression is checked throughout.
   if(mode==0 || mode==2 || cycle<10)begin
    if(av!==bv)bad=bad+1;
    for(w=0;w<32;w=w+1)if(av[w]===1'b1 && {ae[w],aa[9*w+:9],am[4*w+:4],ad[128*w+:128],at[8*w+:8]}!=={be[w],ba[9*w+:9],bm[4*w+:4],bd[128*w+:128],bt[8*w+:8]})bad=bad+1;
   end
   // b8_out fault is FAULT_AGE 3 (per-record mismatch flop, then the sticky OR): exactly one edge after the baseline
   if(af_d!==( |bf))bad=bad+1;
   af_d=af;
   saved={bv,be,ba,bm,bd,bt,|bf};#1;
   if(saved!=={bv,be,ba,bm,bd,bt,|bf})bad=bad+1;
  end
 end
 if((mode==0 && (af || |bf)) || (mode!=0 && (!af || !(|bf))))bad=bad+1;
 if(bad)begin $display("TB_VM_DIRECT_SCATTER FAIL mode %0d checks %0d bad %0d",mode,checks,bad);$fatal;end
 $display("TB_VM_DIRECT_SCATTER PASS mode %0d checks %0d",mode,checks);$finish;
 end
endmodule
