`timescale 1ns/1ps
`default_nettype none
// ---------------------------------------------------------------------------------------------------------------------
// Static SU port-group SLICE (H-ELEM-B 2026-10-15): the physical sub-block of quarter QID that sits at VM bank pair
// {2G, 2G+1} of slice QID (adopted floorplan T_band2__npg4_s5: blocks su_<q>0..3 in the VM band, NPG 4 everywhere).
// Contents: 32 arithmetic lanes (quarter-local ids 16G..16G+15 and 64+16G..64+16G+15), their 32 pinned store banks
// (lane i reads/writes only bank i), the two SU-station VM bank leaves ot_hbm_su_static_vm_bank_leaf of banks 2G/2G+1
// (= port group G of ot_hbm_su_static_vm_ports), and the local fill / drain datapaths. Global lane 0 (QID 0, G 0) carries
// the scalar SIDE pipe ot_hbm_su_static_side.
// Locality rule (compiler, checked): VM port p (= VM bank p of the slice) fills and drains ONLY store groups p and p+8
// (8 banks each), which is exactly where the F2 per-quarter spread puts the words of a 128-word issue block (sector s ->
// VM bank s mod 8, store group s mod 16). So no store bank is ever reached from outside its slice.
// Timing (all fixed; edge = rising clk edge at which a command / pin value is sampled):
//   FILL  vmr_cmd[h] = {v, sector16, grp4, row9} at edge E: LG samples the request at E, returns data held E+10..E+11,
//         the slice registers it at E+11 (FILL_REG 1: one physical stage across the slice), bank pins sample E+12,
//         commit E+13 (readable by a bank read sampled at >= E+13).
//   DRAIN vmw_cmd[h] = {v, src, grp4, row9, sector16, mask8} at E: store drain replica sampled at E, data held E+2..E+3,
//         2:1 group select registered at E+3, LG samples the write at E+4, write done +7. src 1 (RF sector, port 0 of
//         slice 0 only) takes the quarter core's rf_dsec (core RF class-5 read issued at E-1, registered at E+3).
//   LANE  store reads sampled at n are consumed by the lane at n+3 (FETCH_EXTRA_EDGES 2); an RF-source stream (code 1)
//         takes rf_bword[p] (core register held n+2..n+3: core RF class-p read issued at n-1); the lane address must
//         equal rf_bcmd[p] (class-p command delayed one edge by the core).
//   RED   red_sel = {v, op3, osel, lane7} at E: if the lane is in this slice, its ro_x is registered at E (slice_x) and
//         must be live (ro_v) when the op takes an external operand.
// Checks latch FAULT (never stall): lane fault/collision, VM leaf spread/return checks, fill+lane write on one bank,
// command naming a group outside the port's pair, lane write / VM read outside its own bank and quarter, RF-source
// stream address != command, lane source code 2/3 (no constant ROM), RF drain on a port other than slice 0 port 0,
// reducer operand from a non-emitting lane, SIDE fault.
// MUT (bench, must FAIL): 1 fill registered one edge early; 2 drain group select flipped; 4 RF-broadcast select one
// edge early.
// ---------------------------------------------------------------------------------------------------------------------
module ot_hbm_su_static_pgslice #(
 parameter integer QID=0,G=0,READ_RETURN=10,WRITE_RETURN=7,FETCH_EXTRA_EDGES=2,MLAT=3,ALAT=3,LEAF=0,MUT=0,MULTIRATE=0,
 // PIN_REG (owner rule 10-15 19:50): every lane is the pin-registered leaf ot_hbm_su_static_lane_pinreg: its store /
 // RF-stream requests leave +2 edges and its writes / reducer operands +4 edges later (su_top_compile --pin-reg)
 parameter integer PIN_REG=0
)(
 input wire pg_clk,
 input wire [255:0] clk_lane, input wire [127:0] clk_insert, input wire [31:0] rst_lane_n,
 input wire [3:0] clk_bcast, rst_bcast_n,
 input wire [31:0] clk_bank,
 input wire [191:0] clk_bank_macro, // six actual SRAM clock entries per pinned bank
 input wire clk_ctl,
 input wire [5:0] clk_side,
 input wire rst_n,
 input wire bridge_rst_n, // phase-zero reset for MULTIRATE boundary only
 input wire [1741:0] control,
 input wire [2*30-1:0] vmr_cmd,
 input wire [2*39-1:0] vmw_cmd,
 input wire [4*32-1:0] rf_bword,
 input wire [4*9-1:0] rf_bcmd,
 input wire [255:0] rf_dsec,
 input wire [11:0] red_sel,
 output reg [31:0] slice_x,
 output wire [2*17-1:0] lg_rq, output wire [2*281-1:0] lg_wq,
 input wire [2*257-1:0] lg_rr, input wire [1:0] lg_w_done,
 output reg fault
);
 // Serial fill destination delay and stream leaf tap return are different
 // contracts at3:4. n+12 response is sampled into fill at n+13; pinned store
 // macros commit n+15. Stream leaf retains its native10/7 edge contract.
 localparam integer RR=MULTIRATE ? 12 : READ_RETURN;
 initial if(MULTIRATE && (READ_RETURN!=10 || WRITE_RETURN!=7))
  $fatal(1,"SU multirate candidate requires source-proven stream tap10/7");
 function automatic integer lid(input integer n); lid=(n<16)?16*G+n:64+16*G+(n-16); endfunction
 // ------------------------------------------------------------------ lanes
 wire [31:0] vi_re,vm_we,kv_we,ro_v,l_fault,l_coll;
 wire [32*24-1:0] vi_addr,vm_waddr,kv_waddr;
 wire [32*96-1:0] rd_addr; wire [32*4-1:0] rd_re; wire [32*8-1:0] rd_src;
 wire [32*32-1:0] vm_wdata,kv_wdata,ro_x,vi_q;
 wire [32*128-1:0] rd_q;
 wire side_v; wire [31:0] side_x,side_y; wire [2:0] side_fn,side_fn_out; wire side_fault;
 for(genvar b=0;b<4;b=b+1)begin:g_bcast
  reg [1741:0] ctl [0:7];
  for(genvar k=0;k<8;k=k+1)begin:g_replica
   always @(posedge clk_bcast[b] or negedge rst_bcast_n[b])
    if(!rst_bcast_n[b])ctl[k]<=0; else ctl[k]<=control;
  end
 end
 for(genvar n=0;n<32;n=n+1)begin:g_lane
  localparam integer L=lid(n);
  localparam integer KIND=(QID==0&&L==0)?2:(L<32)?1:0;
  wire [0:0] c_ld,c_ld_bank,c_emit,c_bank,c_cpair,c_cx_arnd,c_cx_arelu,c_cx_amin,c_cx_cclip,c_co_rnd;
  wire [1199:0] c_ld_c;
  wire [23:0] c_o_v,c_i_v,c_no,c_ni,c_krow,c_obase,c_aibase;
  wire [3:0] c_ls,c_lvw; wire [119:0] c_vb; wire [1:0] c_aind,c_dst,c_cm_m2,c_ce_e2,c_co_dst; wire [4:0] c_gsh;
  wire [7:0] c_srcs; wire [31:0] c_cx_imm3,c_cp_imm1,c_cm_imm1,c_ca_imm2,c_cs_imm2,c_ce_imm1;
  wire [2:0] c_cp_m1,c_cm_m1,c_cm_qm,c_ca_ad,c_ci_sfu,c_cs_sfu,c_cs_e1;
  assign {c_ld,c_ld_bank,c_ld_c,c_emit,c_bank,c_o_v,c_i_v,c_no,c_ni,c_ls,c_lvw,c_vb,c_krow,c_obase,c_aibase,c_aind,c_gsh,c_cpair,c_dst,c_srcs,c_cx_arnd,c_cx_arelu,c_cx_amin,c_cx_cclip,c_cx_imm3,c_cp_m1,c_cp_imm1,c_cm_m1,c_cm_m2,c_cm_qm,c_cm_imm1,c_ca_ad,c_ca_imm2,c_ci_sfu,c_cs_sfu,c_cs_e1,c_cs_imm2,c_ce_e2,c_ce_imm1,c_co_rnd,c_co_dst}=g_bcast[n/8].ctl[n%8];
  wire [839:0] terms;
  for(genvar s=0;s<5;s=s+1)begin:g_terms assign terms[s*168+:168]=c_ld_c[s*240+:168]; end
  wire sv; wire [31:0] sx;
  if(KIND==2)begin:g_side
   assign side_v=sv; assign side_x=sx;
   if(PIN_REG)begin:g_fn_pin
    // the pin-registered FULL lane sees its commands one edge later: the side function selects follow it
    reg [2:0] fn_q,fn_out_q;
    always @(posedge clk_side[0])begin fn_q<=c_ci_sfu; fn_out_q<=c_cs_sfu; end
    assign side_fn=fn_q; assign side_fn_out=fn_out_q;
   end else begin:g_fn_comb assign side_fn=c_ci_sfu; assign side_fn_out=c_cs_sfu; end
  end
  if(PIN_REG)begin:g_pr
  ot_hbm_su_static_lane_pinreg #(.LN(7),.KIND(KIND),.MLAT(MLAT),.ALAT(ALAT),.LEAF(LEAF),.FETCH_EXTRA_EDGES(FETCH_EXTRA_EDGES)) u_lane(
   .clk_stage(clk_lane[n*8+:8]),.clk_insert(clk_insert[n*4+:4]),.rst_n(rst_lane_n[n]),.lane_id(11'(L)),
   .cx_srcs(c_srcs),.ld(c_ld),.ld_bank(c_ld_bank),.ld_c(terms),.emit(c_emit),.bank(c_bank),.o_v(c_o_v),.i_v(c_i_v),
   .no(c_no),.ni(c_ni),.ls(c_ls),.lvw(c_lvw),.vb(c_vb),.krow(c_krow),.obase(c_obase),.aibase(c_aibase),.aind(c_aind),
   .gsh(c_gsh),.cpair(c_cpair),.dst(c_dst),.srcs(c_srcs),.cx_arnd(c_cx_arnd),.cx_arelu(c_cx_arelu),.cx_amin(c_cx_amin),
   .cx_cclip(c_cx_cclip),.cx_imm3(c_cx_imm3),.cp_m1(c_cp_m1),.cp_imm1(c_cp_imm1),.cm_m1(c_cm_m1),.cm_m2(c_cm_m2),
   .cm_qm(c_cm_qm),.cm_imm1(c_cm_imm1),.ca_ad(c_ca_ad),.ca_imm2(c_ca_imm2),.ci_sfu(c_ci_sfu),.cs_sfu(c_cs_sfu),
   .cs_e1(c_cs_e1),.cs_imm2(c_cs_imm2),.ce_e2(c_ce_e2),.ce_imm1(c_ce_imm1),.co_rnd(c_co_rnd),.co_dst(c_co_dst),
   .vi_q(vi_q[n*32+:32]),.rd_q(rd_q[n*128+:128]),.vi_re(vi_re[n]),.vm_we(vm_we[n]),.kv_we(kv_we[n]),.ro_v(ro_v[n]),
   .fault(l_fault[n]),.coll(l_coll[n]),.vi_addr(vi_addr[n*24+:24]),.vm_waddr(vm_waddr[n*24+:24]),
   .kv_waddr(kv_waddr[n*24+:24]),.rd_addr(rd_addr[n*96+:96]),.rd_re(rd_re[n*4+:4]),.rd_src(rd_src[n*8+:8]),
   .vm_wdata(vm_wdata[n*32+:32]),.kv_wdata(kv_wdata[n*32+:32]),.ro_x(ro_x[n*32+:32]),
   .side_v(sv),.side_x(sx),.side_y(side_y));
  end else begin:g_plain
  ot_hbm_su_static_lane #(.LN(7),.KIND(KIND),.MLAT(MLAT),.ALAT(ALAT),.LEAF(LEAF),.FETCH_EXTRA_EDGES(FETCH_EXTRA_EDGES)) u_lane(
   .clk_stage(clk_lane[n*8+:8]),.clk_insert(clk_insert[n*4+:4]),.rst_n(rst_lane_n[n]),.lane_id(11'(L)),
   .cx_srcs(c_srcs),.ld(c_ld),.ld_bank(c_ld_bank),.ld_c(terms),.emit(c_emit),.bank(c_bank),.o_v(c_o_v),.i_v(c_i_v),
   .no(c_no),.ni(c_ni),.ls(c_ls),.lvw(c_lvw),.vb(c_vb),.krow(c_krow),.obase(c_obase),.aibase(c_aibase),.aind(c_aind),
   .gsh(c_gsh),.cpair(c_cpair),.dst(c_dst),.srcs(c_srcs),.cx_arnd(c_cx_arnd),.cx_arelu(c_cx_arelu),.cx_amin(c_cx_amin),
   .cx_cclip(c_cx_cclip),.cx_imm3(c_cx_imm3),.cp_m1(c_cp_m1),.cp_imm1(c_cp_imm1),.cm_m1(c_cm_m1),.cm_m2(c_cm_m2),
   .cm_qm(c_cm_qm),.cm_imm1(c_cm_imm1),.ca_ad(c_ca_ad),.ca_imm2(c_ca_imm2),.ci_sfu(c_ci_sfu),.cs_sfu(c_cs_sfu),
   .cs_e1(c_cs_e1),.cs_imm2(c_cs_imm2),.ce_e2(c_ce_e2),.ce_imm1(c_ce_imm1),.co_rnd(c_co_rnd),.co_dst(c_co_dst),
   .vi_q(vi_q[n*32+:32]),.rd_q(rd_q[n*128+:128]),.vi_re(vi_re[n]),.vm_we(vm_we[n]),.kv_we(kv_we[n]),.ro_v(ro_v[n]),
   .fault(l_fault[n]),.coll(l_coll[n]),.vi_addr(vi_addr[n*24+:24]),.vm_waddr(vm_waddr[n*24+:24]),
   .kv_waddr(kv_waddr[n*24+:24]),.rd_addr(rd_addr[n*96+:96]),.rd_re(rd_re[n*4+:4]),.rd_src(rd_src[n*8+:8]),
   .vm_wdata(vm_wdata[n*32+:32]),.kv_wdata(kv_wdata[n*32+:32]),.ro_x(ro_x[n*32+:32]),
   .side_v(sv),.side_x(sx),.side_y(side_y));
  end
 end
 if(QID==0&&G==0)begin:g_side_pipe
  ot_hbm_su_static_side u_side(.clk(clk_side),.rst_n(rst_n),.v(side_v),.fn(side_fn),.x(side_x),.fn_out(side_fn_out),
   .y(side_y),.fault(side_fault));
 end else begin:g_no_side
  // no FULL lane in this slice: the side result input of its SFU/LIGHT lanes is not used by the lane
  assign side_y=32'd0; assign side_fault=1'b0;
  assign side_v=1'b0; assign side_x=32'd0; assign side_fn=3'd0; assign side_fn_out=3'd0;
 end
 // ------------------------------------------------------------------ VM bank leaves (port group G = banks 2G, 2G+1)
 wire [2*17-1:0] su_rq; wire [2*281-1:0] su_wq; wire [2*257-1:0] su_rr; wire [1:0] su_w_done,leaf_fault,bridge_fault;
 wire [33:0] leaf_rq; wire [561:0] leaf_wq; wire [513:0] leaf_rr; wire [1:0] leaf_done;
 for(genvar h=0;h<2;h=h+1)begin:g_leaf
  if(MULTIRATE)begin:g_multirate
   ot_hbm_su_multirate_bridge u_bridge(
    .serial_clk(clk_ctl),.stream_clk(pg_clk),.rst_n(bridge_rst_n),
    .serial_rq(su_rq[h*17+:17]),.serial_wq(su_wq[h*281+:281]),
    .serial_rr(su_rr[h*257+:257]),.serial_done(su_w_done[h]),
    .stream_rq(leaf_rq[h*17+:17]),.stream_wq(leaf_wq[h*281+:281]),
    .stream_rr(leaf_rr[h*257+:257]),.stream_done(leaf_done[h]),.fault(bridge_fault[h]));
  end else begin:g_same_clock
   assign leaf_rq[h*17+:17]=su_rq[h*17+:17];
   assign leaf_wq[h*281+:281]=su_wq[h*281+:281];
   assign su_rr[h*257+:257]=leaf_rr[h*257+:257];
   assign su_w_done[h]=leaf_done[h];
   assign bridge_fault[h]=1'b0;
  end
  ot_hbm_su_static_vm_bank_leaf #(.QID(QID),.B(2*G+h),.READ_RETURN(READ_RETURN),.WRITE_RETURN(WRITE_RETURN)) u_leaf(
   .clk(pg_clk),.rst_n(rst_n),.su_rq(leaf_rq[h*17+:17]),.su_wq(leaf_wq[h*281+:281]),.su_rr(leaf_rr[h*257+:257]),
   .su_w_done(leaf_done[h]),.lg_rq(lg_rq[h*17+:17]),.lg_wq(lg_wq[h*281+:281]),.lg_rr(lg_rr[h*257+:257]),
   .lg_w_done(lg_w_done[h]),.fault(leaf_fault[h]));
 end
 // ------------------------------------------------------------------ FILL: request, destination delay line, one stage
 localparam integer FD=(MUT==1)?RR-1:RR;
 reg [10:0] fd [0:1][0:RR];          // {v, grp_hi, row9}
 reg [1:0] fr_v; reg [1:0] fr_hi; reg [8:0] fr_row [0:1]; reg [255:0] fr_dat [0:1];
 wire [1:0] cmd_far;
 for(genvar h=0;h<2;h=h+1)begin:g_fill
  wire [29:0] c=vmr_cmd[h*30+:30];
  wire [38:0] w=vmw_cmd[h*39+:39];
  assign su_rq[h*17+:17]={c[29],c[28:13]};
  assign cmd_far[h]=(c[29]&&c[11:9]!=3'(2*G+h))||(w[38]&&!w[37]&&w[35:33]!=3'(2*G+h));
  integer k;
  always @(posedge clk_ctl or negedge rst_n)
   if(!rst_n)begin for(k=0;k<=RR;k=k+1)fd[h][k]<=11'd0; fr_v[h]<=1'b0; end
   else begin
    fd[h][0]<={c[29],c[12],c[8:0]};for(k=1;k<=RR;k=k+1)fd[h][k]<=fd[h][k-1];
    fr_v[h]<=fd[h][FD][10];
   end
  always @(posedge clk_ctl)begin fr_hi[h]<=fd[h][FD][9];fr_row[h]<=fd[h][FD][8:0];fr_dat[h]<=su_rr[h*257+:256];end
 end
 // ------------------------------------------------------------------ store banks
 wire [32*192-1:0] bank_q;
 wire [31:0] st_conflict,st_id_fault;
 // drain store-group reads: port h reads group (h, grp_hi) = slice lanes 8h + 16*grp_hi .. +7
 wire [1:0] dr_v,dr_hi; wire [8:0] dr_row [0:1];
 for(genvar h=0;h<2;h=h+1)begin:g_dr
  wire [38:0] w=vmw_cmd[h*39+:39];
  assign dr_v[h]=w[38]&&!w[37]; assign dr_hi[h]=w[36]; assign dr_row[h]=w[32:24];
 end
 for(genvar n=0;n<32;n=n+1)begin:g_bank
  localparam integer L=lid(n),H=(n/8)%2,HI=n/16,K=n%8;
  wire [53:0] ra; wire [5:0] rv; wire [191:0] q;
  for(genvar p=0;p<4;p=p+1)begin:g_read
   wire [23:0] a=rd_addr[(n*4+p)*24+:24];
   assign ra[p*9+:9]={a[17:16],a[13:7]}; assign rv[p]=rd_re[n*4+p]&&rd_src[n*8+2*p+:2]==2'd0;
  end
  assign ra[4*9+:9]={vi_addr[n*24+16+:2],vi_addr[n*24+7+:7]}; assign rv[4]=vi_re[n]; assign vi_q[n*32+:32]=q[4*32+:32];
  assign ra[5*9+:9]=dr_row[H]; assign rv[5]=dr_v[H]&&dr_hi[H]==1'(HI);
  assign bank_q[n*192+:192]=q;
  wire lw=vm_we[n]|kv_we[n];
  wire [23:0] la=vm_we[n]?vm_waddr[n*24+:24]:kv_waddr[n*24+:24];
  wire [31:0] ldat=vm_we[n]?vm_wdata[n*32+:32]:kv_wdata[n*32+:32];
  wire fw=fr_v[H]&&fr_hi[H]==1'(HI);
  assign st_conflict[n]=fw&&lw;
  reg idf; integer p2;
  always @*begin
   idf=lw&&(la[6:0]!=7'(L)||la[15:14]!=2'(QID));
   for(p2=0;p2<4;p2=p2+1)if(rv[p2]&&(rd_addr[(n*4+p2)*24+:7]!=7'(L)||rd_addr[(n*4+p2)*24+14+:2]!=2'(QID)))idf=1;
  end
  assign st_id_fault[n]=idf;
  ot_hbm_su_static_pinned_bank #(.READERS(6),.RB(9)) u_bank(.clk(clk_bank[n]),.clk_macro(clk_bank_macro[n*6+:6]),.rst_n(rst_n),.read_v(rv),.read_addr(ra),
   .read_data(q),.read_return(),.write_v(lw|fw),.write_addr(fw?fr_row[H]:{la[17:16],la[13:7]}),
   .write_data(fw?fr_dat[H][K*32+:32]:ldat));
 end
 // ------------------------------------------------------------------ RF broadcast into lane operands
 reg [31:0] rf_src_bad;
 for(genvar n=0;n<32;n=n+1)begin:g_opmux
  wire [3:0] is_rf;
  reg [3:0] src1_a,src1_b,src1_c;      // the stream's source code 1 rides the read: request n -> select held n+2..n+3
  for(genvar p=0;p<4;p=p+1)begin:g_p
   assign is_rf[p]=rd_re[n*4+p]&&rd_src[n*8+2*p+:2]==2'd1;
   assign rd_q[(n*4+p)*32+:32]=((MUT==4)?src1_b[p]:src1_c[p])?rf_bword[p*32+:32]:bank_q[n*192+p*32+:32];
  end
  always @(posedge clk_lane[n*8])begin src1_a<=is_rf;src1_b<=src1_a;src1_c<=src1_b;end
  integer p2;
  always @*begin
   rf_src_bad[n]=0;
   for(p2=0;p2<4;p2=p2+1)begin
    if(rd_re[n*4+p2]&&rd_src[n*8+2*p2+1])rf_src_bad[n]=1;
    if(is_rf[p2]&&(!rf_bcmd[p2*9+8]||rd_addr[(n*4+p2)*24+:24]!={16'd0,rf_bcmd[p2*9+:8]}))rf_src_bad[n]=1;
   end
  end
 end
 // ------------------------------------------------------------------ DRAIN: delay line + registered 2:1 group select
 reg [26:0] dd [0:1][0:2];           // {v, src, grp_hi, sector16, mask8}
 wire [1:0] rf_drain_bad;
 for(genvar h=0;h<2;h=h+1)begin:g_drain
  wire [38:0] w=vmw_cmd[h*39+:39];
  assign rf_drain_bad[h]=w[38]&&w[37]&&!(G==0&&h==0);
  integer k;
  always @(posedge clk_ctl or negedge rst_n)
   if(!rst_n)begin for(k=0;k<3;k=k+1)dd[h][k]<=27'd0; end
   else begin dd[h][0]<={w[38],w[37],w[36],w[23:0]};dd[h][1]<=dd[h][0];dd[h][2]<=dd[h][1]; end
  wire hi=dd[h][2][24]^((MUT==2)?1'b1:1'b0);
  reg [255:0] sel; integer kk;
  always @*begin
   for(kk=0;kk<8;kk=kk+1)sel[kk*32+:32]=bank_q[(8*h+16*hi+kk)*192+5*32+:32];
   if(dd[h][2][25])sel=rf_dsec;
  end
  reg wq_v; reg [279:0] wq_p;
  always @(posedge clk_ctl or negedge rst_n)
   if(!rst_n)wq_v<=1'b0; else wq_v<=dd[h][2][26];
  always @(posedge clk_ctl)wq_p<={dd[h][2][23:8],sel,dd[h][2][7:0]};
  assign su_wq[h*281+:281]={wq_v,wq_p};
 end
 // ------------------------------------------------------------------ reducer operand stage
 // red_sel = {v[11], op[10:8], osel[7], lane[6:0]}; lane L is in this slice iff (L mod 64) / 16 == G
 wire [6:0] rl=red_sel[6:0];
 wire mine=red_sel[11]&&!red_sel[7]&&(rl[5:4]==2'(G));
 wire [4:0] rn={rl[6],rl[3:0]};
 wire ext=red_sel[10:8]==3'd0||red_sel[10:8]==3'd1||red_sel[10:8]==3'd3;
 wire red_bad=mine&&ext&&!ro_v[rn];
 always @(posedge clk_ctl)slice_x<=ro_x[rn*32+:32];
 // ------------------------------------------------------------------ sticky fault
 always @(posedge clk_ctl or negedge rst_n)
  if(!rst_n)fault<=1'b0;
  else if((|l_fault)||(|l_coll)||(|leaf_fault)||(|bridge_fault)||(|st_conflict)||(|st_id_fault)||(|cmd_far)||(|rf_src_bad)||
          (|rf_drain_bad)||red_bad||side_fault)fault<=1'b1;
endmodule
`default_nettype wire
