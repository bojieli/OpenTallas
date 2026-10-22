# smh_xs_ring_kmr_1019 -- SAFE variant A of smh_xs (H.STA.BLK.14.1), LH-SMATT/XS 10-19

Predecessor rg2 (smh_xs_ring_rg2_1019, b1c7e3d2a, failure packet results/rtl/smhxs_ring_1019/rg2_failure_packet) is a
terminal FAIL: GRT 0 overflow, but boundary pin-flop spread 149.5 TT / 136.4 FF ps (> 80), all-sink 185.9 / 153.6, one
root over 20,550 sinks (16 stages, Codex bnd_branch tree, leaf nets up to 316 loads), sink mass south-centre (r0c1 9,756),
and TT reg -> ring-macro read address -80 ps (two shared negedge ra_n flops serve all 4 ring macros).

Structural change (same RTL default; opt-in defines in this kit only):
* Clock: the custom bnd_branch.tcl tree is DROPPED. physical/common_flow/clock_split_km.tcl (S81 xr1 km16: 48.6 / 46.4 ps
  on a 311x395, 16k-flop tile) splits the clock port net into K = 20 regional roots by 2-D k-means on the placed sinks
  (equal-count clusters, ~1,030 sinks each; the measured 9.8k south-centre mass gets ~10 roots beside it), one BUFx24 root
  at each centroid, CTS builds one short tree per region under a latency-balanced top tree. One external clock port.
* OT_SMH_RING_LOCAL_ADDR / OT_SMH_RING_LOCAL_WADDR: every ring macro has its own KEPT (keep_hierarchy, dont_touch)
  positive-edge read AND write address capture (ot_hbm_accel_smh_ring_raddr / _waddr) -> a full-cycle launch from a flop
  placed beside its macro instead of a half-cycle from two shared negedge flops (rg2 -80 ps). Same macro address every edge.
* OT_SMH_RING_RST2: the ring slot counter and its 8 address captures take their own kept ot_rst_relay from the landed
  rst_a (identical SYNC 2 + TREE 1 release edge), so the leaf relay stays <= 32 loads (rg2 33; LOCAL_ADDR alone -> 41).

Region numbers: 20,550 sinks measured (rg2 4_cts) + 12 local address flops + 3 relay flops; K = 20 regions ~1,030 sinks
each; region boxes are the placed k-means clusters (reported by the gate log `CLOCK_SPLIT_KM`). Crossings: all
region-to-region paths are intra-tile (<= 432 x 345.6), single clock, latency-balanced roots; the boundary is judged by the
pin-flop spread <= 80 ps TT and FF (clock rule 0dq), no landed crossing needed inside a < 1 mm tile.

## SAFE 8-item checklist
1. Pins: PASS. RTL input/output pin registers retained (u_rl2/u_bkd2/u_ohl2, output flops), OT_SMH_XSRST 2-stage face
   reset landing; ring relay is fed from the landed rst_l1.
2. Reach: PASS by construction for the changed paths (address capture beside each macro); full placed reach (> 405 um per
   cycle) re-measured by the gate textbook lint.
3. Fanout: FIXED. Address flops 1 macro each (was 2 flops x 4 macros); leaf reset relay <= 32 (ring moved to its own
   relay); strap tree CK4/LCK2/32 middle copies kept (rg2 synth max 32).
4. Depth: PASS, data logic unchanged (rg1 TT depth 281.7 ps); the -80 ps half-cycle address path removed.
5. Storage: PASS, 4-slot SRAM ring (no 788 b x 3 flop delay line), x store in 4 SRAMs.
6. Floorplan: WAIVED (unchanged rg2 geometry, coordinator fill waiver: 432x345.6, 8 macros on the 43.2 lattice, 34.8 / 45.4
   um channels, full faces <= 6/um, fill 30%). The compact rebuild is variant B (smh_xs_ring_c32_1019 / c32k).
7. Clock: FIXED structurally (regional roots beside the register mass, no custom tree); acceptance = gate pin-flop spread
   <= 80 TT+FF; macro clock refs from the LEF/libs; io_hold_margin 0.03, hold_margin 0.03.
8. Schedule: PASS, static II 1, 0 added data / startup edges (nothing to price). Benches (Verilator 5.050, full
   ot_hbm_accel_smh_xs, all 1,615 output bits every cycle, async reset bursts): vs legacy flop pipeline 5000 cyc PASS;
   vs rg2 ring 5000 cyc PASS + 19,496 per-macro read/write address checks 0 mismatches; read-slot and write-slot mutants
   FAIL (2,712 mismatches each). Logs results/rtl/smhxs_ring_1019/safe_ab/A_*.log.

Critical tile: no REVIEW.json / submit; gate PNGs go to lanes/COORD-REVIEW-QUEUE.md.
