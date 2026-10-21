# hcoll_v7_tkm_tile_e86v4b (HBM-E86-6 10-20) -- ot_hgi_coll_tkm_tile_e86 FAN32 2 + SEAM 1
Fix of e86v3 (GRT 0 / native32 PASS, cross_clock TT setup FAIL -28.6/-11.0/-30.4 ps): compare cones no longer cross a
row-group root seam (shadow X copy xs + shadow operand capture cs on the consumer root; see RTL SEAM comment).
Fallback: 302.4 sq outline (util ~50%), pins respread.

Safe-design checklist (owner 10-19, with 10-20 09:05/09:35 relaxations):
1 Pins: inputs registered at the pin stage (PRE 1), all outputs flops; no reset (datapath unreset, clr is a control input). PASS
2 Reach: tile <= 302.4 um; no single-cycle wire > 405 um. PASS
3 Fanout: FAN32 2 kept copies; e86v3 mapped census max 32; SEAM adds i_b 27 -> 30 loads, xn 1 -> 2. census in gate (must be 0 > 32)
4 Depth: e86v3 textbook depth 541.8 ps; SEAM moves the compare cones of seam positions inside one root (no new logic stage). PASS
5 Storage: X 64 x 86 b is a static parallel shift/insert array (every entry read every edge, no runtime index): flops by design. waived (existing)
6 Floorplan: no macros; square; full std-cell band. util: v4 ~70% (e86v3 68% WARN, GRT 0); v4b ~50%.
7 Clock: five related same-frequency roots (row groups), pin-flop spread e86v3 <= 18 ps; seam crossings now flop->mux->flop only.
8 Schedule: static, cycles_added 0 (same edges, lockstep vs CREP 0).
