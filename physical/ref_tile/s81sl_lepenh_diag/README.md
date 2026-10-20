# s81sl_lepenh_diag -- dsdv_slice_lepe_nh parent (s_7S end slice), DIAGNOSTIC stand-in kit

Lane S81-SLICE3-LEPENH, 2026-10-19. Release tree S81.STA.OWN.11.

**Not bindable, never submit.** Every child is a `tools/qwen_dv/slice_standin.py` abstract (`STANDIN_NOT_A_VIEW`).
This kit exists to run parent integration early (owner EFFICIENCY 10-18): gate (synth, place, CTS per region, GRT,
clock pairs) on the real landed parent RTL. Rebuild it as a real kit (new name) once real child views close.

## Structure
- Flat master `ot_s81sl_slice_lepe_nh` (rtl/dsrom_sys/s81_dv/slice/ot_s81sl_slice_lep.sv) -> wires-only flat expansion
  `ot_s81sl_slice_lepe_nh_x` (landed/lepe_nh/) -> lp.py landed parent `ot_s81sl_slice_lepe_nh_x_lp`
  (spec tools/landed_parent/specs/dsdv_slice_lepe_nh.json, record results/rtl/s81_slice3_lepenh_1019/lp/).
- Regions: **S** = u_sl (ot_s81sl_slice), root ck_S; **K** = u_lep (ot_s81sl_lep_nh) + u_ln0/u_ln1 (dsfd_coll_lane_e), root ck_K.
- Landings: lro (S->K, 1104 b), lri (K->S, 1104 b), sf (S->K, 1 b); D 4 / E 2, +3 edges each, 11,084 landing flops.
  The instance graph S->K->S is a cross-region loop, so the record is RESCHEDULE: the +3 edges sit on the outward line
  hop into the elastic link layer (credits / go-back-N, the only flow control, at the d2d boundary). Price: +3 cycles on the
  outbound and +3 on the inbound off-die line hop (compiler: off-die line latency +6 round trip); reset release +4 edges.
- Straps: ch_b (die strap 1'b1, S81-DIE7 port map: switched / board lane timeout basis) and sid (4'd14) are static.
- Floorplan (provisional, die tool owns the final pins): slice 1252.8 x 5702.4 (PL-SLICE draft outline) at W; lep_nh
  475.2 sq beside the slice centre band (line ports); 2 lanes 432 x 336.96 at the E face (PHY side). 2462.4 x 5788.8.

## Children (stand-ins) and their real owners
| inst | master | stand-in source | assumed insertion TT/FF/SS | real view owner |
|---|---|---|---|---|
| u_sl | ot_s81sl_slice | PL-SLICE draft outline, line ports on the centre band | 250/200/330 | PL-SLICE / S81-SLICE3 (31/46 sub-leaves open) |
| u_lep | ot_s81sl_lep_nh | s81sl_lepnh kit pin plan, W/E swapped for the E end | 220/170/290 | S81-SLICE3-LEP (redesign) |
| u_ln0/1 | dsfd_coll_lane_e | closed dsfd_coll_lane_w (dscoll_lane_w_cxea) plan mirrored | 419/347/537 (w view measured) | LINK lane; no closed _e view on main |

## SAFE-DESIGN checklist (owner 10-19) -- parent level
1. Pins: PASS. Parent owns no logic but the lp landing rings / reads / reset pads; every child pin is registered in its
   child (lep pin flops, lane credit faces LCR 1, slice ring stop); parent ports go straight to child pins in the same
   region (no parent combinational path). Reset lands in 2+ registered stages per region (u_lpr_root + u_lpr_<r> depth 3).
2. Reach: OPEN (gate). The S->K line crossing is landed (ring beside the slice E face, read beside lep). The slice
   centre band spans 1382 um of E face while lep's W face is 475 um: the funnel wires must stay < 405 um per hop (ring
   placement beside the source, read beside the reader); lanes abut lep (< 100 um).
3. Fanout: PASS by construction: lp.py read mux selects from the reader counter with per-landing copies; reset runs fan
   out per child (u_lprc_*). The gate textbook_lint high_fanout check confirms.
4. Depth: PASS: landing = ring write + one D:1 read stage; no parent arithmetic.
5. Storage: WAIVED: 3 x D=4 landing rings are flop rings by the landing contract (L1-L7, fixed latency) -- 4 slots,
   below the >= 3-deep-delay-line rule's intent (no runtime-indexed hold chain beyond the D slots).
6. Floorplan: children on the 43.2 lattice (gen PASS), >= 43.2 um margins, aspect 2.35:1 (> 2:1: set by the slice
   column 5.7 mm, a die-plan constraint; WAIVED for the stand-in run, re-slot with the die lane S81-DIE*), std-cell band
   = the channels between children (landing logic only).
7. Clock: PASS by design: two regional roots (ck_S, ck_K) with landed crossings; judge u_sl<->u_lep and u_lep<->u_ln*
   pairs at child flops TT/FF <= 80 (lep 220 vs lane 419 TT in one region: the K root must balance with the child pin
   latencies -- the gate's pair check decides). io_hold_margin 0.03.
8. Schedule: PASS: static; +3/+3 off-die line edges and +4 reset edges handed to the compiler (lp record "compiler").

## Benches / checks
- tools/landed_parent lockstep (landed vs flat, Verilator 5.050) + mutants: rtl/dsrom_sys/s81_dv/slice/landed/lepe_nh/ot_s81sl_slice_lepe_nh_x_lp_bench.sh
- 2-die composition on the LANDED die B: tools/s81_slice/slice_lep_bench.sh OUT none lepe_nh_lp (swap = negative control)
- bind: tools/die_port_bind.py on ot_s81sl_slice_lepe_nh_x_lp (no tied ports; HOST_EN 0 ports absent)
