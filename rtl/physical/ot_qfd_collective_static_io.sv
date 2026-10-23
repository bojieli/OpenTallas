`timescale 1ns/1ps
// Production actual collective plus five per-face static digital transports.
// Caller supplies real compiler command and payload and all physical roots.
// No sequencer/CQ channels or invented idle ties are instantiated. Only the
// PHY frame boundary is external. Normal operation is fixed-cycle; abort is
// exceptional and requires explicit reset/drain before reuse.
module qfd_collective_static_io #(
 parameter integer PU=14,PS=339,LU=47,LS=376,RU=5,RS0=0,RS1=0,RS2=5,SHARED_UCIE=0,SIX_FIVE=0,
 // TOKEN-XDIE-QTP8 10-18 (opt-in, defaults 0 = unchanged behaviour): TOK_REG = the hardened face form (qfd_coll_face_*
 // kits use TOK_REG=1; latency-neutral by construction); LX0..2 = die-level PHY-side lane cycles on SerDes face j that
 // the rx calendar must absorb (forwarded lanes + landing between io_collective and io_serdes_j: E_tx(peer port) +
 // E_rx(own port) from the die GEN fwd_lanes.json); the face then expects the peer frame at PHY = PS + LXj.
 parameter integer TOK_REG=0,LX0=0,LX1=0,LX2=0,
 parameter integer SAFE=0,PLAND=0,PLD=2,PLK=1,UP_SYNC=0
)(
 input wire  clk,
 input wire  clk_pfold0,
 input wire  clk_pfold1,
 input wire  clk_pfold2,
 input wire  clk_pfold3,
 input wire  clk_xfold0,
 input wire  clk_xfold1,
 input wire  clk_xfold2,
 input wire  clk_xfold3,
 input wire  clk_pring0,
 input wire  clk_pring1,
 input wire  clk_sring0,
 input wire  clk_sring1,
 input wire  clk_sring2,
 input wire  clk_sring3,
 input wire  clk_sring4,
 input wire  clk_rring0,
 input wire  clk_rring1,
 input wire  rst_n,
 input wire [1:0] pkg_s,
 input wire  die_ps,
 input wire  cmd_v,
 input wire  cmd_mode,
 input wire [15:0] cmd_words,
 input wire [31:0] cmd_tag,
 input wire  in_valid,
 input wire [511:0] in_data,
 input wire  in_last,
 input wire  in_mode,
 input wire [31:0] in_tag,
 output wire  out_valid,
 output wire [511:0] out_data,
 output wire  out_last,
 output wire [2:0] out_rank,
 output wire  out_err,
 output wire  fault,
 output wire [4:0] fault_code,
 output wire  cmd_free,
 // Eleven physical roots per face: cal core/link, TXw/TXr,RXw/RXr,
 // codec control and four SRAM banks. Index0=P,1=R,2..4=SerDes0..2.
 input wire[54:0]face_ck,
 input wire[((2*(2*RU+RS0+RS1+RS2)>0)?2*(2*RU+RS0+RS1+RS2):1)-1:0]relay_ck,
 input wire[4:0]phy_up,phy_rx_valid,input wire[5*597-1:0]phy_rx,
 output wire[4:0]phy_tx_valid,output wire[5*597-1:0]phy_tx,
 output wire[19:0]transport_cdc_fault,output wire[4:0]transport_abort,
 input wire gearbox_core_ck,fdi_ck,fdi_rx_ck,input wire[1:0]blk_ck,input wire shared_rx_valid,input wire[1042:0]shared_rx,
 output wire shared_tx_valid,output wire[1042:0]shared_tx,output wire shared_fault,
 output wire[39:0]transport_fault_cause
);
 wire  up_valid;
 wire [545:0] up_rec;
 wire  dp_valid;
 wire [545:0] dp_rec;
 wire  ur_valid;
 wire [513:0] ur_rec;
 wire  dr_valid;
 wire [513:0] dr_rec;
 wire  sx0_valid;
 wire  sx1_valid;
 wire  sx2_valid;
 wire [545:0] sx0_rec;
 wire [545:0] sx1_rec;
 wire [545:0] sx2_rec;
 wire  sr0_valid;
 wire  sr1_valid;
 wire  sr2_valid;
 wire [545:0] sr0_rec;
 wire [545:0] sr1_rec;
 wire [545:0] sr2_rec;
 wire  up_slot;
 wire  ur_peer_slot;
 wire  sx0_peer_slot;
 wire  sx1_peer_slot;
 wire  sx2_peer_slot;
 qfd_io_collective_static #(.LU(LU),.LS(LS)) u_collective(
 .clk(clk),
 .clk_pfold0(clk_pfold0),
 .clk_pfold1(clk_pfold1),
 .clk_pfold2(clk_pfold2),
 .clk_pfold3(clk_pfold3),
 .clk_xfold0(clk_xfold0),
 .clk_xfold1(clk_xfold1),
 .clk_xfold2(clk_xfold2),
 .clk_xfold3(clk_xfold3),
 .clk_pring0(clk_pring0),
 .clk_pring1(clk_pring1),
 .clk_sring0(clk_sring0),
 .clk_sring1(clk_sring1),
 .clk_sring2(clk_sring2),
 .clk_sring3(clk_sring3),
 .clk_sring4(clk_sring4),
 .clk_rring0(clk_rring0),
 .clk_rring1(clk_rring1),
 .rst_n(rst_n),
 .pkg_s(pkg_s),
 .die_ps(die_ps),
 .cmd_v(cmd_v),
 .cmd_mode(cmd_mode),
 .cmd_words(cmd_words),
 .cmd_tag(cmd_tag),
 .in_valid(in_valid),
 .in_data(in_data),
 .in_last(in_last),
 .in_mode(in_mode),
 .in_tag(in_tag),
 .up_valid(up_valid),
 .up_rec(up_rec),
 .dp_valid(dp_valid),
 .dp_rec(dp_rec),
 .ur_valid(ur_valid),
 .ur_rec(ur_rec),
 .dr_valid(dr_valid),
 .dr_rec(dr_rec),
 .sx0_valid(sx0_valid),
 .sx1_valid(sx1_valid),
 .sx2_valid(sx2_valid),
 .sx0_rec(sx0_rec),
 .sx1_rec(sx1_rec),
 .sx2_rec(sx2_rec),
 .sr0_valid(sr0_valid),
 .sr1_valid(sr1_valid),
 .sr2_valid(sr2_valid),
 .sr0_rec(sr0_rec),
 .sr1_rec(sr1_rec),
 .sr2_rec(sr2_rec),
 .out_valid(out_valid),
 .out_data(out_data),
 .out_last(out_last),
 .out_rank(out_rank),
 .out_err(out_err),
 .fault(fault),
 .fault_code(fault_code),
 .up_slot(up_slot),
 .ur_peer_slot(ur_peer_slot),
 .sx0_peer_slot(sx0_peer_slot),
 .sx1_peer_slot(sx1_peer_slot),
 .sx2_peer_slot(sx2_peer_slot),
 .cmd_free(cmd_free));
 wire[4:0]expected_tx,expected_rx;
 wire[1:0]shared_rv;wire[1161:0]shared_rd;
 wire mux_txv,mux_rxv,mux_fault;wire[1042:0]mux_tx,mux_rx;
 wire gb_core_fault,gb_fdi_fault;
 if(SIX_FIVE)begin:g_six_five
 wire[596:0]core_rx;
 qfd_ucie_six_five u_gearbox(.core_ck(gearbox_core_ck),.fdi_ck(fdi_ck),.fdi_rx_ck(fdi_rx_ck),.blk_tx_ck(blk_ck[0]),.blk_rx_ck(blk_ck[1]),.rst_n(rst_n),
 .tx_valid(mux_txv),.tx_frame(mux_tx[596:0]),.phy_tx_valid(shared_tx_valid),.phy_tx_frame(shared_tx),
 .phy_rx_valid(shared_rx_valid),.phy_rx_frame(shared_rx),.rx_valid(mux_rxv),.rx_frame(core_rx),
 .core_fault(gb_core_fault),.fdi_fault(gb_fdi_fault));
 assign mux_rx[596:0]=core_rx;   // RXW 597: the gearbox RX frame; mux_rx[1042:597] has no load (share RXW=597)
 end else begin:g_same_clock_diagnostic
 assign {shared_tx_valid,shared_tx}={mux_txv,mux_tx};
 assign {mux_rxv,mux_rx}={shared_rx_valid,shared_rx};
 assign gb_core_fault=0;assign gb_fdi_fault=0;
 end
 assign shared_fault=mux_fault|gb_core_fault|gb_fdi_fault;
 qfd_ucie_static_share #(.RXW(SIX_FIVE?597:1043)) u_shared(.clk(face_ck[6]),.rst_n(rst_n),
 .tx_slot(expected_tx[1:0]),.tx_valid(phy_tx_valid[1:0]),
 .p_frame(phy_tx[0+:597]),.r_frame(phy_tx[597+:565]),
 .rx_slot(expected_rx[1:0]),.phy_rx_valid(mux_rxv),.phy_rx(mux_rx[(SIX_FIVE?597:1043)-1:0]),
 .phy_tx_valid(mux_txv),.phy_tx(mux_tx),.rx_valid(shared_rv),.rx_frames(shared_rd),.fault(mux_fault));
 genvar f;
 generate for(f=0;f<5;f=f+1)begin:g_face
 localparam integer W=f==1?514:546;
 localparam integer PW=W+51;
 localparam integer R=f<2?RU:f==2?RS0:f==3?RS1:RS2;
 localparam integer PR=f<2?RU:f==2?RS2:f==3?RS1:RS0;
 wire[W-1:0]td,rd;wire tv,ts,ps,rv;
 wire[W-1:0]ftd,frd;wire ftv,fts,fps,frv;
 localparam integer BASE=f==0?0:f==1?2*RU:f==2?4*RU:f==3?4*RU+2*RS0:4*RU+2*RS0+2*RS1;
 if(f==0)begin
 assign td=up_rec;assign tv=up_valid;assign ts=up_slot;assign ps=up_slot;
 assign dp_valid=rv;assign dp_rec=rd;
 end else if(f==1)begin
 assign td=ur_rec;assign tv=ur_valid;assign ts=ur_valid;assign ps=ur_peer_slot;
 assign dr_valid=rv;assign dr_rec=rd;
 end else if(f==2)begin
 assign td=sx0_rec;assign tv=sx0_valid;assign ts=sx0_valid;assign ps=sx0_peer_slot;
 assign sr0_valid=rv;assign sr0_rec=rd;
 end else if(f==3)begin
 assign td=sx1_rec;assign tv=sx1_valid;assign ts=sx0_valid;assign ps=sx1_peer_slot;
 assign sr1_valid=rv;assign sr1_rec=rd;
 end else begin
 assign td=sx2_rec;assign tv=sx2_valid;assign ts=sx0_valid;assign ps=sx2_peer_slot;
 assign sr2_valid=rv;assign sr2_rec=rd;
 end
 if(R==0)begin:g_direct
 assign {ftd,ftv,fts,fps}={td,tv,ts,ps};assign {rd,rv}={frd,frv};
 end else begin:g_relay
 qfd_coll_static_relay #(.W(W+3),.N(R))u_txrelay(.ck(relay_ck[BASE+:R]),.rst_n(rst_n),.d({td,tv,ts,ps}),.q({ftd,ftv,fts,fps}));
 qfd_coll_static_relay #(.W(W+1),.N(R))u_rxrelay(.ck(relay_ck[BASE+R+:R]),.rst_n(rst_n),.d({frd,frv}),.q({rd,rv}));
 end
 wire[PW-1:0]pt;
 wire pv=(SHARED_UCIE && f<2)?shared_rv[f]:phy_rx_valid[f];
 wire[PW-1:0]pr;
 if(SHARED_UCIE && f<2)begin:g_shared_rx
 if(f==0)assign pr=shared_rd[0+:597];else assign pr=shared_rd[597+:565];
 end else assign pr=phy_rx[f*597+:PW];
 assign phy_tx[f*597+:PW]=pt;
 if(PW<597)assign phy_tx[f*597+PW+:(597-PW)]=0; // declared frame padding only
 qfd_coll_static_face #(.FW(W),.PHY(f<2?PU:PS+(f==2?LX0:f==3?LX1:LX2)),.L(f<2?LU:LS),.R(R),.PEER_R(PR),.TOK_REG(TOK_REG),.SAFE(SAFE),.PLAND(PLAND),.PLD(PLD),.PLK(PLK),.UP_SYNC(UP_SYNC))u_face(
 .cal_ck(face_ck[f*11]),.cal_lck(face_ck[f*11+1]),
 .tx_wck(face_ck[f*11+2]),.tx_rck(face_ck[f*11+3]),.rx_wck(face_ck[f*11+4]),.rx_rck(face_ck[f*11+5]),
 .codec_ck(face_ck[f*11+6+:5]),.codec_phy_ck(face_ck[f*11+6]),.rst_n(rst_n),.tx_slot(fts),.peer_slot(fps),.tx_valid(ftv),.tx_data(ftd),
 .rx_valid(frv),.rx_data(frd),.phy_up(phy_up[f]),.phy_rx_valid(pv),.phy_rx(pr),
 .phy_tx_valid(phy_tx_valid[f]),.phy_tx(pt),.phy_tx_slot(expected_tx[f]),.phy_rx_slot(expected_rx[f]),.cdc_fault(transport_cdc_fault[f*4+:4]),
 .epoch_abort(transport_abort[f]),.fault_cause(transport_fault_cause[f*8+:8]));
 end endgenerate
 // The fixed die-name collective LU/LS defines and this parent must agree.
 initial if(SIX_FIVE && (PU!=20 || !SHARED_UCIE))$error("six_five (r10 200MHz block stage) requires the actual 20-core-edge registered-pin PHY calendar and the single 1043 boundary");
 // Q-COLLCAL3 10-18: the die-name collective takes LU / LS from this parent (one calendar profile by construction;
 // was a compare against the OT_QFDS_* defines, which a GEN-compiled LS in die.v.params.json could not satisfy).
endmodule

// Source-visible paid relay stages. Every row advances unconditionally.
module qfd_coll_static_relay #(parameter integer W=549,N=1)(
 input wire[N-1:0]ck,input wire rst_n,input wire[W-1:0]d,output wire[W-1:0]q);
 wire[W-1:0]stage[0:N];assign stage[0]=d;assign q=stage[N];
 for(genvar k=0;k<N;k=k+1)begin:g_stage
 (* keep *)reg[W-1:0]r;
 always @(posedge ck[k] or negedge rst_n)if(!rst_n)r<=0;else r<=stage[k];
 assign stage[k+1]=r;
 end
endmodule
