`timescale 1ns/1ps
// cont-takeover 2026-10-09: stream equivalence of the registered NK4 score slice (ot_hdc_v41x_idx_score_slice_reg) against
// the bare full-geometry slice (ot_hdc_v41x_idx_score_slice_l), NK=4 IH=32 NB=4 FPL=7 FML=5 QL=5.  Both see the same
// pre-generated tokens (32 query beats, then NBEAT key beats) through their own handshakes and random output
// back-pressure; every score beat {last,kv,score,index,fault} must match in order.  +MUT swaps two key lanes of the
// wrapper's input (negative control).
module tb_idx_slice_reg_equiv;
 localparam integer NK=4,NB=4,IH=32,IW=30,NT=3,NBEAT=24;
 reg clk=0;always #1 clk=~clk;
 reg rst_n=0;
 reg [NB*128-1:0] qcodes[0:NT*IH-1];reg [NB*8-1:0] qsc[0:NT*IH-1];reg [15:0] qw[0:NT*IH-1];
 reg [NK*NB*136-1:0] keys[0:NT*NBEAT-1];reg [NK-1:0] kvm[0:NT*NBEAT-1],kkeep[0:NT*NBEAT-1];
 integer i,j,b;
 function [NB*136-1:0] key4(input integer s);integer z;begin
  for(z=0;z<NB;z=z+1)begin key4[z*136+:128]={$urandom,$urandom,$urandom,$urandom};key4[z*136+128+:8]=8'd120+($urandom%12);end end endfunction
 initial begin
  for(i=0;i<NT*IH;i=i+1)begin
   for(j=0;j<NB*4;j=j+1)qcodes[i][j*32+:32]=$urandom;
   for(j=0;j<NB;j=j+1)qsc[i][j*8+:8]=8'd120+($urandom%12);
   qw[i]=16'h3c00^($urandom&16'h83ff);
  end
  for(i=0;i<NT*NBEAT;i=i+1)begin for(j=0;j<NK;j=j+1)keys[i][j*NB*136+:NB*136]=key4(i*NK+j);kvm[i]=4'hf^($urandom%16==0);kkeep[i]=$urandom; end
 end
 // ---- two DUTs, two drivers
 wire [1:0] qlr,ir,ov,ol;wire [2*NK-1:0] okv,ofl;wire [2*NK*16-1:0] osc;wire [2*NK*IW-1:0] oix;
 reg [1:0] qlv,iv,ordy;reg [7:0] qh[0:1];reg [NB*128-1:0] qc[0:1];reg [NB*8-1:0] qs[0:1];reg [15:0] qww[0:1];
 reg [1:0] il;reg [IW-1:0] ifi[0:1];reg [NK-1:0] ikv[0:1],ikp[0:1];reg [NK*NB*136-1:0] ik[0:1];
 wire [NK*NB*136-1:0] ik1m=$test$plusargs("MUT")?{ik[1][0+:NB*136],ik[1][NB*136+:NB*136],ik[1][2*NB*136+:(NK-2)*NB*136]}:ik[1];
 ot_hdc_v41x_idx_score_slice_l #(.NK(NK),.NB(NB),.IH(IH),.IW(IW),.FPL(7),.FML(5),.QL(5)) ref_(.clk(clk),.rst_n(rst_n),
  .ql_v(qlv[0]),.ql_ready(qlr[0]),.ql_head(qh[0]),.ql_codes(qc[0]),.ql_sc(qs[0]),.ql_w(qww[0]),
  .i_valid(iv[0]),.i_ready(ir[0]),.i_last(il[0]),.i_first_index(ifi[0]),.i_kv(ikv[0]),.i_ref(4'd0),.i_keep(ikp[0]),.i_key(ik[0]),
  .o_valid(ov[0]),.o_ready(ordy[0]),.o_last(ol[0]),.o_kv(okv[0+:NK]),.o_score(osc[0+:NK*16]),.o_index(oix[0+:NK*IW]),.o_fault(ofl[0+:NK]));
 ot_hdc_v41x_idx_score_slice_reg #(.NK(NK),.NB(NB),.IH(IH),.IW(IW),.FPL(7),.FML(5),.QL(5)) dut(.clk(clk),.rst_n(rst_n),
  .ql_v(qlv[1]),.ql_ready(qlr[1]),.ql_head(qh[1]),.ql_codes(qc[1]),.ql_sc(qs[1]),.ql_w(qww[1]),
  .i_valid(iv[1]),.i_ready(ir[1]),.i_last(il[1]),.i_first_index(ifi[1]),.i_kv(ikv[1]),.i_ref(4'd0),.i_keep(ikp[1]),.i_key(ik1m),
  .o_valid(ov[1]),.o_ready(ordy[1]),.o_last(ol[1]),.o_kv(okv[NK+:NK]),.o_score(osc[NK*16+:NK*16]),.o_index(oix[NK*IW+:NK*IW]),.o_fault(ofl[NK+:NK]));
 // per-DUT driver state: phase 0 = query beats, 1 = key beats, 2 = wait drain
 integer tok[0:1],qi[0:1],ki[0:1],ph[0:1],nout[0:1],sent[0:1];
 reg [1+NK+NK*16+NK*IW+NK-1:0] got[0:1][0:NT*NBEAT-1];
 integer d,cyc=0;
 initial begin for(d=0;d<2;d=d+1)begin tok[d]=0;qi[d]=0;ki[d]=0;ph[d]=0;nout[d]=0;sent[d]=0;end
  qlv=0;iv=0;ordy=0;il=0;repeat(5)@(posedge clk);rst_n=1;end
 always @(posedge clk) if(rst_n) begin
  cyc<=cyc+1;
  for(d=0;d<2;d=d+1)begin
   // completed handshakes
   if(qlv[d]&&qlr[d])begin qi[d]=qi[d]+1;if(qi[d]==IH)ph[d]=1;end
   if(iv[d]&&ir[d])begin ki[d]=ki[d]+1;sent[d]=sent[d]+1;if(ki[d]==NBEAT)ph[d]=2;end
   if(ov[d]&&ordy[d])begin got[d][nout[d]]={ol[d],okv[d*NK+:NK],osc[d*NK*16+:NK*16],oix[d*NK*IW+:NK*IW],ofl[d*NK+:NK]};nout[d]=nout[d]+1;end
   if(ph[d]==2&&nout[d]==sent[d]&&tok[d]<NT)begin tok[d]=tok[d]+1;qi[d]=0;ki[d]=0;ph[d]=(tok[d]<NT)?0:3;end
   // next offers (bare slice: query only when ready, as its protocol requires)
   qlv[d]<=0;iv[d]<=0;
   if(ph[d]==0&&tok[d]<NT&&(d==1||qlr[d]))begin qlv[d]<=1;b=tok[d]*IH+qi[d];qh[d]<=qi[d];qc[d]<=qcodes[b];qs[d]<=qsc[b];qww[d]<=qw[b];end
   if(ph[d]==1&&($urandom%5!=0))begin iv[d]<=1;b=tok[d]*NBEAT+ki[d];ik[d]<=keys[b];ikv[d]<=kvm[b];ikp[d]<=kkeep[b];
    ifi[d]<=b*NK;il[d]<=(ki[d]==NBEAT-1);end
   ordy[d]<=($urandom%3!=0);
  end
  if(nout[0]==NT*NBEAT&&nout[1]==NT*NBEAT)begin
   for(i=0;i<NT*NBEAT;i=i+1)if(got[0][i]!==got[1][i])begin $display("IDXSLICE_EQUIV_MISMATCH beat %0d",i);$fatal(1,"mismatch");end
   $display("IDXSLICE_EQUIV_PASS beats=%0d cycles=%0d",NT*NBEAT,cyc);$finish;
  end
  if(cyc>200000)$fatal(1,"timeout ref %0d dut %0d",nout[0],nout[1]);
 end
endmodule
