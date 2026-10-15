`timescale 1ns/1ps
// Native S81 Engram arithmetic leaf. One copy at a time, 160 ordered 32-word
// beats per 5120-word copy. go clears the reduction epoch. phase=0 accumulates
// hh, kk and dd; gate_v publishes this copy's gate. phase=1 replays h/value
// after gate_v, producing BF16 h + gate*value. No weight/key/value fixture here.
// All four copies use the same leaf in order; downstream stores the tagged
// gate and rows before starting another copy. Input/output faces registered.
module ot_s81_engram_mix #(parameter integer N=32, D=5120, LM=5, LA=4, MUT=0)(
 input wire clk,arst_n,go,phase,in_v,
 input wire [1:0] copy,
 input wire [N*32-1:0] h,key,weight,value,
 input wire [31:0] eps,scale,
 output wire gate_v, output wire [1:0] gate_copy,
 output wire [31:0] gate,hh,kk,dd,
 output wire out_v, output wire [1:0] out_copy,
 output wire [N*32-1:0] out_data,
 output wire fault,input wire [30:0] ck_leaf);

 wire g_v;
 wire [31:0] a_gate,g_x,gy;wire [63:0] norm_rstd;
 wire [7:0] mvalid,mfault,add_copy;wire [3:0] avalid,af;wire [1023:0] hd,kd,dot,oy;
 // Physical hierarchy (S-ELEM-C 2026-10-15, results/arch/s81_mix4_phys_plan_1015): the scalar row (control, gate,
 // norms) sits above the reduction rows, ~925 um from the add8 row and ~805 um from the mul4 / add8 status bits.
 // Those two edges cross ONE registered relay leaf (ot_s81_engram_rly, on the control's root): a_gate is held from
 // eg_valid until the next go, >= VM_LAT + 3 cycles before the first ADD issue, so the relay costs no cycle; the
 // status bits only feed the control's fixed-calendar checks, whose reference lines are lengthened by RLY.  The
 // chunk8 / sum valids are taken from the mul4 of their own column (mvalid[2c]; all mul4 run in lockstep and the
 // control checks it), not one mvalid[0] broadcast across the cluster.
 localparam integer RLY=1;
 wire [7:0] mvalid_r,mfault_r,add_copy_r;wire [3:0] avalid_r,af_r;wire [31:0] a_gate_r;
 ot_s81_engram_rly relay(clk,arst_n,a_gate,{mvalid,mfault,add_copy,avalid,af},a_gate_r,{mvalid_r,mfault_r,add_copy_r,avalid_r,af_r});
 wire [1:0] nv,nf;wire eg_valid;wire [1:0] g_fault;wire [383:0] chunk_sums;wire [11:0] chunk_fault,chunk_valid;wire [2:0] rv,rf;wire [31:0] rhh,rkk,rdd;
 ot_s81_engram_mix_control #(.N(N),.D(D),.LM(LM),.LA(LA),.MUT(MUT),.RLY(RLY)) control(
  .clk(clk),.arst_n(arst_n),.go(go),.phase(phase),.in_v(in_v),.copy(copy),.scale(scale),
  .gate_v(gate_v),.gate_copy(gate_copy),.gate(gate),.hh(hh),.kk(kk),.dd(dd),.fault(fault),
  .g_v(g_v),.a_gate(a_gate),.g_x(g_x),
  .mvalid(mvalid_r),.mfault(mfault_r),.avalid(avalid_r),.af(af_r),.add_copy(add_copy_r),.nv(nv),.nf(nf),.norm_rstd(norm_rstd),.eg_valid(eg_valid),.g_fault(g_fault),.gy(gy),.rv(rv),.rf(rf),.rhh(rhh),.rkk(rkk),.rdd(rdd));
 ot_s81_engram_sum #(.N(N),.D(D),.LA(LA)) hsum(ck_leaf[23],arst_n,go,mvalid[2],rv[0],rhh,rf[0],chunk_sums[0+:128],chunk_fault[0+:4],chunk_valid[0+:4]);
 ot_s81_engram_sum #(.N(N),.D(D),.LA(LA)) ksum(ck_leaf[24],arst_n,go,mvalid[2],rv[1],rkk,rf[1],chunk_sums[128+:128],chunk_fault[4+:4],chunk_valid[4+:4]);
 ot_s81_engram_sum #(.N(N),.D(D),.LA(LA)) dsum(ck_leaf[25],arst_n,go,mvalid[4],rv[2],rdd,rf[2],chunk_sums[256+:128],chunk_fault[8+:4],chunk_valid[8+:4]);
 genvar group,r,c;
 generate for(group=0;group<8;group=group+1)begin:g_mult
  ot_s81_engram_mul4 #(.LM(LM),.MUT(MUT)) leaf(ck_leaf[(group%2)?(26+group/2):(group/2)],arst_n,in_v,phase,
   h[128*group+:128],key[128*group+:128],weight[128*group+:128],
   mvalid[group],hd[128*group+:128],kd[128*group+:128],dot[128*group+:128],mfault[group]);
 end
 for(r=0;r<3;r=r+1)begin:g_reduce
  wire [1023:0] x=(r==0)?hd:(r==1)?kd:dot;
  for(c=0;c<4;c=c+1)begin:g_chunk
   ot_s81_engram_chunk8 #(.LA(LA)) leaf(ck_leaf[4+4*r+c],arst_n,mvalid[2*c],x[256*c+:256],
    chunk_valid[4*r+c],chunk_sums[32*(4*r+c)+:32],chunk_fault[4*r+c]);
  end
 end
 for(group=0;group<4;group=group+1)begin:g_add
  ot_s81_engram_add8 #(.LM(LM),.LA(LA)) leaf(ck_leaf[16+group],arst_n,in_v,phase,
   h[256*group+:256],value[256*group+:256],a_gate_r,copy,avalid[group],oy[256*group+:256],af[group],add_copy[2*group+:2]);
 end
 for(group=0;group<2;group=group+1)begin:g_norm
  ot_s81_engram_norm #(.LM(LM),.LA(LA)) leaf(ck_leaf[20+group],arst_n,rv[group],group==0?rhh:rkk,eps,nv[group],norm_rstd[32*group+:32],nf[group]);
 end endgenerate
 ot_s81_engram_gate #(.LM(LM),.LA(LA)) gate_leaf(ck_leaf[22],arst_n,g_v,g_x,eg_valid,gy,g_fault,ck_leaf[30]);
 assign out_v=avalid[0];assign out_data=oy;assign out_copy=add_copy[1:0];

endmodule

module ot_s81_engram_mix_control #(parameter integer N=32, D=5120, LM=5, LA=4, MUT=0, RLY=0)(
 input wire clk,arst_n,go,phase,in_v,
 input wire [1:0] copy,
 input wire [31:0] scale,
 output reg gate_v, output reg [1:0] gate_copy,
 output reg [31:0] gate,hh,kk,dd,
 output reg fault,
 output wire g_v,
 output wire [31:0] a_gate,g_x,
 input wire [7:0] mvalid,mfault,input wire [3:0] avalid,af,input wire [7:0] add_copy,
 input wire [1:0] nv,nf,input wire [63:0] norm_rstd,
 input wire eg_valid,input wire [1:0] g_fault,input wire [31:0] gy,
 input wire [2:0] rv,rf,input wire [31:0] rhh,rkk,rdd);

 wire rst_n;
 ot_s81_engram_reset root_reset(clk,arst_n,rst_n);
 localparam integer NV=D/N, GD=1+31+1+(7*LM+8*LA+4)+LA+19;
 initial begin
  if(N!=32 || D!=5120 || D%N || N<8 || (N&(N-1))) $fatal(1,"Engram shape must use whole power-of-two chunk8 beats");
 end
 reg epoch,gate_ready;reg [1:0] epoch_copy;
 reg [15:0] nreduce,nadd,nout;
 wire input_ok=epoch && copy==epoch_copy && (phase?((gate_ready||gate_v)&&nadd<NV):(nreduce<NV&&!gate_ready));
 reg protocol_fault;
 always @(posedge clk or negedge rst_n) if(!rst_n)begin
  epoch<=0;gate_ready<=0;nreduce<=0;nadd<=0;nout<=0;epoch_copy<=0;protocol_fault<=0;
 end else begin
  if(go)begin
   if(epoch)protocol_fault<=1;
   epoch<=1;epoch_copy<=copy;gate_ready<=0;nreduce<=0;nadd<=0;nout<=0;
  end
  if(in_v)begin
   if(!input_ok || go)protocol_fault<=1;
   else if(phase)nadd<=nadd+1;else nreduce<=nreduce+1;
  end
  if(gate_v)gate_ready<=1;
  if(avalid[0])begin if(add_copy!={4{copy}})protocol_fault<=1; nout<=nout+1;if(nout==NV-1)epoch<=0;end
 end
 wire [2*LM+2+RLY:0] mv;
 ot_hdc_vline #(.D(2*LM+2+RLY)) u_mv(clk,rst_n,in_v&&!phase,mv);
 wire [31:0] rn[0:1];assign rn[0]=norm_rstd[0+:32];assign rn[1]=norm_rstd[32+:32];
 reg [31:0] d_hold; reg [1:0] copy_hold;
 always @(posedge clk) begin if(go) copy_hold<=copy; if(rv[2]) d_hold<=rdd; end
 wire [3*LM:0] gv;
 ot_hdc_vline #(.D(3*LM)) vgp(clk,rst_n,nv[0]&&nv[1],gv);
 wire [31:0] rstd,gd,scaled,dh; wire [2:0] gf;
 ot_hdc_qmul_lat #(LM) mg0(clk,rst_n,gv[0],rn[0],rn[1],rstd,gf[0]);
 ot_hdc_delay #(.W(32),.D(LM)) ddp(clk,rst_n,d_hold,dh);
 ot_hdc_qmul_lat #(LM) mg1(clk,rst_n,gv[LM],dh,rstd,gd,gf[1]);
 ot_hdc_qmul_lat #(LM) mg2(clk,rst_n,gv[2*LM],gd,scale,scaled,gf[2]);
 reg [31:0] gate_hold;
 always @(posedge clk)if(eg_valid)gate_hold<=gy;
 localparam integer AD=LM+LA+2+RLY;
 wire [AD:0] av_expected;wire [GD+3:0] gv_expected;
 ot_hdc_vline #(.D(AD)) add_calendar(clk,rst_n,in_v&&phase,av_expected);
 ot_hdc_vline #(.D(GD+3)) gate_calendar(clk,rst_n,gv[3*LM],gv_expected);
 always @(posedge clk or negedge rst_n) if(!rst_n) begin gate_v<=0;fault<=0; end
 else begin
  gate_v<=eg_valid;
  if(eg_valid) begin gate<=gy;gate_copy<=copy_hold;end
  if(rv[0]) hh<=rhh;if(rv[1]) kk<=rkk;if(rv[2]) dd<=rdd;
  if(mvalid!={8{mv[2*LM+2+RLY]}}||avalid!={4{av_expected[AD]}}||eg_valid!=gv_expected[GD+3]||nv[0]!=nv[1]||(rv!=0&&rv!=7)||protocol_fault||(|mfault)||(|rf)||(|nf)||(|gf)||(|g_fault)||(|af)) fault<=1;
 end

 assign a_gate=gate_hold;
 assign g_v=gv[3*LM];assign g_x=scaled;

endmodule

module ot_s81_engram_sum #(parameter integer N=32,D=5120,LA=4)(
 input wire clk,arst_n,go,v,
 output reg vo,output reg [31:0] y,output reg fault,
 input wire [N/8*32-1:0] chunks,input wire [N/8-1:0] chunk_fault,chunk_valid);
 wire rst_n;ot_s81_engram_reset root_reset(clk,arst_n,rst_n);
 localparam integer NC=N/8,LT=$clog2(NC),NV=D/N,NP=1<<$clog2(NV),DS=1+(8+LT)*LA;
 reg [$clog2(NV)-1:0] idx;
 always @(posedge clk or negedge rst_n) if(!rst_n) idx<=0;else if(go)idx<=0;else if(v)idx<=idx+1;
 wire [DS:0] vd; ot_hdc_vline #(.D(DS)) vp(clk,rst_n,v,vd);
 wire [$clog2(NV)-1:0] si;
 ot_hdc_delay #(.W($clog2(NV)),.D(DS)) ip(clk,rst_n,idx,si);
 wire [31:0] tv[0:LT][0:NC-1];wire [NC-1:0] cf;wire [NC-1:0] tf[0:LT];
 assign cf=chunk_fault;
 genvar c,k;
 generate for(c=0;c<NC;c=c+1)begin:chunks_root
  assign tv[0][c]=chunks[32*c+:32];
 end
 for(k=0;k<=LT;k=k+1)begin:tree
  if(k==0)assign tf[k]=0;else begin
   for(c=0;c<NC;c=c+1)begin:node
    if(c<(NC>>k))begin
     ot_dsrom_qadd #(.LAT(LA)) ad(clk,rst_n,vd[1+(8+k-1)*LA],tv[k-1][2*c],tv[k-1][2*c+1],tv[k][c],tf[k][c]);
    end else begin assign tv[k][c]=0;assign tf[k][c]=0;end
   end
  end
 end endgenerate
 // Online binary tree: one held left operand per level. Finish the row with
 // scalar +0 padding to NP beats, preserving canonical chunk8 reduction order
 // without retaining 256 vector leaves or building a neighbour chain.
 localparam integer TL=$clog2(NP);
 reg pad;reg [TL:0] pi;
 always @(posedge clk or negedge rst_n)if(!rst_n)begin pad<=0;pi<=0;end
 else if(go)begin pad<=0;pi<=0;end
 else if(vd[DS]&&si==NV-1)begin pad<=NV<NP;pi<=NV;end
 else if(pad)begin pi<=pi+1;if(pi==NP-1)pad<=0;end
 wire [31:0] val[0:TL];wire pulse[0:TL];wire [TL:0] index[0:TL];wire [TL-1:0] ff;
 assign val[0]=pad?32'd0:tv[LT][0];assign pulse[0]=pad||vd[DS];assign index[0]=pad?pi:si;
 genvar n;
 generate for(n=0;n<TL;n=n+1)begin:level
  reg [31:0] left;reg have;
  wire fire=pulse[n]&&index[n][0]&&have;
  wire [LA:0] av;wire [TL:0] next_index;
  ot_hdc_vline #(.D(LA)) vp(clk,rst_n,fire,av);
  ot_hdc_delay #(.W(TL+1),.D(LA)) ip(clk,rst_n,index[n]>>1,next_index);
  ot_dsrom_qadd #(.LAT(LA)) ad(clk,rst_n,fire,left,val[n],val[n+1],ff[n]);
  always @(posedge clk or negedge rst_n)if(!rst_n)have<=0;
  else if(go)have<=0;else if(pulse[n])have<=!index[n][0];
  always @(posedge clk)if(pulse[n]&&!index[n][0])left<=val[n];
  assign pulse[n+1]=av[LA];assign index[n+1]=next_index;
 end endgenerate
 always @(posedge clk or negedge rst_n)if(!rst_n)vo<=0;else vo<=pulse[TL]&&!go;
 always @(posedge clk)if(pulse[TL]&&!go)y<=val[TL];
 reg ft;integer i;
 always @*begin ft=|cf||(|ff)||chunk_valid!={NC{vd[1+8*LA]}};for(i=0;i<=LT;i=i+1)ft=ft||(|tf[i]);end
 always @(posedge clk or negedge rst_n)if(!rst_n)fault<=0;else if(ft)fault<=1;
endmodule

// Every physical arithmetic leaf conditions die reset on its own compensated
// clock root. A parent's already released reset is never reused across roots.
module ot_s81_engram_reset(input wire clk,arst_n,output wire rst_n);
 reg [1:0] sync;
 always @(posedge clk or negedge arst_n)if(!arst_n)sync<=0;else sync<={sync[0],1'b1};
 assign rst_n=sync[1];
endmodule

module ot_s81_engram_mul4 #(parameter integer LM=5,MUT=0)(
 input wire clk,arst_n,v,phase,input wire [127:0] h,k,w,
 output wire vo,output wire [127:0] hh,kk,dot,output reg fault);
 wire rn;ot_s81_engram_reset reset_leaf(clk,arst_n,rn);
 reg [127:0] hr,kr,wr;reg vr;
 always @(posedge clk or negedge rn)if(!rn)vr<=0;else vr<=v&&!phase;
 always @(posedge clk)begin hr<=h;kr<=k;wr<=w;end
 wire [2*LM:0] vp;ot_hdc_vline #(.D(2*LM)) valid_line(clk,rn,vr,vp);
 wire [127:0] hs,ks,hw;wire [15:0] f;
 genvar l;
 generate for(l=0;l<4;l=l+1)begin:lane
  wire [31:0] kd;
  ot_hdc_qmul_lat #(LM) mh(clk,rn,vr,hr[32*l+:32],hr[32*l+:32],hs[32*l+:32],f[4*l]);
  ot_hdc_qmul_lat #(LM) mk(clk,rn,vr,kr[32*l+:32],kr[32*l+:32],ks[32*l+:32],f[4*l+1]);
  ot_hdc_qmul_lat #(LM) mw(clk,rn,vr,hr[32*l+:32],wr[32*l+:32],hw[32*l+:32],f[4*l+2]);
  ot_hdc_delay #(.W(32),.D(LM)) key_line(clk,rn,kr[32*l+:32],kd);
  wire [31:0] dr;
  ot_hdc_qmul_lat #(LM) md(clk,rn,vp[LM],hw[32*l+:32],(MUT==1)?32'h3f800000:kd,dr,f[4*l+3]);
  reg [31:0] dout;always @(posedge clk)dout<=dr;assign dot[32*l+:32]=dout;
 end endgenerate
 wire [127:0] hmid,kmid;
 ot_hdc_delay #(.W(128),.D(LM+1)) hline(clk,rn,hs,hmid);
 ot_hdc_delay #(.W(128),.D(LM+1)) kline(clk,rn,ks,kmid);
 assign hh=hmid;assign kk=kmid;
 reg valid;always @(posedge clk or negedge rn)if(!rn)valid<=0;else valid<=vp[2*LM];
 assign vo=valid;wire raw_fault=|f;
 always @(posedge clk or negedge rn)if(!rn)fault<=0;else if(raw_fault)fault<=1;
endmodule

module ot_s81_engram_chunk8 #(parameter integer LA=4)(
 input wire clk,arst_n,v,input wire [255:0] x,
 output wire vo,output wire [31:0] sum,output reg fault);
 wire rn;ot_s81_engram_reset reset_leaf(clk,arst_n,rn);
 reg [255:0] xr;reg vr;
 always @(posedge clk or negedge rn)if(!rn)vr<=0;else vr<=v;
 always @(posedge clk)xr<=x;
 wire [8*LA:0] vp;ot_hdc_vline #(.D(8*LA)) valid_line(clk,rn,vr,vp);
 wire [31:0] acc[0:8];wire [7:0] f;assign acc[0]=0;
 genvar t;
 generate for(t=0;t<8;t=t+1)begin:term
  wire [31:0] xd;
  ot_hdc_delay #(.W(32),.D(LA*t)) operand_line(clk,rn,xr[32*t+:32],xd);
  ot_dsrom_qadd #(.LAT(LA)) add(clk,rn,vp[LA*t],acc[t],xd,acc[t+1],f[t]);
 end endgenerate
 assign vo=vp[8*LA];assign sum=acc[8];wire raw_fault=|f;
 always @(posedge clk or negedge rn)if(!rn)fault<=0;else if(raw_fault)fault<=1;
endmodule

module ot_s81_engram_norm #(parameter integer LM=5,LA=4)(
 input wire clk,arst_n,v,input wire [31:0] sum,eps,
 output wire vo,output wire [31:0] rstd,output reg fault);
 wire rn;ot_s81_engram_reset reset_leaf(clk,arst_n,rn);
 reg vr;reg [31:0] sr,er;
 always @(posedge clk or negedge rn)if(!rn)vr<=0;else vr<=v;
 always @(posedge clk)begin sr<=sum;er<=eps;end
 wire [31:0] mean,me;wire dv;wire [LA:0] ev;wire [2:0] f;
 ot_dsrom_divc #(.F(5),.K(10)) divide(clk,rn,vr,sr,mean,dv,f[0]);
 ot_hdc_vline #(.D(LA)) valid_line(clk,rn,dv,ev);
 ot_dsrom_qadd #(.LAT(LA)) epsilon(clk,rn,dv,mean,er,me,f[1]);
 ot_dsrom_rsqrt #(.LM(LM),.LA(LA)) rsqrt(clk,rn,ev[LA],me,rstd,vo,f[2]);
 wire raw_fault=|f;
 always @(posedge clk or negedge rn)if(!rn)fault<=0;else if(raw_fault)fault<=1;
endmodule

module ot_s81_engram_gate #(parameter integer LM=5,LA=4)(
 input wire clk,arst_n,v,input wire [31:0] x,
 output wire vo,output wire [31:0] y,output wire [1:0] fault,input wire clk_sigmoid);
 wire sqrt_v;wire [31:0] signed_sqrt;
 ot_s81_engram_signed_sqrt #(.LM(LM),.LA(LA)) magnitude(clk,arst_n,v,x,sqrt_v,signed_sqrt,fault[0]);
 ot_s81_engram_sigmoid #(.LM(LM),.LA(LA)) sigmoid(clk_sigmoid,arst_n,sqrt_v,signed_sqrt,vo,y,fault[1]);
endmodule

module ot_s81_engram_signed_sqrt #(parameter integer LM=5,LA=4)(
 input wire clk,arst_n,v,input wire [31:0] x,
 output reg vo,output reg [31:0] y,output reg fault);
 wire rn;ot_s81_engram_reset reset_leaf(clk,arst_n,rn);
 reg vr;reg [31:0] xr;
 always @(posedge clk or negedge rn)if(!rn)vr<=0;else vr<=v;
 always @(posedge clk)xr<=x;
 localparam integer KS=(LM!=3||LA!=3)?1:0;
 reg [31:0] mag;reg mv;reg [31:0] signs;
 wire [31:0] absx={1'b0,xr[30:0]};wire clamp;
 ot_hdc_kge #(.W(32),.K(KS)) compare(.a(32'h358637bd),.b(absx),.ge(clamp));
 always @(posedge clk or negedge rn)if(!rn)mv<=0;else mv<=vr;
 always @(posedge clk)begin mag<=clamp?32'h358637bd:absx;signs<={signs[30:0],xr[31]&&(xr[30:0]!=0)};end
 wire [31:0] root;wire root_v,root_fault;
 ot_hdc_fsqrt sqrt(.clk(clk),.rst_n(rn),.v(mv),.a(mag),.y(root),.vo(root_v),.fault(root_fault));
 always @(posedge clk or negedge rn)if(!rn)vo<=0;else vo<=root_v;
 always @(posedge clk)y<={root[31]^signs[31],root[30:0]};
 always @(posedge clk or negedge rn)if(!rn)fault<=0;else if(root_fault)fault<=1;
endmodule

module ot_s81_engram_sigmoid #(parameter integer LM=5,LA=4)(
 input wire clk,arst_n,v,input wire [31:0] x,
 output reg vo,output reg [31:0] y,output reg fault);
 localparam integer DE=7*LM+8*LA+4,DS=DE+LA+19,KS=(LM!=3||LA!=3)?1:0;
 wire rn;ot_s81_engram_reset reset_leaf(clk,arst_n,rn);
 reg vr;reg [31:0] xr;
 always @(posedge clk or negedge rn)if(!rn)vr<=0;else vr<=v;
 always @(posedge clk)xr<=x;
 wire [31:0] expy,den,quot;wire [2:0] f;wire [DE:0] ev;wire [LA:0] dv;wire [DS:0] sv;
 ot_hdc_vline #(.D(DE)) exp_calendar(clk,rn,vr,ev);
 ot_hdc_v41x_exp #(.LM(LM),.LA(LA)) exp(.clk(clk),.rst_n(rn),.v(vr),.x({~xr[31],xr[30:0]}),.y(expy),.vo(),.fault(f[0]));
 ot_hdc_qadd_lat #(.KEEP(KS),.LAT(LA)) plus_one(clk,rn,ev[DE],expy,32'h3f800000,den,f[1]);
 ot_hdc_vline #(.D(LA)) den_calendar(clk,rn,ev[DE],dv);
 ot_hdc_v41x_fdiv divide(.clk(clk),.rst_n(rn),.v(dv[LA]),.a(32'h3f800000),.b(den),.y(quot),.vo(),.fault(f[2]));
 ot_hdc_vline #(.D(DS)) output_calendar(clk,rn,vr,sv);
 always @(posedge clk or negedge rn)if(!rn)vo<=0;else vo<=sv[DS];
 always @(posedge clk)y<=quot;
 always @(posedge clk or negedge rn)if(!rn)fault<=0;else if(|f)fault<=1;
endmodule

module ot_s81_engram_add8 #(parameter integer LM=5,LA=4)(
 input wire clk,arst_n,v,phase,input wire [255:0] h,value,input wire [31:0] gate,input wire [1:0] copy,
 output reg vo,output reg [255:0] y,output reg fault,output wire [1:0] copy_out);
 wire rn;ot_s81_engram_reset reset_leaf(clk,arst_n,rn);
 reg vr;reg [255:0] hr,valr;reg [31:0] gr;
 always @(posedge clk or negedge rn)if(!rn)vr<=0;else vr<=v&&phase;
 always @(posedge clk)begin hr<=h;valr<=value;gr<=gate;end
 wire [LM+LA:0] vp;ot_hdc_vline #(.D(LM+LA)) valid_line(clk,rn,vr,vp);
 wire [15:0] f;
 genvar l;
 generate for(l=0;l<8;l=l+1)begin:lane
  wire [31:0] prod,hd,ys;
  ot_hdc_qmul_lat #(LM) mul(clk,rn,vr,valr[32*l+:32],gr,prod,f[2*l]);
  ot_hdc_delay #(.W(32),.D(LM)) hline(clk,rn,hr[32*l+:32],hd);
  ot_dsrom_qadd #(.LAT(LA)) add(clk,rn,vp[LM],hd,prod,ys,f[2*l+1]);
  wire [31:0] rounded=ys+32'h7fff+ys[16];
  always @(posedge clk)y[32*l+:32]<={rounded[31:16],16'd0};
 end endgenerate
 always @(posedge clk or negedge rn)if(!rn)vo<=0;else vo<=vp[LM+LA];
 wire raw_fault=|f;
 always @(posedge clk or negedge rn)if(!rn)fault<=0;else if(raw_fault)fault<=1;
 ot_hdc_delay #(.W(2),.D(LM+LA+2)) copy_line(clk,rn,copy,copy_out);
endmodule

// Registered relay leaf (S-ELEM-C 2026-10-15): one stage each way between the control row and the mul4 / add8 rows,
// on the control's clock root (own leaf, own clock entry).  Data/valid only; reset releases on its own root.
module ot_s81_engram_rly(input wire clk,arst_n,input wire [31:0] gate_i,input wire [31:0] st_i,
 output reg [31:0] gate_o,output reg [31:0] st_o);
 wire rn;ot_s81_engram_reset reset_leaf(clk,arst_n,rn);
 always @(posedge clk)gate_o<=gate_i;
 always @(posedge clk or negedge rn)if(!rn)st_o<=0;else st_o<=st_i;
endmodule
