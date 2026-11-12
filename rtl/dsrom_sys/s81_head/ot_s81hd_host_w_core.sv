`timescale 1ns/1ps
`default_nettype none
// DH55-HSPLIT (COORD ruling (a), GEOM-111, 2026-11-02): hd_host split into two abutted plan types.
//   hd_host_w = ot_s81hd_host_w_core: lane0 + HBC1 + host276 rx/tx + frame mux + job-active pin (W/N faces).
//   hd_host_e = ot_s81hd_host_e_core: lane1 only (S face).
// The original ot_s81hd_host_ep_core (unchanged, ot_s81hd_host_ep_core.sv) is the reference. Instance names
// (u_lane0, u_lane1, u_ctl_rx, u_ctl_tx, u_hbc, u_mux) are kept so the hard-core paths of the plan carry over.
// Seam (two plan buses, every partition output registered and every input landed on a register):
//   l1_rx  E->W  {flt[3:0], rx_v, rx_d[552:0]} (558): driven directly by the lane1 RX pin flops / fault flops in E
//          (lsc_r0m rd_q/rv_q/flt_q, lsc_r1m rx_d), landed in W on u_l1rx_* (+1 cycle on host1 frames and lane1 faults).
//   l1_tx  W->E  {tx_v, tx_d[552:0]} (554): registered in W at its E face on u_l1tx_* (+1 cycle on lane1 STATUS TX);
//          landed in E by the lane1 tx_d pin flops (lsc_t* txd_p) and tx_v kf copies, exactly as before the split.
// Latency: +1 cycle E->W, +1 cycle W->E; lane0, HBC dates (BOOT_HEADER/COMMIT_EDGE, lane0 records), host276 and
// the lane0 RESULT TX are unchanged. Only valid/fault bits are reset; data holds are unreset.
// MUT (bench negative controls only; 0 = production): 1 drop the W landing register (0-cycle), 2 swap rx_d bits
// 16/17 at the landing, 3 extra W->E cycle, 4 lane1 fault not landed, 5 lane0 RX stage dropped.
// DH58-RFRTL (l48rf, DIE-HEAD-56 ruling 06:1x on the DH56 3_place r2r census, W 448 um lane0 rx_d -> u_mux/u_hbc):
// L0_STAGE=1 registers the lane0 RX outputs {flt, rx_v, rx_d} once before u_mux / u_hbc (valid / fault reset, data
// unreset): +1 cycle on every lane0 ingress frame (HBC records, HFWD, lane0 faults).  The HBC dates move with it
// (BOOT_HEADER_EDGE / BOOT_COMMIT_EDGE and the record date fields +1: the plan declares the lane0 ingress lane
// fixed_cycles +1, so head_boot_recipe re-derives them); the lane0 RESULT TX path and the HOST receiver epoch
// relative to its own records are unchanged.  L0_STAGE=0 = the DH56 form (bench reference only).
// HEAD-94 11-11 (COORD 04:xx hd_host_w a3 TT -76, worst path l0s_v -> u_mux select fan-out (86/84) -> u_ctl_tx.oq_p, 860 ps, 11 gates,
// not a core-core hop): TX_STAGE=1 registers the frame mux output {ctl_rx_v, ctl_rx_d} once before u_ctl_tx (valid reset, data unreset,
// keep): +1 cycle on EVERY host276 h_rx_o frame (HFWD type 7, CSR type 6, fault STATUS type 8, all others); the lane0 ingress / HBC dates,
// peer0/peer1 RX and the lane1 seam are unchanged.  The plan declares the cycle as fixed_cycles +1 on the host_rx lane (LAT_HD_HOST_RX +1).
// TX_STAGE=0 = the DH58 circuit (bench reference); production default 1 after the lockstep bench passed (HEAD-94 11-11).
module ot_s81hd_host_w_core #(
 parameter[1:0]CH_B=2'b11,
 parameter integer LOCAL_STAGE=255,LOCAL_RANK=4,PHASE_BOUND=0,
 parameter integer MUT=0,
 parameter integer SPLIT_MUT=0,
 parameter integer L0_STAGE=1,
 parameter integer TX_STAGE=1,
 parameter[63:0]CLOCK_RESET_ID=0,
 parameter[47:0]BOOT_HEADER_EDGE=48'hffffffffffff,
 parameter[47:0]BOOT_COMMIT_EDGE=48'hffffffffffff
)(
 input wire ck,rst_n,start_i,
 input wire[513:0]coll_i0,
 output wire[511:0]coll_o0,
 input wire[276:0]h_tx_i,output wire[275:0]h_rx_o,
 input wire[557:0]l1_rx_i,
 output wire[553:0]l1_tx_o
);
 (* keep="true",face_keep="true" *)reg job_active_pin;
 always@(posedge ck or negedge rst_n)if(!rst_n)job_active_pin<=0;else job_active_pin<=h_tx_i[276];
 // Seam landing (E->W): lane1 RX valid/fault reset, data unreset.
 (* keep="true" *)reg l1rx_v;(* keep="true" *)reg[3:0]l1rx_f;(* keep="true" *)reg[552:0]l1rx_d;
 always@(posedge ck or negedge rst_n)if(!rst_n)begin l1rx_v<=0;l1rx_f<=0;end
  else begin l1rx_v<=l1_rx_i[553];l1rx_f<=(SPLIT_MUT==4)?4'd0:l1_rx_i[557:554];end
 always@(posedge ck)l1rx_d<=l1_rx_i[552:0];
 wire lv1=(SPLIT_MUT==1)?l1_rx_i[553]:l1rx_v;
 wire[552:0]ld1=(SPLIT_MUT==1)?l1_rx_i[552:0]:(SPLIT_MUT==2)?{l1rx_d[552:18],l1rx_d[16],l1rx_d[17],l1rx_d[15:0]}:l1rx_d;
 wire[3:0]lf1=l1rx_f;
 wire[1:0]lv,txv;wire[1105:0]ld,txd;wire[3:0]lf0;
 assign lv[1]=lv1;assign ld[1105:553]=ld1;
 wire l0v_q;wire[552:0]l0d_q;wire[3:0]l0f_q;
 ot_s81hd_mesh_lane u_lane0(.ck(ck),.rst_n(rst_n),.chb(CH_B[0]),
  .rx(coll_i0),.tx(coll_o0),.tx_v(txv[0]),.tx_d(txd[552:0]),
  .rx_v(l0v_q),.rx_d(l0d_q),.flt(l0f_q));
 generate if(L0_STAGE!=0&&SPLIT_MUT!=5)begin:g_l0s
  (* keep="true" *)reg l0s_v;(* keep="true" *)reg[3:0]l0s_f;(* keep="true" *)reg[552:0]l0s_d;
  always@(posedge ck or negedge rst_n)if(!rst_n)begin l0s_v<=0;l0s_f<=0;end else begin l0s_v<=l0v_q;l0s_f<=l0f_q;end
  always@(posedge ck)l0s_d<=l0d_q;
  assign lv[0]=l0s_v;assign ld[552:0]=l0s_d;assign lf0=l0s_f;
 end else begin:g_l0d
  assign lv[0]=l0v_q;assign ld[552:0]=l0d_q;assign lf0=l0f_q;
 end endgenerate
 // Seam launch (W->E): lane1 TX registered at the E face.
 (* keep="true" *)reg l1tx_v;(* keep="true" *)reg[552:0]l1tx_d;
 always@(posedge ck or negedge rst_n)if(!rst_n)l1tx_v<=0;else l1tx_v<=txv[1];
 always@(posedge ck)l1tx_d<=txd[1105:553];
 generate if(SPLIT_MUT==3)begin:g_mut3
  reg l1tx_v2;reg[552:0]l1tx_d2;
  always@(posedge ck or negedge rst_n)if(!rst_n)l1tx_v2<=0;else l1tx_v2<=l1tx_v;
  always@(posedge ck)l1tx_d2<=l1tx_d;
  assign l1_tx_o={l1tx_v2,l1tx_d2};
 end else begin:g_seam
  assign l1_tx_o={l1tx_v,l1tx_d};
 end endgenerate
 wire cv,crxf,ctxv;wire[552:0]cd,rxframe;wire rxv,crtxf;
 wire rxv_m;wire[552:0]rxframe_m;   // u_mux output (before the optional TX stage)
 ot_s81hd_host276_rx u_ctl_rx(.ck(ck),.rn(rst_n),.lane(h_tx_i[275:0]),.v(cv),.frame(cd),.fault(crxf));
 ot_s81hd_host276_tx u_ctl_tx(.ck(ck),.rn(rst_n),.v(rxv),.frame(rxframe),.lane(h_rx_o),.fault(crtxf));
 wire[1103:0]from_prev,to_local,next_ro;
 wire[1103:0]local_ro={571'd0,cd[527:16],8'd0,4'd0,5'd1,3'd6,cv};
 wire[3:0]return_fault;wire[11:0]hbc_stage_fault;wire[7:0]hbc_fault;
 wire[514:0]f_host;wire[52:0]ks;wire[2:0]ks_slot;wire[5:0]arm_mask;wire arm_commit;
 wire[47:0]receiver_edge,boot_edge;
 dsdv_hostb_stage_hbc #(.ENABLE(1),.LOCAL_STAGE(LOCAL_STAGE),.LOCAL_RANK(LOCAL_RANK),
  .PHASE_BOUND(PHASE_BOUND),.RETURN_LOCAL(0),.RX_ONLY(1),.HOST_FRAMES(1),.CLOCK_RESET_ID(CLOCK_RESET_ID),
  .BOOT_HEADER_EDGE(BOOT_HEADER_EDGE),.BOOT_COMMIT_EDGE(BOOT_COMMIT_EDGE))u_hbc(
  .ck(ck),.rst_n(rst_n),.job_active(job_active_pin),.starter_armed(start_i),
  .from_prev(from_prev),.local_ro(local_ro),.return_ro(local_ro),
  .status_t_host({11'd0,job_active_pin,65'd0}),.status_t_kd(cd[69:16]),
  .return_fault(return_fault),.to_local(to_local),.next_ro(next_ro),
  .f_host(f_host),.ks_descriptor(ks),.ks_slot(ks_slot),.arm_mask(arm_mask),
  .arm_commit(arm_commit),.fault(hbc_stage_fault),.context_valid(ctxv),
  .receiver_edge(receiver_edge),.boot_edge(boot_edge),.hbc_fault(hbc_fault));
 wire[16:0]source_fault={
  (f_host[0]||arm_commit||ks[52]),
  (|return_fault),(|hbc_stage_fault),(|hbc_fault),crtxf,crxf,
  3'd0,lf1,lf0};
 wire[16:0]host_fault;
 ot_s81hd_host_frame_mux #(.MUT(MUT))u_mux(.ck(ck),.rst_n(rst_n),.context_valid(ctxv),
  .host0_v(lv[0]),.host1_v(lv[1]),.host0_d(ld[552:0]),.host1_d(ld[1105:553]),
  .local_ring(to_local),.source_fault(source_fault),.ctl_v(cv),.ctl_d(cd),
  .from_prev(from_prev),.ctl_rx_v(rxv_m),.ctl_rx_d(rxframe_m),
  .lane_tx_v(txv),.lane_tx_d(txd),.fault(host_fault));

 generate if(TX_STAGE!=0)begin:g_txs
  (* keep="true" *)reg txs_v;(* keep="true" *)reg[552:0]txs_d;
  always@(posedge ck or negedge rst_n)if(!rst_n)txs_v<=0;else txs_v<=rxv_m;
  always@(posedge ck)txs_d<=rxframe_m;
  assign rxv=txs_v;assign rxframe=txs_d;
 end else begin:g_txd
  assign rxv=rxv_m;assign rxframe=rxframe_m;
 end endgenerate
endmodule
`default_nettype wire
