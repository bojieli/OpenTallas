`timescale 1ns/1ps
// S81 Engram MIX, four parallel copy clusters (capacity repair of dsfd_engram_mix_c,
// which ran the four residual copies in sequence: 2982 cycles vs 871.2 priced).
//
// One command (same descriptor format as dsfd_engram_mix_c: arg[13:0] = descriptor
// VM row, arg[23:14] = 0) runs all four copies at once on four identical clusters
// ot_s81_engram_mixq, each = one exact ot_s81_engram_mix arithmetic leaf set
// (unchanged) + its own static row sequencer, on its own 33 clock roots.
//
// Static schedule, no credit/ready/backpressure anywhere in this master:
//  * the top reads the descriptor ONCE (physical lane 0, before any cluster
//    issues) and broadcasts {start, descriptor} through BC registered stages, equal
//    depth to every cluster, so the four clusters run cycle-identical calendars;
//  * physical read lanes 5q..5q+4 belong to cluster q (H, K0, K1, W0, W1); in the
//    ADD phase the shared V row pair is read ONCE on cluster 0's lanes 1,2 and the
//    registered return is broadcast to all four clusters (one bank access, no
//    replicated V image); clusters 1..3 issue no physical V request;
//  * each cluster owns one write lane (4W) in its reserved slot;
//  * a fixed four-done join: every cluster must report done in the same cycle,
//    any skew/early/late done or any cluster fault is a sticky fault (c_st[0]);
//    completion is never re-timed by waiting.
// Every request and return passes one registered top stage each way; clusters see
// the published VM latency + 2 and check it exactly (lost/late reply = fault).
// The command/completion pins use the shared ot_s81_slab_ep endpoint (as every S81
// slab master); its inherited adapter is owned by the static control stream.
// MUT (negative controls): 1 key->1.0 data mutant inside every multiplier leaf;
// 2 cluster 3 reads copy 2's H rows (address/lane map); 3 the V broadcast tree
// hands clusters 1..3 the previous beat's V row pair (stale broadcast stage).
module dsfd_engram_mix4_c #(parameter integer MUT=0, VM_LAT=1, WRITE_COMMIT_LAT=1, BC=2)(
 input wire [132:0] ck,              // ck[0] top; ck[1+33q +: 33] cluster q roots
 input wire [0:0] rst,input wire [84:0] c_cmd,
 output wire [8:0] c_done,output wire [1:0] c_st,input wire [0:0] f_inp,
 output reg [19:0] rq_v,output reg [279:0] rq_row,
 input wire [19:0] rs_v,input wire [10239:0] rs_d,
 output wire [3:0] wq_v,output wire [55:0] wq_row,
 output wire [63:0] wq_mask,output wire [2047:0] wq_d);

 reg [1:0] reset_sync;
 always @(posedge ck[0] or negedge rst[0])if(!rst[0])reset_sync<=0;else reset_sync<={reset_sync[0],1'b1};
 wire rn=reset_sync[1];
 wire jv,jnew,epf;wire [83:0] jd,jnd;reg done,fault;reg inp_q;
 always @(posedge ck[0] or negedge rn)if(!rn)inp_q<=0;else inp_q<=f_inp[0];
 ot_s81_slab_ep ep(.c_clk(ck[0]),.c_rst_n(rn),.c_cmd(c_cmd),.c_done(c_done),.c_st(c_st),
  .e_clk(ck[0]),.e_rst_n(rn),.j_v(jv),.j_d(jd),.j_new(jnew),.j_new_d(jnd),.j_present(1'b1),.j_done(done),.slab_fault(fault),.ep_fault(epf));

 // ---- cluster interfaces
 wire [19:0] c_rqv;wire [279:0] c_rqrow;wire [3:0] c_vtag;   // vtag: this cycle's lanes 1,2 request is V
 wire [3:0] c_done_q,c_fault_q;
 reg [19:0] l_rsv;reg [10239:0] l_rsd;                        // returns delivered to the clusters
 reg [BC:0] st_line;reg [223:0] desc_line[0:BC];

 // ---- descriptor read (top), static: issued only while every cluster is idle
 reg [2:0] tstate;localparam T_IDLE=0,T_DESC=1,T_RUN=2,T_DONE=3,T_POP=4;
 reg desc_rq;reg [1023:0] v_prev;
 // registered request stage: lane 0 of cluster 0 doubles as descriptor reader,
 // lanes 1,2 of clusters 1..3 are suppressed for V (cluster 0 reads V once).
 integer q,l;
 always @(posedge ck[0] or negedge rn)if(!rn)begin rq_v<=0;rq_row<=0;end else begin
  rq_v<=c_rqv;rq_row<=c_rqrow;
  for(q=1;q<4;q=q+1)if(c_vtag[q])begin rq_v[5*q+1]<=0;rq_v[5*q+2]<=0;end
  if(desc_rq)begin rq_v[0]<=1'b1;rq_row[0+:14]<=jd[7+:14];end
 end
 // fixed-latency tag lines: request flop (+1) -> VM (VM_LAT) -> return pin flop (+1)
 localparam integer TL=VM_LAT+1;
 reg [TL:0] dtag;reg [TL:0] vtag;
 always @(posedge ck[0] or negedge rn)if(!rn)begin dtag<=0;vtag<=0;end else begin
  dtag<={dtag[TL-1:0],desc_rq};vtag<={vtag[TL-1:0],c_vtag[0]};
 end
 reg [19:0] rvq;reg [10239:0] rdq;
 always @(posedge ck[0] or negedge rn)if(!rn)rvq<=0;else rvq<=rs_v;
 always @(posedge ck[0])rdq<=rs_d;
 // return demux (combinational after the registered pin stage; the clusters
 // capture in their own rvq/rdq flops)
 always @*begin
  l_rsv=rvq;l_rsd=rdq;
  if(dtag[TL])begin l_rsv[0]=1'b0;end
  for(q=0;q<4;q=q+1)if(vtag[TL])begin
   l_rsv[5*q+1]=rvq[1];l_rsv[5*q+2]=rvq[2];
   l_rsd[2560*q+512+:1024]=(MUT==3&&q!=0)?v_prev:rdq[512+:1024];
  end
 end

 always @(posedge ck[0] or negedge rn)if(!rn)begin
  tstate<=T_IDLE;desc_rq<=0;done<=0;fault<=0;st_line<=0;
 end else begin
  desc_rq<=0;done<=0;st_line<={st_line[BC-1:0],1'b0};
  if(epf||(|c_fault_q))fault<=1;
  if(dtag[TL]&&!rvq[0])fault<=1;                      // lost descriptor reply
  if(desc_rq&&c_rqv[0])fault<=1;                          // lane 0 reservation clash
  if(c_vtag!=4'b0000&&c_vtag!=4'b1111)fault<=1;           // clusters out of lockstep
  case(tstate)
  T_IDLE:if(jv&&!fault)begin
   if(!inp_q||jd[30:21]!=0)fault<=1;else begin desc_rq<=1;tstate<=T_DESC;end
  end
  T_DESC:if(dtag[TL])begin
   if(rdq[0+:32]>15744||rdq[32+:32]>15104||rdq[64+:32]>15104||rdq[96+:32]>16064||rdq[128+:32]>15744)fault<=1;
   if((rdq[128+:32]!=rdq[0+:32] && rdq[128+:32]<rdq[0+:32]+640 && rdq[0+:32]<rdq[128+:32]+640) ||
      (rdq[128+:32]<rdq[32+:32]+1280 && rdq[32+:32]<rdq[128+:32]+640) ||
      (rdq[128+:32]<rdq[64+:32]+1280 && rdq[64+:32]<rdq[128+:32]+640) ||
      (rdq[128+:32]<rdq[96+:32]+320 && rdq[96+:32]<rdq[128+:32]+640))fault<=1;
   if(rdq[191] || rdq[183+:8]==255 || rdq[160+:31]==0 || rdq[223] || rdq[215+:8]==255 || rdq[192+:31]==0)fault<=1;
   st_line[0]<=1'b1;tstate<=T_RUN;
  end
  T_RUN:begin
   // four-done join: all four in the same cycle, or fault
   if(|c_done_q)begin if(c_done_q!=4'b1111)fault<=1;tstate<=T_DONE;end
  end
  T_DONE:begin done<=!fault&&!epf;tstate<=T_POP;end
  T_POP:tstate<=T_IDLE;                                   // queue head pops with done
  default:fault<=1;
  endcase
 end
 always @(posedge ck[0])begin
  desc_line[0]<=(tstate==T_DESC&&dtag[TL])?rdq[0+:224]:desc_line[0];
  if(vtag[TL])v_prev<=rdq[512+:1024];
 end
 genvar s,c;
 generate for(s=1;s<=BC;s=s+1)begin:bc_tree
  always @(posedge ck[0])desc_line[s]<=desc_line[s-1];
 end
 for(c=0;c<4;c=c+1)begin:cl
  ot_s81_engram_mixq #(.CL(c),.MUT(MUT),.VM_LAT(VM_LAT+2),.WRITE_COMMIT_LAT(WRITE_COMMIT_LAT)) u(
   .ck(ck[1+33*c+:33]),.rst(rst[0]),.start(st_line[BC]),.desc(desc_line[BC]),
   .rq_v(c_rqv[5*c+:5]),.rq_row(c_rqrow[70*c+:70]),.vtag(c_vtag[c]),
   .rs_v(l_rsv[5*c+:5]),.rs_d(l_rsd[2560*c+:2560]),
   .wq_v(wq_v[c]),.wq_row(wq_row[14*c+:14]),.wq_mask(wq_mask[16*c+:16]),.wq_d(wq_d[512*c+:512]),
   .done(c_done_q[c]),.fault(c_fault_q[c]));
 end endgenerate
endmodule

// One copy cluster: static row sequencer + the unchanged exact arithmetic leaf.
// Copy index CL is fixed by placement; lanes: 0 H, 1-2 K (REDUCE) / V (ADD, vtag), 3-4 W.
module ot_s81_engram_mixq #(parameter integer CL=0, MUT=0, VM_LAT=3, WRITE_COMMIT_LAT=1)(
 input wire [32:0] ck,input wire rst,input wire start,input wire [223:0] desc,
 output wire [4:0] rq_v,output wire [69:0] rq_row,output wire vtag,
 input wire [4:0] rs_v,input wire [2559:0] rs_d,
 output wire wq_v,output wire [13:0] wq_row,output wire [15:0] wq_mask,output wire [511:0] wq_d,
 output wire done,output wire fault);
 // Wires-only composition: shell owns ck[0] state; arithmetic keeps ck[1:32].
 wire go,iv,phase,gv,ov,mf;wire [1:0] copy,gc,oc;
 wire [1023:0] h,kv,w,result;wire [31:0] eps,scale,gate,hh,kk,dd;
 ot_s81_engram_mixq_shell #(.CL(CL),.MUT(MUT),.VM_LAT(VM_LAT),.WRITE_COMMIT_LAT(WRITE_COMMIT_LAT)) shell(
  .ck(ck[0]),.rst(rst),.start(start),.desc(desc),
  .rq_v(rq_v),.rq_row(rq_row),.vtag(vtag),.rs_v(rs_v),.rs_d(rs_d),
  .wq_v(wq_v),.wq_row(wq_row),.wq_mask(wq_mask),.wq_d(wq_d),.done(done),.fault(fault),
  .go(go),.iv(iv),.phase(phase),.copy(copy),.h(h),.kv(kv),.w(w),.eps(eps),.scale(scale),
  .gv(gv),.gc(gc),.ov(ov),.oc(oc),.result(result),.mf(mf));
 ot_s81_engram_mix #(.MUT(MUT==1?1:0)) mix(ck[1],rst,go,phase,iv,copy,h,kv,w,kv,eps,scale,
  gv,gc,gate,hh,kk,dd,ov,oc,result,mf,ck[32:2]);
endmodule

// Actual FSM/data-register boundary. No pipeline stage is added or removed.
// Arithmetic-facing outputs are the original registers/wires, and returns land
// at the original shell consumers. The arithmetic source and clock ABI stand.
module ot_s81_engram_mixq_shell #(parameter integer CL=0, MUT=0, VM_LAT=3, WRITE_COMMIT_LAT=1)(
 input wire [0:0] ck,input wire rst,input wire start,input wire [223:0] desc,
 output reg [4:0] rq_v,output reg [69:0] rq_row,output reg vtag,
 input wire [4:0] rs_v,input wire [2559:0] rs_d,
 output reg wq_v,output reg [13:0] wq_row,output reg [15:0] wq_mask,output reg [511:0] wq_d,
 output reg done,output reg fault,
 output reg go,iv,phase,output wire [1:0] copy,
 output reg [1023:0] h,kv,w,output wire [31:0] eps,scale,
 input wire gv,ov,mf,input wire [1:0] gc,oc,input wire [1023:0] result);
 reg [1:0] reset_sync;
 always @(posedge ck[0] or negedge rst)if(!rst)reset_sync<=0;else reset_sync<={reset_sync[0],1'b1};
 wire rn=reset_sync[1];
 localparam [1:0] COPY=CL;
 assign copy=COPY;
 reg [223:0] dsc;
 assign eps=dsc[160+:32];assign scale=dsc[192+:32];
 wire [13:0] hb=dsc[0+:14],kb=dsc[32+:14],wb=dsc[64+:14],vb=dsc[96+:14],ob=dsc[128+:14];
 wire [13:0] hrow_base=(MUT==2&&CL==3)?hb+14'd320:hb+14'd160*CL;
 reg [4:0] expected[0:VM_LAT];integer k;
 always @(posedge ck[0] or negedge rn)if(!rn)begin
  for(k=0;k<=VM_LAT;k=k+1)expected[k]<=0;
 end else begin
  expected[0]<=rq_v;for(k=1;k<=VM_LAT;k=k+1)expected[k]<=expected[k-1];
 end
 reg [4:0] rvq;reg [2559:0] rdq;
 always @(posedge ck[0] or negedge rn)if(!rn)rvq<=0;else rvq<=rs_v;
 always @(posedge ck[0])rdq<=rs_d;
 reg [2:0] state;localparam IDLE=0,BEGIN=1,REDUCE=2,GATE=3,ADD=4,DRAIN=5,FINISH=6;
 reg [8:0] req,received,written;reg [15:0] commit_left;integer lane;
 always @(posedge ck[0] or negedge rn)if(!rn)begin
  state<=IDLE;rq_v<=0;rq_row<=0;vtag<=0;wq_v<=0;wq_row<=0;wq_mask<=0;done<=0;fault<=0;go<=0;iv<=0;phase<=0;
  req<=0;received<=0;written<=0;commit_left<=0;dsc<=0;
 end else begin
  rq_v<=0;vtag<=0;wq_v<=0;done<=0;go<=0;iv<=0;
  if(mf||rvq!=expected[VM_LAT])fault<=1;
  case(state)
  IDLE:if(start)begin dsc<=desc;state<=BEGIN;end
  BEGIN:begin go<=1;phase<=0;req<=0;received<=0;written<=0;state<=REDUCE;end
  REDUCE:begin
   if(req<160)begin
    rq_v<=5'b11111;rq_row[0+:14]<=hrow_base+req;
    for(lane=0;lane<2;lane=lane+1)begin
     rq_row[14*(lane+1)+:14]<=kb+14'd320*CL+2*req+lane;
     rq_row[14*(lane+3)+:14]<=wb+14'd320*CL+2*req+lane;
    end
    req<=req+1;
   end
   if(|rvq)begin
    if(rvq!=5'b11111||received>=160)fault<=1;
    else begin for(lane=0;lane<32;lane=lane+1)h[32*lane+:32]<={rdq[16*lane+:16],16'd0};kv<=rdq[512+:1024];w<=rdq[1536+:1024];iv<=1;received<=received+1;if(received==159)state<=GATE;end
   end
  end
  GATE:if(gv)begin if(gc!=COPY)fault<=1;phase<=1;req<=0;received<=0;state<=ADD;end
  ADD:begin
   if(req<160)begin
    rq_v<=5'b00111;vtag<=1'b1;rq_row[0+:14]<=hrow_base+req;
    for(lane=0;lane<2;lane=lane+1)rq_row[14*(lane+1)+:14]<=vb+2*req+lane;
    req<=req+1;
   end
   if(|rvq)begin
    if(rvq!=5'b00111||received>=160)fault<=1;
    else begin for(lane=0;lane<32;lane=lane+1)h[32*lane+:32]<={rdq[16*lane+:16],16'd0};kv<=rdq[512+:1024];iv<=1;received<=received+1;if(received==159)state<=DRAIN;end
   end
  end
  DRAIN:;
  FINISH:begin
   if(commit_left!=0)commit_left<=commit_left-1;
   else begin done<=!fault&&!mf;state<=IDLE;end
  end
  default:fault<=1;
  endcase
  if(start&&state!=IDLE)fault<=1;
  if(ov)begin
   if((state!=ADD&&state!=DRAIN)||oc!=COPY||written>=160)fault<=1;
   wq_v<=1'b1;wq_mask<=16'hffff;
   for(lane=0;lane<32;lane=lane+1)wq_d[16*lane+:16]<=result[32*lane+16+:16];
   wq_row<=ob+14'd160*CL+written;
   written<=written+1;
   if(written==159)begin state<=FINISH;commit_left<=WRITE_COMMIT_LAT;end
  end
 end
endmodule
