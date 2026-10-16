`timescale 1ns/1ps
// H-MTP2/sudma: P-row indexed SU.VOP (route gather) on the actual static VM banks (ot_vms_bank_static, 32 banks,
// 96 ot_sram_1r1w_1024x256 macros) with the same register-only tap transport as tb_indexed_scalar.  Golden per row:
// O[dest_r] = A[base_r + I[ix_r]] (FP32 word copy), every other word of the O sector unchanged; computed here from
// the addresses, never from the engine.  Fixed schedule: every record of R rows must take the same start->done edges
// in every case (reported per R).  MUT: engine mutant (1 I stride dropped, 2 O stride dropped, 3 value pipe short).
module tb_indexed_scalar_rows;
 parameter MUT=0;
 reg clk=0;always #5 clk=~clk;
 reg rst_n=0,start=0,preload=0,readback=0;
 reg[3:0]rows=1;
 reg[23:0]ix=0,base=0,limit=0,dst=0,is_=0,as_=0,os_=0;
 wire[543:0]rq;wire[8991:0]wq;
 wire[8223:0]raw_rr,rr;wire busy,done,fault;
 reg[8991:0]dq=0;reg[543:0]verify_rq=0;
 wire[575:0]status;
 ot_hbm_su_indexed_scalar_rows #(.MUT(MUT))dut(
 .clk(clk),.rst_n(rst_n),.start(start),.rows(rows),.index_word(ix),.score_base(base),.score_limit(limit),
 .dest_word(dst),.i_stride(is_),.a_stride(as_),.o_stride(os_),.dyn_mul(24'd1),
 .rr(rr),.rq(rq),.wq(wq),.busy(busy),.done(done),.fault(fault));
 reg[8223:0]ret[0:2];reg[8991:0]wr[0:3];integer s;
 always @(posedge clk)begin
  ret[0]<=raw_rr;ret[1]<=ret[0];ret[2]<=ret[1];
  wr[0]<=wq;for(s=1;s<4;s=s+1)wr[s]<=wr[s-1];
 end
 assign rr=ret[2];
 for(genvar q=0;q<4;q=q+1)begin:gq
  localparam RG=q<2?3:5,WG=q<2?1:3;
  for(genvar b=0;b<8;b=b+1)begin:gb
   localparam I=q*8+b;
   wire[RG*257-1:0]brr;
   wire[16:0]brq=readback?verify_rq[I*17+:17]:rq[I*17+:17];
   ot_vms_bank_static #(.RG(RG),.WG(WG))bank(.clk(clk),.rst_n(rst_n),.bid(3'(b)),.sid(2'(q)),
   .rslot_v(1'b1),.rslot(0),.wslot_v(1'b1),.wslot(preload?WG+4:0),
   .rq({{(RG-1)*17{1'b0}},brq}),.rr(brr),.wq({{(WG-1)*281{1'b0}},wr[3][I*281+:281]}),.wq_done(),
   .dq(dq[I*281+:281]),.dq_done(),.kq(281'd0),.kq_done(),.xq(276'd0),.xq_done(),.xq2(276'd0),.xq2_done(),
   .eg(),.pq(285'd0),.pr(),.status(status[I*18+:18]));
   assign raw_rr[I*257+:257]=brr[256:0];
  end
 end
 integer c,r,j,errors=0,checks=0,cyc=0,start_c,ncase=0;
 integer fixed_cyc[0:15];
 integer sel,score,a,bank;
 reg[255:0]img[int];reg[255:0]exp_[int];
 int unsigned seed=32'd20261016;
 always @(posedge clk)cyc=cyc+1;
 function automatic integer bankof(input integer adr);bankof=((adr>>16)&3)*8+((adr>>3)&7);endfunction
 function automatic integer rnd(input integer m);seed=seed*1103515245+12345;rnd=(seed>>8)%m;endfunction
 task automatic load_sector(input integer sec,input[255:0]payload);
  begin
   @(negedge clk);dq=0;dq[bankof(sec*8)*281+:281]={1'b1,16'(sec),payload,8'hff};
   @(negedge clk);dq=0;repeat(12)@(negedge clk);
  end
 endtask
 task automatic put_word(input integer adr,input[31:0]w,input integer kind);
  // kind 0 score background, 1 index background, 2 dest background
  reg[255:0]d;integer k;
  begin
   if(!img.exists(adr/8))begin
    for(k=0;k<8;k=k+1)d[k*32+:32]=kind==0?32'h3e800000+32'((adr/8)*8+k):kind==1?32'hdeadbeef:32'h6f55aa33;
    img[adr/8]=d;
   end
   d=img[adr/8];d[(adr%8)*32+:32]=w;img[adr/8]=d;
  end
 endtask
 // one record: R rows; window size W words; strides in words
 task automatic run_case(input integer R,input integer i0,input integer b0,input integer W,input integer d0,
                         input integer si,input integer sa,input integer so,input integer canon);
  integer rr_,k,sc;reg[255:0]d;
  begin
   img.delete();exp_.delete();
   for(rr_=0;rr_<R;rr_=rr_+1)begin                           // score windows (background = address-derived)
    for(k=0;k<W;k=k+8)put_word(b0+rr_*sa+k,32'h3e800000+32'(b0+rr_*sa+k),0);
   end
   for(rr_=0;rr_<R;rr_=rr_+1)begin
    sel=canon?((rr_==0)?7:(rr_==1)?1:(rr_==2)?W-1:(rr_==3)?64%W:(rr_==4)?128%W:3):rnd(W);
    put_word(i0+rr_*si,32'(sel),1);
    sc=b0+rr_*sa+sel;
    put_word(d0+rr_*so,32'h6f55aa33,2);
    if(!exp_.exists((d0+rr_*so)/8))exp_[(d0+rr_*so)/8]=img[(d0+rr_*so)/8];
    d=exp_[(d0+rr_*so)/8];d[((d0+rr_*so)%8)*32+:32]=32'h3e800000+32'(sc);exp_[(d0+rr_*so)/8]=d;
   end
   preload=1;
   foreach(img[sec])load_sector(sec,img[sec]);
   preload=0;repeat(10)@(negedge clk);
   rows=4'(R);ix=24'(i0);base=24'(b0);limit=24'(b0+W);dst=24'(d0);is_=24'(si);as_=24'(sa);os_=24'(so);
   start=1;start_c=cyc;@(negedge clk);start=0;
   wait(done);@(negedge clk);
   if(fixed_cyc[R]<0)fixed_cyc[R]=cyc-start_c;
   if(cyc-start_c!=fixed_cyc[R])begin errors=errors+1;$display("variable schedule R%0d",R);end
   repeat(12)@(negedge clk);readback=1;
   foreach(exp_[sec])begin
    verify_rq=0;bank=bankof(sec*8);verify_rq[bank*17+:17]={1'b1,16'(sec)};
    @(negedge clk);verify_rq=0;repeat(6)@(negedge clk);
    checks=checks+8;
    if(raw_rr[bank*257+256]!==1'b1||raw_rr[bank*257+:256]!==exp_[sec])begin
     if(errors<6)$display("ERR case%0d R%0d sector%0d got%h expected%h",ncase,R,sec,raw_rr[bank*257+:256],exp_[sec]);
     errors=errors+1;
    end
   end
   if(fault!==0||status!==0)begin if(errors<6)$display("FAULT case%0d engine%b",ncase,fault);errors=errors+1;end
   readback=0;repeat(12)@(negedge clk);
   ncase=ncase+1;
  end
 endtask
 initial begin
  for(j=0;j<16;j=j+1)fixed_cyc[j]=-1;
  repeat(8)@(negedge clk);rst_n=1;
  // canonical route gather (route.gather*: I = rid word, A window = gsc 384 scores, O = SEL word), P = 1 and P = 6
  run_case(1,88512,87360,384,88576,0,0,0,1);
  // P = 6 rows: per-position copies of rid / gsc / SEL at a 4,096-word position stride (same banks, II = 1)
  run_case(6,88512,87360,384,88576,4096,4096,4096,1);
  // P = 6 rows, position copies packed one word apart (rows share I / O sectors: word-masked writes per row)
  run_case(6,88512,80000,384,88576,1,384,1,1);
  // rows crossing SIDs / banks (stride 40 Ki + 8 words)
  run_case(6,20000,1000,384,30000,40968,40968,40968,0);
  // row-count sweep R = 1..8 and random strides / windows
  for(c=1;c<=8;c=c+1)run_case(c,90000+c*8,0,32768,120000+c*16,8*rnd(8)+1,4096,8*rnd(8)+3,0);
  for(c=0;c<12;c=c+1)begin
   r=1+rnd(8);
   run_case(r,100000+rnd(4000),rnd(40000),1+rnd(2000),150000+rnd(4000),1+rnd(3000),2000+rnd(3000),1+rnd(3000),0);
  end
  if(errors)$fatal(1,"GATHER_ROWS FAIL checks=%0d errors=%0d",checks,errors);
  $write("GATHER_ROWS PASS checks=%0d cases=%0d banks=32 SRAMs=96 fixed_cycles",checks,ncase);
  for(j=1;j<=8;j=j+1)$write(" R%0d=%0d",j,fixed_cyc[j]);
  $display("");$finish;
 end
endmodule
