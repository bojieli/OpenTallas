`timescale 1ns/1ps
// S81 Engram MIX4, BANDED copy cluster (S-ENGRAM+NORM helper MIX4-PARENT, 2026-10-16). Structural repair of the
// 248 TT-negative inter-child joins of the frozen own-column-valid R0 cluster (artifacts frozen_r0_tt248_0407: worst
// -146.99 ps; shctl.phase/iv/copy/fr/fa fan-outs, rly<->mul4/add8 gathers, chunk8->sum, sum->norm, eps->norm).
// Top = the own-column-valid localized top (return/request capture roots, RS stations, HLAYOUT re-slice) unchanged;
// only the copy cluster is replaced by ot_s81_engram_mixq_b:
//  * band c (c=0..3) = shcol_b[c], add8[c], mul4[2c], mul4[2c+1], chunk8[0..2][c] plus three band relays rt0/rt1/rb
//    (the CLOSED ot_s81_engram_rly master, replicated; spare relay bits are declared DEDUPE pads tied low);
//  * shcol_b issues its own column's operand valid (iv = registered load) and phase to its mul4 pair and add8, the
//    same edge it loads h/kv/w (no shctl iv/phase/fr/fa broadcast to 16 sinks);
//  * every band -> spine signal crosses ONE band relay: chunk8 sums/valids/faults (96+6 bits, +1 cycle on the
//    reduction, the only calendar change), mul4/add8 valid/fault/copy (replaces the central relay's leg: same depth);
//  * every spine -> band signal crosses ONE band relay: a_gate (same depth as through the central relay) and the add8
//    copy tag (the control's registered gate_copy = the copy captured at go, valid from the gate on: add8 tags only ADD
//    beats); the shell control's fr/fa phase flags are gone: shcol_b decodes the phase from the return-valid pattern;
//  * sum v is taken from the relayed mvalid of the band relay (aligned with the relayed chunks); the central relay keeps
//    go/phase/in_v/copy/scale toward the control and gate_v/gate_copy/fault toward the shell, and now also carries eps
//    to the norms (static per command, 0 cycles).
// Exact arithmetic and the golden reduction order are unchanged (stages only). Static fixed-cycle schedule, no credits.
// MUT: as the localized top (1 key->1.0, 2 address map, 3 stale V, 26 column-3 result valid dropped) plus
//  27 band 2's relayed chunk sums bypass the band relay (arrive one edge early: reduction misaligned);
//  28 shcol_b column 3 issue valid dropped (mul4[6], mul4[7], add8[3] never see a beat).
module dsfd_engram_mix4_banded #(parameter integer MUT=0, VM_LAT=1, WRITE_COMMIT_LAT=1, BC=2, RS=5, HLAYOUT=1)(
 input wire [232+8*RS:0] ck, //0 control;1..208 clusters (52 each);209..208+8RS stations;then 20 ingress + 4 request roots
 input wire [0:0] rst,input wire [84:0] c_cmd,
 output wire [8:0] c_done,output wire [1:0] c_st,
`ifndef DSFD_ENGRAM_STATIC_ISSUE
 input wire [0:0] f_inp,
`endif
 output wire [19:0] rq_v,output wire [279:0] rq_row,
 input wire [19:0] rs_v,input wire [10239:0] rs_d,
 output wire [3:0] wq_v,output wire [55:0] wq_row,
 output wire [63:0] wq_mask,output wire [2047:0] wq_d);

 reg [1:0] reset_sync;
 always @(posedge ck[0] or negedge rst[0])if(!rst[0])reset_sync<=0;else reset_sync<={reset_sync[0],1'b1};
 wire rn=reset_sync[1];
 wire jv,jnew,epf;wire [83:0] jd,jnd;reg done,fault;reg inp_q;
`ifdef DSFD_ENGRAM_STATIC_ISSUE
 // Compiled issue edge proves operand availability; late/missing VM results remain faults.
 always @(posedge ck[0] or negedge rn)if(!rn)inp_q<=0;else inp_q<=1'b1;
`else
 always @(posedge ck[0] or negedge rn)if(!rn)inp_q<=0;else inp_q<=f_inp[0];
`endif
 ot_s81_slab_ep ep(.c_clk(ck[0]),.c_rst_n(rn),.c_cmd(c_cmd),.c_done(c_done),.c_st(c_st),
  .e_clk(ck[0]),.e_rst_n(rn),.j_v(jv),.j_d(jd),.j_new(jnew),.j_new_d(jnd),.j_present(1'b1),.j_done(done),.slab_fault(fault),.ep_fault(epf));

 // ---- cluster interfaces
 wire [19:0] c_rqv;wire [279:0] c_rqrow;wire [3:0] c_vtag;   // vtag: this cycle's lanes 1,2 request is V
 wire [3:0] c_done_q,c_fault_q;
 wire [3:0] c_wq_v;wire [2047:0] c_wq_d;                     // cluster write lanes (copy-major data)
 assign wq_v=c_wq_v;
 genvar wj,we,wk;
 generate if(HLAYOUT!=0)begin:g_hwr
  for(wj=0;wj<4;wj=wj+1)for(we=0;we<8;we=we+1)for(wk=0;wk<4;wk=wk+1)begin:p
   assign wq_d[512*wj+16*(4*we+wk)+:16]=c_wq_d[512*wk+16*(8*wj+we)+:16];
  end
 end else begin:g_cwr
  assign wq_d=c_wq_d;
 end endgenerate
 reg [19:0] l_rsv;reg [10239:0] l_rsd;                        // returns delivered to the clusters
 reg [BC:0] st_line;reg [223:0] desc_line[0:BC];

 // ---- descriptor read (top), static: issued only while every cluster is idle
 reg [2:0] tstate;localparam T_IDLE=0,T_DESC=1,T_RUN=2,T_DONE=3,T_POP=4;
 // Descriptor bit18 selects operand storage; it is not part of the H row address.
 wire [31:0] desc_hrow=rdq[0+:32]&32'hfffbffff;
 wire [31:0] desc_kw_span=rdq[18]?32'd5120:32'd1280;
 wire [31:0] desc_v_span=rdq[18]?32'd640:32'd320;
 reg desc_rq;reg [1023:0] v_prev;
 // registered request stage: lane 0 of cluster 0 doubles as descriptor reader,
 // lanes 1,2 of clusters 1..3 are suppressed for V (cluster 0 reads V once).
 integer q,l,hm;
 genvar rqcopy;
 generate for(rqcopy=0;rqcopy<4;rqcopy=rqcopy+1)begin:g_request_capture
  ot_s81_engram_request_capture #(.COPY(rqcopy)) cap(
   .clk((MUT==25&&rqcopy==0)?1'b0:ck[229+8*RS+rqcopy]),.rst_n(rn),
   .v_i(c_rqv[5*rqcopy+:5]),.row_i(c_rqrow[70*rqcopy+:70]),
   .vtag(c_vtag[rqcopy]),.desc_rq(desc_rq),.desc_row(jd[7+:14]),
   .v_o(rq_v[5*rqcopy+:5]),.row_o(rq_row[70*rqcopy+:70]));
 end endgenerate
 // fixed-latency tag lines: request flop (+1) -> VM (VM_LAT) -> return pin flop (+1)
 localparam integer TL=VM_LAT+1;
 reg [TL:0] dtag;reg [TL:0] vtag;
 always @(posedge ck[0] or negedge rn)if(!rn)begin dtag<=0;vtag<=0;end else begin
  dtag<={dtag[TL-1:0],desc_rq};vtag<={vtag[TL-1:0],c_vtag[0]};
 end
 wire [19:0] rvq;wire [10239:0] rdq;
 genvar rlane;
 generate for(rlane=0;rlane<20;rlane=rlane+1)begin:g_return_capture
  ot_s81_engram_return_capture cap(
   .clk((MUT==24&&rlane==0)?1'b0:ck[209+8*RS+rlane]),.rst_n(rn),
   .v_i(rs_v[rlane]),.d_i(rs_d[512*rlane+:512]),
   .v_o(rvq[rlane]),.d_o(rdq[512*rlane+:512]));
 end endgenerate
 // return demux (combinational after the registered pin stage; the clusters
 // capture in their own rvq/rdq flops)
 always @*begin
  l_rsv=rvq;l_rsd=rdq;
  if(dtag[TL])begin l_rsv[0]=1'b0;end
  for(q=0;q<4;q=q+1)if(vtag[TL])begin
   l_rsv[5*q+1]=rvq[1];l_rsv[5*q+2]=rvq[2];
   l_rsd[2560*q+512+:1024]=(MUT==3&&q!=0)?v_prev:rdq[512+:1024];
  end
  if(HLAYOUT!=0)for(q=0;q<4;q=q+1)for(hm=0;hm<32;hm=hm+1)
   l_rsd[2560*q+16*hm+:16]=rdq[2560*(hm/8)+16*(4*(hm%8)+q)+:16];
 end

 always @(posedge ck[0] or negedge rn)if(!rn)begin
  tstate<=T_IDLE;desc_rq<=0;done<=0;fault<=0;st_line<=0;
 end else begin
  desc_rq<=0;done<=0;st_line<={st_line[BC-1:0],1'b0};
  if(epf||(|c_fault_q))fault<=1;
  if(dtag[TL]&&!rvq[0])fault<=1;                      // lost descriptor reply
  if(desc_rq&&c_rqv[0])fault<=1;                          // lane 0 reservation clash
  if(c_vtag!=4'b0000&&c_vtag!=4'b1111)fault<=1;           // clusters out of lockstep
  if(HLAYOUT!=0&&!dtag[TL]&&{rvq[15],rvq[10],rvq[5],rvq[0]}!=4'b0000&&{rvq[15],rvq[10],rvq[5],rvq[0]}!=4'b1111)fault<=1; // H rows re-sliced across clusters
  if(HLAYOUT!=0&&c_wq_v!=4'b0000&&c_wq_v!=4'b1111)fault<=1;                       // interleaved H writes need all four
  case(tstate)
  T_IDLE:if(jv&&!fault)begin
   if(!inp_q||jd[30:21]!=0)fault<=1;else begin desc_rq<=1;tstate<=T_DESC;end
  end
  T_DESC:if(dtag[TL])begin
   if(desc_hrow>15744||rdq[32+:32]>16384-desc_kw_span||rdq[64+:32]>16384-desc_kw_span||rdq[96+:32]>16384-desc_v_span||rdq[128+:32]>15744)fault<=1;
   if((rdq[128+:32]!=desc_hrow && rdq[128+:32]<desc_hrow+640 && desc_hrow<rdq[128+:32]+640) ||
      (rdq[128+:32]<rdq[32+:32]+desc_kw_span && rdq[32+:32]<rdq[128+:32]+640) ||
      (rdq[128+:32]<rdq[64+:32]+desc_kw_span && rdq[64+:32]<rdq[128+:32]+640) ||
      (rdq[128+:32]<rdq[96+:32]+desc_v_span && rdq[96+:32]<rdq[128+:32]+640))fault<=1;
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
  // cluster-side wires; the top-side ends cross RS relay stations (toward the cluster: start/desc + returns; toward
  // the top/VM: requests, writes, done/fault)
  wire k_rqv_v;wire [4:0] k_rqv;wire [69:0] k_rqrow;wire k_vtag,k_wv,k_done,k_fault;wire [13:0] k_wrow;wire [15:0] k_wmask;wire [511:0] k_wd;
  wire [4:0] k_rsv;wire [2559:0] k_rsd;wire k_start;wire [223:0] k_desc;
  wire [((RS>0)?RS:1)-1:0] up_ck, down_ck;
  if(RS>0)begin:g_station_clocks
   assign up_ck=ck[209+2*RS*c+:RS];
   assign down_ck=ck[209+2*RS*c+RS+:RS];
  end else begin:g_no_station_clocks
   assign up_ck=ck[0];assign down_ck=ck[0];
  end
  ot_s81_engram_vrly_clocked #(.D(RS),.WV(5+1+1+1+1),.WD(70+14+16+512)) up(up_ck,rn,
   {k_rqv,k_vtag,k_wv,k_done,k_fault},{k_rqrow,k_wrow,k_wmask,k_wd},
   {c_rqv[5*c+:5],c_vtag[c],c_wq_v[c],c_done_q[c],c_fault_q[c]},{c_rqrow[70*c+:70],wq_row[14*c+:14],wq_mask[16*c+:16],c_wq_d[512*c+:512]});
  // per-cluster descriptor: the copy's row bases and its copy index are folded here in the top (ONE cluster master
  // for all four clusters, no per-instance constant or strap in the cluster); MUT 2 moves cluster 3's H base onto
  // copy 2's rows.
  localparam [1:0] CC=c;wire [223:0] cdesc;
  assign cdesc[13:0]=(HLAYOUT!=0)?desc_line[BC][13:0]+((MUT==2&&c==3)?14'd2:14'(c)):(MUT==2&&c==3)?desc_line[BC][13:0]+14'd320:desc_line[BC][13:0]+14'd160*c;
  assign cdesc[31:14]={desc_line[BC][31:18],CC,desc_line[BC][15:14]};
  assign cdesc[45:32]=desc_line[BC][18]?desc_line[BC][45:32]:desc_line[BC][45:32]+14'd320*c;assign cdesc[63:46]=desc_line[BC][63:46];
  assign cdesc[77:64]=desc_line[BC][18]?desc_line[BC][77:64]:desc_line[BC][77:64]+14'd320*c;assign cdesc[127:78]=desc_line[BC][127:78];
  assign cdesc[141:128]=desc_line[BC][141:128]+((HLAYOUT!=0)?14'(c):14'd160*c);assign cdesc[223:142]=desc_line[BC][223:142];
  // start leaves the top ONE edge early (st_line[BC-1]); the cluster's shell control registers it in start_q at its
  // input pin (S-ENGRAM 10-15 native capture repair: shctl start capture 224.78 > 190 ps), so start_q is high in the
  // same cycle the old pin was and cdesc (st_line[BC] timing) is sampled on the same edge: 0 added cycles.
  ot_s81_engram_vrly_clocked #(.D(RS),.WV(5+1),.WD(2560+224)) down(down_ck,rn,
   {l_rsv[5*c+:5],st_line[BC-1]},{l_rsd[2560*c+:2560],cdesc},{k_rsv,k_start},{k_rsd,k_desc});
  ot_s81_engram_mixq_b #(.MUT(MUT),.VM_LAT(VM_LAT+2+2*RS),.WRITE_COMMIT_LAT(WRITE_COMMIT_LAT),.HLAYOUT(HLAYOUT)) u(
   .ck(ck[1+52*c+:52]),.rst(rst[0]),.start(k_start),.desc(k_desc),
   .rq_v(k_rqv),.rq_row(k_rqrow),.vtag(k_vtag),
   .rs_v(k_rsv),.rs_d(k_rsd),
   .wq_v(k_wv),.wq_row(k_wrow),.wq_mask(k_wmask),.wq_d(k_wd),
   .done(k_done),.fault(k_fault));
 end endgenerate
endmodule

// ---- BANDED copy cluster ot_s81_engram_mixq_b: wires only, every child registers its pins.
//  ck[0] shctl | ck[4:1] shcol_b[3:0] | ck[5] control | ck[36:6] arithmetic leaves (ot_s81_engram_mix ck_leaf order)
//  ck[37] central relay | ck[41:38] band relay rt0[3:0] | ck[45:42] rt1[3:0] | ck[49:46] rb[3:0] | ck[50] rsl | ck[51] rsr.
//  52 clock entries.
// Banded copy cluster with the old single return port (dsfd_engram_mix4_banded top): wires only, slices the return word
// per shell column and drives the per-column core.
module ot_s81_engram_mixq_b #(parameter integer MUT=0, VM_LAT=3, WRITE_COMMIT_LAT=1, HLAYOUT=1, N=32, D=5120, LM=5, LA=4)(
 input wire [51:0] ck,input wire rst,input wire start,input wire [223:0] desc,
 output wire [4:0] rq_v,output wire [69:0] rq_row,output wire vtag,
 input wire [4:0] rs_v,input wire [2559:0] rs_d,
 output wire wq_v,output wire [13:0] wq_row,output wire [15:0] wq_mask,output wire [511:0] wq_d,
 output wire done,output wire fault);
 wire [2559:0] dc;
 genvar c;
 generate for(c=0;c<4;c=c+1)begin:sl assign dc[640*c+:640]={rs_d[1536+256*c+:256],rs_d[512+256*c+:256],rs_d[128*c+:128]};end endgenerate
 ot_s81_engram_mixq_bc #(.MUT(MUT),.VM_LAT(VM_LAT),.WRITE_COMMIT_LAT(WRITE_COMMIT_LAT),.HLAYOUT(HLAYOUT),.N(N),.D(D),.LM(LM),.LA(LA)) core(
  .ck(ck),.rst(rst),.start(start),.desc(desc),.rq_v(rq_v),.rq_row(rq_row),.vtag(vtag),.rs_v_col({4{rs_v}}),.rs_d_col(dc),
  .wq_v(wq_v),.wq_row(wq_row),.wq_mask(wq_mask),.wq_d(wq_d),.done(done),.fault(fault));
endmodule

module ot_s81_engram_mixq_bc #(parameter integer MUT=0, VM_LAT=3, WRITE_COMMIT_LAT=1, HLAYOUT=1, N=32, D=5120, LM=5, LA=4)(
 input wire [51:0] ck,input wire rst,input wire start,input wire [223:0] desc,
 output wire [4:0] rq_v,output wire [69:0] rq_row,output wire vtag,
 input wire [19:0] rs_v_col,input wire [2559:0] rs_d_col,     // per shell column c: rs_v_col[5c+:5], rs_d_col[640c+:640]
 output wire wq_v,output wire [13:0] wq_row,output wire [15:0] wq_mask,output wire [511:0] wq_d,
 output wire done,output wire fault);
 localparam integer MM=(MUT==1)?1:(MUT==22)?22:0;   // multiplier-leaf mutants, as ot_s81_engram_mixq
 wire [30:0] ck_leaf=ck[36:6];
 // ---- shell: control leaf + four own-column payload leaves
 wire go,iv,phase,ov,mf,gv;wire [1:0] copy,gc,oc;wire [31:0] eps,scale;wire fr,fa;
 wire [1023:0] h,kv,w,oy;wire [3:0] avalid,af;wire [7:0] add_copy;
 wire [3:0] c_iv,c_ph;                      // own-column issue valid / phase from shcol_b[c]
 wire [7:0] copy_b;wire [127:0] gate_b;   // relayed per band
 ot_s81_engram_mixq_shctl #(.MUT(MUT),.VM_LAT(VM_LAT),.WRITE_COMMIT_LAT(WRITE_COMMIT_LAT),.HLAYOUT(HLAYOUT)) ctl(
  .ck(ck[0]),.rst(rst),.start(start),.desc(desc),.rq_v(rq_v),.rq_row(rq_row),.vtag(vtag),.rs_v(rs_v_col[10+:5]),
  .wq_v(wq_v),.wq_row(wq_row),.wq_mask(wq_mask),.done(done),.fault(fault),
  .go(go),.iv(iv),.phase(phase),.copy(copy),.eps(eps),.scale(scale),.gv(gv),.ov(ov),.mf(mf),.gc(gc),.oc(oc),.fr(fr),.fa(fa));
 // the shell's write-row counter takes the result valid of band 2's add8 (its add8 pins face the spine) (all four add8 run in lockstep; the control
 // checks it); each payload column takes its own add8's valid (own-column, as the localized candidate).
 assign ov=avalid[2];assign oc=add_copy[5:4];
 genvar c;
 generate for(c=0;c<4;c=c+1)begin:col
  ot_s81_engram_mixq_shcol_b #(.MUT(MUT)) u(.ck(ck[c+1]),.rst(rst),.rs_v(rs_v_col[5*c+:5]),
   .rs_d(rs_d_col[640*c+:640]),
   .ov((MUT==26&&c==3)?1'b0:avalid[c]),.result(oy[256*c+:256]),
   .h(h[256*c+:256]),.kv(kv[256*c+:256]),.w(w[256*c+:256]),.wq_d(wq_d[128*c+:128]),.iv(c_iv[c]),.ph(c_ph[c]));
 end endgenerate
 // ---- arithmetic
 wire [7:0] mvalid,mfault;wire [1023:0] hd,kd,dot;
 wire [383:0] chunk_sums;wire [11:0] chunk_fault,chunk_valid;      // chunk8 outputs (band side)
 wire [383:0] chunk_sums_r;wire [11:0] chunk_fault_r,chunk_valid_r;// after the band relays (spine side)
 wire [7:0] mvalid_r,mfault_r,add_copy_r;wire [3:0] avalid_r,af_r;   // control inputs, two edges (band + side relay)
 wire [7:0] mvalid_b;wire [31:0] band_up;wire [35:0] side_dn[0:1];
 wire go_r,phase_r,in_v_r;wire [1:0] copy_r;wire [31:0] scale_r,eps_r;
 wire gate_v_c,fault_c;wire [1:0] gate_copy_c;wire [31:0] a_gate;
 // central relay: {eps 32, go, phase, in_v, copy 2, scale 32} toward the spine; {a_gate, gate_v, gate_copy, fault}
 // toward the shell (its a_gate output is unused: the add8 take a_gate from their band relay A).
 wire [31:0] a_gate_unused;
 ot_s81_engram_rly relay(ck[37],rst,{eps,go,phase,iv,copy,scale},{a_gate,gate_v_c,gate_copy_c,fault_c},
  {eps_r,go_r,phase_r,in_v_r,copy_r,scale_r},{a_gate_unused,gv,gc,mf});
 genvar b,r,g;
 generate for(b=0;b<4;b=b+1)begin:band
  // Three band relays per band, placed where their traffic is (the band is a vertical column: shell payload leaf at the
  // bottom, add8, mul4 pair, chunk8 rows at the top):
  //  rt0 (top)    up {pad, fault r1, fault r0, vo r1, vo r0, sum r1, sum r0}                    dn 36 pad bits
  //  rt1 (top)    up {pad 31, mfault 2, mvalid 2, fault r2, vo r2, sum r2}                     dn 36 pad bits
  //  rb  (bottom) up {pad 65, add_copy 2, af, avalid}                                        dn = side relay dn
  wire [68:0] t0_up,t1_up,b_up;wire [35:0] b_dn,t0_dn_unused,t1_dn_unused;
  wire [31:0] s0,s1,s2;
  ot_s81_engram_rly rt0(ck[38+b],rst,
   {1'b0,chunk_fault[4*1+b],chunk_fault[4*0+b],chunk_valid[4*1+b],chunk_valid[4*0+b],chunk_sums[32*(4*1+b)+:32],chunk_sums[32*(4*0+b)+:32]},
   36'd0,t0_up,t0_dn_unused);
  ot_s81_engram_rly rt1(ck[42+b],rst,{31'd0,mfault[2*b+:2],mvalid[2*b+:2],chunk_fault[4*2+b],chunk_valid[4*2+b],chunk_sums[32*(4*2+b)+:32]},36'd0,t1_up,t1_dn_unused);
  ot_s81_engram_rly rb(ck[46+b],rst,{65'd0,add_copy[2*b+:2],af[b],avalid[b]},side_dn[b/2],b_up,b_dn);
  assign band_up[8*b+:8]={b_up[3:2],b_up[1],b_up[0],t1_up[37:36],t1_up[35:34]};   // {add_copy, af, avalid, mfault, mvalid}
  assign {s1,s0}=t0_up[63:0];assign s2=t1_up[31:0];
  assign chunk_sums_r[32*(4*0+b)+:32]=(MUT==27&&b==2)?chunk_sums[32*(4*0+b)+:32]:s0;
  assign chunk_sums_r[32*(4*1+b)+:32]=(MUT==27&&b==2)?chunk_sums[32*(4*1+b)+:32]:s1;
  assign chunk_sums_r[32*(4*2+b)+:32]=(MUT==27&&b==2)?chunk_sums[32*(4*2+b)+:32]:s2;
  assign chunk_valid_r[4*0+b]=t0_up[64];assign chunk_valid_r[4*1+b]=t0_up[65];
  assign chunk_fault_r[4*0+b]=t0_up[66];assign chunk_fault_r[4*1+b]=t0_up[67];
  assign chunk_valid_r[4*2+b]=t1_up[32];assign chunk_fault_r[4*2+b]=t1_up[33];
  assign mvalid_b[2*b+:2]=t1_up[35:34];                  // one edge: the sums' reference valid (aligned with chunks)
  assign gate_b[32*b+:32]=b_dn[35:4];assign copy_b[2*b+:2]=b_dn[1:0];
 end endgenerate
 // Side relays at the spine's W and E edges (second stage between the band relays and the control, which gathers from
 // both sides): toward the control {band c's mvalid 2, mfault 2, avalid, af, add_copy 2} of the two bands on that side,
 // and on the W side also go/phase/in_v/copy from the central relay, so every control input that is cross-checked against
 // in_v is exactly two edges from its producer (as one edge was through the old central relay); toward the bands
 // {a_gate, pad 2, gate_copy} (static from the gate on: add8 uses them only on ADD beats).
 wire [68:0] sl_up,sr_up;wire [35:0] sl_dn,sr_dn;
 ot_s81_engram_rly rsl(ck[50],rst,{48'd0,go_r,phase_r,in_v_r,copy_r,band_up[15:0]},{a_gate,2'b00,gate_copy_c},sl_up,sl_dn);
 ot_s81_engram_rly rsr(ck[51],rst,{53'd0,band_up[31:16]},{a_gate,2'b00,gate_copy_c},sr_up,sr_dn);
 assign side_dn[0]=sl_dn;assign side_dn[1]=sr_dn;
 wire go_c,phase_c,in_v_c;wire [1:0] copy_c;
 assign {go_c,phase_c,in_v_c,copy_c}=sl_up[20:16];
 wire [31:0] bu={sr_up[15:0],sl_up[15:0]};
 genvar u;
 generate for(u=0;u<4;u=u+1)begin:g_unpack
  assign mvalid_r[2*u+:2]=bu[8*u+:2];assign mfault_r[2*u+:2]=bu[8*u+2+:2];
  assign avalid_r[u]=bu[8*u+4];assign af_r[u]=bu[8*u+5];assign add_copy_r[2*u+:2]=bu[8*u+6+:2];
 end endgenerate
 wire [1:0] nv,nf;wire eg_valid,g_v;wire [1:0] g_fault;wire [31:0] g_x,gy,rhh,rkk,rdd,gate_o,hh_o,kk_o,dd_o;wire [63:0] norm_rstd;wire [2:0] rv,rf;
 ot_s81_engram_mix_control #(.N(N),.D(D),.LM(LM),.LA(LA),.MUT(MUT)) control(
  .clk(ck[5]),.arst_n(rst),.go(go_c),.phase(phase_c),.in_v(in_v_c),.copy(copy_c),.scale(scale_r),
  .gate_v(gate_v_c),.gate_copy(gate_copy_c),.gate(gate_o),.hh(hh_o),.kk(kk_o),.dd(dd_o),.fault(fault_c),
  .g_v(g_v),.a_gate(a_gate),.g_x(g_x),
  .mvalid(mvalid_r),.mfault(mfault_r),.avalid(avalid_r),.af(af_r),.add_copy(add_copy_r),.nv(nv),.nf(nf),.norm_rstd(norm_rstd),
  .eg_valid(eg_valid),.g_fault(g_fault),.gy(gy),.rv(rv),.rf(rf),.rhh(rhh),.rkk(rkk),.rdd(rdd));
 // sums: chunks and their reference valid both cross the band relays (sum v = band 1's / band 2's relayed mul4 valid,
 // as the old mvalid[2] / mvalid[4] choice); go from the central relay as before.
 ot_s81_engram_sum #(.N(N),.D(D),.LA(LA)) hsum(ck_leaf[23],rst,go_r,mvalid_b[2],rv[0],rhh,rf[0],chunk_sums_r[0+:128],chunk_fault_r[0+:4],chunk_valid_r[0+:4]);
 ot_s81_engram_sum #(.N(N),.D(D),.LA(LA)) ksum(ck_leaf[24],rst,go_r,mvalid_b[2],rv[1],rkk,rf[1],chunk_sums_r[128+:128],chunk_fault_r[4+:4],chunk_valid_r[4+:4]);
 ot_s81_engram_sum #(.N(N),.D(D),.LA(LA)) dsum(ck_leaf[25],rst,go_r,mvalid_b[4],rv[2],rdd,rf[2],chunk_sums_r[256+:128],chunk_fault_r[8+:4],chunk_valid_r[8+:4]);
 generate for(g=0;g<8;g=g+1)begin:g_mult
  ot_s81_engram_mul4 #(.LM(LM),.MUT(MM)) leaf(ck_leaf[(g%2)?(26+g/2):(g/2)],rst,(MUT==28&&g/2==3)?1'b0:c_iv[g/2],c_ph[g/2],
   h[128*g+:128],kv[128*g+:128],w[128*g+:128],mvalid[g],hd[128*g+:128],kd[128*g+:128],dot[128*g+:128],mfault[g]);
 end
 for(r=0;r<3;r=r+1)begin:g_reduce
  wire [1023:0] x=(r==0)?hd:(r==1)?kd:dot;
  for(c=0;c<4;c=c+1)begin:g_chunk
   ot_s81_engram_chunk8 #(.LA(LA)) leaf(ck_leaf[4+4*r+c],rst,mvalid[2*c],x[256*c+:256],
    chunk_valid[4*r+c],chunk_sums[32*(4*r+c)+:32],chunk_fault[4*r+c]);
  end
 end
 for(g=0;g<4;g=g+1)begin:g_add
  ot_s81_engram_add8 #(.LM(LM),.LA(LA)) leaf(ck_leaf[16+g],rst,(MUT==28&&g==3)?1'b0:c_iv[g],c_ph[g],
   h[256*g+:256],kv[256*g+:256],gate_b[32*g+:32],copy_b[2*g+:2],avalid[g],oy[256*g+:256],af[g],add_copy[2*g+:2]);
 end
 for(g=0;g<2;g=g+1)begin:g_norm
  ot_s81_engram_norm #(.LM(LM),.LA(LA)) leaf(ck_leaf[20+g],rst,rv[g],g==0?rhh:rkk,eps_r,nv[g],norm_rstd[32*g+:32],nf[g]);
 end endgenerate
 ot_s81_engram_gate #(.LM(LM),.LA(LA)) gate_leaf(ck_leaf[22],rst,g_v,g_x,eg_valid,gy,g_fault,ck_leaf[30]);
endmodule

// Shell payload column leaf, banded form (replaces ot_s81_engram_mixq_shcol in the banded cluster). Identical payload
// registers and load edges in every fault-free cycle; the load decision uses the captured return-valid pattern alone
// (no fr/fa phase flags from the shell control), and the leaf issues its own column's operand valid and phase to the
// column's mul4 pair and add8 from that decision (iv = ld_r|ld_a, ph = ld_a, registered on the edge that loads h/kv/w,
// exactly the cycle the shell control's iv/phase broadcast used to arrive). Every input and output is registered at
// the leaf boundary (rs_v/ov/rs_d/result captured; h/kv/w/wq_d/iv/ph launched from flops).
module ot_s81_engram_mixq_shcol_b #(parameter integer MUT=0)(
 input wire ck,input wire rst,input wire [4:0] rs_v,input wire [639:0] rs_d,input wire ov,
 input wire [255:0] result,
 output reg [255:0] h,kv,w,output reg [127:0] wq_d,output reg iv,ph);
 reg [1:0] reset_sync;
 always @(posedge ck or negedge rst)if(!rst)reset_sync<=0;else reset_sync<={reset_sync[0],1'b1};
 wire rn=reset_sync[1];
 reg [4:0] rvq;reg ov_q;
 always @(posedge ck or negedge rn)if(!rn)begin rvq<=0;ov_q<=0;end else begin rvq<=rs_v;ov_q<=ov;end
 reg [639:0] rdq;reg [127:0] result_q;integer lane;
 always @(posedge ck)rdq<=rs_d;
 always @(posedge ck)for(lane=0;lane<8;lane=lane+1)result_q[16*lane+:16]<=result[32*lane+16+:16];
 // The return-valid pattern identifies the phase: only REDUCE issues all five lanes, only ADD issues lanes 0..2 (the
 // top masks the descriptor return); the shell control faults on any pattern other than the one it expects.
 wire ld_r=rvq==5'b11111,ld_a=rvq==5'b00111;
 wire ov_use=(MUT==21)?(ov&&rn):ov_q;
 always @(posedge ck or negedge rn)if(!rn)begin iv<=0;ph<=0;end else begin iv<=ld_r||ld_a;ph<=ld_a;end
 always @(posedge ck)begin
  if(ld_r||ld_a)begin
   for(lane=0;lane<8;lane=lane+1)h[32*lane+:32]<={rdq[16*lane+:16],16'd0};
   kv<=rdq[128+:256];
  end
  if(ld_r)w<=rdq[384+:256];
  if(ov_use)wq_d<=result_q;
 end
endmodule
