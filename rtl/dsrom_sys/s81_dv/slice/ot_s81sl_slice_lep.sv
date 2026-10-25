`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------------
// RTL-BUILD-S81 (owner 0dv 2026-10-18): the END-SLICE link endpoint master (p4j end_slice_lep: s_0S / s_0N = W end,
// s_7S / s_7N = E end; residual row 1: lt_lk_{WS,WN,ES,EN}{0,1} 8 x 512 b had no producer).
//
// Function (SPEC 0b-p4i "end-slice link endpoints"; SPEC l.217 "the end slices' outward E/W ring port carries the PHY
// link lanes along the street"): the tier LINE simply continues across the die edge.  A line beat that reaches an end
// slice with hops > 1 is forwarded by the unchanged ring stop (ot_s81sl_rstop) out of the slice's OUTWARD port
// (W end: ro_w, E end: ro_e); here that port feeds two reliable UCIe link lanes instead of a neighbour.  The peer die's
// end slice presents the beat on its outward input (ri_w / ri_e), where its ring stop delivers it (hops 1) or forwards
// it inward (hops - 1) exactly like a neighbour's beat: cross-die all-gather rows (XQ / XB) join the mesh stream at the
// end slice, all-reduce partials ride to the owning slice, which keeps the fixed fold order ((p0+p1)+(p2+p3)).
// The compiler addresses an off-die destination by hop count (col + 1 + remote hops for a W-bound beat).
//
// Structure (cluster, wires only; every function in a hardened child with its own clock root):
//   ot_s81sl_slice            the vector slice cluster, UNCHANGED (HB = 0, C1)
//   ot_s81sl_lep              link-port leaf (this file): outward-port pin flops, per-lane TX landing FIFOs, RX pair
//                             re-assembly, lane-receive enables, the fault collector
//   dsfd_coll_lane_w / _e x2  the hardened collective link lane tile (ot_s81ph_link_ep reliable link layer: seq, CRC-32,
//                             go-back-N replay, credits + ot_s81ph_link_gbx 512-b beat format), unchanged
//   A 1,104-b ring beat = 2 link flits of 552 b (FLIT_BYTES 69): low half [551:0] on lane 0, high half [1103:552] on
//   lane 1; the flit's `last` bit carries the beat-sequence parity (checked at re-assembly).
// Flow control exists ONLY at this off-die boundary (owner 10-14: flow control kept at SerDes / d2d incl. cross-die
// collectives): the ring side is static (a valid beat on ro is pushed the same cycle; a full landing FIFO is a sticky
// fault: the compiler keeps the off-die rate <= the lane rate 456/596 * 1023/1024 = 0.764 beats/cycle with bursts
// <= DT / (1 - 0.764) = ~2,170 back-to-back beats at DT = 512), the lane side is the link layer's valid/ready + credits.
//
// Ports (lepw = W end; lepe = E end mirrors ri_e/ro_e <-> ri_w/ro_w):
//   tx0 / tx1 [511:0]   -> ot_pdie_ucie tx (lt_lk_<side><tier>{0,1})
//   rx0 / rx1 [513:0]   <- {ot_pdie_ucie st[1:0] = {live, fault}, rx[511:0]} (lr_lk_*; the plan lane is 512 b: + 2 st)
//   tf [1:0]            forwarded lane clocks (to the PHY macro side)
//   ch_b                static strap: 0 = UCIe lane timeout basis, 1 = board lane
//   t_host 77 / t_kd 54 <- dsdv_seq_host (host status / completion, key-store done): sent as THOST / TKD link frames
//   f_host 515 / f_lf 4 / f_ks 53 -> dsdv_seq_host: HOST / KS link frames from the peer (the host-side endpoint) and
//                       the lane block status {fault, live} x 2 (lane 1, lane 0) -- the HOST PLANE of the cross-die link
//                       (coordinator 10-18: seq_host's host lane is the end-slice link, not a separate PHY)
//   all other ports     = ot_s81sl_slice (inward line port, V rung, band port (mode-unused at HB 0), x chains, return
//                         lanes, forwarded clocks)
// The lane rx word {fault, live, beat, valid} of dsfd_coll_lane_*: valid = the lep's registered lane-receive enable
// (1 from the cycle after reset release): ot_pdie_ucie's rate matcher presents a beat EVERY cycle (an IDLE beat 512'b10
// when its FIFO is empty, skipped by the gearbox), and the gearbox qualifies beats with `live` itself.
// Pin rules (S81-RTLB3 2026-10-18; gate b6bf54dea WARNs: lo0_r / lo1_r drove 556 / 558 loads, 6 levels to wp; one
// reset flop drove 1,232 loads): the core-side lane faces are CREDIT links (rtl/common/ot_link_credit.sv protocol, the
// lane tile in LCR = 1 mode, as the S81 collective die lanes: run_die_layer.sh +define+OT_S81PH_LANE_CR).  lo_r is a
// credit pulse that lands in ONE pin flop (cr_q); a TX read is issued only with a credit in hand (CRED 8 = the lane's
// landing depth), lo_v / lo_d leave from flops.  li_v / li_d land in pin flops, li_r is a registered credit pulse per pop
// (RX landing DR 8 = the lane sender's CRED 8).  The rst_n port drives only an ot_rst_relay (4 regions: TX lane 0, TX
// lane 1, RX, host plane / faults); the 1,103 ri data bits carry no reset (ri[0] is the beat valid).
// Added edges vs the valid/ready skid face (compiler + die): ro -> lane endpoint +2 cycles (lane credit landing pin flop
// + FIFO), lane -> ri +1 cycle (lane credit sender flop); reset release +1 cycle (relay stage: 3 edges from rst_n).
// The credit round trips (TX ~7, RX ~6 cycles) stay inside 8 credits: full beat rate; the off-die rate cap (0.764) and
// the TX landing burst bound are unchanged.
// Mutants (bench only): OT_S81SL_LEP_MUT_SWAP (halves swapped onto the lanes), OT_S81SL_LEP_MUT_NOPAIR (re-assembly
// releases on lane 0 alone), OT_S81SL_LEP_MUT_NOOVF (landing-FIFO overflow not flagged), OT_S81SL_LEP_MUT_KSOFF
// (key-store payload decoded one bit off), OT_S81SL_LEP_MUT_HDROP (a pending t_v host word overwritten),
// OT_S81SL_LEP_MUT_NHACC (a HOST_EN = 0 endpoint accepts HOST / KS frames silently).
// HOST_EN (S81-LEPV 2026-10-18, owner "remove ties where cheap"): only s_7N carries the host plane.  HOST_EN = 0 removes
// the host plane from the leaf (no t_host / t_kd pin flops, no THOST / TKD pending registers, no f_host / f_ks / f_lf
// registers; a HOST / KS frame arriving there is a protocol fault like any unknown frame type).  The PORTS go with it in
// the parameter-free tops ot_s81sl_lep_nh (leaf) and ot_s81sl_slice_lepw / ot_s81sl_slice_lepe_nh (die masters), so the
// three host-less endpoints carry no tied die pads.  The core's host ports are unread at HOST_EN = 0 (generate), so
// synthesis of a _nh top keeps no host pin and no host logic.
// ---------------------------------------------------------------------------------------------------------------------
// MU-S81/LINK (2026-10-18, owner MU.DECIDE option A, HANDOFF 0is): multi-user stage hand-off, all opt-in (MU_EN = 0 and
// AB_EN = 0 build exactly the logic above; the leaf tops ot_s81sl_lep / ot_s81sl_lep_nh keep their ports and params).
//   (a) user tag.  The stage h message (h slices on the ring to the edge links, SPEC s81_dv_1016 "Stage hop") is XB
//       beats {59'd0, bf 1024, gidx 8, sid, hops, kind 2, v} (ot_s81sl_vq): bits [1103:1045] are spare in every XB / XQ
//       beat (0 die wires).  MU_EN = 1: the compiler opens a TX TAG WINDOW with one mu_c command {pos 21, user 10, land,
//       ab, v} at least 2 cycles before the first h beat reaches ro; the next NB outbound ring beats are that user's h
//       message share of this endpoint and are stamped (combinationally into the frame, NO added cycle) with
//       [1045] tag, [1046] land, [1056:1047] user, [1077:1057] pos.  A non-XB/XQ ring beat inside a window, or a second
//       window while one is open, is a sticky fault (the lep TX port is a calendar resource: the shift lemma gives each
//       window the port alone).  RX: a tagged beat is delivered with the tag bits cleared (ri bit-identical to the
//       single-user beat) and its tag on mu_rt {v, user 10, pos 21} in the same cycle as ri (-> seq_host: the receiving
//       stage selects that user's bases); a tagged beat with land = 1 goes to the landing leaf (ml_wv / ml_wd, the full
//       beat) instead of ri.  Replayed beats (ml_rv / ml_rd, from dsdv_mu_land) enter through pin flops and leave on ri
//       (tag stripped, tag on mu_rt); a replayed beat in the same cycle as a cut-through ring beat is a sticky fault.
//   (c) copy A / B.  AB_EN = 1 adds a second lane pair (lo2 / lo3, li2 / li3, rxvb, l2_f / l3_f) = a 2nd STATIC CIRCUIT
//       through the multi-plane switch (two more dsfd_coll_lane tiles, unchanged HF-3 contract): a window opened with
//       ab = 1 sends its NB beats on pair B; everything else (other ring beats, host frames) stays on pair A.  The latency
//       user (user 0) is always A in hardware (ab = 1 with user 0, or ab = 1 at AB_EN = 0, is a sticky fault and the beats
//       go to A).  RX of pair B is re-assembled like pair A and merged into ri (both pairs releasing in one cycle is a
//       sticky fault; pair B carries ring beats only).  Each pair has its own frame-sequence parity.
//   Why a 2nd circuit and not a destination field: the lane tile's reliable link layer (ot_s81ph_link_ep seq / CRC /
//   go-back-N replay / credits, FROZEN HF-3) is end-to-end per peer pair across the switch (tb_xdie_s81 ACK timeout set
//   by the 553-cycle crossing); alternating one lane's frames between two peers would mix two sequence spaces in one
//   endpoint, so a destination field needs a per-destination link layer inside the frozen tile.
// S81-FIX3 (10-19, route s81sl_lepnh-90fc20580 NEEDS_RTL TT -55.92: all 66 failing endpoints = lane-1 TX SRAM rd_out
// (macro clk->q 421 ps TT) -> WREG forward mux (AO21) -> ~265 ps of buffered wire -> the lo1_d output pin flop across
// the lane-0 SRAM column; not fanout, not depth): TXRP = 1 adds ONE read pipeline register (odr, no reset) that the
// placer keeps beside the SRAM column, so the macro read word crosses the tile in its own cycle (odr -> od pin flop).
// lo_v follows one edge later (inf -> inr -> ov).  TX: issue -> lo_v 3 edges (was 2); TX credit round trip ~8 cycles
// <= CRED 8 (full beat rate kept); the elastic off-die boundary absorbs the edge (no static-calendar change on-die).
// Applies to every lep variant (lep / lep_nh / lep_mu*), as they share this core.
// Mutants (bench only): OT_S81SL_LEP_MUT_TAGDROP (TX window does not stamp), OT_S81SL_LEP_MUT_WRONGCOPY (ab ignored: all
// beats on pair A), OT_S81SL_LEP_MUT_LANDCUT (RX ignores the land bit: landed beats cut through to ri; MU-S81b).
// MU-S81-2/RX (10-19, CTS gates: rpc -> 8:1 RX row mux -> tag / land decode -> 1,103-bit select fanout -> rid missed
// setup by 71 ps (copy-A master) / 575 ps (A/B master: + pair-B mux and ~300 um)): MU_EN 1 only -- a show-ahead head
// register per RX lane (head row from flops), a land bit pre-decoded per FIFO row, rid = one AO222 per bit with the
// selects duplicated per column group.  Same cycles and bits; MU_EN 0 logic untouched.  Mutant
// OT_S81SL_LEP_MUT_STALEHD (head register loads the old pointer's row: stale head after a pop / write).
// MU-S81-2/HOSTEP (10-19): parameter-free host-plane MU top ot_s81sl_lep_mu_h (s_7N); mutant OT_S81SL_LEP_MUT_HSTAMP
// (a THOST / TKD frame sent while a TX tag window is open gets the window's tag stamped).
module ot_s81sl_lep_core #(
    parameter integer DT = 512,        // TX landing FIFO depth per lane (flits; SRAM macro depth)
    parameter integer DR = 8,          // RX landing FIFO depth per lane (flits, flops) = the lane sender's CRED 8
    parameter integer CRED = 8,        // TX credits = the lane's core-face landing depth (ot_link_credit_rx DEPTH 8)
    parameter integer SRAM = 1,        // 1: TX storage in SRAM macros (0: flops, same cycle behaviour)
    parameter integer HOST_EN = 1,     // 1: host plane (THOST / TKD out, HOST / KS in, f_lf); 0: ring beats only
    parameter integer MU_EN = 0,       // 1: user-tag windows (TX stamp, RX strip / land / replay merge)
    parameter integer AB_EN = 0,       // 1: second lane pair (copy B static circuit)
    parameter integer NB = 80,         // ring beats per h message per endpoint (40,960 B / 4 end slices / 128 B)
    parameter integer RX_SRAM = 0,     // opt-in true SRAM RX, same show-ahead edge
    parameter integer TXRP = 1,        // 1: TX read pipeline register beside the SRAM column (S81-FIX3; +1 lo edge)
    parameter integer NATIVE32_STD = 0, // separate opt-in standard bounded SRAM/control path
    parameter integer NATIVE32 = 0,    // opt-in MU same-age bounded control replicas
    parameter integer IDX_EN = 0,      // 1 (S81/H4 10-24): index rank-tree frames tl -> link, link -> ca / cb (see g_itx)
    parameter integer IDX_TP = 0,      // S81/IDXNET 10-25 (IDX_EN 1): 0 stage-tree end (H4: lane 2 -> pair A, 3 -> B; RX B -> ca,
                                       // A -> cb); TP4 peer end (topk_final, every beat on pair A, lane 2): 1 TX + RX (s_7N),
                                       // 2 TX only (s_7S), 3 RX only (s_0S); a TP end hands every received beat to ca
    parameter integer IDX_MRG = 0,     // 1 (S81/IDXNET, s_0N): tm (the s_0S TP RX beats) merged into ca, collision = fault
    parameter integer IDX_Q = 0,       // 1 (S81/IDXNET, s_0N): rank-tree query frames: qc (iqf, 2-beat) -> link pair A, pair B
                                       // -> ql (iqf) + cut-through relay to pair A by the header relay count (see g_qrx)
    parameter integer IN_PIPE = 0      // 1 (LEPCAP 10-19): one registered face stage on ro / t_host / t_kd / mu_c (+1 edge on
                                       // each, same relative timing); ro[0] / t_kd[53] re-fanned by 6 KEPT copies <= 28 loads
) (
    input  wire            clk,
    input  wire            rst_n,
    // slice outward line port
    input  wire [1103:0]   ro,
    output wire [1103:0]   ri,
    // link lanes (dsfd_coll_lane_* core side: lo = to link, li = from link)
    output wire            lo0_v, input wire lo0_r, output wire [552:0] lo0_d,
    output wire            lo1_v, input wire lo1_r, output wire [552:0] lo1_d,
    input  wire            li0_v, output wire li0_r, input wire [552:0] li0_d,
    input  wire            li1_v, output wire li1_r, input wire [552:0] li1_d,
    output wire [1:0]      rxv,        // lane receive enables (the lane rx word's valid bit)
    // fault collector: slice fault, lane faults {meso, gearbox, endpoint}
    input  wire            sl_f,
    input  wire [2:0]      l0_f,
    input  wire [2:0]      l1_f,
    input  wire [1:0]      l0_st,      // ot_pdie_ucie st {live, fault} of lane 0 / lane 1
    input  wire [1:0]      l1_st,
    // host plane (dsdv_seq_host host lane + key store), carried as non-ring link frames
    input  wire [76:0]     t_host,     // seq_host t_host {alive, st 11, t_v, t_d 64}  -> THOST frames
    input  wire [53:0]     t_kd,       // seq_host t_kd {done, tok 21, 32'b0}          -> TKD frames
    output wire [514:0]    f_host,     // -> seq_host f_host {h_cls 2, h_d 512, h_v}   <- HOST frames
    output wire [3:0]      f_lf,       // -> seq_host f_lf {fault, live} x 2 (lane 1, lane 0)
    output wire [52:0]     f_ks,       // -> seq_host f_ks {start, user 10, tok 21, pos 21} <- KS frames
    // MU (MU_EN 1): TX tag window command, RX tag, landing leaf ports
    input  wire [33:0]     mu_c,       // {pos 21, user 10, land, ab, v}
    output wire [31:0]     mu_rt,      // {v, user 10, pos 21} of the beat on ri this cycle
    output wire            ml_wv,      // -> dsdv_mu_land: a land = 1 tagged beat (full beat, tag kept)
    output wire [1103:0]   ml_wd,
    input  wire            ml_rv,      // <- dsdv_mu_land: replayed beat
    input  wire [1103:0]   ml_rd,
    input  wire            ml_f,       // <- dsdv_mu_land fault (collected here)
    // copy-B lane pair (AB_EN 1)
    output wire            lo2_v, input wire lo2_r, output wire [552:0] lo2_d,
    output wire            lo3_v, input wire lo3_r, output wire [552:0] lo3_d,
    input  wire            li2_v, output wire li2_r, input wire [552:0] li2_d,
    input  wire            li3_v, output wire li3_r, input wire [552:0] li3_d,
    output wire [1:0]      rxvb,
    input  wire [2:0]      l2_f,
    input  wire [2:0]      l3_f,
    output reg             fault,
    // S81/H4 (IDX_EN 1): index rank-tree beats (276-b V beats of dsdv_bk_sel_vmtx): tl <- its tree transmitter tl_o,
    // ca / cb -> its landed child lanes (unread / 0 at IDX_EN 0)
    input  wire [275:0]    tl,
    output wire [275:0]    ca,
    output wire [275:0]    cb,
    // S81/IDXNET (IDX_MRG / IDX_Q; unread / 0 otherwise): tm <- the s_0S TP RX lane; qc <- iqf 2-beat Q lane
    // {data 256, beat, v} (beat 0 = word[256:1], beat 1 = word[512:257] the next cycle); ql -> iqf (513-b Q word {d, v})
    input  wire [275:0]    tm,
    input  wire [257:0]    qc,
    output wire [512:0]    ql
);
    localparam integer H = 552;
    localparam integer SAFE_STD=(NATIVE32_STD!=0 && MU_EN==0);
    localparam integer SAFE_FIFO=(MU_EN!=0 || SAFE_STD) && RX_SRAM!=0;
    localparam integer SAFE_CONTROL=((NATIVE32!=0 && MU_EN!=0) || SAFE_STD) && RX_SRAM!=0;
    localparam integer AT = $clog2(DT), AR = $clog2(DR);
    localparam integer NL = (AB_EN != 0) ? 4 : 2;      // lanes (2 per pair)
    localparam integer NBW = $clog2(NB + 1);
    localparam [2:0] K_XQ = 3'd1, K_XB = 3'd2;
    localparam integer TG = 1045;                      // tag field base: [TG] tag, [TG+1] land, user, pos
    // regional reset: the port drives only this relay (own synchroniser on this leaf's clock root); one copy per region
    localparam integer RX_NS=(H+8)/8;
    localparam integer NRX_MEMRST=(SAFE_FIFO)?NL*RX_NS:0;
    localparam integer NRX_OUTRST=(SAFE_FIFO)?((1103+15)/16):0;
    localparam integer TX_NS=(H+8)/8;
    localparam integer FRAME_NS=(2*H+7)/8;
    localparam integer TX_NA=(TX_NS+3)/4;
    localparam integer PUSH_GROUPS=TX_NA;
    localparam integer TX_RST_STRIDE=TX_NS+2*TX_NA;
    localparam integer NTX_MEMRST=(SAFE_FIFO)?NL*TX_RST_STRIDE:0;
    localparam integer NFRAME_RST=(SAFE_FIFO)?FRAME_NS:0;
    localparam integer NHOST_RST=(SAFE_FIFO && HOST_EN!=0 )?37:0;
    localparam integer TX_RSTBASE=4+NRX_MEMRST+NRX_OUTRST;
    localparam integer FRAME_RSTBASE=TX_RSTBASE+NTX_MEMRST;
    localparam integer HOST_RSTBASE=FRAME_RSTBASE+NFRAME_RST;
    localparam integer CTRL_RSTBASE=HOST_RSTBASE+NHOST_RST;
    localparam integer NCTRL_RST=(SAFE_FIFO)?NL+8+PUSH_GROUPS+NL+((HOST_EN!=0)?17:0):0;
    localparam integer PAYLOAD_RSTBASE=CTRL_RSTBASE+NL+8+PUSH_GROUPS+NL;
    localparam integer NRX_RST_OLD=NRX_MEMRST+NRX_OUTRST+NTX_MEMRST+NFRAME_RST+NHOST_RST+NCTRL_RST;
    localparam integer NATIVE32_RSTBASE=4+NRX_RST_OLD;
    localparam integer NATIVE32_RXRSTBASE=NATIVE32_RSTBASE+((SAFE_CONTROL && HOST_EN!=0)?4:0);
    localparam integer NRX_RST=NRX_RST_OLD+((SAFE_CONTROL)?NL+((HOST_EN!=0)?4:0):0);
    // L5B-LEPMU 10-21: AB_EN 1 + SAFE_FIFO adds two leaves (lanes 2 / 3 TX state) so rr[0] / rr[1] stop driving 40 / 38
    // reset pins (native census); same release edge as every leaf.
    localparam integer NXR=(SAFE_FIFO && NL==4)?2:0;
    wire [3+NRX_RST+NXR:0] rr;
    generate if(SAFE_FIFO) begin:g_reset_balanced
      ot_rst_relay_tree3 #(.REGIONS(4+NRX_RST+NXR)) u_rstr(.clk(clk),.rst_n_in(rst_n),.rst_n(rr));
    end else begin:g_reset_legacy
      ot_rst_relay #(.REGIONS(4+NRX_RST), .SYNC_STAGES(2), .TREE_STAGES(1)) u_rstr (.clk(clk), .rst_n_in(rst_n), .rst_n(rr));
    end endgenerate
    wire rn = rr[3];                                   // host plane, outward-port valid, fault collector
    wire rnx = rr[2];                                  // RX landing + re-assembly
    // ---------------------------------------------------------------- input face stage (IN_PIPE)
    // ro_x / th_x / tk_x / mc_x are the core's view of ro / t_host / t_kd / mu_c.  rvx[k] / kvx[k] are the copies of the
    // ring-valid ro[0] and the key-done t_kd[53] that feed the per-slice / push / lane landing registers (<= 28 loads each).
    // IN_PIPE 1: every one is a register at the face (reset-free: the drivers are reset parent pin flops), so all four ports
    // move by exactly +1 edge together and the ro[0] / t_kd[53] input nets drive 7 flops instead of 160 / 139.
    localparam integer NVC = 6;
`ifdef OT_S81SL_LEP_MUT_VSKEW
    localparam integer VSKEW = 1;
`else
    localparam integer VSKEW = 0;
`endif
    wire [1103:0] ro_x; wire [76:0] th_x; wire [53:0] tk_x; wire [33:0] mc_x; wire [NVC-1:0] rvx, kvx;
    generate if (IN_PIPE != 0) begin : g_inpipe
      reg [1103:0] rop; reg [76:0] thp; reg [53:0] tkp; reg [33:0] mcp;
      always @(posedge clk) begin rop <= ro; thp <= t_host; tkp <= t_kd; mcp <= mu_c; end
      assign ro_x = rop; assign th_x = thp; assign tk_x = tkp; assign mc_x = mcp;
      for (genvar vc = 0; vc < NVC; vc = vc + 1) begin : g_vc
        if (VSKEW != 0 && vc == NVC - 1) begin : g_skew assign rvx[vc] = ro[0]; end   // MUTANT: one copy group skips the stage
        else begin : g_rv (* keep=1 *) ot_s81sl_lep_vcopy u_rv (.clk(clk), .d(ro[0]), .q(rvx[vc])); end
        if (HOST_EN != 0) begin : g_kv (* keep=1 *) ot_s81sl_lep_vcopy u_kv (.clk(clk), .d(t_kd[53]), .q(kvx[vc])); end
        else begin : g_nkv assign kvx[vc] = 1'b0; end                  // HOST_EN 0: t_kd unread
      end
    end else begin : g_noinpipe
      assign ro_x = ro; assign th_x = t_host; assign tk_x = t_kd; assign mc_x = mu_c;
      assign rvx = {NVC{ro[0]}}; assign kvx = {NVC{t_kd[53]}};
    end endgenerate
    // S81/H4: the tree beat takes a pin flop + the face stage (IN_PIPE), one edge more than ro (a pin here, not a landing); tvx[k] / ibx[k]
    // = kept copies of its valid / pair-B select for the frame slices, push groups and lane landings (as rvx).
    // S81/IDXNET 10-25: ivx = tvx | qvx | rvy (tree beat, root Q word, relayed Q word: at most one a cycle, else a fault);
    // tsx = data-select copies of the tree valid for the 32-b slices of the frame payload register iq (S2).
    localparam integer ITX = (IDX_EN != 0 && IDX_TP != 3);   // this end sends tree / TP beats
    localparam integer IRX = (IDX_EN != 0 && IDX_TP != 2);   // this end receives them
    localparam integer QEN = (IDX_EN != 0 && IDX_Q != 0);    // rank-tree query frames (s_0N)
    wire [275:0] tl_x; wire [NVC-1:0] tvx, ibx, qvx, rvy, ivx; wire [8:0] tsx; wire [16:0] qsx, rsx;
    wire [512:0] qw, rw; wire qterr, qrerr;
    assign ivx = tvx | qvx | rvy;
    generate if (ITX == 0) begin : g_nitl
      assign tl_x = 276'd0; assign tvx = '0; assign ibx = '0; assign tsx = '0;
    end else if (IN_PIPE != 0) begin : g_itlp
      // tl is a partition pin of the LP slice: ONE pin flop per bit (tlp, the face register face_guard checks: an input
      // bit loads exactly one flop D), then the face stage (tlq + the kept valid / select copies, all from tlp).
      reg [275:0] tlp, tlq;
      always @(posedge clk) begin tlp <= tl; tlq <= tlp; end
      assign tl_x = tlq;
      for (genvar vc = 0; vc < NVC; vc = vc + 1) begin : g_vc
        (* keep=1 *) ot_s81sl_lep_vcopy u_iv (.clk(clk), .d(tlp[0]), .q(tvx[vc]));
`ifdef OT_S81SL_LEP_MUT_IDXPAIR
        (* keep=1 *) ot_s81sl_lep_vcopy u_ib (.clk(clk), .d(IDX_TP == 0 && tlp[0] && tlp[5:4] == 2'd2), .q(ibx[vc]));  // MUTANT: lane 2 -> pair B
`else
        (* keep=1 *) ot_s81sl_lep_vcopy u_ib (.clk(clk), .d(IDX_TP == 0 && tlp[0] && tlp[5:4] == 2'd3), .q(ibx[vc]));
`endif
      end
      for (genvar sj = 0; sj < 9; sj = sj + 1) begin : g_ts
        (* keep=1 *) ot_s81sl_lep_vcopy u_ts (.clk(clk), .d(tlp[0]), .q(tsx[sj]));
      end
    end else begin : g_itl
      assign tl_x = tl; assign tvx = {NVC{tl[0]}}; assign ibx = {NVC{IDX_TP == 0 && tl[0] && tl[5:4] == 2'd3}};
      assign tsx = {9{tl[0]}};
    end endgenerate
    // S81/IDXNET: root Q word from iqf (2-beat lane qc): pin flop qcp (S0 = the beat-1 cycle), beat 0 held one cycle in qlo
    // (no enable: beat 1 always follows beat 0 in the next cycle), the full word in qw (S1).  Beat 1 without beat 0, or two
    // beat 0 in a row (the root's frame must arrive at <= 1 word / 2 cycles), is a sticky fault.
    generate if (QEN != 0) begin : g_qtx
      reg [257:0] qcp; reg [255:0] qlo; reg [512:0] qw_r; reg qlo_v, qte;
`ifdef OT_S81SL_LEP_MUT_QBEAT
      always @(posedge clk) begin qcp <= qc; qlo <= qcp[257:2]; qw_r <= {qlo, qcp[257:2], 1'b1}; end   // MUTANT: halves swapped
`else
      always @(posedge clk) begin qcp <= qc; qlo <= qcp[257:2]; qw_r <= {qcp[257:2], qlo, 1'b1}; end
`endif
      wire b0 = qcp[0] && !qcp[1], b1 = qcp[0] && qcp[1];
      always @(posedge clk or negedge rn)
        if (!rn) begin qlo_v <= 1'b0; qte <= 1'b0; end
        else begin qlo_v <= b0; if ((b1 && !qlo_v) || (b0 && qlo_v)) qte <= 1'b1; end
      for (genvar vc = 0; vc < NVC; vc = vc + 1) begin : g_vc
        (* keep=1 *) ot_s81sl_lep_vcopy u_qv (.clk(clk), .d(b1 && qlo_v), .q(qvx[vc]));
      end
      for (genvar sj = 0; sj < 17; sj = sj + 1) begin : g_qs
        (* keep=1 *) ot_s81sl_lep_vcopy u_qs (.clk(clk), .d(b1 && qlo_v), .q(qsx[sj]));
      end
      assign qw = qw_r; assign qterr = qte;
    end else begin : g_nqtx
      assign qw = 513'd0; assign qvx = '0; assign qsx = '0; assign qterr = 1'b0;
    end endgenerate
    reg [NL-1:0] rxv_r;
    always @(posedge clk or negedge rnx) if (!rnx) rxv_r <= {NL{1'b0}}; else rxv_r <= {NL{1'b1}};
    assign rxv = rxv_r[1:0];

    // ---------------------------------------------------------------- outward-port pin flops
    reg rov; reg [1103:0] roq;
    always @(posedge clk or negedge rn) if (!rn) rov <= 1'b0; else rov <= rvx[0];
    always @(posedge clk) roq <= ro_x;
    // ---------------------------------------------------------------- IDX tree frames, TX (IDX_EN 1; S81/H4 10-24)
    // COORD H4 ruling (option A): the bk_sel tree lanes end here.  A valid tree beat (tl[0]) is sent as ONE non-ring link
    // frame, like a THOST frame: low half {.., beat 276 at [4 +: 276], type 3'd5 at [3:1], 1'b0}, the rest 0.  Pair = the
    // beat's lane field (the PARENT's child slot, lower_bk CHILD_LANES = (2, 3)): lane 2 -> pair A (stage NEXT), lane 3 ->
    // pair B (stage PREV); the receiving end hands pair-B frames to ca and pair-A frames to cb, so lane 2 <-> ca and
    // lane 3 <-> cb hold on both ends.  Static slot rule (no arbitration, no wait): the compiler gives a tree beat a cycle
    // with no ring beat at this port; a tree beat on a ring-beat cycle is dropped (the ring beat goes) and a lane field
    // other than 2 / 3 (3 without pair B) is a sticky fault.  Host frames (HOST_EN 1) wait behind a tree frame.
    // S81/IDXNET 10-25: the same frame stage also sends Q frames (type 6, payload = the 513-b word at [4 +: 513], always pair A):
    // the root's own word (qw) and the relayed words of a frame received from PREV (rw).  TP ends (IDX_TP 1 / 2) send every
    // tree beat on pair A and require lane 2.  Two sources in one cycle is a sticky fault (static schedule).
    wire iv, ib, ie, ixt; wire [512:0] iq;
    wire igo = iv && !rov;                             // this cycle's frame is the tree / Q frame
    generate if (IDX_EN != 0) begin : g_itx
      reg iv_r, ib_r, ie_r, tv_r, xt_r; reg [512:0] iq_r;
      wire tv1 = tvx[0], qv1 = qvx[0], rv1 = rvy[0];
      wire [512:0] tlw = {237'd0, tl_x};
      always @(posedge clk or negedge rn)
        if (!rn) begin iv_r <= 1'b0; ib_r <= 1'b0; ie_r <= 1'b0; tv_r <= 1'b0; xt_r <= 1'b0; end
        else begin
          iv_r <= ivx[0]; ib_r <= ibx[0]; tv_r <= tv1; xt_r <= qv1 || rv1;
          if ((tv1 && qv1) || (tv1 && rv1) || (qv1 && rv1)) ie_r <= 1'b1;   // two frame sources in one slot
          if (iv_r && rov) ie_r <= 1'b1;               // a tree / Q frame on a ring-beat cycle (compile error)
          if (tv_r && IDX_TP == 0 && !(iq_r[5:4] == 2'd2 || (iq_r[5:4] == 2'd3 && NL == 4))) ie_r <= 1'b1;
          if (tv_r && IDX_TP != 0 && iq_r[5:4] != 2'd2) ie_r <= 1'b1;      // TP beats carry lane 2
          if (qterr || qrerr) ie_r <= 1'b1;
        end
      for (genvar sj = 0; sj < 17; sj = sj + 1) begin : g_xs   // data: no reset; 32-b slices, each under its own copies
        localparam integer LO = 32 * sj, W = (513 - LO < 32) ? 513 - LO : 32;
        wire ts = (sj < 9) && tsx[(sj < 9) ? sj : 0];
        always @(posedge clk) iq_r[LO +: W] <= (tlw[LO +: W] & {W{ts}}) | (qw[LO +: W] & {W{qsx[sj]}}) | (rw[LO +: W] & {W{rsx[sj]}});
      end
      assign iv = iv_r; assign ib = ib_r; assign ie = ie_r; assign iq = iq_r; assign ixt = xt_r;
    end else begin : g_nitx
      assign iv = 1'b0; assign ib = 1'b0; assign ie = 1'b0; assign iq = 513'd0; assign ixt = 1'b0;
    end endgenerate
    // ---------------------------------------------------------------- host plane, TX: THOST / TKD frames
    // Link frame = one flit pair.  Ring beat: bit 0 = 1 (the beat itself).  Host-plane frame: bit 0 = 0, [3:1] type
    // (1 HOST, 2 KS: inbound; 3 THOST, 4 TKD: outbound), payload at [4 +: n] in the low half, the rest 0.
    // THOST is sent on t_v or on a change of {alive, st}; TKD on done.  A frame waits in its pending register while ring
    // beats (which never wait) take the lanes; a status-only change merges into a pending t_v frame; a second t_v / done
    // event while one is still pending is a sticky fault (the compiler's host slots respect the lane rate).
    wire h_event,k_event;
    wire [11:0] h_status_now,h_status_old; wire h_status_valid;
    wire [47:0] host_now_regions,host_old_regions; wire [3:0] host_valid_regions;
    wire hp_go, kp_go, herr; wire [76:0] ph_d; wire [53:0] pk_d;
    generate if (HOST_EN != 0) begin : g_htx
    reg [76:0] thq; reg [53:0] tkq;
    always @(posedge clk) begin thq <= th_x; tkq <= tk_x; end
    reg ph_v, pk_v, he; reg [76:0] pd; reg [53:0] kd; wire [11:0] st_l;
    wire ev_h = (SAFE_CONTROL)?(host_valid_regions[0] || host_now_regions[11:0]!=host_old_regions[11:0]):(thq[64] || thq[76:65] != st_l), ev_k = tkq[53];
    wire status_reset=(SAFE_FIFO)?rr[CTRL_RSTBASE+NL+2]:rn;
    if(SAFE_CONTROL) begin:g_native_status
      for(genvar hs=0;hs<4;hs=hs+1) begin:g_region
        (* keep=1 *) ot_s81sl_lep_status_region u_status(.clk(clk),.rn(rr[NATIVE32_RSTBASE+hs]),
          .sample({th_x[76:65],th_x[64]}),.now_status(host_now_regions[12*hs+:12]),
          .old_status(host_old_regions[12*hs+:12]),.valid(host_valid_regions[hs]));
      end
      assign st_l=host_old_regions[11:0];
    end else begin:g_legacy_status
      reg [11:0] history;
      always @(posedge clk or negedge status_reset)
        if(!status_reset) history<=0; else if(ev_h) history<=thq[76:65];
      assign st_l=history;
      assign host_now_regions={4{thq[76:65]}};assign host_old_regions={4{history}};
      assign host_valid_regions={4{thq[64]}};
    end
    assign h_event=ev_h;assign k_event=ev_k;
    assign h_status_now=host_now_regions[11:0];assign h_status_old=st_l;assign h_status_valid=host_valid_regions[0];
    assign hp_go = !rov && !iv && ph_v; assign kp_go = !rov && !iv && !ph_v && pk_v;   // S81/H4: wait behind a tree frame
    assign herr = he; assign ph_d = pd; assign pk_d = kd;
    always @(posedge clk or negedge rn)
        if (!rn) begin ph_v <= 1'b0; pk_v <= 1'b0; he <= 1'b0; end
        else begin
            if (hp_go) ph_v <= 1'b0;
            if (kp_go) pk_v <= 1'b0;
            if (ev_h) begin
                ph_v <= 1'b1;
`ifdef OT_S81SL_LEP_MUT_HDROP
                if(MU_EN==0 || RX_SRAM==0) pd <= thq;                  // MUTANT: a pending t_v word is overwritten
`else
                if(MU_EN==0 || RX_SRAM==0) pd <= (ph_v && !hp_go && pd[64] && !thq[64]) ? {thq[76:65], pd[64:0]} : thq;
                if (ph_v && !hp_go && pd[64] && thq[64]) he <= 1'b1;
`endif
            end
            if (ev_k) begin pk_v <= 1'b1; if(MU_EN==0 || RX_SRAM==0) kd <= tkq; if (pk_v && !kp_go) he <= 1'b1; end
        end
    if(SAFE_FIFO) begin:g_payload_regions
      wire [79:0] old_host={3'd0,pd},new_host={3'd0,thq},next_host;
      wire [55:0] old_key={2'd0,kd},new_key={2'd0,tkq},next_key;
      for(genvar hh=0;hh<10;hh=hh+1) begin:g_host
        localparam [7:0] KM=(hh<8)?8'hff:((hh==8)?8'h01:8'h00);
        (* keep=1 *) ot_s81sl_lep_host_hold8 u_hold(.now_status(host_now_regions[(hh%4)*12+:12]),.old_status(host_old_regions[(hh%4)*12+:12]),.valid(host_valid_regions[hh%4]),
          .rn(rr[PAYLOAD_RSTBASE+hh]),.pending(ph_v),.send_now(hp_go),.old_valid(pd[64]),.keep_mask(KM),
          .old_data(old_host[8*hh+:8]),.new_data(new_host[8*hh+:8]),.next_data(next_host[8*hh+:8]));
      end
      for(genvar kh=0;kh<7;kh=kh+1) begin:g_key
        (* keep=1 *) ot_s81sl_lep_key_hold8 u_hold(.rn(rr[PAYLOAD_RSTBASE+10+kh]),.valid(tkq[53]),
          .old_data(old_key[8*kh+:8]),.new_data(new_key[8*kh+:8]),.next_data(next_key[8*kh+:8]));
      end
      always @(posedge clk) begin pd<=next_host[76:0];kd<=next_key[53:0];end
    end
    end else begin : g_nhtx                            // HOST_EN 0: ring beats only (t_host / t_kd unread)
    assign h_event=1'b0;assign k_event=1'b0;
    assign h_status_now=0;assign h_status_old=0;assign h_status_valid=0;
    assign host_now_regions=0;assign host_old_regions=0;assign host_valid_regions=0;
    assign hp_go = 1'b0; assign kp_go = 1'b0; assign herr = 1'b0; assign ph_d = 77'd0; assign pk_d = 54'd0;
    end endgenerate
    wire push = rov || hp_go || kp_go || igo;
    // ---------------------------------------------------------------- MU TX tag window (MU_EN 1)
    wire [31:0] window_count;
    wire wopen, wab; wire [32:0] wtag; wire terr;       // window open, pair B, {pos, user, land, 1}
    generate if (MU_EN != 0) begin : g_mtx
    reg [33:0] mcq; reg [NBW-1:0] wn; reg w_ab, te; reg [32:0] w_t;
    for(genvar mb=0;mb<34;mb=mb+1) begin:g_command_reset
        wire command_reset=(RX_SRAM!=0)?rr[CTRL_RSTBASE+NL+mb/24]:rn;
        always @(posedge clk or negedge command_reset) if(!command_reset) mcq[mb]<=0; else mcq[mb]<=mc_x[mb];
    end
    wire tag_state_reset=(RX_SRAM!=0)?rr[CTRL_RSTBASE+NL+7]:rn;
    wire mcv = mcq[0];
    wire [9:0] mcu = mcq[12:3];
    wire ab_ok = (AB_EN != 0) && mcu != 10'd0;           // the latency user (0) is always on copy A
    always @(posedge clk or negedge tag_state_reset)
        if (!tag_state_reset) begin wn <= '0; w_ab <= 1'b0; te <= 1'b0; end
        else begin
            if (mcv) begin
                if (wn != '0 && !(rov && wn == NBW'(1))) te <= 1'b1;     // a window while one is open
                wn <= NBW'(NB); w_ab <= mcq[1] && ab_ok; if(NATIVE32==0 || RX_SRAM==0) w_t <= {mcq[33:13], mcq[12:3], mcq[2], 1'b1};
                if (mcq[1] && !ab_ok) te <= 1'b1;                        // ab with user 0 / without pair B
            end else if (rov && wn != '0) wn <= wn - 1'b1;
            if (rov && wn != '0 && roq[3:1] != K_XB && roq[3:1] != K_XQ) te <= 1'b1;   // non-h beat inside a window
        end
    if(NATIVE32!=0 && RX_SRAM!=0) begin:g_tag_payload_regions
      wire [32:0] tag_in={mcq[33:13],mcq[12:3],mcq[2],1'b1};
      for(genvar wt=0;wt<4;wt=wt+1) begin:g_group
        localparam integer LO=wt*9,W=(33-LO<9)?33-LO:9;
        wire load_tag;
        (* keep=1 *) ot_s81sl_lep_host_enable u_load(.ne0(tag_state_reset),.ne1(mcv),.hit(1'b1),.en(load_tag));
        always @(posedge clk) if(load_tag) w_t[LO+:W]<=tag_in[LO+:W];
      end
    end
    assign window_count=32'(wn);
    assign wopen = wn != '0; assign wtag = w_t; assign terr = te;
`ifdef OT_S81SL_LEP_MUT_WRONGCOPY
    assign wab = 1'b0;                                 // MUTANT: copy select ignored
`else
    assign wab = w_ab;
`endif
    end else begin : g_nmtx
    assign window_count=0;
    assign wopen = 1'b0; assign wab = 1'b0; assign wtag = 33'd0; assign terr = 1'b0;
    end endgenerate
    wire stamp = rov && wopen;
    wire bsel = stamp && wab;                          // this frame goes to pair B
    reg [2*H-1:0] fr;
    wire [FRAME_NS-1:0] frame_host_pending,frame_key_pending;
    genvar fc,fb;
    generate if(SAFE_FIFO) begin:g_frame_local
      localparam integer HG=(FRAME_NS+7)/8;
      wire [HG-1:0] host_event;
      for(genvar hg=0;hg<HG;hg=hg+1) begin:g_host_event
        (* keep=1 *) ot_s81sl_lep_host_event u_event(.now_status(host_now_regions[(hg%4)*12+:12]),.old_status(host_old_regions[(hg%4)*12+:12]),.valid(host_valid_regions[hg%4]),.event_o(host_event[hg]));
      end
      for(fc=0;fc<FRAME_NS;fc=fc+1) begin:g_slice
        (* keep="true" *) reg rov_r,ph_r,pk_r,kevent_r;
        assign frame_host_pending[fc]=ph_r;assign frame_key_pending[fc]=pk_r;
        wire iv_s;                                       // S81/H4: this slice's copy of the tree-frame valid
        if (IDX_EN != 0) begin : g_iv
          (* keep="true" *) reg iv_r;
          always @(posedge clk or negedge rr[FRAME_RSTBASE+fc]) if (!rr[FRAME_RSTBASE+fc]) iv_r <= 1'b0; else iv_r <= ivx[fc/23];
          assign iv_s = iv_r;
        end else begin : g_niv assign iv_s = 1'b0; end
        wire hp=!rov_r && !iv_s && ph_r, kp=!rov_r && !iv_s && !ph_r && pk_r, ip=!rov_r && iv_s;
        wire stamp_local;
        if(8*fc<TG+33 && 8*(fc+1)>TG) begin:g_stamp_active
`ifdef OT_S81SL_LEP_MUT_HSTAMP
        (* keep=1 *) ot_s81sl_lep_stamp u_stamp(.count(window_count),.ring(1'b1),.stamp(stamp_local));
`else
        (* keep=1 *) ot_s81sl_lep_stamp u_stamp(.count(window_count),.ring(rov_r),.stamp(stamp_local));
`endif
        end else begin:g_stamp_unused assign stamp_local=1'b0;end
        always @(posedge clk or negedge rr[FRAME_RSTBASE+fc])
          if(!rr[FRAME_RSTBASE+fc]) begin rov_r<=0;ph_r<=0;pk_r<=0;kevent_r<=0;end
          else begin
            rov_r<=rvx[fc/23];kevent_r<=kvx[fc/23];
            if(HOST_EN!=0) begin
              if(hp) ph_r<=0;if(host_event[fc/8]) ph_r<=1;
              if(kp) pk_r<=0;if(kevent_r) pk_r<=1;
            end
          end
        for(fb=8*fc;fb<8*(fc+1) && fb<2*H;fb=fb+1) begin:g_bit
          wire hd,kd;
          if(fb>=4 && fb<81) begin:g_host_payload assign hd=ph_d[fb-4]; end
          else if(fb>=1 && fb<=3) begin:g_host_kind assign hd=1'(3'd3>>(fb-1)); end
          else begin:g_host_zero assign hd=1'b0; end
          if(fb>=4 && fb<58) begin:g_key_payload assign kd=pk_d[fb-4]; end
          else if(fb>=1 && fb<=3) begin:g_key_kind assign kd=1'(3'd4>>(fb-1)); end
          else begin:g_key_zero assign kd=1'b0; end
          wire id;                                       // S81/H4 tree frame bit: type 5 at [3:1], beat at [4 +: 276]
          // S81/IDXNET: Q frame = type 6 (ixt), word at [4 +: 513]: type bits [3:1] = {1, ixt, !ixt}
          if(fb>=4 && fb<517) begin:g_idx_payload assign id=iq[fb-4]; end
          else if(fb==1) begin:g_idx_k0 assign id=!ixt; end
          else if(fb==2) begin:g_idx_k1 assign id=ixt; end
          else if(fb==3) begin:g_idx_k2 assign id=1'b1; end
          else begin:g_idx_zero assign id=1'b0; end
          wire base=rov_r?roq[fb]:(ip?id:(hp?hd:(kp?kd:1'b0)));
          if(fb>=TG && fb<TG+33) begin:g_tag
`ifdef OT_S81SL_LEP_MUT_HSTAMP
            assign fr[fb]=stamp_local?wtag[fb-TG]:base;
`elsif OT_S81SL_LEP_MUT_TAGDROP
            assign fr[fb]=base;
`else
            assign fr[fb]=stamp_local?wtag[fb-TG]:base;
`endif
          end else begin:g_plain assign fr[fb]=base; end
        end
      end
    end else begin:g_frame_legacy
    always @(*) begin
        fr = {2*H{1'b0}};
        if (rov) begin
            fr = roq;
`ifndef OT_S81SL_LEP_MUT_TAGDROP
            if (stamp) fr[TG +: 33] = wtag;
`endif
        end
        else if (igo) begin fr[3:1] = ixt ? 3'd6 : 3'd5; fr[4 +: 513] = iq; end   // S81/H4 tree frame (S81/IDXNET: or Q frame)
        else if (hp_go) begin fr[3:1] = 3'd3; fr[4 +: 77] = ph_d; end
        else if (kp_go) begin fr[3:1] = 3'd4; fr[4 +: 54] = pk_d; end
`ifdef OT_S81SL_LEP_MUT_HSTAMP
        if (!rov && wopen) fr[TG +: 33] = wtag;        // MUTANT: host-plane frames inside a TX window are stamped
`endif
    end
    end endgenerate
    wire [1:0] pp = {(push && bsel) || (igo && ib), push && !bsel && !(igo && ib)};     // push per pair (S81/H4: tree frame by ib)
    wire [2*PUSH_GROUPS-1:0] push_group;
    wire [2*NL-1:0] push_lane;
    generate if(SAFE_FIFO) begin:g_push_groups
      for(genvar pg=0;pg<PUSH_GROUPS;pg=pg+1) begin:g_group
        (* keep *) reg ring_r;
        always @(posedge clk or negedge rr[CTRL_RSTBASE+NL+8+pg])
          if(!rr[CTRL_RSTBASE+NL+8+pg]) ring_r<=0;else ring_r<=rvx[pg/3];
        wire iv_g, ib_g; wire [1:0] pp_g;               // S81/H4: tree-frame valid / pair-B copies of this group
        if (IDX_EN != 0) begin : g_i
          (* keep *) reg iv_r, ib_r;
          always @(posedge clk or negedge rr[CTRL_RSTBASE+NL+8+pg])
            if(!rr[CTRL_RSTBASE+NL+8+pg]) begin iv_r<=0; ib_r<=0; end else begin iv_r<=ivx[pg/3]; ib_r<=ibx[pg/3]; end
          assign iv_g = iv_r; assign ib_g = ib_r;
        end else begin : g_ni assign iv_g = 1'b0; assign ib_g = 1'b0; end
        (* keep=1 *) ot_s81sl_lep_tx_push u_push(.ring(ring_r),.host_go(!ring_r && !iv_g && frame_host_pending[pg]),.key_go(!ring_r && !iv_g && !frame_host_pending[pg] && frame_key_pending[pg]),.open(wopen),.pair_b(wab),.pp(pp_g));
        assign push_group[2*pg+:2] = pp_g | {!ring_r && iv_g && ib_g, !ring_r && iv_g && !ib_g};
      end
      for(genvar pl=0;pl<NL;pl=pl+1) begin:g_lane
        (* keep *) reg ring_r;
        always @(posedge clk or negedge rr[CTRL_RSTBASE+NL+8+PUSH_GROUPS+pl])
          if(!rr[CTRL_RSTBASE+NL+8+PUSH_GROUPS+pl]) ring_r<=0;else ring_r<=rvx[1+pl];
        wire iv_g, ib_g; wire [1:0] pp_g;               // S81/H4: as the push groups
        if (IDX_EN != 0) begin : g_i
          (* keep *) reg iv_r, ib_r;
          always @(posedge clk or negedge rr[CTRL_RSTBASE+NL+8+PUSH_GROUPS+pl])
            if(!rr[CTRL_RSTBASE+NL+8+PUSH_GROUPS+pl]) begin iv_r<=0; ib_r<=0; end else begin iv_r<=ivx[1+pl]; ib_r<=ibx[1+pl]; end
          assign iv_g = iv_r; assign ib_g = ib_r;
        end else begin : g_ni assign iv_g = 1'b0; assign ib_g = 1'b0; end
        (* keep=1 *) ot_s81sl_lep_tx_push u_push(.ring(ring_r),.host_go(!ring_r && !iv_g && frame_host_pending[PUSH_GROUPS+pl]),.key_go(!ring_r && !iv_g && !frame_host_pending[PUSH_GROUPS+pl] && frame_key_pending[PUSH_GROUPS+pl]),.open(wopen),.pair_b(wab),.pp(pp_g));
        assign push_lane[2*pl+:2] = pp_g | {!ring_r && iv_g && ib_g, !ring_r && iv_g && !ib_g};
      end
    end endgenerate
    reg [1:0] sq;                                      // frame-sequence parity (TX), per pair
    always @(posedge clk or negedge rn) if (!rn) sq <= 2'b00; else sq <= sq ^ pp;
`ifdef OT_S81SL_LEP_MUT_SWAP
    wire [H-1:0] hf0 = fr[2*H-1:H], hf1 = fr[H-1:0];
`else
    wire [H-1:0] hf0 = fr[H-1:0], hf1 = fr[2*H-1:H];
`endif

    // ---------------------------------------------------------------- TX landing FIFOs (one per lane)
    // Storage: ot_s81ph_mem1r1w SRAM = 1 (5 x ot_sram_1r1w_512x128_m4_r2c2 a lane, registered write port WREG = 1,
    // registered read), DT entries.  Credit sender: lo_r (a credit pulse per freed lane landing slot) lands in the pin flop
    // cr_q; a read is issued only with a credit in hand (the credit is spent at issue), its word leaves on lo_v / lo_d
    // from flops two edges later (three at TXRP 1).  lo_d loads the SRAM read word every cycle (the lane samples it only with lo_v).
    // Lanes 2 / 3 (AB_EN 1) = pair B, same structure, fed by pp[1] (reset regions: lane 2 with lane 0, lane 3 with 1).
    wire [NL-1:0] ovf;
    wire [3:0] lo_v; wire [3:0] lo_r = {lo3_r, lo2_r, lo1_r, lo0_r};
    wire [4*(H+1)-1:0] lo_d;
    localparam integer CW = $clog2(CRED + 1);
    genvar t;
    generate for (t = 0; t < NL; t = t + 1) begin : g_tx
        wire rt = (NXR != 0 && t >= 2) ? rr[4+NRX_RST+t-2] : rr[t % 2];
        reg [AT-1:0] wp, rp; reg [AT:0] n; reg [CW-1:0] cnt;
        reg inf, of, ov; reg [H:0] od;
        wire inq; wire [H:0] qd;                      // read word / valid one stage before the lo pin flops
        (* keep = "true" *) reg cr_q;                  // lo_r pin flop
        wire [H:0] q;
        wire iss = n != 0 && cnt != 0;
        wire psh = (SAFE_FIFO)?push_lane[2*t+t/2]:pp[t / 2];
        wire wr = psh && (n != DT || iss);
        if(SAFE_FIFO && SRAM!=0) begin:g_safe_write
            localparam integer GA=4, NA=(TX_NS+GA-1)/GA;
            wire [NA*AT-1:0] wa_copy,ra_copy;
            wire [NA-1:0] wr_group,rd_group;
            for(c=0;c<NA;c=c+1) begin:g_address
                (* keep="true" *) reg [AT-1:0] wp_r,rp_r;
                (* keep="true" *) reg [AT:0] count_r;
                (* keep="true" *) reg [CW-1:0] credit_r;
                (* keep="true" *) reg credit_pin_r;
                wire wr_update,rd_update,wr_pointer,rd_pointer;
                if(SAFE_STD) begin:g_std_qualify
                  // Separate genuine state/pointer/memory consumer cones. A
                  // single write/read predicate otherwise fans ~45 ABC pins.
                  (* keep=1 *) ot_s81sl_std_tx_qualify #(.AT(AT),.CW(CW),.DT(DT)) u_memory(
                    .push(push_group[2*c+t/2]),.count(count_r),.credit(credit_r),.wr(wr_group[c]),.rd(rd_group[c]));
                  (* keep=1 *) ot_s81sl_std_tx_qualify #(.AT(AT),.CW(CW),.DT(DT)) u_state(
                    .push(push_group[2*c+t/2]),.count(count_r),.credit(credit_r),.wr(wr_update),.rd(rd_update));
                  (* keep=1 *) ot_s81sl_std_tx_qualify #(.AT(AT),.CW(CW),.DT(DT)) u_pointer(
                    .push(push_group[2*c+t/2]),.count(count_r),.credit(credit_r),.wr(wr_pointer),.rd(rd_pointer));
                end else begin:g_existing_qualify
                  assign rd_group[c]=(count_r!=0 && credit_r!=0);
                  assign wr_group[c]=push_group[2*c+t/2] && (count_r!=(AT+1)'(DT) || rd_group[c]);
                  assign wr_update=wr_group[c];assign rd_update=rd_group[c];
                  assign wr_pointer=wr_group[c];assign rd_pointer=rd_group[c];
                end
                wire pointer_reset=rr[TX_RSTBASE+t*TX_RST_STRIDE+TX_NS+2*c];
                wire state_reset=rr[TX_RSTBASE+t*TX_RST_STRIDE+TX_NS+2*c+1];
                always @(posedge clk or negedge state_reset)
                    if(!state_reset) begin count_r<=0;credit_r<=CW'(CRED);credit_pin_r<=0; end else begin
                        credit_pin_r<=lo_r[t];
                        credit_r<=credit_r+CW'(credit_pin_r)-CW'(rd_update);
                        count_r<=count_r+(AT+1)'(wr_update)-(AT+1)'(rd_update);
                    end
                always @(posedge clk or negedge pointer_reset)
                    if(!pointer_reset) begin wp_r<=0;rp_r<=0; end else begin
                        wp_r<=(wp_r==AT'(DT-1) && wr_pointer)?AT'(0):wp_r+AT'(wr_pointer);
                        rp_r<=(rp_r==AT'(DT-1) && rd_pointer)?AT'(0):rp_r+AT'(rd_pointer);
                    end
`ifdef OT_S81SL_TX_GROUP_ASSERT
                always @(posedge clk) if(rt && pointer_reset && state_reset) begin
                    if({wr_group[c],rd_group[c],wp_r,rp_r,count_r,credit_r} !== {wr,iss,wp,rp,n,cnt})
                        $fatal(1,"TX regional state differs lane%0d group%0d",t,c);
                end
`endif
                assign wa_copy[c*AT+:AT]=wp_r;assign ra_copy[c*AT+:AT]=rp_r;
            end
            ot_sram_oldread_wreg #(.W(H+1),.AW(AT),.SB(8),.GA(GA),.GROUP_IO(1)) u_m(.clk(clk),.rst_n(rr[TX_RSTBASE+t*TX_RST_STRIDE+:TX_NS]),
                .we(wr),.we_group(wr_group),.re_group(rd_group),.wa(wa_copy),.wd({sq[t/2],(t%2==0)?hf0:hf1}),.re(iss),.ra(ra_copy),.q(q));
        end else begin:g_legacy_write
        ot_s81ph_mem1r1w #(.W(H + 1), .DEPTH(DT), .SRAM(SRAM), .WREG(1)) u_m (.clk(clk), .rst_n(rt), .we(wr), .wa(wp),
            .wd({sq[t / 2], (t % 2 == 0) ? hf0 : hf1}), .re(iss), .ra(rp), .q(q));
        end
        always @(posedge clk or negedge rt)
            if (!rt) begin wp <= 0; rp <= 0; n <= 0; inf <= 1'b0; of <= 1'b0; cr_q <= 1'b0; cnt <= CW'(CRED); ov <= 1'b0; end
            else begin
                cr_q <= lo_r[t];
                cnt <= cnt + CW'(cr_q) - CW'(iss);
                if (wr) wp <= (wp == DT - 1) ? 0 : wp + 1'b1;
                if (iss) rp <= (rp == DT - 1) ? 0 : rp + 1'b1;
                n <= n + (wr ? 1'b1 : 1'b0) - (iss ? 1'b1 : 1'b0);
                inf <= iss;
                ov <= inq;
`ifndef OT_S81SL_LEP_MUT_NOOVF
                if (psh && n == DT && !iss) of <= 1'b1;
`endif
            end
        if (TXRP != 0) begin : g_rp                   // S81-FIX3: read pipeline register beside the SRAM column
            reg inr; reg [H:0] odr;
            always @(posedge clk or negedge rt) if (!rt) inr <= 1'b0; else inr <= inf;
            always @(posedge clk) odr <= q;
            assign inq = inr; assign qd = odr;
        end else begin : g_nrp
            assign inq = inf; assign qd = q;
        end
        always @(posedge clk) od <= qd;
        assign lo_v[t] = ov; assign lo_d[t * (H + 1) +: H + 1] = od; assign ovf[t] = of;
    end
    if (NL == 2) begin : g_txnb                         // AB_EN 0: no pair-B lanes (lo2 / lo3 unread outputs = 0)
        assign lo_v[3:2] = 2'b00; assign lo_d[4*(H+1)-1:2*(H+1)] = '0;
    end endgenerate
    assign lo0_v = lo_v[0]; assign lo0_d = lo_d[H:0];
    assign lo1_v = lo_v[1]; assign lo1_d = lo_d[2*H+1:H+1];
    assign lo2_v = lo_v[2]; assign lo2_d = lo_d[3*H+2:2*H+2];
    assign lo3_v = lo_v[3]; assign lo3_d = lo_d[4*H+3:3*H+3];

    // ---------------------------------------------------------------- RX pair re-assembly
    // Credit receiver per lane (ot_link_credit_rx WFREE 2 form): li_v / li_d land in pin flops (vq / dq); the landing
    // register is written every non-full cycle into mem[wp] through REGISTERED one-hot slot enables (credits guarantee a
    // free slot), the non-empty flag is registered, li_r is a registered credit pulse per pop, a beat landing on a full
    // FIFO is a sticky fault.  The read pointer is replicated RREP times (each copy selects <= 35 data columns).
    localparam integer RREP = 16, SW = (H + 1 + RREP - 1) / RREP;
    wire [3:0] li_v = {li3_v, li2_v, li1_v, li0_v}; wire [4*(H+1)-1:0] li_d = {li3_d, li2_d, li1_d, li0_d};
    wire [NL-1:0] rne, rxf; wire [NL*(H+1)-1:0] rhd; wire [NL-1:0] lir;
    wire [NL*4-1:0] ring_meta_regions;
    wire [NL-1:0] rne_addr,rne_meta,rne_return;
    wire [NL-1:0] rhostx,rksx;
    wire [NL-1:0] rnex, rhkx, rringx, rtagx;
    wire [NL-1:0] rhk;                                 // MU_EN 1: pre-decoded land bit of each lane's head row
    wire [1:0] relp;                                   // pair releases (pair B only at AB_EN 1)
`ifdef OT_S81SL_LEP_MUT_NOPAIR
    assign relp[0] = rne[0];
`else
    assign relp[0] = rne[0] && rne[1];
`endif
    generate if (NL == 4) begin : g_relb
        assign relp[1] = rne[2] && rne[3];
    end else begin : g_nrelb
        assign relp[1] = 1'b0;
    end endgenerate
    wire rel = relp[0] || relp[1];
    wire rpb = relp[1] && !relp[0];                    // the released pair is B
    genvar c;
    generate for (t = 0; t < NL; t = t + 1) begin : g_rx
        wire rx_state_reset=(SAFE_FIFO)?rr[CTRL_RSTBASE+t]:rnx;
        reg [H:0] mem [0:DR-1];
        reg [AR-1:0] wp, rp; reg [AR:0] n; reg vq, nz, cr, f; reg [DR-1:0] we; reg [H:0] dq;
        wire pop;
        if(SAFE_CONTROL) begin:g_native_pop
`ifdef OT_S81SL_LEP_MUT_NOPAIR
          wire pair_b=(t==0)?1'b1:rne[2*(t/2)+1];
`else
          wire pair_b=rne[2*(t/2)+1];
`endif
          (* keep=1 *) ot_s81sl_lep_pair_ready u_ready(.a(rne[2*(t/2)]),.b(pair_b),.q(pop));
        end else begin:g_legacy_pop assign pop=relp[t/2] && nz;end
        wire full = n == (AR+1)'(DR);
        wire wr = vq && !full;
        wire [AR-1:0] wp_nx = wr ? ((wp == AR'(DR - 1)) ? '0 : wp + 1'b1) : wp;
        wire [AR-1:0] rp_nx = pop ? ((rp == AR'(DR - 1)) ? '0 : rp + 1'b1) : rp;
        wire [AR:0] n_nx = n + (AR+1)'(wr) - (AR+1)'(pop);
        assign rnex[t]=n_nx!=0;
        integer k;
        always @(posedge clk or negedge rx_state_reset)
            if (!rx_state_reset) begin wp <= 0; rp <= 0; n <= 0; vq <= 1'b0; nz <= 1'b0; cr <= 1'b0; f <= 1'b0; we <= DR'(1); end
            else begin
                vq <= li_v[t];
                cr <= pop;
                if (vq && full && !pop) f <= 1'b1;
                wp <= wp_nx; rp <= rp_nx; n <= n_nx; nz <= n_nx != 0;
                for (k = 0; k < DR; k = k + 1) we[k] <= (wp_nx == AR'(k)) && (n_nx != (AR+1)'(DR));
            end
        if(SAFE_CONTROL) begin:g_nonempty_regions
          (* keep=1 *) reg addr_nz,meta_nz,return_nz;
          wire reset_c=rr[NATIVE32_RXRSTBASE+t];
          always @(posedge clk or negedge reset_c)
            if(!reset_c) begin addr_nz<=0;meta_nz<=0;return_nz<=0;end
            else begin addr_nz<=n_nx!=0;meta_nz<=n_nx!=0;return_nz<=n_nx!=0;end
          assign rne_addr[t]=addr_nz;assign rne_meta[t]=meta_nz;assign rne_return[t]=return_nz;
        end else begin:g_nonempty_shared
          assign rne_addr[t]=rne[t];assign rne_meta[t]=rne[t];assign rne_return[t]=rne[t];
        end
        always @(posedge clk) dq<=li_d[t*(H+1)+:H+1];
        if(!SAFE_FIFO) begin:g_legacy_mem
            integer j;
            always @(posedge clk)
                for(j=0;j<DR;j=j+1) if(we[j]) mem[j]<=dq;
        end
        // MU_EN 0: the head is read combinationally from mem[rpc] (pre-MU structure, unchanged; loop empty at MU_EN 1)
        for (c = 0; c < ((MU_EN != 0 || SAFE_STD) ? 0 : RREP); c = c + 1) begin : g_c
            localparam integer LO = c * SW, HI = ((c + 1) * SW > H + 1) ? H + 1 : (c + 1) * SW;
            if (LO < H + 1) begin : g_on
                (* keep = "true" *) reg [AR-1:0] rpc;
                always @(posedge clk or negedge rx_state_reset) if (!rx_state_reset) rpc <= 0; else rpc <= rp_nx;
                wire [H:0] row = mem[rpc];
                assign rhd[t * (H + 1) + LO +: HI - LO] = row[HI-1:LO];
            end
        end
        // MU-S81-2/RX (10-19): SHOW-AHEAD head register (MU_EN 1).  hd = mem[rp] at every cycle, from flops: on each edge
        // it loads the row the pointer will hold (rp_nx), or the landing word dq when that row is written on the same
        // edge (registered one-hot enables we).  Same FIFO order, nz timing and full / empty faults; 0 added cycles.
        // The pointer copy + increment is replicated per column group (as RREP above); pop = this pair's release (nz
        // flops of the pair only), so rp_nx -> 8:1 row mux -> hd stays inside the lane.  hk = a PRE-DECODED land bit of
        // the head row (stored per row at write): lane 0 of a pair = XB / XQ ring beat, lane 1 = tag && land bits.
        if (MU_EN != 0 || SAFE_STD) begin : g_sa
            wire kd = (t % 2 == 0) ? (dq[0] && (dq[3:1] == K_XB || dq[3:1] == K_XQ)) : (dq[TG - H] && dq[TG + 1 - H]);
            reg [DR-1:0] mk,mrk,mtk,mhost,mks; reg hk;
            wire [3*AR-1:0] meta_read_next;
            for(genvar mp=0;mp<3;mp=mp+1) begin:g_meta_ptr
              if((NATIVE32!=0 || SAFE_STD) && RX_SRAM!=0) begin:g_local
`ifdef OT_S81SL_LEP_MUT_NOPAIR
                wire mb=(t==0)?1'b1:rne_meta[2*(t/2)+1];
`else
                wire mb=rne_meta[2*(t/2)+1];
`endif
                (* keep=1 *) ot_sram_showahead_readptr #(.AW(AR),.DEPTH(DR)) u_ptr(
                  .clk(clk),.rn(rr[NATIVE32_RXRSTBASE+t]),.advance_a(rne_meta[2*(t/2)]),.advance_b(mb),
                  .next_addr(meta_read_next[mp*AR+:AR]));
              end else begin:g_shared assign meta_read_next[mp*AR+:AR]=rp_nx;end
            end
            wire [AR-1:0] host_ra=meta_read_next[0+:AR],ring_ra=meta_read_next[AR+:AR],land_ra=meta_read_next[2*AR+:AR];
            wire host_d=(t==0) && !dq[0] && dq[3:1]==3'd1;
            wire ks_d=(t==0) && !dq[0] && dq[3:1]==3'd2;
            assign rhostx[t]=we[host_ra]?host_d:mhost[host_ra];
            assign rksx[t]=we[host_ra]?ks_d:mks[host_ra];
            wire rd=(t%2==0)?dq[0]:1'b0;
            wire td=(t%2!=0)?dq[TG-H]:1'b0;
            assign rringx[t]=we[ring_ra]?rd:mrk[ring_ra];
            assign rtagx[t]=we[ring_ra]?td:mtk[ring_ra];
`ifdef OT_S81SL_LEP_MUT_STALEHD
            assign rhkx[t]=mk[rp];
`else
            assign rhkx[t]=we[land_ra]?kd:mk[land_ra];
`endif
            integer jk;
            always @(posedge clk) begin
                for(jk=0;jk<DR;jk=jk+1) if(we[jk]) begin mk[jk]<=kd; mrk[jk]<=rd; mtk[jk]<=td;mhost[jk]<=host_d;mks[jk]<=ks_d; end
`ifdef OT_S81SL_LEP_MUT_STALEHD
                hk <= mk[rp];
`else
                hk <= we[land_ra] ? kd : mk[land_ra];
`endif
            end
            assign rhk[t] = hk;
            if(RX_SRAM!=0) begin:g_true_sram
                wire [H:0] head;
`ifdef OT_S81SL_LEP_MUT_STALEHD
                wire [AR-1:0] read_next=rp;
`else
                wire [AR-1:0] read_next=rp_nx;
`endif
                ot_sram_showahead_1r1w #(.W(H+1),.AW(AR),.LOCAL_HIT(1),.SB(8),.LOCAL_RA(NATIVE32+SAFE_STD),.LOCAL_WA(NATIVE32+SAFE_STD),.LOCAL_WD(SAFE_STD),.DEPTH(DR)) u_rx_mem(
                    .clk(clk),.rst_n(rr[4+t*RX_NS+:RX_NS]),.we(wr),.wa(wp),.wd(dq),
                    .ra(read_next),.q(head),.advance_a(rne_addr[2*(t/2)]),
`ifdef OT_S81SL_LEP_MUT_NOPAIR
                    .advance_b((t==0)?1'b1:rne_addr[2*(t/2)+1]));
`else
                    .advance_b(rne_addr[2*(t/2)+1]));
`endif
                assign rhd[t*(H+1)+:H+1]=head;
            end else begin:g_old_head
            for (c = 0; c < RREP; c = c + 1) begin : g_h
                localparam integer LO = c * SW, HI = ((c + 1) * SW > H + 1) ? H + 1 : (c + 1) * SW;
                if (LO < H + 1) begin : g_on
                    (* keep = "true" *) reg [AR-1:0] rpc;
                    wire [AR-1:0] rpn = pop ? ((rpc == AR'(DR - 1)) ? '0 : rpc + 1'b1) : rpc;
                    reg [HI-LO-1:0] hd;
                    always @(posedge clk or negedge rx_state_reset) if (!rx_state_reset) rpc <= 0; else rpc <= rpn;
                    wire [H:0] row = mem[rpn];
                    always @(posedge clk)
`ifdef OT_S81SL_LEP_MUT_STALEHD
                        hd <= mem[rpc][HI-1:LO];               // MUTANT: no show-ahead (head of the OLD pointer / old row)
`else
                        hd <= we[rpn] ? dq[HI-1:LO] : row[HI-1:LO];
`endif
                    assign rhd[t * (H + 1) + LO +: HI - LO] = hd;
                end
            end
            end // g_old_head
        end
        assign rne[t] = nz; assign lir[t] = cr; assign rxf[t] = f;
    end endgenerate
    generate for(genvar rh=0;rh<NL;rh=rh+1) begin:g_ring_meta
      if(SAFE_CONTROL) begin:g_native
        for(genvar rg=0;rg<4;rg=rg+1) begin:g_copy
          (* keep=1 *) ot_s81sl_lep_vcopy u_copy(.clk(clk),.d(rringx[rh]),.q(ring_meta_regions[4*rh+rg]));
        end
      end else begin:g_shared assign ring_meta_regions[4*rh+:4]={4{rhd[rh*(H+1)]}};end
    end endgenerate
    wire [3:0] active_ring_flags=rpb?ring_meta_regions[2*4+:4]:ring_meta_regions[0+:4];
    assign li0_r = lir[0]; assign li1_r = lir[1];
    generate if (NL == 4) begin : g_rxb
        assign li2_r = lir[2]; assign li3_r = lir[3];
        // pair-B receiver-valid pin flops of their own (S face), cleared by reset region 1 (released on the same edge as
        // region 2 = rnx): with the same clear net yosys opt_merge folded them into the W-face rxv flops ((* keep *) on the
        // reg does not stop that) and one flop drove rxv[1] and rxvb[*] ~580 um apart (gate textbook.wire_reach 10-19)
        wire rnb = rr[1];
        (* keep = "true" *) reg [1:0] rxvb_q;
        always @(posedge clk or negedge rnb) if (!rnb) rxvb_q <= 2'b00; else rxvb_q <= 2'b11;
        assign rxvb = rxvb_q;
    end else begin : g_nrxb
        assign li2_r = 1'b0; assign li3_r = 1'b0; assign rxvb = 2'b00;
    end endgenerate
    wire [H:0] h0, h1;
    generate if (NL == 4) begin : g_hsel
        assign h0 = rpb ? rhd[3*H+2:2*H+2] : rhd[H:0];
        assign h1 = rpb ? rhd[4*H+3:3*H+3] : rhd[2*H+1:H+1];
    end else begin : g_hsel0
        assign h0 = rhd[H:0]; assign h1 = rhd[2*H+1:H+1];
    end endgenerate
    reg perr;
    // host-plane frame types this endpoint accepts (HOST 1, KS 2) -- none at HOST_EN 0, never on pair B
`ifdef OT_S81SL_LEP_MUT_NHACC
    wire hacc = !h0[0] && (h0[3:1] == 3'd1 || h0[3:1] == 3'd2);        // MUTANT: accepted even at HOST_EN 0
`else
    wire hacc = (HOST_EN != 0) && !rpb && !active_ring_flags[1] && (h0[3:1] == 3'd1 || h0[3:1] == 3'd2);
`endif
    // S81/H4: a tree frame (type 5) is accepted on either pair at IDX_EN 1 and never reaches ri (not a ring beat)
    wire iacc = (IRX != 0) && !h0[0] && h0[3:1] == 3'd5 && (IDX_TP == 0 || !rpb);   // S81/IDXNET: TP ends on pair A only
    wire qacc = (QEN != 0) && !h0[0] && h0[3:1] == 3'd6 && rpb;                       // S81/IDXNET: Q words only from PREV
    reg [1103:1] rid; reg riv;
    assign ri = {rid, riv};
    wire mcol_w;                                       // MU: replay collided with a cut-through beat
    wire [1103:0] rb = {h1[H-1:0], h0[H-1:0]};          // the released frame (ring beat when bit 0)
    generate if (MU_EN == 0) begin : g_rxr
    if(SAFE_STD) begin:g_std_output
      localparam integer SG=69,CG=(SG+7)/8;
      wire [CG-1:0] en;
      for(genvar cg=0;cg<CG;cg=cg+1) begin:g_decode
        (* keep=1 *) ot_s81sl_lep_std_enable u_decode(.a(rnex[0]),.b(rnex[1]),.ring(rringx[0]),.q(en[cg]));
      end
      for(genvar sg=0;sg<SG;sg=sg+1) begin:g_slice
        localparam integer LO=1+16*sg,SW=(1104-LO<16)?1104-LO:16;
        (* keep=1 *) reg select_r;
        always @(posedge clk or negedge rr[4+NRX_MEMRST+sg])
          if(!rr[4+NRX_MEMRST+sg]) select_r<=0;
`ifdef OT_S81SL_LEP_MUT_STDSEL
          else select_r<=rel && h0[0]; // causal mutant: misses look-ahead age
`else
          else select_r<=en[sg/8];
`endif
        always @(posedge clk) rid[LO+:SW]<=select_r?rb[LO+:SW]:'0;
      end
    end else begin:g_std_legacy
    always @(posedge clk) rid <= (rel && h0[0]) ? {h1[H-1:0], h0[H-1:1]} : 1103'd0;   // data: no reset
    end
    always @(posedge clk or negedge rnx)
        if (!rnx) riv <= 1'b0;
        else riv <= rel && h0[0];
    assign mu_rt = 32'd0; assign ml_wv = 1'b0; assign ml_wd = 1104'd0; assign mcol_w = 1'b0; if(!SAFE_STD) assign rhk = '0;
    end else begin : g_rxm
    // tagged = an XB / XQ ring beat with the tag bit; land = 1 -> landing leaf, else ri (tag stripped, tag on mu_rt)
    function automatic [1103:0] strip(input [1103:0] b);
        begin strip = b; strip[TG +: 33] = 33'd0; end
    endfunction
    function automatic tagd(input [1103:0] b);
        begin tagd = b[0] && (b[3:1] == K_XB || b[3:1] == K_XQ) && b[TG]; end
    endfunction
    reg mrv, mcol, mwv; reg [1103:0] mrd, mwd; reg [31:0] rtq;
    always @(posedge clk) mrd <= ml_rd;
    // MU-S81-2/RX: selects straight from the show-ahead flops.  Per pair X: gX = X releases a ring beat (pair A wins a
    // collision, as rpb), lX = its pre-decoded land bit (lane 0 XB / XQ ring beat && lane 1 tag && land); sX = deliver
    // X's beat on ri, sM = deliver the replayed beat (cut-through wins a collision, mcol fault as before).
    wire [1103:0] bA = {rhd[2*H:H+1], rhd[H-1:0]};     // pair A frame (lane 1 high half, lane 0 low half)
    wire lA = rhk[0] && rhk[1];
    wire gA = relp[0] && ring_meta_regions[0];
    wire [1103:0] bB; wire lB, gB;
    if (NL == 4) begin : g_mb
        assign bB = {rhd[4*H+2:3*H+3], rhd[3*H+1:2*H+2]};
        assign lB = rhk[2] && rhk[3];
        assign gB = rpb && ring_meta_regions[2*4];               // rpb: nz flops only
    end else begin : g_nmb
        assign bB = 1104'd0; assign lB = 1'b0; assign gB = 1'b0;
    end
`ifdef OT_S81SL_LEP_MUT_LANDCUT
    wire ldA = 1'b0, ldB = 1'b0;                       // MUTANT: land bit ignored (landed beats cut through to ri)
`else
    wire ldA = lA, ldB = lB;
`endif
    wire rr_land = (gA && ldA) || (gB && ldB);
    wire rr_dlv = (gA && !ldA) || (gB && !ldB);
    wire [1103:0] db = rr_dlv ? rb : mrd;               // delivered beat (tag fields only: rtq)
    // rid: one AO222 per bit, {sA, sB, sM} duplicated per column group (keep) so each select net drives ~70 bits
    localparam integer OREP = (RX_SRAM!=0)?((1103+15)/16):16, OW = (1103 + OREP - 1) / OREP;
    wire [1103:1] nrid;
    // strip only TAGGED beats (XB / XQ ring beat with the tag bit, SPEC (a)): any other beat is delivered bit-exact.
    // Lane-0 kind is pre-decoded per FIFO row (rhk[0] / rhk[2]); the tag bit is a show-ahead flop; the replay word a pin flop.
    wire tA = rhk[0] && bA[TG];
    wire tB = (NL == 4) ? (rhk[NL - 2] && bB[TG]) : 1'b0;
    wire tM = tagd(mrd);
`ifdef OT_S81SL_LEP_MUT_STRIPALL
    wire [1103:0] sbA = strip(bA), sbB = strip(bB), sbM = strip(mrd);   // MUTANT: strips every beat (pre-fix behaviour)
`else
    wire [1103:0] sbA = tA ? strip(bA) : bA, sbB = tB ? strip(bB) : bB, sbM = tM ? strip(mrd) : mrd;
`endif
    // With SRAM, next-head metadata is available alongside next read address. Register the
    // delivery selects there, one reset-distinct copy per<=16outputbits. Data still reaches rid
    // on the original edge; no global1103load select or extra receive stage remains.
    wire a_rel_next=rnex[0] && rnex[1];
    wire a_ring_next=a_rel_next && rringx[0];
    wire b_ring_next;
    wire b_land_next, b_tag_next;
    if(NL==4) begin:g_b_lookahead
        assign b_ring_next=rnex[2] && rnex[3] && !a_rel_next && rringx[2];
        assign b_land_next=rhkx[2] && rhkx[3];
        assign b_tag_next=rhkx[2] && rtagx[3];
    end else begin:g_no_b_lookahead
        assign b_ring_next=1'b0; assign b_land_next=1'b0; assign b_tag_next=1'b0;
    end
`ifdef OT_S81SL_LEP_MUT_LANDCUT
    wire a_cut_next=a_ring_next, b_cut_next=b_ring_next;
`else
    wire a_cut_next=a_ring_next && !(rhkx[0] && rhkx[1]);
    wire b_cut_next=b_ring_next && !b_land_next;
`endif
`ifdef OT_S81SL_LEP_MUT_STRIPALL
    wire a_tag_next=1'b1, bt_next=1'b1, m_tag_next=1'b1;
`else
    wire a_tag_next=rhkx[0] && rtagx[1];
    wire bt_next=b_tag_next;
    wire m_tag_next=tagd(ml_rd);
`endif
    localparam integer CG=(OREP+7)/8;
    wire [CG*6-1:0] control_local;
    wire [CG-1:0] pb_next;                            // L5B-LEPMU: rpb one edge early, per control group (AB_EN 1)
    if(RX_SRAM!=0) begin:g_control_groups
        for(genvar cg=0;cg<CG;cg=cg+1) begin:g_group
            (* keep=1 *) ot_s81sl_lep_rx_control u_ctrl(.ne({{(4-NL){1'b0}},rnex}),.ring({{(4-NL){1'b0}},rringx}),
                .hk({{(4-NL){1'b0}},rhkx}),.tag({{(4-NL){1'b0}},rtagx}),
                .mv(ml_rv),.mt({ml_rd[TG],ml_rd[3:0]}),.sel(control_local[cg*6+:6]));
            if(NATIVE32!=0 && NL==4) begin:g_pb
                (* keep=1 *) ot_s81sl_lep_bsel_next u_pb(.ne(rnex),.q(pb_next[cg]));
            end else begin:g_npb assign pb_next[cg]=1'b0; end
        end
    end else begin:g_no_control_groups
        assign pb_next='0;
    end
    // L5B-LEPMU 10-21 (native census: rpb drove the 1,104-bit mwd pair select, 1,109 / 1,102 loads): at NATIVE32 + AB_EN 1
    // mwd takes per-16-bit-group registered copies of rpb (pb_r <= rpb's next value), exact and same edge.
    wire [1103:0] mwd_n;
    wire [OREP-1:0] pb_g;
    for (c = 0; c < OREP; c = c + 1) begin : g_o
        localparam integer LO = 1 + c * OW, HI = (1 + (c + 1) * OW > 1104) ? 1104 : 1 + (c + 1) * OW;
        if (LO < 1104) begin : g_on
            if(RX_SRAM!=0) begin:g_registered_select
                (* keep *) reg sa_r, sb_r, sm_r, ta_r, tb_r, tm_r, pb_r;
                wire reset_o=rr[4+NRX_MEMRST+c];
                always @(posedge clk or negedge reset_o)
                    if(!reset_o) begin sa_r<=0; sb_r<=0; sm_r<=0; ta_r<=0; tb_r<=0; tm_r<=0; pb_r<=0; end
                    else begin
                        {tm_r,tb_r,ta_r,sm_r,sb_r,sa_r}<=control_local[(c/8)*6+:6];
                        pb_r<=pb_next[c/8];
                    end
                assign pb_g[c]=pb_r;
                assign mwd_n[HI-1:LO]=(NATIVE32!=0 && NL==4) ? (pb_r ? bB[HI-1:LO] : bA[HI-1:LO]) : rb[HI-1:LO];
                genvar ob;
                for(ob=LO;ob<HI;ob=ob+1) begin:g_bit
                    wire da, dbit, dm;
                    if(ob>=TG && ob<TG+33) begin:g_tag
                        assign da=bA[ob] && !ta_r; assign dbit=bB[ob] && !tb_r; assign dm=mrd[ob] && !tm_r;
                    end else begin:g_payload
                        assign da=bA[ob]; assign dbit=bB[ob]; assign dm=mrd[ob];
                    end
                    assign nrid[ob]=(sa_r && da) || (sb_r && dbit) || (sm_r && dm);
                end
            end else begin:g_old_select
            (* keep = "true" *) wire sA = gA && !ldA;
            (* keep = "true" *) wire sB = gB && !ldB;
            (* keep = "true" *) wire sM = mrv && !(gA && !ldA) && !(gB && !ldB);
            assign nrid[HI-1:LO] = ({(HI - LO){sA}} & sbA[HI-1:LO]) | ({(HI - LO){sB}} & sbB[HI-1:LO])
                                 | ({(HI - LO){sM}} & sbM[HI-1:LO]);
            assign pb_g[c]=1'b0; assign mwd_n[HI-1:LO]=rb[HI-1:LO];
            end
        end
    end
    always @(posedge clk) begin
        rid <= nrid;
        mwd[1103:1] <= mwd_n[1103:1];

    end
    // L5B-LEPMU: the return tag / code bits and mwd[0] take the released frame through their own kept copies of rpb
    // (3 x ot_s81sl_lep_vcopy of pb_next, <= 16 bits each) at NATIVE32 + AB_EN 1; rb elsewhere.
    wire [1103:0] rbx;
    if(NATIVE32!=0 && RX_SRAM!=0 && NL==4) begin:g_rbx
      wire [2:0] pbx;
      for(genvar px=0;px<3;px=px+1) begin:g_pbx
        (* keep=1 *) ot_s81sl_lep_vcopy u_pbx(.clk(clk),.d(pb_next[px]),.q(pbx[px]));
      end
      assign rbx[TG+2+:16]=pbx[0]?bB[TG+2+:16]:bA[TG+2+:16];
      assign rbx[TG+18+:15]=pbx[1]?bB[TG+18+:15]:bA[TG+18+:15];
      assign rbx[TG+1:TG]=pbx[2]?bB[TG+1:TG]:bA[TG+1:TG];
      assign rbx[3:0]=pbx[2]?bB[3:0]:bA[3:0];
      assign rbx[TG-1:4]=rb[TG-1:4]; assign rbx[1103:TG+33]=rb[1103:TG+33];
    end else begin:g_nrbx
      assign rbx=rb;
    end
    always @(posedge clk) mwd[0] <= rbx[0];
    if(NATIVE32!=0 && RX_SRAM!=0) begin:g_native_return
      wire [31:0] ring_tag={1'b1,rbx[TG+2+:10],rbx[TG+12+:21]};
      wire [31:0] replay_tag={1'b1,mrd[TG+2+:10],mrd[TG+12+:21]};
      for(genvar rt=0;rt<4;rt=rt+1) begin:g_byte
        wire [7:0] next_tag;
        (* keep=1 *) ot_s81sl_lep_return8 u_tag(.ne({{(4-NL){1'b0}},rne_return}),
          .ring({((NL==4)?ring_meta_regions[2*4+3]:1'b0),ring_meta_regions[3]}),.land({ldB,ldA}),.ring_code({rbx[TG],rbx[3:1],active_ring_flags[2]}),
          .replay_code({mrd[TG],mrd[3:0]}),.ring_data(ring_tag[rt*8+:8]),
          .replay_data(replay_tag[rt*8+:8]),.q(next_tag));
        always @(posedge clk) rtq[rt*8+:8]<=next_tag;
      end
    end else begin:g_legacy_return
      always @(posedge clk) rtq<=tagd(db)?{1'b1,db[TG+2+:10],db[TG+12+:21]}:32'd0;
    end
    always @(posedge clk or negedge rnx)
        if (!rnx) begin riv <= 1'b0; mrv <= 1'b0; mcol <= 1'b0; mwv <= 1'b0; end
        else begin
            mrv <= ml_rv;
            riv <= rr_dlv || mrv;
            mwv <= rr_land;
            if (rr_dlv && mrv) mcol <= 1'b1;            // replay against a cut-through beat
        end
    if(RX_SRAM!=0) begin:g_return_valid
        for(genvar rv=0;rv<4;rv=rv+1) begin:g_slice
            (* keep *) reg valid_r;
            always @(posedge clk or negedge rr[CTRL_RSTBASE+NL+3+rv])
                if(!rr[CTRL_RSTBASE+NL+3+rv]) valid_r<=0; else valid_r<=rr_dlv || mrv;
            assign mu_rt[8*rv+:8]=valid_r?rtq[8*rv+:8]:8'd0;
        end
    end else begin:g_return_legacy assign mu_rt=riv?rtq:32'd0;end
    assign ml_wv = mwv; assign ml_wd = mwd; assign mcol_w = mcol;
    end endgenerate
    always @(posedge clk or negedge rnx)
        if (!rnx) perr <= 1'b0;
        else begin
            if (|rxf) perr <= 1'b1;                    // a beat landed on a full RX FIFO (credit protocol broken)
            // a released pair must be one frame (equal sequence parity); a die endpoint accepts ring / HOST / KS only
            // (ring only at HOST_EN 0 and on pair B); both pairs releasing in one cycle is a collision
            if (rel && (h0[H] != h1[H] || (!active_ring_flags[1] && !hacc && !iacc && !qacc))) perr <= 1'b1;
            // S81/H4: a tree frame carries a valid beat whose lane matches the pair (pair B / PREV: lane 2, pair A: 3)
            if (rel && iacc && (!h0[4] || h0[9:8] != ((IDX_TP != 0 || rpb) ? 2'd2 : 2'd3))) perr <= 1'b1;   // TP: lane 2
            if (rel && qacc && !h0[4]) perr <= 1'b1;   // S81/IDXNET: a Q frame carries a valid word
            if (relp[0] && relp[1]) perr <= 1'b1;
        end
    generate if (HOST_EN != 0) begin : g_hrx
`ifdef OT_S81SL_LEP_MUT_KSOFF
    wire [52:0] ksp = h0[5 +: 53];                     // MUTANT: key-store payload read one bit off
`else
    wire [52:0] ksp = h0[4 +: 53];
`endif
    reg fh_v, fk_s; reg [513:0] fh_d; reg [51:0] fk_d; reg [3:0] lf;
    always @(posedge clk or negedge rnx)
        if (!rnx) begin fh_v <= 1'b0; fk_s <= 1'b0; end
        else begin
            fh_v <= rel && hacc && h0[3:1] == 3'd1;
            fk_s <= rel && hacc && h0[3:1] == 3'd2 && ksp[52];
        end
    if(SAFE_FIFO) begin:g_host_local
      wire [4:0] host_enable;wire key_enable;
      for(genvar hg=0;hg<5;hg=hg+1) begin:g_enable
        (* keep=1 *) ot_s81sl_lep_host_enable u_host(.ne0(rnex[0]),.ne1(rnex[1]),.hit(rhostx[0]),.en(host_enable[hg]));
      end
      (* keep=1 *) ot_s81sl_lep_host_enable u_key(.ne0(rnex[0]),.ne1(rnex[1]),.hit(rksx[0]),.en(key_enable));
      for(c=0;c<37;c=c+1) begin:g_slice
        (* keep="true" *) reg enable_r;
        wire hit=(c<33)?rhostx[0]:rksx[0];
        always @(posedge clk or negedge rr[HOST_RSTBASE+c])
          if(!rr[HOST_RSTBASE+c]) enable_r<=0;else enable_r<=(c<33)?host_enable[c/8]:key_enable;
        if(c<33) begin:g_host
          localparam integer LO=16*c,HSW=(514-LO<16)?514-LO:16;
          always @(posedge clk) if(enable_r) fh_d[LO+:HSW]<=h0[4+LO+:HSW];
        end else begin:g_key
          localparam integer LO=16*(c-33),KSW=(52-LO<16)?52-LO:16;
          always @(posedge clk) if(enable_r) fk_d[LO+:KSW]<=ksp[LO+:KSW];
        end
      end
    end else begin:g_host_legacy
      always @(posedge clk) begin
        if (rel && hacc && h0[3:1] == 3'd1) fh_d <= h0[4 +: 514];
        if (rel && hacc && h0[3:1] == 3'd2) fk_d <= ksp[51:0];
      end
    end
    always @(posedge clk) lf <= {l1_st[0] | (|l1_f), l1_st[1], l0_st[0] | (|l0_f), l0_st[1]};
    assign f_host = {fh_d, fh_v};
    assign f_ks = {fk_s, fk_d};
    assign f_lf = lf;
    end else begin : g_nhrx                            // HOST_EN 0: no host outputs (the _nh tops have no such ports)
    assign f_host = 515'd0; assign f_ks = 53'd0; assign f_lf = 4'd0;
    end endgenerate

    wire merr;                                         // S81/IDXNET: tm / ca merge collision (sticky)
    // ---------------------------------------------------------------- IDX tree frames, RX (IDX_EN 1; S81/H4 10-24)
    // The released frame's lane-0 head h0 (show-ahead flops) -> ih (data, no reset) and the pair selects -> kept reset
    // copies (<= 24 data bits each) on the same edge; ca / cb leave from flops one edge later: release -> ca / cb = 2 edges.
    // Pair B (from the PREV stage) -> ca, pair A (from NEXT) -> cb.  Idle = all-zero (the vmux reads valid-masked data).
    generate if (IDX_EN != 0) begin : g_irx
      localparam integer IJ = 12, IW = 23;             // 12 x 23 = 276 bits
      reg [275:0] ih, ca_q, cb_q;
      wire [IJ-1:0] sca, scb;
`ifdef OT_S81SL_LEP_MUT_IDXDMX
      wire to_ca = rel && iacc && (IDX_TP != 0 ? 1'b0 : !rpb);   // MUTANT: demux swapped
`else
      wire to_ca = rel && iacc && (IDX_TP != 0 || rpb);          // S81/IDXNET: a TP end hands every beat to ca
`endif
      wire to_cb = rel && iacc && !to_ca;
      always @(posedge clk) ih <= h0[4 +: 276];
      // S81/IDXNET (IDX_MRG 1): tm (the s_0S TP RX beats, a partition pin) -> pin flop tmp -> tmq + kept valid copies smc,
      // ORed into ca: tm pin -> ca 3 edges.  A tm beat and a pair-B tree beat in the same ca cycle is a sticky fault.
      wire [275:0] tmw; wire [IJ-1:0] smc;
      if (IDX_MRG != 0) begin : g_tm
        reg [275:0] tmp, tmq; reg me;
        always @(posedge clk) begin tmp <= tm; tmq <= tmp; end
        for (genvar j = 0; j < IJ; j = j + 1) begin : g_mc
`ifdef OT_S81SL_LEP_MUT_TPMRG
          (* keep=1 *) ot_s81sl_lep_idx_sel u_sm (.clk(clk), .rn(rnx), .d(1'b0), .q(smc[j]));   // MUTANT: tm never merged
`else
          (* keep=1 *) ot_s81sl_lep_idx_sel u_sm (.clk(clk), .rn(rnx), .d(tmp[0]), .q(smc[j]));
`endif
        end
        always @(posedge clk or negedge rnx) if (!rnx) me <= 1'b0; else if (smc[0] && sca[0]) me <= 1'b1;
        assign tmw = tmq; assign merr = me;
      end else begin : g_ntm
        assign tmw = 276'd0; assign smc = '0; assign merr = 1'b0;
      end
      for (genvar j = 0; j < IJ; j = j + 1) begin : g_j
        (* keep=1 *) ot_s81sl_lep_idx_sel u_sa (.clk(clk), .rn(rnx), .d(to_ca), .q(sca[j]));
        (* keep=1 *) ot_s81sl_lep_idx_sel u_sb (.clk(clk), .rn(rnx), .d(to_cb), .q(scb[j]));
        if (j == 0) begin : g_v
          always @(posedge clk or negedge rnx)
            if (!rnx) begin ca_q[0] <= 1'b0; cb_q[0] <= 1'b0; end
            else begin ca_q[0] <= (sca[0] && ih[0]) || (smc[0] && tmw[0]); cb_q[0] <= scb[0] && ih[0]; end
          always @(posedge clk) begin
            ca_q[IW-1:1] <= (ih[IW-1:1] & {(IW-1){sca[0]}}) | (tmw[IW-1:1] & {(IW-1){smc[0]}});
            cb_q[IW-1:1] <= ih[IW-1:1] & {(IW-1){scb[0]}};
          end
        end else begin : g_d
          always @(posedge clk) begin
            ca_q[j*IW +: IW] <= (ih[j*IW +: IW] & {IW{sca[j]}}) | (tmw[j*IW +: IW] & {IW{smc[j]}});
            cb_q[j*IW +: IW] <= ih[j*IW +: IW] & {IW{scb[j]}};
          end
        end
      end
      assign ca = ca_q; assign cb = cb_q;
    end else begin : g_nirx
      assign ca = 276'd0; assign cb = 276'd0; assign merr = 1'b0;
    end endgenerate

    // ---------------------------------------------------------------- Q frames, RX + relay (IDX_Q 1; S81/IDXNET 10-25)
    // S81 DECISION 2: the rank-tree query frame (dsdv_idx_qf type 10: header, spec words, query words; 513-b words {d, v})
    // walks the rank's shard dies NEXT-ward.  A Q word released from pair B (PREV) goes to ql (iqf; release -> ql 2 edges,
    // as ca) and, by the frame's header relay count RL = d[7:4] (compiler: k - 1 at the root, lower_bk), is cut-through
    // relayed to pair A: the header with RL - 1, then its len = d[491:480] words, while RL != 0.  The framer follows len; a
    // header that is not type 10 or has len 0 is a sticky fault.  Relay: release -> rw (S1) -> iq (S2) -> frame, so a
    // pass-through die costs the link + ~3 edges, not the iqf round trip.  iqf's own qc only carries the root's frames.
    generate if (QEN != 0) begin : g_qrx
      localparam integer QJ = 23, QW = 23;             // 23 x 23 >= 513
      wire [512:0] qd = h0[4 +: 513];
      wire to_ql = rel && qacc;
      reg [528:0] qh, qlq; wire [QJ-1:0] sq;
      always @(posedge clk) qh <= {16'd0, qd};
      for (genvar j = 0; j < QJ; j = j + 1) begin : g_j
        (* keep=1 *) ot_s81sl_lep_idx_sel u_sq (.clk(clk), .rn(rnx), .d(to_ql), .q(sq[j]));
        if (j == 0) begin : g_v
          always @(posedge clk or negedge rnx) if (!rnx) qlq[0] <= 1'b0; else qlq[0] <= sq[0] && qh[0];
          always @(posedge clk) qlq[QW-1:1] <= qh[QW-1:1] & {(QW-1){sq[0]}};
        end else begin : g_d
          always @(posedge clk) qlq[j*QW +: QW] <= qh[j*QW +: QW] & {QW{sq[j]}};
        end
      end
      assign ql = qlq[512:0];
      reg qin, qrel, qfe; reg [11:0] qleft;
      wire qhdr = to_ql && !qin;
      wire [3:0] qrl = qd[8:5];
      wire rly = to_ql && (qin ? qrel : (qrl != 4'd0));
      always @(posedge clk or negedge rnx)
        if (!rnx) begin qin <= 1'b0; qrel <= 1'b0; qleft <= 12'd0; qfe <= 1'b0; end
        else if (to_ql) begin
          if (!qin) begin
            qin <= qd[492:481] != 12'd0; qleft <= qd[492:481]; qrel <= qrl != 4'd0;
            if (qd[512:509] != 4'd10 || qd[492:481] == 12'd0) qfe <= 1'b1;
          end else begin
            qleft <= qleft - 12'd1;
            if (qleft == 12'd1) qin <= 1'b0;
          end
        end
      reg [512:0] rw_r;
`ifdef OT_S81SL_LEP_MUT_QRL
      always @(posedge clk) rw_r <= qd;                // MUTANT: relay count not decremented
`else
      always @(posedge clk) rw_r <= {qd[512:9], qhdr ? qrl - 4'd1 : qd[8:5], qd[4:0]};
`endif
      for (genvar vc = 0; vc < NVC; vc = vc + 1) begin : g_vc
        (* keep=1 *) ot_s81sl_lep_vcopy u_rv (.clk(clk), .d(rly), .q(rvy[vc]));
      end
      for (genvar sj = 0; sj < 17; sj = sj + 1) begin : g_rs
        (* keep=1 *) ot_s81sl_lep_vcopy u_rs (.clk(clk), .d(rly), .q(rsx[sj]));
      end
      assign rw = rw_r; assign qrerr = qfe;
    end else begin : g_nqrx
      assign ql = 513'd0; assign rw = 513'd0; assign rvy = '0; assign rsx = '0; assign qrerr = 1'b0;
    end endgenerate

    // ---------------------------------------------------------------- fault collector (sticky)
    wire mferr;
    generate if (MU_EN != 0) begin : g_mf
        reg mlfq;
        always @(posedge clk or negedge rn) if (!rn) mlfq <= 1'b0; else mlfq <= ml_f;
        assign mferr = terr || mcol_w || mlfq;
    end else begin : g_nmf
        assign mferr = 1'b0;
    end endgenerate
    wire [5:0] lfb_in;
    generate if (NL == 4) begin : g_lfb
        assign lfb_in = {l3_f, l2_f};
    end else begin : g_nlfb
        assign lfb_in = 6'd0;
    end endgenerate
    reg slq; reg [5:0] lfq, lfbq;
    always @(posedge clk or negedge rn)
        if (!rn) begin slq <= 1'b0; lfq <= 6'd0; lfbq <= 6'd0; fault <= 1'b0; end
        else begin
            slq <= sl_f; lfq <= {l1_f, l0_f}; lfbq <= lfb_in;
            if ((|ovf) || perr || herr || slq || (|lfq) || (|lfbq) || mferr || ie || merr) fault <= 1'b1;
        end
endmodule

// The hardened leaf tops.  ot_s81sl_lep / ot_s81sl_lep_nh: exactly the pre-MU ports and function (MU_EN 0, AB_EN 0;
// the MU ports of the core are unread / undriven there).  ot_s81sl_lep_mu: the multi-user endpoint (MU_EN 1).
module ot_s81sl_lep #(
    parameter integer DT = 512, parameter integer DR = 8, parameter integer CRED = 8, parameter integer SRAM = 1,
    parameter integer HOST_EN = 1, parameter integer NATIVE32_STD = 0
) (
    input  wire            clk,
    input  wire            rst_n,
    input  wire [1103:0]   ro,
    output wire [1103:0]   ri,
    output wire            lo0_v, input wire lo0_r, output wire [552:0] lo0_d,
    output wire            lo1_v, input wire lo1_r, output wire [552:0] lo1_d,
    input  wire            li0_v, output wire li0_r, input wire [552:0] li0_d,
    input  wire            li1_v, output wire li1_r, input wire [552:0] li1_d,
    output wire [1:0]      rxv,
    input  wire            sl_f,
    input  wire [2:0]      l0_f,
    input  wire [2:0]      l1_f,
    input  wire [1:0]      l0_st,
    input  wire [1:0]      l1_st,
    input  wire [76:0]     t_host,
    input  wire [53:0]     t_kd,
    output wire [514:0]    f_host,
    output wire [3:0]      f_lf,
    output wire [52:0]     f_ks,
    output wire            fault
);
    ot_s81sl_lep_core #(.DT(DT), .DR(DR), .CRED(CRED), .SRAM(SRAM), .HOST_EN(HOST_EN), .MU_EN(0), .AB_EN(0), .NATIVE32_STD(NATIVE32_STD), .RX_SRAM(NATIVE32_STD), .IN_PIPE(NATIVE32_STD)) u (
        .clk(clk), .rst_n(rst_n), .ro(ro), .ri(ri),
        .lo0_v(lo0_v), .lo0_r(lo0_r), .lo0_d(lo0_d), .lo1_v(lo1_v), .lo1_r(lo1_r), .lo1_d(lo1_d),
        .li0_v(li0_v), .li0_r(li0_r), .li0_d(li0_d), .li1_v(li1_v), .li1_r(li1_r), .li1_d(li1_d), .rxv(rxv),
        .sl_f(sl_f), .l0_f(l0_f), .l1_f(l1_f), .l0_st(l0_st), .l1_st(l1_st),
        .t_host(t_host), .t_kd(t_kd), .f_host(f_host), .f_lf(f_lf), .f_ks(f_ks),
        // MU / pair-B ports: unread at MU_EN 0 / AB_EN 0 (generate), outputs constant 0
        .mu_c(34'd0), .mu_rt(), .ml_wv(), .ml_wd(), .ml_rv(1'b0), .ml_rd(1104'd0), .ml_f(1'b0),
        .lo2_v(), .lo2_r(1'b0), .lo2_d(), .lo3_v(), .lo3_r(1'b0), .lo3_d(),
        .li2_v(1'b0), .li2_r(), .li2_d(553'd0), .li3_v(1'b0), .li3_r(), .li3_d(553'd0), .rxvb(), .l2_f(3'd0), .l3_f(3'd0),
        .fault(fault));
endmodule

// HOST_EN = 0 leaf top (hardened master of the three host-less endpoints s_0S / s_0N / s_7S): no host ports
module ot_s81sl_lep_nh #(
    parameter integer DT = 512, parameter integer DR = 8, parameter integer CRED = 8, parameter integer SRAM = 1, parameter integer NATIVE32_STD = 0
) (
    input  wire            clk,
    input  wire            rst_n,
    input  wire [1103:0]   ro,
    output wire [1103:0]   ri,
    output wire            lo0_v, input wire lo0_r, output wire [552:0] lo0_d,
    output wire            lo1_v, input wire lo1_r, output wire [552:0] lo1_d,
    input  wire            li0_v, output wire li0_r, input wire [552:0] li0_d,
    input  wire            li1_v, output wire li1_r, input wire [552:0] li1_d,
    output wire [1:0]      rxv,
    input  wire            sl_f,
    input  wire [2:0]      l0_f,
    input  wire [2:0]      l1_f,
    output wire            fault
);
    // no l0_st / l1_st: the PHY lane status feeds only f_lf (host plane) at HOST_EN 1 (the lane tiles still take it in
    // their rx word, and lane faults reach the fault collector through l0_f / l1_f).  The core reads none of t_host / t_kd /
    // l*_st at HOST_EN 0 (generate), so these constants are not logic: synthesis of this top keeps no host pin or flop.
    ot_s81sl_lep_core #(.DT(DT), .DR(DR), .CRED(CRED), .SRAM(SRAM), .HOST_EN(0), .MU_EN(0), .AB_EN(0), .NATIVE32_STD(NATIVE32_STD), .RX_SRAM(NATIVE32_STD), .IN_PIPE(NATIVE32_STD)) u (
        .clk(clk), .rst_n(rst_n), .ro(ro), .ri(ri),
        .lo0_v(lo0_v), .lo0_r(lo0_r), .lo0_d(lo0_d), .lo1_v(lo1_v), .lo1_r(lo1_r), .lo1_d(lo1_d),
        .li0_v(li0_v), .li0_r(li0_r), .li0_d(li0_d), .li1_v(li1_v), .li1_r(li1_r), .li1_d(li1_d), .rxv(rxv),
        .sl_f(sl_f), .l0_f(l0_f), .l1_f(l1_f), .l0_st(2'b00), .l1_st(2'b00),
        .t_host(77'd0), .t_kd(54'd0), .f_host(), .f_lf(), .f_ks(),
        .mu_c(34'd0), .mu_rt(), .ml_wv(), .ml_wd(), .ml_rv(1'b0), .ml_rd(1104'd0), .ml_f(1'b0),
        .lo2_v(), .lo2_r(1'b0), .lo2_d(), .lo3_v(), .lo3_r(1'b0), .lo3_d(),
        .li2_v(1'b0), .li2_r(), .li2_d(553'd0), .li3_v(1'b0), .li3_r(), .li3_d(553'd0), .rxvb(), .l2_f(3'd0), .l3_f(3'd0),
        .fault(fault));
endmodule

// MU leaf top (MU_EN 1): every port of the core.  AB_EN 1 = the endpoint of a stage before / after a duplicated group
// (pre-group: TX copy select; post-group: RX merge of copy B); HOST_EN as the plain tops.  A die master that does not
// carry the host plane (HOST_EN 0) or pair B (AB_EN 0) gets its own parameter-free top when the die lead adopts it
// (the core leaves those ports unread / 0, as ot_s81sl_lep_nh).
module ot_s81sl_lep_mu #(
    parameter integer DT = 512, parameter integer DR = 8, parameter integer CRED = 8, parameter integer SRAM = 1,
    parameter integer HOST_EN = 0, parameter integer AB_EN = 1, parameter integer NB = 80, parameter integer RX_SRAM = 0
) (
    input  wire            clk,
    input  wire            rst_n,
    input  wire [1103:0]   ro,
    output wire [1103:0]   ri,
    output wire            lo0_v, input wire lo0_r, output wire [552:0] lo0_d,
    output wire            lo1_v, input wire lo1_r, output wire [552:0] lo1_d,
    input  wire            li0_v, output wire li0_r, input wire [552:0] li0_d,
    input  wire            li1_v, output wire li1_r, input wire [552:0] li1_d,
    output wire [1:0]      rxv,
    input  wire            sl_f,
    input  wire [2:0]      l0_f,
    input  wire [2:0]      l1_f,
    input  wire [1:0]      l0_st,
    input  wire [1:0]      l1_st,
    input  wire [76:0]     t_host,
    input  wire [53:0]     t_kd,
    output wire [514:0]    f_host,
    output wire [3:0]      f_lf,
    output wire [52:0]     f_ks,
    input  wire [33:0]     mu_c,
    output wire [31:0]     mu_rt,
    output wire            ml_wv,
    output wire [1103:0]   ml_wd,
    input  wire            ml_rv,
    input  wire [1103:0]   ml_rd,
    input  wire            ml_f,
    output wire            lo2_v, input wire lo2_r, output wire [552:0] lo2_d,
    output wire            lo3_v, input wire lo3_r, output wire [552:0] lo3_d,
    input  wire            li2_v, output wire li2_r, input wire [552:0] li2_d,
    input  wire            li3_v, output wire li3_r, input wire [552:0] li3_d,
    output wire [1:0]      rxvb,
    input  wire [2:0]      l2_f,
    input  wire [2:0]      l3_f,
    output wire            fault
);
    ot_s81sl_lep_core #(.DT(DT), .DR(DR), .CRED(CRED), .SRAM(SRAM), .HOST_EN(HOST_EN), .MU_EN(1), .RX_SRAM(RX_SRAM), .AB_EN(AB_EN), .NB(NB)) u (
        .clk(clk), .rst_n(rst_n), .ro(ro), .ri(ri),
        .lo0_v(lo0_v), .lo0_r(lo0_r), .lo0_d(lo0_d), .lo1_v(lo1_v), .lo1_r(lo1_r), .lo1_d(lo1_d),
        .li0_v(li0_v), .li0_r(li0_r), .li0_d(li0_d), .li1_v(li1_v), .li1_r(li1_r), .li1_d(li1_d), .rxv(rxv),
        .sl_f(sl_f), .l0_f(l0_f), .l1_f(l1_f), .l0_st(l0_st), .l1_st(l1_st),
        .t_host(t_host), .t_kd(t_kd), .f_host(f_host), .f_lf(f_lf), .f_ks(f_ks),
        .mu_c(mu_c), .mu_rt(mu_rt), .ml_wv(ml_wv), .ml_wd(ml_wd), .ml_rv(ml_rv), .ml_rd(ml_rd), .ml_f(ml_f),
        .lo2_v(lo2_v), .lo2_r(lo2_r), .lo2_d(lo2_d), .lo3_v(lo3_v), .lo3_r(lo3_r), .lo3_d(lo3_d),
        .li2_v(li2_v), .li2_r(li2_r), .li2_d(li2_d), .li3_v(li3_v), .li3_r(li3_r), .li3_d(li3_d), .rxvb(rxvb),
        .l2_f(l2_f), .l3_f(l3_f), .fault(fault));
endmodule

// MU-S81/KIT (2026-10-19): hardened master of the copy A/B endpoint WITHOUT the host plane (kit s81sl_lepmu): MU_EN 1,
// AB_EN 1, HOST_EN 0.  Same core and cycles as ot_s81sl_lep_mu #(.HOST_EN(0), .AB_EN(1)); the host ports (t_host / t_kd
// in, f_host / f_lf / f_ks out) and l0_st / l1_st are not ports (the core reads none of them at HOST_EN 0, generate), so
// the hard block carries no tied pad and no constant output.  Faces (kit): W lanes A, S lanes B, N landing (dsdv_mu_land),
// E ring + mu_c / mu_rt.
module ot_s81sl_lep_mu_ab #(
    parameter integer DT = 512, parameter integer DR = 8, parameter integer CRED = 8, parameter integer SRAM = 1,
    parameter integer NB = 80, parameter integer RX_SRAM = 0, parameter integer IN_PIPE = 0, parameter integer NATIVE32 = 0
) (
    input  wire            clk,
    input  wire            rst_n,
    input  wire [1103:0]   ro,
    output wire [1103:0]   ri,
    output wire            lo0_v, input wire lo0_r, output wire [552:0] lo0_d,
    output wire            lo1_v, input wire lo1_r, output wire [552:0] lo1_d,
    input  wire            li0_v, output wire li0_r, input wire [552:0] li0_d,
    input  wire            li1_v, output wire li1_r, input wire [552:0] li1_d,
    output wire [1:0]      rxv,
    input  wire            sl_f,
    input  wire [2:0]      l0_f,
    input  wire [2:0]      l1_f,
    input  wire [33:0]     mu_c,
    output wire [31:0]     mu_rt,
    output wire            ml_wv,
    output wire [1103:0]   ml_wd,
    input  wire            ml_rv,
    input  wire [1103:0]   ml_rd,
    input  wire            ml_f,
    output wire            lo2_v, input wire lo2_r, output wire [552:0] lo2_d,
    output wire            lo3_v, input wire lo3_r, output wire [552:0] lo3_d,
    input  wire            li2_v, output wire li2_r, input wire [552:0] li2_d,
    input  wire            li3_v, output wire li3_r, input wire [552:0] li3_d,
    output wire [1:0]      rxvb,
    input  wire [2:0]      l2_f,
    input  wire [2:0]      l3_f,
    output wire            fault
);
    ot_s81sl_lep_core #(.DT(DT), .DR(DR), .CRED(CRED), .SRAM(SRAM), .HOST_EN(0), .MU_EN(1), .RX_SRAM(RX_SRAM), .AB_EN(1), .NB(NB),
        .IN_PIPE(IN_PIPE), .NATIVE32(NATIVE32)) u (   // L5B-LEPMU 10-21: native32 / face-stage opt-ins exposed (defaults 0 = unchanged)
        .clk(clk), .rst_n(rst_n), .ro(ro), .ri(ri),
        .lo0_v(lo0_v), .lo0_r(lo0_r), .lo0_d(lo0_d), .lo1_v(lo1_v), .lo1_r(lo1_r), .lo1_d(lo1_d),
        .li0_v(li0_v), .li0_r(li0_r), .li0_d(li0_d), .li1_v(li1_v), .li1_r(li1_r), .li1_d(li1_d), .rxv(rxv),
        .sl_f(sl_f), .l0_f(l0_f), .l1_f(l1_f), .l0_st(2'b00), .l1_st(2'b00),
        .t_host(77'd0), .t_kd(54'd0), .f_host(), .f_lf(), .f_ks(),
        .mu_c(mu_c), .mu_rt(mu_rt), .ml_wv(ml_wv), .ml_wd(ml_wd), .ml_rv(ml_rv), .ml_rd(ml_rd), .ml_f(ml_f),
        .lo2_v(lo2_v), .lo2_r(lo2_r), .lo2_d(lo2_d), .lo3_v(lo3_v), .lo3_r(lo3_r), .lo3_d(lo3_d),
        .li2_v(li2_v), .li2_r(li2_r), .li2_d(li2_d), .li3_v(li3_v), .li3_r(li3_r), .li3_d(li3_d), .rxvb(rxvb),
        .l2_f(l2_f), .l3_f(l3_f), .fault(fault));
endmodule

// S81/H4 (2026-10-24, COORD H4 ruling option A): the s_0N copy-A/B endpoint WITH the index rank-tree frames.  Exactly
// ot_s81sl_lep_mu_ab plus IDX_EN 1 and the three tree ports: tl (276, <- bk_sel tl_o over the die lane tl__bk_sel__s_0N_LP),
// ca / cb (276, -> bk_sel ca / cb over the lanes ca__ / cb__s_0N_LP__bk_sel).  Tree frame = one non-ring link frame on the
// stage circuit picked by the beat's lane field (2 -> pair A / NEXT, 3 -> pair B / PREV); received pair B -> ca, pair A ->
// cb.  Edges: tl pin -> frame push 3 (IN_PIPE 1: pin flop tlp + face stage tlq + iq_r), FIFO -> lo 3 (TXRP), lanes / link elastic
// (off-die boundary), RX release -> ca / cb 2.  Faces (kit): as ot_s81sl_lep_mu_ab + tl / ca / cb on the E (ring) face.
module ot_s81sl_lep_mu_ab_idx #(
    parameter integer DT = 512, parameter integer DR = 8, parameter integer CRED = 8, parameter integer SRAM = 1,
    parameter integer NB = 80, parameter integer RX_SRAM = 0, parameter integer IN_PIPE = 0, parameter integer NATIVE32 = 0
) (
    input  wire            clk,
    input  wire            rst_n,
    input  wire [1103:0]   ro,
    output wire [1103:0]   ri,
    output wire            lo0_v, input wire lo0_r, output wire [552:0] lo0_d,
    output wire            lo1_v, input wire lo1_r, output wire [552:0] lo1_d,
    input  wire            li0_v, output wire li0_r, input wire [552:0] li0_d,
    input  wire            li1_v, output wire li1_r, input wire [552:0] li1_d,
    output wire [1:0]      rxv,
    input  wire            sl_f,
    input  wire [2:0]      l0_f,
    input  wire [2:0]      l1_f,
    input  wire [33:0]     mu_c,
    output wire [31:0]     mu_rt,
    output wire            ml_wv,
    output wire [1103:0]   ml_wd,
    input  wire            ml_rv,
    input  wire [1103:0]   ml_rd,
    input  wire            ml_f,
    output wire            lo2_v, input wire lo2_r, output wire [552:0] lo2_d,
    output wire            lo3_v, input wire lo3_r, output wire [552:0] lo3_d,
    input  wire            li2_v, output wire li2_r, input wire [552:0] li2_d,
    input  wire            li3_v, output wire li3_r, input wire [552:0] li3_d,
    output wire [1:0]      rxvb,
    input  wire [2:0]      l2_f,
    input  wire [2:0]      l3_f,
    output wire            fault,
    input  wire [275:0]    tl,
    output wire [275:0]    ca,
    output wire [275:0]    cb
);
    ot_s81sl_lep_core #(.DT(DT), .DR(DR), .CRED(CRED), .SRAM(SRAM), .HOST_EN(0), .MU_EN(1), .RX_SRAM(RX_SRAM), .AB_EN(1), .NB(NB),
        .IN_PIPE(IN_PIPE), .NATIVE32(NATIVE32), .IDX_EN(1)) u (   // L5B-LEPMU 10-21: native32 / face-stage opt-ins exposed (defaults 0 = unchanged)
        .clk(clk), .rst_n(rst_n), .ro(ro), .ri(ri),
        .lo0_v(lo0_v), .lo0_r(lo0_r), .lo0_d(lo0_d), .lo1_v(lo1_v), .lo1_r(lo1_r), .lo1_d(lo1_d),
        .li0_v(li0_v), .li0_r(li0_r), .li0_d(li0_d), .li1_v(li1_v), .li1_r(li1_r), .li1_d(li1_d), .rxv(rxv),
        .sl_f(sl_f), .l0_f(l0_f), .l1_f(l1_f), .l0_st(2'b00), .l1_st(2'b00),
        .t_host(77'd0), .t_kd(54'd0), .f_host(), .f_lf(), .f_ks(),
        .mu_c(mu_c), .mu_rt(mu_rt), .ml_wv(ml_wv), .ml_wd(ml_wd), .ml_rv(ml_rv), .ml_rd(ml_rd), .ml_f(ml_f),
        .lo2_v(lo2_v), .lo2_r(lo2_r), .lo2_d(lo2_d), .lo3_v(lo3_v), .lo3_r(lo3_r), .lo3_d(lo3_d),
        .li2_v(li2_v), .li2_r(li2_r), .li2_d(li2_d), .li3_v(li3_v), .li3_r(li3_r), .li3_d(li3_d), .rxvb(rxvb),
        .l2_f(l2_f), .l3_f(l3_f), .fault(fault), .tl(tl), .ca(ca), .cb(cb));
endmodule

// S81/IDXNET (2026-10-25, S81 DECISIONS 1 + 2): the s_0N copy-A/B endpoint = ot_s81sl_lep_mu_ab_idx + tm (the s_0S TP RX
// beats of topk_final step 2, merged into ca: tm pin -> ca 3 edges) + the rank-tree query frames: qc (iqf, 2-beat 258 b) ->
// Q frame (type 6) on pair A (qc beat 1 pin -> frame push 3 edges), pair-B Q words -> ql (release -> ql 2 edges) and the
// cut-through relay to pair A while the header relay count is non-zero (release -> frame push 3 edges).
module ot_s81sl_lep_mu_ab_idxq #(
    parameter integer DT = 512, parameter integer DR = 8, parameter integer CRED = 8, parameter integer SRAM = 1,
    parameter integer NB = 80, parameter integer RX_SRAM = 0, parameter integer IN_PIPE = 0, parameter integer NATIVE32 = 0
) (
    input  wire            clk,
    input  wire            rst_n,
    input  wire [1103:0]   ro,
    output wire [1103:0]   ri,
    output wire            lo0_v, input wire lo0_r, output wire [552:0] lo0_d,
    output wire            lo1_v, input wire lo1_r, output wire [552:0] lo1_d,
    input  wire            li0_v, output wire li0_r, input wire [552:0] li0_d,
    input  wire            li1_v, output wire li1_r, input wire [552:0] li1_d,
    output wire [1:0]      rxv,
    input  wire            sl_f,
    input  wire [2:0]      l0_f,
    input  wire [2:0]      l1_f,
    input  wire [33:0]     mu_c,
    output wire [31:0]     mu_rt,
    output wire            ml_wv,
    output wire [1103:0]   ml_wd,
    input  wire            ml_rv,
    input  wire [1103:0]   ml_rd,
    input  wire            ml_f,
    output wire            lo2_v, input wire lo2_r, output wire [552:0] lo2_d,
    output wire            lo3_v, input wire lo3_r, output wire [552:0] lo3_d,
    input  wire            li2_v, output wire li2_r, input wire [552:0] li2_d,
    input  wire            li3_v, output wire li3_r, input wire [552:0] li3_d,
    output wire [1:0]      rxvb,
    input  wire [2:0]      l2_f,
    input  wire [2:0]      l3_f,
    output wire            fault,
    input  wire [275:0]    tl,
    output wire [275:0]    ca,
    output wire [275:0]    cb,
    input  wire [275:0]    tm,
    input  wire [257:0]    qc,
    output wire [512:0]    ql
);
    ot_s81sl_lep_core #(.DT(DT), .DR(DR), .CRED(CRED), .SRAM(SRAM), .HOST_EN(0), .MU_EN(1), .RX_SRAM(RX_SRAM), .AB_EN(1), .NB(NB),
        .IN_PIPE(IN_PIPE), .NATIVE32(NATIVE32), .IDX_EN(1), .IDX_MRG(1), .IDX_Q(1)) u (   // L5B-LEPMU 10-21: native32 / face-stage opt-ins exposed (defaults 0 = unchanged)
        .clk(clk), .rst_n(rst_n), .ro(ro), .ri(ri),
        .lo0_v(lo0_v), .lo0_r(lo0_r), .lo0_d(lo0_d), .lo1_v(lo1_v), .lo1_r(lo1_r), .lo1_d(lo1_d),
        .li0_v(li0_v), .li0_r(li0_r), .li0_d(li0_d), .li1_v(li1_v), .li1_r(li1_r), .li1_d(li1_d), .rxv(rxv),
        .sl_f(sl_f), .l0_f(l0_f), .l1_f(l1_f), .l0_st(2'b00), .l1_st(2'b00),
        .t_host(77'd0), .t_kd(54'd0), .f_host(), .f_lf(), .f_ks(),
        .mu_c(mu_c), .mu_rt(mu_rt), .ml_wv(ml_wv), .ml_wd(ml_wd), .ml_rv(ml_rv), .ml_rd(ml_rd), .ml_f(ml_f),
        .lo2_v(lo2_v), .lo2_r(lo2_r), .lo2_d(lo2_d), .lo3_v(lo3_v), .lo3_r(lo3_r), .lo3_d(lo3_d),
        .li2_v(li2_v), .li2_r(li2_r), .li2_d(li2_d), .li3_v(li3_v), .li3_r(li3_r), .li3_d(li3_d), .rxvb(rxvb),
        .l2_f(l2_f), .l3_f(l3_f), .fault(fault), .tl(tl), .ca(ca), .cb(cb), .tm(tm), .qc(qc), .ql(ql));
endmodule

// S81/IDXNET (2026-10-25, S81 DECISION 1, topk_final step 1): s_7N host-plane endpoint + the TP4 d+2 exchange: tp_i (<- bk_sel
// tpn_o) -> type-5 frame on pair A (lane 2 required; tp_i pin -> frame push 3 edges), received type-5 frames (pair A) -> tp_o
// (-> bk_sel tpn_i; release -> tp_o 2 edges).  Otherwise exactly ot_s81sl_lep_mu_h.
module ot_s81sl_lep_mu_h_tp #(
    parameter integer DT = 512, parameter integer DR = 8, parameter integer CRED = 8, parameter integer SRAM = 1,
    parameter integer NB = 80, parameter integer RX_SRAM = 0, parameter integer IN_PIPE = 0, parameter integer NATIVE32 = 0
) (
    input  wire            clk,
    input  wire            rst_n,
    input  wire [1103:0]   ro,
    output wire [1103:0]   ri,
    output wire            lo0_v, input wire lo0_r, output wire [552:0] lo0_d,
    output wire            lo1_v, input wire lo1_r, output wire [552:0] lo1_d,
    input  wire            li0_v, output wire li0_r, input wire [552:0] li0_d,
    input  wire            li1_v, output wire li1_r, input wire [552:0] li1_d,
    output wire [1:0]      rxv,
    input  wire            sl_f,
    input  wire [2:0]      l0_f,
    input  wire [2:0]      l1_f,
    input  wire [1:0]      l0_st,
    input  wire [1:0]      l1_st,
    input  wire [76:0]     t_host,
    input  wire [53:0]     t_kd,
    output wire [514:0]    f_host,
    output wire [3:0]      f_lf,
    output wire [52:0]     f_ks,
    input  wire [33:0]     mu_c,
    output wire [31:0]     mu_rt,
    output wire            ml_wv,
    output wire [1103:0]   ml_wd,
    input  wire            ml_rv,
    input  wire [1103:0]   ml_rd,
    input  wire            ml_f,
    output wire            fault,
    input  wire [275:0]    tp_i,
    output wire [275:0]    tp_o
);
    ot_s81sl_lep_core #(.DT(DT), .DR(DR), .CRED(CRED), .SRAM(SRAM), .HOST_EN(1), .MU_EN(1), .RX_SRAM(RX_SRAM), .AB_EN(0), .NB(NB), .IN_PIPE(IN_PIPE), .NATIVE32(NATIVE32), .IDX_EN(1), .IDX_TP(1)) u (
        .clk(clk), .rst_n(rst_n), .ro(ro), .ri(ri),
        .lo0_v(lo0_v), .lo0_r(lo0_r), .lo0_d(lo0_d), .lo1_v(lo1_v), .lo1_r(lo1_r), .lo1_d(lo1_d),
        .li0_v(li0_v), .li0_r(li0_r), .li0_d(li0_d), .li1_v(li1_v), .li1_r(li1_r), .li1_d(li1_d), .rxv(rxv),
        .sl_f(sl_f), .l0_f(l0_f), .l1_f(l1_f), .l0_st(l0_st), .l1_st(l1_st),
        .t_host(t_host), .t_kd(t_kd), .f_host(f_host), .f_lf(f_lf), .f_ks(f_ks),
        .mu_c(mu_c), .mu_rt(mu_rt), .ml_wv(ml_wv), .ml_wd(ml_wd), .ml_rv(ml_rv), .ml_rd(ml_rd), .ml_f(ml_f),
        .lo2_v(), .lo2_r(1'b0), .lo2_d(), .lo3_v(), .lo3_r(1'b0), .lo3_d(),
        .li2_v(1'b0), .li2_r(), .li2_d(553'd0), .li3_v(1'b0), .li3_r(), .li3_d(553'd0), .rxvb(),
        .l2_f(3'd0), .l3_f(3'd0), .fault(fault), .tl(tp_i), .ca(tp_o), .cb());
endmodule

// HOST + reserve copy-B + TP4 step1: no functional pair-B port is removed.
module ot_s81sl_lep_mu_hab_tp #(
    parameter integer DT = 512, parameter integer DR = 8, parameter integer CRED = 8, parameter integer SRAM = 1,
    parameter integer NB = 80, parameter integer RX_SRAM = 0, parameter integer IN_PIPE = 0, parameter integer NATIVE32 = 0
) (
    input  wire            clk,
    input  wire            rst_n,
    input  wire [1103:0]   ro,
    output wire [1103:0]   ri,
    output wire            lo0_v, input wire lo0_r, output wire [552:0] lo0_d,
    output wire            lo1_v, input wire lo1_r, output wire [552:0] lo1_d,
    input  wire            li0_v, output wire li0_r, input wire [552:0] li0_d,
    input  wire            li1_v, output wire li1_r, input wire [552:0] li1_d,
    output wire [1:0]      rxv,
    input  wire            sl_f,
    input  wire [2:0]      l0_f,
    input  wire [2:0]      l1_f,
    input  wire [1:0]      l0_st,
    input  wire [1:0]      l1_st,
    input  wire [76:0]     t_host,
    input  wire [53:0]     t_kd,
    output wire [514:0]    f_host,
    output wire [3:0]      f_lf,
    output wire [52:0]     f_ks,
    input  wire [33:0]     mu_c,
    output wire [31:0]     mu_rt,
    output wire            ml_wv,
    output wire [1103:0]   ml_wd,
    input  wire            ml_rv,
    input  wire [1103:0]   ml_rd,
    input  wire            ml_f,
    output wire            lo2_v, input wire lo2_r, output wire [552:0] lo2_d,
    output wire            lo3_v, input wire lo3_r, output wire [552:0] lo3_d,
    input  wire            li2_v, output wire li2_r, input wire [552:0] li2_d,
    input  wire            li3_v, output wire li3_r, input wire [552:0] li3_d,
    output wire [1:0]      rxvb,
    input  wire [2:0]      l2_f,
    input  wire [2:0]      l3_f,
    output wire            fault,
    input wire [275:0]     tp_i,
    output wire [275:0]    tp_o
);
    ot_s81sl_lep_core #(.DT(DT), .DR(DR), .CRED(CRED), .SRAM(SRAM), .HOST_EN(1), .MU_EN(1), .RX_SRAM(RX_SRAM), .AB_EN(1), .NB(NB),
        .IN_PIPE(IN_PIPE), .NATIVE32(NATIVE32), .IDX_EN(1), .IDX_TP(1)) u (
        .clk(clk), .rst_n(rst_n), .ro(ro), .ri(ri),
        .lo0_v(lo0_v), .lo0_r(lo0_r), .lo0_d(lo0_d), .lo1_v(lo1_v), .lo1_r(lo1_r), .lo1_d(lo1_d),
        .li0_v(li0_v), .li0_r(li0_r), .li0_d(li0_d), .li1_v(li1_v), .li1_r(li1_r), .li1_d(li1_d), .rxv(rxv),
        .sl_f(sl_f), .l0_f(l0_f), .l1_f(l1_f), .l0_st(l0_st), .l1_st(l1_st),
        .t_host(t_host), .t_kd(t_kd), .f_host(f_host), .f_lf(f_lf), .f_ks(f_ks),
        .mu_c(mu_c), .mu_rt(mu_rt), .ml_wv(ml_wv), .ml_wd(ml_wd), .ml_rv(ml_rv), .ml_rd(ml_rd), .ml_f(ml_f),
        .lo2_v(lo2_v), .lo2_r(lo2_r), .lo2_d(lo2_d), .lo3_v(lo3_v), .lo3_r(lo3_r), .lo3_d(lo3_d),
        .li2_v(li2_v), .li2_r(li2_r), .li2_d(li2_d), .li3_v(li3_v), .li3_r(li3_r), .li3_d(li3_d), .rxvb(rxvb),
        .l2_f(l2_f), .l3_f(l3_f), .fault(fault), .tl(tp_i), .ca(tp_o), .cb());
endmodule

// S81/IDXNET (2026-10-25, S81 DECISION 1, topk_final step 2 TX): s_7S endpoint + TP4 TX to d+1: tp_i (<- bk_sel tps_o) ->
// type-5 frame on pair A (lane 2).  A received type-5 frame is a protocol fault (nothing is sent to an s_7S).
module ot_s81sl_lep_mu_a_tpt #(
    parameter integer DT = 512, parameter integer DR = 8, parameter integer CRED = 8, parameter integer SRAM = 1,
    parameter integer NB = 80, parameter integer RX_SRAM = 0, parameter integer IN_PIPE = 0, parameter integer NATIVE32 = 0
) (
    input  wire            clk,
    input  wire            rst_n,
    input  wire [1103:0]   ro,
    output wire [1103:0]   ri,
    output wire            lo0_v, input wire lo0_r, output wire [552:0] lo0_d,
    output wire            lo1_v, input wire lo1_r, output wire [552:0] lo1_d,
    input  wire            li0_v, output wire li0_r, input wire [552:0] li0_d,
    input  wire            li1_v, output wire li1_r, input wire [552:0] li1_d,
    output wire [1:0]      rxv,
    input  wire            sl_f,
    input  wire [2:0]      l0_f,
    input  wire [2:0]      l1_f,
    input  wire [33:0]     mu_c,
    output wire [31:0]     mu_rt,
    output wire            ml_wv,
    output wire [1103:0]   ml_wd,
    input  wire            ml_rv,
    input  wire [1103:0]   ml_rd,
    input  wire            ml_f,
    output wire            fault,
    input  wire [275:0]    tp_i
);
    ot_s81sl_lep_core #(.DT(DT), .DR(DR), .CRED(CRED), .SRAM(SRAM), .HOST_EN(0), .MU_EN(1), .RX_SRAM(RX_SRAM), .AB_EN(0), .NB(NB), .IN_PIPE(IN_PIPE), .NATIVE32(NATIVE32), .IDX_EN(1), .IDX_TP(2)) u (
        .clk(clk), .rst_n(rst_n), .ro(ro), .ri(ri),
        .lo0_v(lo0_v), .lo0_r(lo0_r), .lo0_d(lo0_d), .lo1_v(lo1_v), .lo1_r(lo1_r), .lo1_d(lo1_d),
        .li0_v(li0_v), .li0_r(li0_r), .li0_d(li0_d), .li1_v(li1_v), .li1_r(li1_r), .li1_d(li1_d), .rxv(rxv),
        .sl_f(sl_f), .l0_f(l0_f), .l1_f(l1_f), .l0_st(2'b00), .l1_st(2'b00),
        .t_host(77'd0), .t_kd(54'd0), .f_host(), .f_lf(), .f_ks(),
        .mu_c(mu_c), .mu_rt(mu_rt), .ml_wv(ml_wv), .ml_wd(ml_wd), .ml_rv(ml_rv), .ml_rd(ml_rd), .ml_f(ml_f),
        .lo2_v(), .lo2_r(1'b0), .lo2_d(), .lo3_v(), .lo3_r(1'b0), .lo3_d(),
        .li2_v(1'b0), .li2_r(), .li2_d(553'd0), .li3_v(1'b0), .li3_r(), .li3_d(553'd0), .rxvb(),
        .l2_f(3'd0), .l3_f(3'd0), .fault(fault), .tl(tp_i), .ca(), .cb());
endmodule

// S81/IDXNET (2026-10-25, S81 DECISION 1, topk_final step 2 RX): s_0S endpoint + TP4 RX from d-1: received type-5 frames
// (pair A, lane 2) -> tp_o (-> s_0N lep tm; release -> tp_o 2 edges).  This end sends no tree frame (tl unread: IDX_TP 3).
module ot_s81sl_lep_mu_a_tpr #(
    parameter integer DT = 512, parameter integer DR = 8, parameter integer CRED = 8, parameter integer SRAM = 1,
    parameter integer NB = 80, parameter integer RX_SRAM = 0, parameter integer IN_PIPE = 0, parameter integer NATIVE32 = 0
) (
    input  wire            clk,
    input  wire            rst_n,
    input  wire [1103:0]   ro,
    output wire [1103:0]   ri,
    output wire            lo0_v, input wire lo0_r, output wire [552:0] lo0_d,
    output wire            lo1_v, input wire lo1_r, output wire [552:0] lo1_d,
    input  wire            li0_v, output wire li0_r, input wire [552:0] li0_d,
    input  wire            li1_v, output wire li1_r, input wire [552:0] li1_d,
    output wire [1:0]      rxv,
    input  wire            sl_f,
    input  wire [2:0]      l0_f,
    input  wire [2:0]      l1_f,
    input  wire [33:0]     mu_c,
    output wire [31:0]     mu_rt,
    output wire            ml_wv,
    output wire [1103:0]   ml_wd,
    input  wire            ml_rv,
    input  wire [1103:0]   ml_rd,
    input  wire            ml_f,
    output wire            fault,
    output wire [275:0]    tp_o
);
    ot_s81sl_lep_core #(.DT(DT), .DR(DR), .CRED(CRED), .SRAM(SRAM), .HOST_EN(0), .MU_EN(1), .RX_SRAM(RX_SRAM), .AB_EN(0), .NB(NB), .IN_PIPE(IN_PIPE), .NATIVE32(NATIVE32), .IDX_EN(1), .IDX_TP(3)) u (
        .clk(clk), .rst_n(rst_n), .ro(ro), .ri(ri),
        .lo0_v(lo0_v), .lo0_r(lo0_r), .lo0_d(lo0_d), .lo1_v(lo1_v), .lo1_r(lo1_r), .lo1_d(lo1_d),
        .li0_v(li0_v), .li0_r(li0_r), .li0_d(li0_d), .li1_v(li1_v), .li1_r(li1_r), .li1_d(li1_d), .rxv(rxv),
        .sl_f(sl_f), .l0_f(l0_f), .l1_f(l1_f), .l0_st(2'b00), .l1_st(2'b00),
        .t_host(77'd0), .t_kd(54'd0), .f_host(), .f_lf(), .f_ks(),
        .mu_c(mu_c), .mu_rt(mu_rt), .ml_wv(ml_wv), .ml_wd(ml_wd), .ml_rv(ml_rv), .ml_rd(ml_rd), .ml_f(ml_f),
        .lo2_v(), .lo2_r(1'b0), .lo2_d(), .lo3_v(), .lo3_r(1'b0), .lo3_d(),
        .li2_v(1'b0), .li2_r(), .li2_d(553'd0), .li3_v(1'b0), .li3_r(), .li3_d(553'd0), .rxvb(),
        .l2_f(3'd0), .l3_f(3'd0), .fault(fault), .tl(276'd0), .ca(tp_o), .cb());
endmodule

// MU-S81b (2026-10-19): hardened master of the copy-A-only multi-user endpoint (kit s81sl_lepmua) for the stages with NO
// copy B (the 51 non-duplicated stage groups; host-less ends s_0S / s_0N / s_7S): MU_EN 1, AB_EN 0, HOST_EN 0.  Same core
// and cycles as ot_s81sl_lep_mu #(.HOST_EN(0), .AB_EN(0)); neither the host ports nor the pair-B ports (lo2 / lo3, li2 /
// li3, rxvb, l2_f / l3_f) are ports (the core reads none of them at HOST_EN 0 / AB_EN 0, generate), so the hard block
// carries no tied pad and no constant output.  Faces (kit): W lanes A, N landing (dsdv_mu_land), E ring + mu_c / mu_rt.
module ot_s81sl_lep_mu_a #(
    parameter integer DT = 512, parameter integer DR = 8, parameter integer CRED = 8, parameter integer SRAM = 1,
    parameter integer NB = 80, parameter integer RX_SRAM = 0, parameter integer IN_PIPE = 0, parameter integer NATIVE32 = 0
) (
    input  wire            clk,
    input  wire            rst_n,
    input  wire [1103:0]   ro,
    output wire [1103:0]   ri,
    output wire            lo0_v, input wire lo0_r, output wire [552:0] lo0_d,
    output wire            lo1_v, input wire lo1_r, output wire [552:0] lo1_d,
    input  wire            li0_v, output wire li0_r, input wire [552:0] li0_d,
    input  wire            li1_v, output wire li1_r, input wire [552:0] li1_d,
    output wire [1:0]      rxv,
    input  wire            sl_f,
    input  wire [2:0]      l0_f,
    input  wire [2:0]      l1_f,
    input  wire [33:0]     mu_c,
    output wire [31:0]     mu_rt,
    output wire            ml_wv,
    output wire [1103:0]   ml_wd,
    input  wire            ml_rv,
    input  wire [1103:0]   ml_rd,
    input  wire            ml_f,
    output wire            fault
);
    ot_s81sl_lep_core #(.DT(DT), .DR(DR), .CRED(CRED), .SRAM(SRAM), .HOST_EN(0), .MU_EN(1), .RX_SRAM(RX_SRAM), .AB_EN(0), .NB(NB), .IN_PIPE(IN_PIPE), .NATIVE32(NATIVE32)) u (
        .clk(clk), .rst_n(rst_n), .ro(ro), .ri(ri),
        .lo0_v(lo0_v), .lo0_r(lo0_r), .lo0_d(lo0_d), .lo1_v(lo1_v), .lo1_r(lo1_r), .lo1_d(lo1_d),
        .li0_v(li0_v), .li0_r(li0_r), .li0_d(li0_d), .li1_v(li1_v), .li1_r(li1_r), .li1_d(li1_d), .rxv(rxv),
        .sl_f(sl_f), .l0_f(l0_f), .l1_f(l1_f), .l0_st(2'b00), .l1_st(2'b00),
        .t_host(77'd0), .t_kd(54'd0), .f_host(), .f_lf(), .f_ks(),
        .mu_c(mu_c), .mu_rt(mu_rt), .ml_wv(ml_wv), .ml_wd(ml_wd), .ml_rv(ml_rv), .ml_rd(ml_rd), .ml_f(ml_f),
        .lo2_v(), .lo2_r(1'b0), .lo2_d(), .lo3_v(), .lo3_r(1'b0), .lo3_d(),
        .li2_v(1'b0), .li2_r(), .li2_d(553'd0), .li3_v(1'b0), .li3_r(), .li3_d(553'd0), .rxvb(),
        .l2_f(3'd0), .l3_f(3'd0), .fault(fault));
endmodule

// MU-S81-2/HOSTEP (2026-10-19): hardened master of the HOST-PLANE multi-user endpoint (kit s81sl_lepmuh) for the one
// end slice that carries the host plane on a non-duplicated die (s_7N): MU_EN 1, AB_EN 0, HOST_EN 1.  Same core and
// cycles as ot_s81sl_lep_mu #(.HOST_EN(1), .AB_EN(0)); the pair-B ports (lo2 / lo3, li2 / li3, rxvb, l2_f / l3_f) are not
// ports (the core reads none of them at AB_EN 0, generate), so the hard block carries no tied pad and no constant
// output.  User 0 is cycle- and bit-identical to the single-user ot_s81sl_lep (bench tb_s81sl_lep_mu, LEP_MU_H).
// Faces (kit): W lanes A + l*_st, N landing (dsdv_mu_land) + host plane on the NW corner, E ring + mu_c / mu_rt.
module ot_s81sl_lep_mu_h #(
    parameter integer DT = 512, parameter integer DR = 8, parameter integer CRED = 8, parameter integer SRAM = 1,
    parameter integer NB = 80, parameter integer RX_SRAM = 0, parameter integer IN_PIPE = 0, parameter integer NATIVE32 = 0
) (
    input  wire            clk,
    input  wire            rst_n,
    input  wire [1103:0]   ro,
    output wire [1103:0]   ri,
    output wire            lo0_v, input wire lo0_r, output wire [552:0] lo0_d,
    output wire            lo1_v, input wire lo1_r, output wire [552:0] lo1_d,
    input  wire            li0_v, output wire li0_r, input wire [552:0] li0_d,
    input  wire            li1_v, output wire li1_r, input wire [552:0] li1_d,
    output wire [1:0]      rxv,
    input  wire            sl_f,
    input  wire [2:0]      l0_f,
    input  wire [2:0]      l1_f,
    input  wire [1:0]      l0_st,
    input  wire [1:0]      l1_st,
    input  wire [76:0]     t_host,
    input  wire [53:0]     t_kd,
    output wire [514:0]    f_host,
    output wire [3:0]      f_lf,
    output wire [52:0]     f_ks,
    input  wire [33:0]     mu_c,
    output wire [31:0]     mu_rt,
    output wire            ml_wv,
    output wire [1103:0]   ml_wd,
    input  wire            ml_rv,
    input  wire [1103:0]   ml_rd,
    input  wire            ml_f,
    output wire            fault
);
    ot_s81sl_lep_core #(.DT(DT), .DR(DR), .CRED(CRED), .SRAM(SRAM), .HOST_EN(1), .MU_EN(1), .RX_SRAM(RX_SRAM), .AB_EN(0), .NB(NB), .IN_PIPE(IN_PIPE), .NATIVE32(NATIVE32)) u (
        .clk(clk), .rst_n(rst_n), .ro(ro), .ri(ri),
        .lo0_v(lo0_v), .lo0_r(lo0_r), .lo0_d(lo0_d), .lo1_v(lo1_v), .lo1_r(lo1_r), .lo1_d(lo1_d),
        .li0_v(li0_v), .li0_r(li0_r), .li0_d(li0_d), .li1_v(li1_v), .li1_r(li1_r), .li1_d(li1_d), .rxv(rxv),
        .sl_f(sl_f), .l0_f(l0_f), .l1_f(l1_f), .l0_st(l0_st), .l1_st(l1_st),
        .t_host(t_host), .t_kd(t_kd), .f_host(f_host), .f_lf(f_lf), .f_ks(f_ks),
        .mu_c(mu_c), .mu_rt(mu_rt), .ml_wv(ml_wv), .ml_wd(ml_wd), .ml_rv(ml_rv), .ml_rd(ml_rd), .ml_f(ml_f),
        .lo2_v(), .lo2_r(1'b0), .lo2_d(), .lo3_v(), .lo3_r(1'b0), .lo3_d(),
        .li2_v(1'b0), .li2_r(), .li2_d(553'd0), .li3_v(1'b0), .li3_r(), .li3_d(553'd0), .rxvb(),
        .l2_f(3'd0), .l3_f(3'd0), .fault(fault));
endmodule

// ---------------------------------------------------------------------------------------------------------------------
// The end-slice cluster: slice + lep + 2 link lanes.  SIDE 0 = W end (outward = ri_w / ro_w), 1 = E end.  The die
// masters are the parameter-free tops below (one per outward face: pin plans differ, as dsfd_coll_lane_w / _e).
// MU-S81/LINK: MU_EN 1 = leaf ot_s81sl_lep_mu + the NEW leaf dsdv_mu_land beside it (mu_c TX window, mu_rc replay,
// mu_rt RX tag); AB_EN 1 (needs MU_EN 1) = two more lane tiles on tx2 / tx3 / rx2 / rx3 / tfb (copy-B static circuit).
// At MU_EN 0 / AB_EN 0 the new ports are unread / 0 and the cluster is the pre-MU cluster.
// ---------------------------------------------------------------------------------------------------------------------
module ot_s81sl_slice_lep #(
    parameter integer SIDE = 0,
    parameter integer HOST_EN = 1,       // 0: leaf ot_s81sl_lep_nh, host ports unread / driven 0 (the _nh masters drop them)
    parameter integer MU_EN = 0,
    parameter integer AB_EN = 0
) (
    input  wire            clk,
    input  wire            rst_n,
    input  wire [3:0]      sid,
    input  wire [1103:0]   ri_n,         // inward line port (from / to the inward neighbour)
    output wire [1103:0]   ro_n,
    input  wire [275:0]    vi,   output wire [275:0] vo,
    input  wire [1103:0]   bi,   output wire [1103:0] bo,
    output wire [4*1104-1:0] xc,
    input  wire [8*70-1:0] rt,
    output wire [15:0]     ck_line,
    output wire [1:0]      ck_v,
    output wire [15:0]     ck_xc,
    output wire [7:0]      ck_rt,
    input  wire            ch_b,
    output wire [511:0]    tx0, output wire [511:0] tx1,
    input  wire [513:0]    rx0, input  wire [513:0] rx1,
    output wire [1:0]      tf,
    input  wire [76:0]     t_host, input wire [53:0] t_kd,
    output wire [514:0]    f_host, output wire [3:0] f_lf, output wire [52:0] f_ks,
    input  wire [33:0]     mu_c,         // MU: TX tag window {pos, user, land, ab, v}
    input  wire [10:0]     mu_rc,        // MU: replay {user, v} -> dsdv_mu_land
    output wire [31:0]     mu_rt,        // MU: RX tag {v, user, pos} with ri
    output wire [511:0]    tx2, output wire [511:0] tx3,
    input  wire [513:0]    rx2, input  wire [513:0] rx3,
    output wire [1:0]      tfb,
    output wire            fault
);
    wire [1103:0] lro, lri; wire sf;
    wire l0v, l0r, l1v, l1r, i0v, i0r, i1v, i1r; wire [552:0] l0d, l1d, i0d, i1d; wire [2:0] f0, f1; wire [1:0] rxv;
    wire l2v, l2r, l3v, l3r, i2v, i2r, i3v, i3r; wire [552:0] l2d, l3d, i2d, i3d; wire [2:0] f2, f3; wire [1:0] rxvb;
    generate if (SIDE == 0) begin : g_w
        ot_s81sl_slice u_sl (.clk(clk), .rst_n(rst_n), .sid(sid), .ri_w(lri), .ri_e(ri_n), .ro_e(ro_n), .ro_w(lro),
            .vi(vi), .vo(vo), .bi(bi), .bo(bo), .xc(xc), .rt(rt), .ck_line(ck_line), .ck_v(ck_v), .ck_xc(ck_xc),
            .ck_rt(ck_rt), .fault(sf));
        dsfd_coll_lane_w #(.LCR(1)) u_ln0 (.ck(clk), .rs(rst_n), .chb(ch_b), .rx({rx0[512], rx0[513], rx0[511:0], rxv[0]}),
            .tx(tx0), .tf(tf[0]), .lo_v(l0v), .lo_r(l0r), .lo_d(l0d), .li_v(i0v), .li_r(i0r), .li_d(i0d), .flt(f0));
        dsfd_coll_lane_w #(.LCR(1)) u_ln1 (.ck(clk), .rs(rst_n), .chb(ch_b), .rx({rx1[512], rx1[513], rx1[511:0], rxv[1]}),
            .tx(tx1), .tf(tf[1]), .lo_v(l1v), .lo_r(l1r), .lo_d(l1d), .li_v(i1v), .li_r(i1r), .li_d(i1d), .flt(f1));
        if (AB_EN != 0) begin : g_b
        dsfd_coll_lane_w #(.LCR(1)) u_ln2 (.ck(clk), .rs(rst_n), .chb(ch_b), .rx({rx2[512], rx2[513], rx2[511:0], rxvb[0]}),
            .tx(tx2), .tf(tfb[0]), .lo_v(l2v), .lo_r(l2r), .lo_d(l2d), .li_v(i2v), .li_r(i2r), .li_d(i2d), .flt(f2));
        dsfd_coll_lane_w #(.LCR(1)) u_ln3 (.ck(clk), .rs(rst_n), .chb(ch_b), .rx({rx3[512], rx3[513], rx3[511:0], rxvb[1]}),
            .tx(tx3), .tf(tfb[1]), .lo_v(l3v), .lo_r(l3r), .lo_d(l3d), .li_v(i3v), .li_r(i3r), .li_d(i3d), .flt(f3));
        end
    end else begin : g_e
        ot_s81sl_slice u_sl (.clk(clk), .rst_n(rst_n), .sid(sid), .ri_w(ri_n), .ri_e(lri), .ro_e(lro), .ro_w(ro_n),
            .vi(vi), .vo(vo), .bi(bi), .bo(bo), .xc(xc), .rt(rt), .ck_line(ck_line), .ck_v(ck_v), .ck_xc(ck_xc),
            .ck_rt(ck_rt), .fault(sf));
        dsfd_coll_lane_e #(.LCR(1)) u_ln0 (.ck(clk), .rs(rst_n), .chb(ch_b), .rx({rx0[512], rx0[513], rx0[511:0], rxv[0]}),
            .tx(tx0), .tf(tf[0]), .lo_v(l0v), .lo_r(l0r), .lo_d(l0d), .li_v(i0v), .li_r(i0r), .li_d(i0d), .flt(f0));
        dsfd_coll_lane_e #(.LCR(1)) u_ln1 (.ck(clk), .rs(rst_n), .chb(ch_b), .rx({rx1[512], rx1[513], rx1[511:0], rxv[1]}),
            .tx(tx1), .tf(tf[1]), .lo_v(l1v), .lo_r(l1r), .lo_d(l1d), .li_v(i1v), .li_r(i1r), .li_d(i1d), .flt(f1));
        if (AB_EN != 0) begin : g_b
        dsfd_coll_lane_e #(.LCR(1)) u_ln2 (.ck(clk), .rs(rst_n), .chb(ch_b), .rx({rx2[512], rx2[513], rx2[511:0], rxvb[0]}),
            .tx(tx2), .tf(tfb[0]), .lo_v(l2v), .lo_r(l2r), .lo_d(l2d), .li_v(i2v), .li_r(i2r), .li_d(i2d), .flt(f2));
        dsfd_coll_lane_e #(.LCR(1)) u_ln3 (.ck(clk), .rs(rst_n), .chb(ch_b), .rx({rx3[512], rx3[513], rx3[511:0], rxvb[1]}),
            .tx(tx3), .tf(tfb[1]), .lo_v(l3v), .lo_r(l3r), .lo_d(l3d), .li_v(i3v), .li_r(i3r), .li_d(i3d), .flt(f3));
        end
    end endgenerate
    generate if (AB_EN == 0) begin : g_nb
        assign tx2 = 512'd0; assign tx3 = 512'd0; assign tfb = 2'b00;
        assign l2r = 1'b0; assign l3r = 1'b0; assign i2v = 1'b0; assign i3v = 1'b0; assign i2d = 553'd0; assign i3d = 553'd0;
        assign f2 = 3'd0; assign f3 = 3'd0;
    end endgenerate
    generate if (MU_EN != 0) begin : g_mu
    wire mwv, mrv, lf, mf; wire [1103:0] mwd, mrd;
    ot_s81sl_lep_mu #(.HOST_EN(HOST_EN), .AB_EN(AB_EN)) u_lep (.clk(clk), .rst_n(rst_n), .ro(lro), .ri(lri),
        .lo0_v(l0v), .lo0_r(l0r), .lo0_d(l0d), .lo1_v(l1v), .lo1_r(l1r), .lo1_d(l1d),
        .li0_v(i0v), .li0_r(i0r), .li0_d(i0d), .li1_v(i1v), .li1_r(i1r), .li1_d(i1d), .rxv(rxv),
        .sl_f(sf), .l0_f(f0), .l1_f(f1), .l0_st(rx0[513:512]), .l1_st(rx1[513:512]),
        .t_host(t_host), .t_kd(t_kd), .f_host(f_host), .f_lf(f_lf), .f_ks(f_ks),
        .mu_c(mu_c), .mu_rt(mu_rt), .ml_wv(mwv), .ml_wd(mwd), .ml_rv(mrv), .ml_rd(mrd), .ml_f(mf),
        .lo2_v(l2v), .lo2_r(l2r), .lo2_d(l2d), .lo3_v(l3v), .lo3_r(l3r), .lo3_d(l3d),
        .li2_v(i2v), .li2_r(i2r), .li2_d(i2d), .li3_v(i3v), .li3_r(i3r), .li3_d(i3d), .rxvb(rxvb),
        .l2_f(f2), .l3_f(f3), .fault(fault));
    dsdv_mu_land #(.SRAM(1)) u_land (.clk(clk), .rst_n(rst_n), .wv(mwv), .wd(mwd), .rc(mu_rc), .rv(mrv), .rd(mrd), .fault(mf));
    end else if (HOST_EN != 0) begin : g_h
    ot_s81sl_lep u_lep (.clk(clk), .rst_n(rst_n), .ro(lro), .ri(lri),
        .lo0_v(l0v), .lo0_r(l0r), .lo0_d(l0d), .lo1_v(l1v), .lo1_r(l1r), .lo1_d(l1d),
        .li0_v(i0v), .li0_r(i0r), .li0_d(i0d), .li1_v(i1v), .li1_r(i1r), .li1_d(i1d), .rxv(rxv),
        .sl_f(sf), .l0_f(f0), .l1_f(f1), .l0_st(rx0[513:512]), .l1_st(rx1[513:512]),
        .t_host(t_host), .t_kd(t_kd), .f_host(f_host), .f_lf(f_lf), .f_ks(f_ks), .fault(fault));
    assign mu_rt = 32'd0;
    end else begin : g_nh
    ot_s81sl_lep_nh u_lep (.clk(clk), .rst_n(rst_n), .ro(lro), .ri(lri),
        .lo0_v(l0v), .lo0_r(l0r), .lo0_d(l0d), .lo1_v(l1v), .lo1_r(l1r), .lo1_d(l1d),
        .li0_v(i0v), .li0_r(i0r), .li0_d(i0d), .li1_v(i1v), .li1_r(i1r), .li1_d(i1d), .rxv(rxv),
        .sl_f(sf), .l0_f(f0), .l1_f(f1), .fault(fault));
    assign f_host = 515'd0; assign f_lf = 4'd0; assign f_ks = 53'd0; assign mu_rt = 32'd0;
    end endgenerate
endmodule

// die masters (S81-LEPV 10-18: host plane only on s_7N)
//   dsdv_slice_lepw     s_0S / s_0N   W end, no host plane (HOST_EN 0: no host ports)
//   dsdv_slice_lepe     s_7N          E end, host plane (t_host / t_kd in, f_host / f_lf / f_ks out)
//   dsdv_slice_lepe_nh  s_7S          E end, no host plane
module ot_s81sl_slice_lepw (
    input  wire clk, input wire rst_n, input wire [3:0] sid,
    input  wire [1103:0] ri_e, output wire [1103:0] ro_e,
    input  wire [275:0] vi, output wire [275:0] vo, input wire [1103:0] bi, output wire [1103:0] bo,
    output wire [4*1104-1:0] xc, input wire [8*70-1:0] rt,
    output wire [15:0] ck_line, output wire [1:0] ck_v, output wire [15:0] ck_xc, output wire [7:0] ck_rt,
    input  wire ch_b, output wire [511:0] tx0, output wire [511:0] tx1, input wire [513:0] rx0, input wire [513:0] rx1,
    output wire [1:0] tf,
    output wire fault
);
    ot_s81sl_slice_lep #(.SIDE(0), .HOST_EN(0)) u (.clk(clk), .rst_n(rst_n), .sid(sid), .ri_n(ri_e), .ro_n(ro_e), .vi(vi), .vo(vo),
        .bi(bi), .bo(bo), .xc(xc), .rt(rt), .ck_line(ck_line), .ck_v(ck_v), .ck_xc(ck_xc), .ck_rt(ck_rt), .ch_b(ch_b),
        .tx0(tx0), .tx1(tx1), .rx0(rx0), .rx1(rx1), .tf(tf),
        .t_host(77'd0), .t_kd(54'd0), .f_host(), .f_lf(), .f_ks(),   // host ports unread at HOST_EN 0
        .mu_c(34'd0), .mu_rc(11'd0), .mu_rt(), .tx2(), .tx3(), .rx2(514'd0), .rx3(514'd0), .tfb(), .fault(fault));   // MU ports unread at MU_EN 0
endmodule
module ot_s81sl_slice_lepe (
    input  wire clk, input wire rst_n, input wire [3:0] sid,
    input  wire [1103:0] ri_w, output wire [1103:0] ro_w,
    input  wire [275:0] vi, output wire [275:0] vo, input wire [1103:0] bi, output wire [1103:0] bo,
    output wire [4*1104-1:0] xc, input wire [8*70-1:0] rt,
    output wire [15:0] ck_line, output wire [1:0] ck_v, output wire [15:0] ck_xc, output wire [7:0] ck_rt,
    input  wire ch_b, output wire [511:0] tx0, output wire [511:0] tx1, input wire [513:0] rx0, input wire [513:0] rx1,
    output wire [1:0] tf,
    input  wire [76:0] t_host, input wire [53:0] t_kd, output wire [514:0] f_host, output wire [3:0] f_lf, output wire [52:0] f_ks,
    output wire fault
);
    ot_s81sl_slice_lep #(.SIDE(1), .HOST_EN(1)) u (.clk(clk), .rst_n(rst_n), .sid(sid), .ri_n(ri_w), .ro_n(ro_w), .vi(vi), .vo(vo),
        .bi(bi), .bo(bo), .xc(xc), .rt(rt), .ck_line(ck_line), .ck_v(ck_v), .ck_xc(ck_xc), .ck_rt(ck_rt), .ch_b(ch_b),
        .tx0(tx0), .tx1(tx1), .rx0(rx0), .rx1(rx1), .tf(tf),
        .t_host(t_host), .t_kd(t_kd), .f_host(f_host), .f_lf(f_lf), .f_ks(f_ks),
        .mu_c(34'd0), .mu_rc(11'd0), .mu_rt(), .tx2(), .tx3(), .rx2(514'd0), .rx3(514'd0), .tfb(), .fault(fault));   // MU ports unread at MU_EN 0
endmodule
module ot_s81sl_slice_lepe_nh (
    input  wire clk, input wire rst_n, input wire [3:0] sid,
    input  wire [1103:0] ri_w, output wire [1103:0] ro_w,
    input  wire [275:0] vi, output wire [275:0] vo, input wire [1103:0] bi, output wire [1103:0] bo,
    output wire [4*1104-1:0] xc, input wire [8*70-1:0] rt,
    output wire [15:0] ck_line, output wire [1:0] ck_v, output wire [15:0] ck_xc, output wire [7:0] ck_rt,
    input  wire ch_b, output wire [511:0] tx0, output wire [511:0] tx1, input wire [513:0] rx0, input wire [513:0] rx1,
    output wire [1:0] tf,
    output wire fault
);
    ot_s81sl_slice_lep #(.SIDE(1), .HOST_EN(0)) u (.clk(clk), .rst_n(rst_n), .sid(sid), .ri_n(ri_w), .ro_n(ro_w), .vi(vi), .vo(vo),
        .bi(bi), .bo(bo), .xc(xc), .rt(rt), .ck_line(ck_line), .ck_v(ck_v), .ck_xc(ck_xc), .ck_rt(ck_rt), .ch_b(ch_b),
        .tx0(tx0), .tx1(tx1), .rx0(rx0), .rx1(rx1), .tf(tf),
        .t_host(77'd0), .t_kd(54'd0), .f_host(), .f_lf(), .f_ks(),   // host ports unread at HOST_EN 0
        .mu_c(34'd0), .mu_rc(11'd0), .mu_rt(), .tx2(), .tx3(), .rx2(514'd0), .rx3(514'd0), .tfb(), .fault(fault));   // MU ports unread at MU_EN 0
endmodule

// Nine independent combinational control regions serve <=8 registered select
// slices each. The raw next-head metadata lands on the original select edge.
(* keep_hierarchy="yes" *) module ot_s81sl_lep_rx_control(
 input wire [3:0] ne,ring,hk,tag,input wire mv,input wire [4:0] mt,output wire [5:0] sel);
 wire ar=ne[0] && ne[1],br=ne[2] && ne[3] && !ar;
`ifdef OT_S81SL_LEP_MUT_LANDCUT
 wire ac=ar && ring[0],bc=br && ring[2];
`else
 wire ac=ar && ring[0] && !(hk[0] && hk[1]);
 wire bc=br && ring[2] && !(hk[2] && hk[3]);
`endif
`ifdef OT_S81SL_LEP_MUT_STRIPALL
 wire at=1'b1,bt=1'b1,rt=1'b1;
`else
 wire at=hk[0] && tag[1],bt=hk[2] && tag[3];
 wire rt=mt[0] && (mt[3:1]==3'd1 || mt[3:1]==3'd2) && mt[4];
`endif
 assign sel={rt,bt,at,(mv && !ac && !bc),bc,ac};
endmodule

(* keep_hierarchy=1 *) module ot_s81sl_lep_host_event(input wire [11:0] now_status,old_status,input wire valid,output wire event_o);
 assign event_o=valid || now_status!=old_status;
endmodule
(* keep_hierarchy=1 *) module ot_s81sl_lep_tx_push(input wire ring,host_go,key_go,open,pair_b,output wire [1:0] pp);
 wire push=ring || host_go || key_go;
 wire bsel=ring && open && pair_b;
 assign pp={push && bsel,push && !bsel};
endmodule

(* keep_hierarchy=1 *) module ot_s81sl_lep_host_enable(input wire ne0,ne1,hit,output wire en);
 assign en=ne0 && ne1 && hit;
endmodule

(* keep_hierarchy=1 *) module ot_s81sl_lep_stamp(input wire [31:0] count,input wire ring,output wire stamp);
 assign stamp=ring && count!=0;
endmodule

(* keep_hierarchy=1 *) module ot_s81sl_lep_host_hold8(
 input wire [11:0] now_status,old_status,input wire valid,rn,pending,send_now,old_valid,
 input wire [7:0] keep_mask,old_data,new_data,output wire [7:0] next_data);
 wire event_h=valid || now_status!=old_status;
`ifdef OT_S81SL_LEP_MUT_HDROP
 wire preserve=1'b0;
`else
 wire preserve;
 (* keep=1 *) ot_s81sl_lep_host_preserve u_preserve(.pending(pending),.send_now(send_now),.old_valid(old_valid),.new_valid(valid),.preserve(preserve));
`endif
 wire [7:0] merged=new_data ^ ((new_data ^ old_data) & {8{preserve}} & keep_mask);
 assign next_data=(rn && event_h)?merged:old_data;
endmodule
(* keep_hierarchy=1 *) module ot_s81sl_lep_key_hold8(input wire rn,valid,input wire [7:0] old_data,new_data,output wire [7:0] next_data);
 wire enable;
 (* keep=1 *) ot_s81sl_lep_host_enable u_enable(.ne0(rn),.ne1(valid),.hit(1'b1),.en(enable));
 assign next_data=enable?new_data:old_data;
endmodule

(* keep_hierarchy=1 *) module ot_s81sl_lep_host_preserve(input wire pending,send_now,old_valid,new_valid,output wire preserve);
 assign preserve=pending && !send_now && old_valid && !new_valid;
endmodule

// LEPCAP 10-19: one face-stage copy of a valid bit (kept hierarchy: Yosys may not merge the copies back into one flop).
(* keep_hierarchy="yes" *) module ot_s81sl_lep_vcopy(input wire clk, input wire d, output reg q);
 always @(posedge clk) q <= d;
endmodule

// S81/H4 10-24: one kept, reset (control) copy of a tree-frame demux select (<= 23 data loads each).
(* keep_hierarchy="yes" *) module ot_s81sl_lep_idx_sel(input wire clk, input wire rn, input wire d, output reg q);
 always @(posedge clk or negedge rn) if (!rn) q <= 1'b0; else q <= d;
endmodule

// Native32 MU control regions. Same capture edge and static protocol as the legacy core.
(* keep_hierarchy=1 *) module ot_s81sl_lep_status_region(
 input wire clk,rn,input wire [12:0] sample,
 output wire [11:0] now_status,output reg [11:0] old_status,output wire valid);
 (* keep=1 *) reg [12:0] snapshot;
 always @(posedge clk) snapshot<=sample;
 assign now_status=snapshot[12:1];assign valid=snapshot[0];
 always @(posedge clk or negedge rn)
   if(!rn) old_status<=0;
   else if(valid || now_status!=old_status) old_status<=now_status;
endmodule
(* keep_hierarchy=1 *) module ot_s81sl_lep_pair_ready(input wire a,b,output wire q);
 assign q=a && b;
endmodule
(* keep_hierarchy=1 *) module ot_s81sl_lep_return8(
 input wire [3:0] ne,input wire [1:0] ring,land,
 input wire [4:0] ring_code,replay_code,input wire [7:0] ring_data,replay_data,
 output wire [7:0] q);
`ifdef OT_S81SL_LEP_MUT_NOPAIR
 wire pa=ne[0];
`else
 wire pa=ne[0] && ne[1];
`endif
 wire pb=ne[2] && ne[3] && !pa;
 wire cut=(pa && ring[0] && !land[0]) || (pb && ring[1] && !land[1]);
 wire [4:0] code=cut?ring_code:replay_code;
 wire has_tag=code[0] && (code[3:1]==3'd1 || code[3:1]==3'd2) && code[4];
 assign q=has_tag?(cut?ring_data:replay_data):8'd0;
endmodule

// Independent combinational decode groups keep each shared metadata input local.
(* keep_hierarchy=1 *) module ot_s81sl_lep_std_enable(input wire a,b,ring,output wire q);
 assign q=a&&b&&ring;
endmodule

// Default-off standard TX: independent physical qualification decoders.
(* keep_hierarchy=1 *) module ot_s81sl_std_tx_qualify #(parameter integer AT=9,CW=4,DT=512)(
 input wire push,input wire [AT:0] count,input wire [CW-1:0] credit,output wire wr,rd);
 assign rd=(count!=0)&&(credit!=0);
 assign wr=push&&((count!=(AT+1)'(DT))||rd);
endmodule

// L5B-LEPMU 10-21: next value of rpb (pair B releases, pair A does not) from the RX non-empty next states; one kept copy
// per rx control group so rnex fans <= CG and each pb_r group register drives <= 16 mwd select bits.
(* keep_hierarchy=1 *) module ot_s81sl_lep_bsel_next (input wire [3:0] ne, output wire q);
    assign q = ne[2] && ne[3] && !(ne[0] && ne[1]);
endmodule
