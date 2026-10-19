# Compute system face with independent D2D start lists

Opt-in `qfd_sys_face #(MU=1, OVL=1)`. The six new N-face control bits drive
qfd_d2d_static_ovl's cal_start_rx, cal_seg_rx, cal_user_tx[1:0], cal_user_rx[1:0].
The d2d tile's tx_user/rx_user outputs must continue to native59/record codecs;
GEN must not tie either side. The closed serial face is unchanged at OVL=0.

Shared compiler evidence is rtl/qwen_sys/d2d_static_20261015/ovl_release.
The compiler reserves all four playheads; K ATTN_LAND codec2 gives TXDP_K
0x03030416, C0x0a010308. Admission bytes derive from 5ae543bfa and live at
calendar entry16. FIRST_OFS1176 follows ADM_OFS72+ADM_LEN1100 and the two
segment-base writes. H4026800;1703 words/list;1702 starts/list; X8 is charged.
Two4096x72 mask ROMs hold the C lists. One plain low32 capture register per
ROM isolates slow macro output from list decode; the player's age2 prefetch
covers macro+capture with no start-edge change.

Verilator5.050 fleet bench compares the hard-ROM/capture path against synchronous
compiler lists for a full frame and admission:1703 TX and1703 RX starts, all four
users. RX-start-tied mutant fails at admission. Witness logs are committed in
results/rtl/mu_qwen_1018/sysface_ovl. Existing MU face event/filler checks are
regressed separately.

This kit supplies the link calendar producer. It does not replace the face's
T/L/E compute programme calendar. A die claiming the overlapped token rate must
bind the corresponding MU programme starts, token contexts and codec user tags.
The historical serial T-marker/link-start equality check applies only at OVL0;
OVL1 checks list integrity and link calendar occupancy independently. No claim
of full-die OVL token exactness is made by the ROM integration bench.

SAFE-DESIGN checklist before gate:
1. PASS: recipe4 pin registers; two-stage reset landing; six added control bits
   are registered by the same boundary wrapper. Existing reset regions retained.
2. PASS:276.48x172.8um outline; no route can exceed405um within the tile.
3. PASS for new controls: separate TX/RX players and capture registers; list
   state drives one ROM and a bounded control cone. Existing face fanout is
   inherited from the MU face and measured by the new synthesis gate.
4. PASS structurally: ROM outputs drive capture flops only; prefetch pipeline
   and registered list outputs. Gate must confirm actual stage depth.
5. PASS: additional109kb logical lists use two mask ROMs, no runtime-indexed
   flop storage. Calendar tables remain the existing32x32 or64x32 structures.
6. PASS geometry: ROM origins(43.2,86.4),(129.6,86.4),(216,86.4) lie on43.2um
   lattice; gap48.384um; full-width std band below. Aspect1.6. Macro-to-pin
   edge clearance>=20um. Utilization waiver: N/S data pins require a wide
   face; inherited MU face is pin-limited. Actual utilization from synthesis
   must be recorded, then reviewed with gate PNGs before submission.
7. PASS settings: one compact local root at N-face centre beside pin mass,
   hold margin0.03. TT/FF pin-flop spread<=80ps and neighbour boundary remain
   mandatory gate checks; their measured values are pending.
8. PASS pricing: zero added normal start-list edges, reset landing+2 already
   in MU face; codec2 extra response edge priced via X8. Outline change handed
   to QW GEN. Static lists, no credits, no backpressure.

Critical prefix qfd_sys_face: gate PNGs and checklist go to coordinator review.
No REVIEW.json or submit_exact is authorized in this lane before that review.

R2 epoch-recovery correction (mandatory, source510c0cd51 and successor): halt
rewinds both listplayers including addr/nxt/nv/age/cnt/cur; reload also clears
liststate under the existing idle-only reload contract. Faults remain sticky
untilreset. Fleet recovery benches PASS from midframe, each prefetchage0/1/2,
and immediatelybeforewrap, then replay one whole frame; old-rewind mutantFAIL.
The original OVL1 gate is retained as geometry/timing diagnostic only. Only
this R2 source is eligible for future integration/review.

Native59 SAFE2 prefetch adoption is separate and currently blocked on
production Qdd-ready/seam evidence. sys_face_image's q_prefetch guard advances
L/class2 only with source-pinned perbeat raw-Qdd-ready bounds and measured
request_edges; it rejects absent/late data. The emitted D2D CMD/Q image is
unchanged. Default images are unchanged; no unproved production advance is
made by this kit.
