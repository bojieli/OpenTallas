`timescale 1ns/1ps
// S81 Engram MIX4 FLAT parent candidate for S-DIE slot A (S-ENGRAM+NORM helper MIX4-PARENT, 2026-10-16).
// Same function and fixed-cycle static schedule as dsfd_engram_mix4_banded (localized top + banded copy clusters), with
// the top-level glue hardened as tiles so the parent is wires only:
//   ot_s81_mx4_sreg  universal registered station (8 reset bits + 544 data bits, one edge): the 20 VM return captures,
//                    every transport station, the 4 VM write ports;
//   ot_s81_mx4_rq    per-quarter VM request port (one edge): V-lane suppression (strap SUP=1 on quarters 1..3), the
//                    descriptor read injection and lane-0 clash check (quarter 0), and the VM_LAT+2 delay lines that
//                    give the descriptor-reply mask (dtag) and the shared-V select (vtag) aligned with the captures;
//   ot_s81_mx4_mcol  per-column return merge (two edges: input and output registers), 4 per copy cluster: own K/W
//                    halves, the shared V half (vtag), the H piece of quarter c (HLAYOUT re-slice), the lane valids
//                    (descriptor reply masked on copy 0) and the H-lockstep check of the old top;
//   ot_s81_mx4_ctl   command endpoint, descriptor read/check, four-done join and lockstep checks, per-copy
//                    descriptor folding.
// Transport depths are parameters (set from the slot geometry): every return branch (own lanes, shared V, H pieces)
// crosses exactly DD stations from capture to merge, so each copy cluster sees one fixed VM latency
// VM_LAT + 2 + DU + DD + 2 (DU stations from the shell control to its request port); writes cross DW stations to the
// write port of quarter c (column c of every copy writes HC rows of VM write lane c); status crosses DC >= DW + 1
// stations to the control so completion never precedes the last write at the port.
// HLAYOUT=1 (production) only.  MUT: 1 key->1.0, 2 copy-3 H base on copy 2, 26 column-3 result valid dropped (cluster),
// 27 band-2 chunk relay bypass (cluster), 28 column-3 issue valid dropped (cluster), 29 merge tile of copy 1 column 2
// takes the own K half instead of the shared V half (V select broken on one column).
module dsfd_engram_mix4_flat #(parameter integer MUT=0, VM_LAT=1, WRITE_COMMIT_LAT=1, BC=2, HLAYOUT=1,
  DU=1, DD=6, DW=7, DC=8, DQ=1, DR=1, DS=6,
  // clock entries: clusters 4 x 52 | 20 captures | 4 rq | 16 mcol | ctl | stations
  NCL=208, NST=4*DU+20*DD+6*DD+16*DD+4*DW+16*DW+4*DC+DQ+DR+4*DS, NCK=NCL+20+4+16+1+4+NST)(
 input wire [NCK-1:0] ck,
 input wire [0:0] rst,input wire [84:0] c_cmd,
 output wire [8:0] c_done,output wire [1:0] c_st,
 output wire [19:0] rq_v,output wire [279:0] rq_row,
 input wire [19:0] rs_v,input wire [10239:0] rs_d,
 output wire [3:0] wq_v,output wire [55:0] wq_row,
 output wire [63:0] wq_mask,output wire [2047:0] wq_d);
 initial if(HLAYOUT!=1||DC<DW+1||DD<0)$fatal(1,"flat MIX4: HLAYOUT=1, DC>=DW+1 required");
 localparam integer CK_CAP=NCL, CK_RQ=NCL+20, CK_MC=NCL+24, CK_CTL=NCL+40, CK_WT=NCL+41, CK_ST=NCL+45;
 // station clock offsets
 localparam integer S_U=CK_ST, S_D=S_U+4*DU, S_V=S_D+20*DD, S_H=S_V+6*DD, S_W=S_H+16*DD, S_X=S_W+4*DW, S_C=S_X+16*DW,
                    S_Q=S_C+4*DC, S_R=S_Q+DQ, S_S=S_R+DR;
 genvar q,p,c,k;

 // ---------------- VM return captures (one station per physical lane, at the E face)
 wire [7:0] cap_v[0:19];wire [543:0] cap_d[0:19];
 generate for(k=0;k<20;k=k+1)begin:g_cap
  ot_s81_mx4_sreg cap(.ck(ck[CK_CAP+k]),.rst(rst[0]),.vi({7'd0,rs_v[k]}),.di({32'd0,rs_d[512*k+:512]}),.vo(cap_v[k]),.do_(cap_d[k]));
 end endgenerate

 // ---------------- request ports
 wire [75:0] u_req[0:3];             // {vtag, rq_row 70, rq_v 5} from each shell control after DU stations
 wire [14:0] q_desc;                 // {desc_rq, desc_row 14} from the control after DQ stations
 wire [3:0] dtag_c,vtag_c,rq_fault;
 generate for(q=0;q<4;q=q+1)begin:g_rq
  ot_s81_mx4_rq #(.VM_LAT(VM_LAT),.SUP(q!=0)) rqp(.ck(ck[CK_RQ+q]),.rst(rst[0]),
   .u_v(u_req[q][4:0]),.u_row(u_req[q][74:5]),.u_vtag(u_req[q][75]),
   .desc_rq(q==0?q_desc[14]:1'b0),.desc_row(q==0?q_desc[13:0]:14'd0),
   .rq_v(rq_v[5*q+:5]),.rq_row(rq_row[70*q+:70]),.dtag(dtag_c[q]),.vtag(vtag_c[q]),.fault(rq_fault[q]));
 end endgenerate

 // ---------------- return transport (every branch DD stations) and per-column merge
 // own lane k of quarter q -> copy q; aux carries {dtag of quarter q (q0 only)} on lane 0 and lane 0's raw valid on lanes 1..4
 wire [7:0] own_v[0:19];wire [543:0] own_d[0:19];
 generate for(q=0;q<4;q=q+1)for(k=0;k<5;k=k+1)begin:g_own
  wire [7:0] vi=(k==0)?{6'd0,(q==0)?dtag_c[0]:1'b0,cap_v[5*q][0]}:{6'd0,cap_v[5*q][0],cap_v[5*q+k][0]};
  ot_s81_mx4_chain #(.D(DD)) ch(.ck(ck[S_D+(5*q+k)*DD+:((DD>0)?DD:1)]),.rst(rst[0]),.vi(vi),.di(cap_d[5*q+k]),.vo(own_v[5*q+k]),.do_(own_d[5*q+k]));
 end endgenerate
 // shared V (quarter 0 lanes 1, 2) to every other copy: aux {vtag}
 wire [7:0] shv_v[0:3][0:1];wire [543:0] shv_d[0:3][0:1];
 generate for(p=1;p<4;p=p+1)for(k=0;k<2;k=k+1)begin:g_v
  ot_s81_mx4_chain #(.D(DD)) ch(.ck(ck[S_V+(2*(p-1)+k)*DD+:((DD>0)?DD:1)]),.rst(rst[0]),.vi({6'd0,vtag_c[0],cap_v[1+k][0]}),.di(cap_d[1+k]),
   .vo(shv_v[p][k]),.do_(shv_d[p][k]));
 end
 // copy 0 reads V on its own lanes 1, 2, so its own chains are the V (no select needed).
 endgenerate
 // H pieces: quarter c lane 0 -> column c of copy p (words 16*(4*i+p), i = 0..7); aux {dtag (c == 0), source valid}
 wire [7:0] hp_v[0:3][0:3];wire [543:0] hp_d[0:3][0:3];
 generate for(c=0;c<4;c=c+1)for(p=0;p<4;p=p+1)begin:g_h
  wire [127:0] piece;
  for(k=0;k<8;k=k+1)begin:w assign piece[16*k+:16]=cap_d[5*c][16*(4*k+p)+:16];end
  if(c==p)begin:g_local      // the own lane-0 chain of quarter c carries this piece (re-sliced at the merge tile)
   assign hp_v[c][p]=8'd0;assign hp_d[c][p]=544'd0;
  end else begin:g_far
   ot_s81_mx4_chain #(.D(DD)) ch(.ck(ck[S_H+(4*c+p)*DD+:((DD>0)?DD:1)]),.rst(rst[0]),.vi({6'd0,(c==0)?dtag_c[0]:1'b0,cap_v[5*c][0]}),
    .di({416'd0,piece}),.vo(hp_v[c][p]),.do_(hp_d[c][p]));
  end
 end endgenerate
 // per-copy merge tiles and the copy clusters
 wire [3:0] mc_fault[0:3];wire [3:0] c_stat_vtag,c_stat_wqv;wire rq_fault_r;
 wire [75:0] c_req[0:3];wire [30:0] c_wctl[0:3];wire [511:0] c_wd[0:3];wire [3:0] c_done_q,c_fault_q;
 wire [224:0] cl_desc[0:3];          // {start, desc} after DS stations
 generate for(p=0;p<4;p=p+1)begin:cl
  wire [4:0] k_rsv[0:3];wire [639:0] k_rsd[0:3];
  for(c=0;c<4;c=c+1)begin:col
   // own K half and W half of this column (copy p's lanes 1..4: lane 1/3 -> columns 0,1, lane 2/4 -> columns 2,3)
   wire [255:0] kv_own=own_d[5*p+1+(c/2)][256*(c%2)+:256];
   wire [255:0] w_own =own_d[5*p+3+(c/2)][256*(c%2)+:256];
   wire [255:0] kv_v  =(p==0)?kv_own:shv_d[p][c/2][256*(c%2)+:256];
   wire [127:0] h_pc  =hp_d[c][p][127:0];
   // the local piece travels inside the own lane-0 chain as the full lane: re-slice it here
   wire [127:0] h_loc;
   for(k=0;k<8;k=k+1)begin:w assign h_loc[16*k+:16]=own_d[5*c][16*(4*k+p)+:16];end
   wire hv_src=(c==p)?own_v[5*c][0]:hp_v[c][p][0];
   wire hd_tag=(c==p)?own_v[5*c][1]:hp_v[c][p][1];
   ot_s81_mx4_mcol mc(.ck(ck[CK_MC+4*p+c]),.rst(rst[0]),
    .v_own({own_v[5*p+4][0],own_v[5*p+3][0],own_v[5*p+2][0],own_v[5*p+1][0],own_v[5*p][0]}),
    .d_own(p==0?own_v[0][1]:1'b0),
    .v_sh({(p==0)?own_v[2][0]:shv_v[p][1][0],(p==0)?own_v[1][0]:shv_v[p][0][0]}),
    .vtag((p==0)?1'b0:shv_v[p][0][1]),
    .kv_own(kv_own),.kv_sh((MUT==29&&p==1&&c==2)?kv_own:kv_v),.w(w_own),.h((c==p)?h_loc:h_pc),
    .h_src_v(hv_src),.h_dtag(hd_tag),
    .rs_v(k_rsv[c]),.rs_d(k_rsd[c]),.fault(mc_fault[p][c]));
  end
  wire [4:0] rq_v_c;wire [69:0] rq_row_c;wire vtag_c_k,wq_v_c,done_c,fault_c;wire [13:0] wq_row_c;wire [15:0] wq_mask_c;wire [511:0] wq_d_c;
  ot_s81_engram_mixq_bc #(.MUT(MUT),.VM_LAT(VM_LAT+2+DU+DD+2),.WRITE_COMMIT_LAT(WRITE_COMMIT_LAT),.HLAYOUT(HLAYOUT)) u(
   .ck(ck[52*p+:52]),.rst(rst[0]),.start(cl_desc[p][224]),.desc(cl_desc[p][223:0]),
   .rq_v(rq_v_c),.rq_row(rq_row_c),.vtag(vtag_c_k),
   .rs_v_col({k_rsv[3],k_rsv[2],k_rsv[1],k_rsv[0]}),.rs_d_col({k_rsd[3],k_rsd[2],k_rsd[1],k_rsd[0]}),
   .wq_v(wq_v_c),.wq_row(wq_row_c),.wq_mask(wq_mask_c),.wq_d(wq_d_c),.done(done_c),.fault(fault_c));
  // up transport: request -> own request port (DU); write control -> own write port, write data column c -> write
  // port c (DW); status -> control (DC)
  wire [7:0] ur_v;wire [543:0] ur_d;
  ot_s81_mx4_chain #(.D(DU)) cu(.ck(ck[S_U+p*DU+:((DU>0)?DU:1)]),.rst(rst[0]),.vi({2'd0,vtag_c_k,rq_v_c}),.di({474'd0,rq_row_c}),.vo(ur_v),.do_(ur_d));
  assign u_req[p]={ur_v[5],ur_d[69:0],ur_v[4:0]};
  wire [7:0] uw_v;wire [543:0] uw_d;
  ot_s81_mx4_chain #(.D(DW)) cw(.ck(ck[S_W+p*DW+:((DW>0)?DW:1)]),.rst(rst[0]),.vi({7'd0,wq_v_c}),.di({514'd0,wq_mask_c,wq_row_c}),.vo(uw_v),.do_(uw_d));
  assign c_wctl[p]={uw_d[29:0],uw_v[0]};
  for(c=0;c<4;c=c+1)begin:wx
   wire [7:0] xv;wire [543:0] xd;
   ot_s81_mx4_chain #(.D(DW)) cx(.ck(ck[S_X+(4*p+c)*DW+:((DW>0)?DW:1)]),.rst(rst[0]),.vi(8'd0),.di({416'd0,wq_d_c[128*c+:128]}),.vo(xv),.do_(xd));
   assign c_wd[p][128*c+:128]=xd[127:0];
  end
  wire [7:0] us_v;wire [543:0] us_d;
  ot_s81_mx4_chain #(.D(DC)) cs(.ck(ck[S_C+p*DC+:((DC>0)?DC:1)]),.rst(rst[0]),
   .vi({2'd0,mc_fault[p]!=4'd0,1'b0,wq_v_c,vtag_c_k,fault_c,done_c}),.di(544'd0),.vo(us_v),.do_(us_d));
  assign c_done_q[p]=us_v[0];assign c_fault_q[p]=us_v[1]|us_v[5];
  assign c_stat_vtag[p]=us_v[2];assign c_stat_wqv[p]=us_v[3];
 end endgenerate
 // ---------------- write ports (quarter j = VM write lane j): control from copy j, data column j of every copy
 generate for(q=0;q<4;q=q+1)begin:g_wt
  wire [511:0] d;
  for(k=0;k<8;k=k+1)for(p=0;p<4;p=p+1)begin:il assign d[16*(4*k+p)+:16]=c_wd[p][128*q+16*k+:16];end
  wire [7:0] wv;wire [543:0] wd;
  ot_s81_mx4_sreg wt(.ck(ck[CK_WT+q]),.rst(rst[0]),.vi({7'd0,c_wctl[q][0]}),.di({c_wctl[q][30:1],d}),.vo(wv),.do_(wd));
  assign wq_v[q]=wv[0];assign wq_d[512*q+:512]=wd[511:0];assign wq_row[14*q+:14]=wd[525:512];assign wq_mask[16*q+:16]=wd[541:526];
 end endgenerate

 // ---------------- control
 wire [7:0] dr_v;wire [543:0] dr_d;   // descriptor reply from quarter 0 lane 0: aux {dtag}, data {rdq[223:0]}
 ot_s81_mx4_chain #(.D(DR)) cr(.ck(ck[S_R+:((DR>0)?DR:1)]),.rst(rst[0]),.vi({5'd0,rq_fault[0],dtag_c[0],cap_v[0][0]}),.di({320'd0,cap_d[0][223:0]}),.vo(dr_v),.do_(dr_d));
 wire [14:0] ctl_desc;wire [224:0] ctl_cdesc[0:3];
 ot_s81_mx4_ctl #(.MUT(MUT),.BC(BC)) ctl(.ck(ck[CK_CTL]),.rst(rst[0]),.c_cmd(c_cmd),.c_done(c_done),.c_st(c_st),
  .desc_v(dr_v[1]),.desc_rv(dr_v[0]),.desc_d(dr_d[223:0]),
  .cl_done(c_done_q),.cl_fault(c_fault_q|{3'd0,rq_fault_r}),.cl_vtag(c_stat_vtag),.cl_wqv(c_stat_wqv),
  .desc_rq(ctl_desc[14]),.desc_row(ctl_desc[13:0]),
  .cdesc0(ctl_cdesc[0]),.cdesc1(ctl_cdesc[1]),.cdesc2(ctl_cdesc[2]),.cdesc3(ctl_cdesc[3]));
 wire [7:0] qq_v;wire [543:0] qq_d;
 ot_s81_mx4_chain #(.D(DQ)) cq(.ck(ck[S_Q+:((DQ>0)?DQ:1)]),.rst(rst[0]),.vi({7'd0,ctl_desc[14]}),.di({530'd0,ctl_desc[13:0]}),.vo(qq_v),.do_(qq_d));
 assign q_desc={qq_v[0],qq_d[13:0]};
 assign rq_fault_r=dr_v[2];          // the quarter-0 request-port clash fault rides the descriptor-reply stations
 generate for(p=0;p<4;p=p+1)begin:g_ds
  wire [7:0] sv;wire [543:0] sd;
  ot_s81_mx4_chain #(.D(DS)) cd(.ck(ck[S_S+p*DS+:((DS>0)?DS:1)]),.rst(rst[0]),.vi({7'd0,ctl_cdesc[p][224]}),.di({320'd0,ctl_cdesc[p][223:0]}),.vo(sv),.do_(sd));
  assign cl_desc[p]={sv[0],sd[223:0]};
 end endgenerate
endmodule

// D-station transport chain (wires only; every station is one ot_s81_mx4_sreg tile on its own clock entry)
module ot_s81_mx4_chain #(parameter integer D=1)(input wire [((D>0)?D:1)-1:0] ck,input wire rst,
 input wire [7:0] vi,input wire [543:0] di,output wire [7:0] vo,output wire [543:0] do_);
 generate if(D==0)begin:g_w assign vo=vi;assign do_=di;end else begin:g_s
  wire [7:0] v[0:D];wire [543:0] d[0:D];assign v[0]=vi;assign d[0]=di;
  for(genvar s=0;s<D;s=s+1)begin:st
   ot_s81_mx4_sreg r(.ck(ck[s]),.rst(rst),.vi(v[s]),.di(d[s]),.vo(v[s+1]),.do_(d[s+1]));
  end
  assign vo=v[D];assign do_=d[D];
 end endgenerate
endmodule

// Universal station tile: one registered edge for 8 reset (valid / tag) bits and 544 data bits; reset released on its
// own root.  Captures, transport stations and write ports are all this one master (spare bits are declared pads).
module ot_s81_mx4_sreg(input wire ck,input wire rst,input wire [7:0] vi,input wire [543:0] di,
 output reg [7:0] vo,output reg [543:0] do_);
 reg [1:0] rs;always @(posedge ck or negedge rst)if(!rst)rs<=0;else rs<={rs[0],1'b1};
 wire rn=rs[1];
 always @(posedge ck or negedge rn)if(!rn)vo<=0;else vo<=vi;
 always @(posedge ck)do_<=di;
endmodule

// Request port of one quarter (the old top request stage, now per quarter): one registered edge to the VM request pins.
// SUP=1 (quarters 1..3, strap): a V-tagged request issues no physical lane-1/2 request (copy 0 reads the shared V).
// Quarter 0: the control's descriptor read rides lane 0 (desc_rq) and a simultaneous copy-0 lane-0 request is a clash
// fault.  dtag / vtag = desc_rq / u_vtag delayed VM_LAT+2 edges: aligned with this quarter's return captures.
module ot_s81_mx4_rq #(parameter integer VM_LAT=1, SUP=0)(input wire ck,input wire rst,
 input wire [4:0] u_v,input wire [69:0] u_row,input wire u_vtag,input wire desc_rq,input wire [13:0] desc_row,
 output reg [4:0] rq_v,output reg [69:0] rq_row,output wire dtag,output wire vtag,output reg fault);
 reg [1:0] rs;always @(posedge ck or negedge rst)if(!rst)rs<=0;else rs<={rs[0],1'b1};
 wire rn=rs[1];
 reg [VM_LAT+1:0] dl,vl;
 // descriptor-read pin register (ENGRAM-3 10-16, native capture: the scalar desc_rq fanned out to the 15-bit injection
 // mux + delay line + clash check, 200-212 ps > 190 at the pin): desc_rq/desc_row are captured at the pin first; the
 // descriptor request leaves one edge later (+1 cycle on the descriptor read only) and dtag stays aligned (dl takes dq_q).
 reg dq_q;reg [13:0] dr_q;
 always @(posedge ck or negedge rn)if(!rn)dq_q<=0;else dq_q<=desc_rq;
 always @(posedge ck)dr_q<=desc_row;
 always @(posedge ck or negedge rn)if(!rn)begin rq_v<=0;rq_row<=0;dl<=0;vl<=0;fault<=0;end else begin
  rq_v<=u_v;rq_row<=u_row;
  if(SUP!=0&&u_vtag)begin rq_v[1]<=0;rq_v[2]<=0;end
  if(dq_q)begin rq_v[0]<=1'b1;rq_row[0+:14]<=dr_q;end
  fault<=dq_q&&u_v[0];
  dl<={dl[VM_LAT:0],dq_q};vl<={vl[VM_LAT:0],u_vtag};
 end
 assign dtag=dl[VM_LAT+1];assign vtag=vl[VM_LAT+1];
endmodule

// Column merge tile (input registers + output registers: two edges).  Builds one shell payload column's return word
// exactly as the old top's return demux did for this column: lanes 1,2 = shared V (vtag) or own, lanes 0,3,4 own; the
// lane-0 valid of copy 0 is masked by the descriptor-reply tag; payload {W half, K/V half, H piece}.  H lockstep: the
// H piece's source lane-0 valid must equal the own lane-0 valid unless the reply is the descriptor (sticky fault).
module ot_s81_mx4_mcol(input wire ck,input wire rst,input wire [4:0] v_own,input wire d_own,input wire [1:0] v_sh,
 input wire vtag,input wire [255:0] kv_own,kv_sh,w,input wire [127:0] h,input wire h_src_v,h_dtag,
 output reg [4:0] rs_v,output reg [639:0] rs_d,output reg fault);
 reg [1:0] rs;always @(posedge ck or negedge rst)if(!rst)rs<=0;else rs<={rs[0],1'b1};
 wire rn=rs[1];
 reg [4:0] vo_q;reg do_q;reg [1:0] vs_q;reg vt_q,hv_q,ht_q;reg [255:0] ko_q,ks_q,w_q;reg [127:0] h_q;
 always @(posedge ck or negedge rn)if(!rn)begin vo_q<=0;do_q<=0;vs_q<=0;vt_q<=0;hv_q<=0;ht_q<=0;end
 else begin vo_q<=v_own;do_q<=d_own;vs_q<=v_sh;vt_q<=vtag;hv_q<=h_src_v;ht_q<=h_dtag;end
 always @(posedge ck)begin ko_q<=kv_own;ks_q<=kv_sh;w_q<=w;h_q<=h;end
 always @(posedge ck or negedge rn)if(!rn)begin rs_v<=0;fault<=0;end else begin
  rs_v<={vo_q[4],vo_q[3],vt_q?vs_q[1]:vo_q[2],vt_q?vs_q[0]:vo_q[1],vo_q[0]&&!do_q};
  if(!ht_q&&!do_q&&hv_q!=vo_q[0])fault<=1;
 end
 always @(posedge ck)rs_d<={w_q,vt_q?ks_q:ko_q,h_q};
endmodule

// Control tile: the old top FSM.  Descriptor reply (desc_v = dtag after the reply stations) is checked and broadcast
// as four folded per-copy descriptors; every cluster's done must arrive in one cycle; lockstep of the V tag and of the
// write valid; sticky faults.
module ot_s81_mx4_ctl #(parameter integer MUT=0, BC=2)(input wire ck,input wire rst,input wire [84:0] c_cmd,
 output wire [8:0] c_done,output wire [1:0] c_st,
 input wire desc_v,desc_rv,input wire [223:0] desc_d,
 input wire [3:0] cl_done,cl_fault,cl_vtag,cl_wqv,
 output reg desc_rq,output reg [13:0] desc_row,
 output wire [224:0] cdesc0,cdesc1,cdesc2,cdesc3);
 reg [1:0] reset_sync;
 always @(posedge ck or negedge rst)if(!rst)reset_sync<=0;else reset_sync<={reset_sync[0],1'b1};
 wire rn=reset_sync[1];
 wire jv,jnew,epf;wire [83:0] jd,jnd;reg done,fault;reg inp_q;
 always @(posedge ck or negedge rn)if(!rn)inp_q<=0;else inp_q<=1'b1;   // static issue
 ot_s81_slab_ep ep(.c_clk(ck),.c_rst_n(rn),.c_cmd(c_cmd),.c_done(c_done),.c_st(c_st),
  .e_clk(ck),.e_rst_n(rn),.j_v(jv),.j_d(jd),.j_new(jnew),.j_new_d(jnd),.j_present(1'b1),.j_done(done),.slab_fault(fault),.ep_fault(epf));
 reg [3:0] cdone_q,cfault_q,cvtag_q,cwqv_q;reg dv_q,drv_q;reg [223:0] dd_q;
 always @(posedge ck or negedge rn)if(!rn)begin cdone_q<=0;cfault_q<=0;cvtag_q<=0;cwqv_q<=0;dv_q<=0;drv_q<=0;end
 else begin cdone_q<=cl_done;cfault_q<=cl_fault;cvtag_q<=cl_vtag;cwqv_q<=cl_wqv;dv_q<=desc_v;drv_q<=desc_rv;end
 always @(posedge ck)dd_q<=desc_d;
 reg [2:0] tstate;localparam T_IDLE=0,T_DESC=1,T_RUN=2,T_DONE=3,T_POP=4;
 reg [BC:0] st_line;reg [223:0] desc_line[0:BC];
 wire [31:0] desc_hrow=dd_q[0+:32]&32'hfffbffff;
 wire [31:0] desc_kw_span=dd_q[18]?32'd5120:32'd1280;
 wire [31:0] desc_v_span=dd_q[18]?32'd640:32'd320;
 always @(posedge ck or negedge rn)if(!rn)begin
  tstate<=T_IDLE;desc_rq<=0;desc_row<=0;done<=0;fault<=0;st_line<=0;
 end else begin
  desc_rq<=0;done<=0;st_line<={st_line[BC-1:0],1'b0};
  if(epf||(|cfault_q))fault<=1;
  if(dv_q&&!drv_q)fault<=1;                                      // lost descriptor reply
  if(cvtag_q!=4'b0000&&cvtag_q!=4'b1111)fault<=1;                // clusters out of lockstep
  if(cwqv_q!=4'b0000&&cwqv_q!=4'b1111)fault<=1;                  // interleaved H writes need all four
  case(tstate)
  T_IDLE:if(jv&&!fault)begin
   if(!inp_q||jd[30:21]!=0)fault<=1;else begin desc_rq<=1;desc_row<=jd[7+:14];tstate<=T_DESC;end
  end
  T_DESC:if(dv_q)begin
   if(desc_hrow>15744||dd_q[32+:32]>16384-desc_kw_span||dd_q[64+:32]>16384-desc_kw_span||dd_q[96+:32]>16384-desc_v_span||dd_q[128+:32]>15744)fault<=1;
   if((dd_q[128+:32]!=desc_hrow && dd_q[128+:32]<desc_hrow+640 && desc_hrow<dd_q[128+:32]+640) ||
      (dd_q[128+:32]<dd_q[32+:32]+desc_kw_span && dd_q[32+:32]<dd_q[128+:32]+640) ||
      (dd_q[128+:32]<dd_q[64+:32]+desc_kw_span && dd_q[64+:32]<dd_q[128+:32]+640) ||
      (dd_q[128+:32]<dd_q[96+:32]+desc_v_span && dd_q[96+:32]<dd_q[128+:32]+640))fault<=1;
   if(dd_q[191] || dd_q[183+:8]==255 || dd_q[160+:31]==0 || dd_q[223] || dd_q[215+:8]==255 || dd_q[192+:31]==0)fault<=1;
   st_line[0]<=1'b1;tstate<=T_RUN;
  end
  T_RUN:if(|cdone_q)begin if(cdone_q!=4'b1111)fault<=1;tstate<=T_DONE;end
  T_DONE:begin done<=!fault&&!epf;tstate<=T_POP;end
  T_POP:tstate<=T_IDLE;
  default:fault<=1;
  endcase
 end
 always @(posedge ck)desc_line[0]<=(tstate==T_DESC&&dv_q)?dd_q:desc_line[0];
 genvar s,c;
 generate for(s=1;s<=BC;s=s+1)begin:bc always @(posedge ck)desc_line[s]<=desc_line[s-1];end
 for(c=0;c<4;c=c+1)begin:fold
  // per-copy descriptor folded exactly as the old top (HLAYOUT=1): H/output row + copy index, copy index in bits 17:16
  localparam [1:0] CC=c;wire [223:0] cd;
  assign cd[13:0]=desc_line[BC][13:0]+((MUT==2&&c==3)?14'd2:14'(c));
  assign cd[31:14]={desc_line[BC][31:18],CC,desc_line[BC][15:14]};
  assign cd[45:32]=desc_line[BC][18]?desc_line[BC][45:32]:desc_line[BC][45:32]+14'd320*c;assign cd[63:46]=desc_line[BC][63:46];
  assign cd[77:64]=desc_line[BC][18]?desc_line[BC][77:64]:desc_line[BC][77:64]+14'd320*c;assign cd[127:78]=desc_line[BC][127:78];
  assign cd[141:128]=desc_line[BC][141:128]+14'(c);assign cd[223:142]=desc_line[BC][223:142];
  reg [224:0] o;always @(posedge ck)o<={st_line[BC],cd};     // registered output: start and descriptor leave together
  if(c==0)begin:o0 assign cdesc0=o;end else if(c==1)begin:o1 assign cdesc1=o;end else if(c==2)begin:o2 assign cdesc2=o;end else begin:o3 assign cdesc3=o;end
 end endgenerate
endmodule
