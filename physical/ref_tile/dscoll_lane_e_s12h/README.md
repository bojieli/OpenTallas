# dscoll_lane_e_s12h

S81 regional LEPAB matched core-face buffer/return budget: CORE_CRED12 opt-in (default8 unchanged). Core landing SRAM logical DEPTH12 and reverse sender CRED12 rise together, physical32x64 banks unchanged; explicit two-edge lane data/credit relays add4 to the offdie RTT. Existing finite fixed-circuit return pulses only; no new scheduling credits. Source exact ffb9d6552 safe4 base plus this bounded parameter patch; all old CRED8 routes preserved independently. GAP-SKQ/GSKQ-LKTO (10-21) successors of dscoll_lane_{w,e}_s8nq / _s8nr: SRAM macro-edge via guard.

Why: dscoll_lane_e_s8-s8-84d7d9b8f (same lane RTL family, same 55-SRAM lattice, same recipe-1 kit flow) routed
TT +44.77 / FF +3.75 ps but DRC 51 (DRT stalled 56 -> 51 from iter 40 to 64); e_s7 DRC 50 / e_s7k DRC 32 the same.
All 51 markers are M4 Short (33) / Metal Spacing (18) "inst:<ot_sram_1r1w2c_256x64_m1> net:<n>", every bbox 0.06-0.08 um
inside the macro M4 OBS end (x = macro pin edge 77.784 / 164.184 / 250.584 / 423.384 / 596.184 minus 0.072..0.083):
the net sits on the first over-macro M5 track (77.724, between the OBS end 77.712 and the pin stub 77.760) and its
V4 enclosure / M4 jog cuts the macro OBS -- exactly the shape physical/common_flow/macro_edge_via_guard.tcl was written
for (s81su qnq/qbe, qkd_sbufp q14, qfd_tt_head h16c, qkd_embedding_row_tx).  The lane kits are recipe 1, so
ref_tile.macro_edge_guard() never added the guard.  Fix (structural, routing-resource level; no timing relaxed): source
the guard (physical/qwen_die_masters/sram_edge_guard.tcl as boundary_tcl: added before GRT, removed after DRT) with
OT_MEG_DEPTH_UM 6.0 (the depth that closed qfd_tt_head h16c / qkd_embedding_row_tx r2 DRC 0).
  s8ng = s8nq (K=24, best pin-flop spread W 55.5/51.7, E 53.9/53.1) + guard depth 6.0            (MAIN)
  s8nh = s8nr (K=32) + guard depth 6.0 + OT_MEG_OUT_UM 1.2 (straddling GCell outside the edge too,
         KV r7t-hd2 lesson; halo 5.4 um > 1.2)                                                      (FALLBACK)
Same RTL, outline, macros, pins / bit order, PDN, layer contract, CTS and cycles.  M5 over each macro loses 2 x 6 um of
its 34.6 um width; trial GRT had headroom (overflow 0, worst layer M2 13 %).

--- s8nr base ---
S81-COLL-1021 (10-21) successors of dscoll_lane_{w,e}_s8nk: k-means regional CTS with K=24 (s8nq) / K=32 (s8nr).

Why: the s8n / s8nk --cts gates (10-21 01:53-02:09, ep6) FAILED only clock_rule (pin-flop spread > 80 ps within the one
region): s8n TritonCTS TT 121.6 / 118.3 ps (E / W); s8nk K=16 TT 83.0 / 87.8, FF 69.6 / 86.6 ps.  All else passed: census
max 32, trial GRT overflow 0, setup/hold WNS >= 0 at the placement STA.  The pin_balance bit order (group_max 1) spreads the
four wide buses over the full W/E faces (99% of 583 um), so the boundary flops form a 2 x 583 um perimeter ring 726 um apart;
K=16 arcs (~90 um of ring each) left a ~85 ps tail.  The fix splits the ring into shorter arcs (K=24 ~ 60 um, K=32 ~ 45 um)
with one local root each under the balanced top tree, so each leaf tree is small and the top tree balances equal-load
roots.  Same RTL, outline, macros, pins / bit order, PDN, layer contract and cycles; no timing constraint relaxed.

--- s8nk base ---
DRIVE-S81-NTF (10-20) MU-die COLL lane kits dscoll_lane_{w,e}_s8n (TritonCTS) / dscoll_lane_{w,e}_s8nk (k-means K=16):
the tf-less lane tiles of the lepe_mu / lepw_mu landed parents (release die), ported from the DRIVE-S81-COLL s8 kits.

Top dsfd_coll_lane_{w,e}_safe8_ntf = ot_s81ph_coll_lane_safe4 REACH = 2 (s7 relay hops + endpoint RX FIFO write landing,
the s8 structural fix of the s7 GRT reach FAIL: 5,379 pairs > 405 um from c_diff / c_crc_ok / xp_v fanned across the tile),
CH_BOARD 700, TF_CLEANUP 1, NO tf pin and NO parameters (a default-parameter die bind is this view).  Same outline, macro map,
pins (minus tf), PDN, layer contract and clock recipe as s8 / s8k; K=16 fallback for both sides.

--- s8 base ---
S81-COLL8 (10-20) COLL lane kits dscoll_lane_{w,e}_s8 (TritonCTS) / dscoll_lane_e_s8k (k-means regional CTS, K=16):
structural fallback of s7 (S81.STA.LKTO.2), gated in parallel with the running s7 routes.

s7 E gates WARN (GRT0, spread 73.3/67.9 and 67.2/65.3) and route, but the actual GRT native reach audit on the s7 E
gate ODB (scratch/s81-tilesf/reach_e_s7) still FAILS: 5,379 pairs > 405 um, max 765 um; 4.8k of them are ONE cone:
u_ep c_diff / c_crc_ok / xp_v (receive decision, placed by the gearbox at the link face) -> the 18 RX FIFO address
groups (g_fifo_safe g_address[].count_r / wp_r) and u_m g_slice[].valid_r beside the 18 RX FIFO banks at the core
face, in one cycle (W s7 gate placement TT reg->reg -246 ps at g_address[5].wp_r).  The REACH = 1 frame hops did not
move the decision: the placer keeps it by the gearbox.

s8 = RTL top dsfd_coll_lane_{w,e}_safe8 (ot_s81ph_coll_lane_safe4 REACH = 2 = REACH 1 + ot_s81ph_link_ep_safe4
WRL = 2): RX FIFO write LANDING.  c_acc -> 3 kept copies (edge 1, one per 6 groups) -> 18 per-group kept copies
(edge 2, each on its group's reset leaf) beside the banks; write data 2 reset-free stages; logical occupancy (fill,
c_full / overflow) still counts c_acc at once, physical occupancy (fillw / tail / drain) counts the landed write.
No single-cycle wire from the decision to the FIFO groups; +2 receive edges (credits return 2 edges later).
Same outline, macro map, pins, PDN, layer contract as s7.

SAFE review before first gate:
1 PASS source-registered lane pins; reset_landing2+tree3.
2 FIXED existing REACH2 relay/write-landing architecture, original guarded geometry.
3 PENDING exact CORE_CRED12 mapped census; source change adds one RX pointer bit; no layout gate until <=32 including reset.
4 PASS same endpoint/gearbox pipeline; no wide combinational new mux.
5 FIXED SRAM logical landing12 in existing32-deep macros; sender12 matched.
6 PASS exact ffb9d6552 macro lattice/43.2pitch, face density<=6, full rows; outline725.76x583.2, area rechecked at native synth.
7 PASS existing K24(g)/K32(h) trees; TT/FF<=80 measured at gate; io_hold .03.
8 FIXED +4 outer credit RTT priced with two-edge payload/valid+reverse return relays. Finite offdie return pulses only.
