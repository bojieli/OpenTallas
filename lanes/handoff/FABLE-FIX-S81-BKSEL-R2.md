# FABLE-FIX-S81-BKSEL-R2 (11-20): bk_sel__t2 and slice_station__t41, J3 placed BAD/HOLD

Lane dirs: intel1 + epyc7 + epyc10 `/srv/opentallas-scratch2/claude/fable-fix-s81-bksel-r2`; hub `~/fable-fix-s81-bksel-r2`.
Lane clone intel1 `.../repo`, branch `claude/fable-fix-s81-bksel-r2-a3p` (not pushed until the bench passes).

## 1. bk_sel__t2: root cause (measured)

The placed J3 form is the OLD core layout with NO stations. The fix that S81-GEOM-OPUS designed on 11-19 (BK-PLACE core
moves + OT_BKSEL_A2P stations, rows_bk.json 3c632455897c) was never in a bound plan: D8i, J3, J4 and the J5 candidate
8cf9560f3978 all still carry the old origins (q0 794.88/328.32, tx 3594.24/190.08) and verilog_defines = [OT_BKQ_ECO3].
It waited on the dsdv_bksel_c re-harden, which failed LEC.

Pin-to-pin lengths, LEF pins x plan sites (intel1 J3 kit, script a1.py in the lane dir):

| link (one clock, 0 stations) | bits | J3/J5 layout um | BK-PLACE um |
|---|---|---|---|
| u_g.ln -> quarter lane | 4 x 515 | 242-1164 | 579-1602 |
| u_c.t_c -> quarter f_c | 4 x 66 | 226-1345 | 641-1613 |
| quarter t_s -> u_c.f_s | 4 x 865 | 136-1322 | 551-1590 |
| quarter t_o -> u_c.f_o | 4 x 354 | 100-1824 | 672-2265 |
| u_g.vo_s -> u_tx.vo (not stationable: u_tx taps vo_s and vi_m together) | 276 | 1646-1826 | 308-488 |
| u_tx.lo -> tl_o0 face | 276 | 3229-3664 | 1613-2109 |
| u_tx.lo -> tp_o0 / tp_o1 faces | 2 x 276 | 744-1210 | 2778-3331 |

Placed scan (geom.tsv, all register/macro pairs): 4,759 pairs over 300 um. Besides the rows above: u_vm.o -> u_tx 2127,
u_tx.lo -> lp_q 2889, east-bank buses to the hub (idx_i0 2169, tp_i0 1929, xtier_i1 relay -> u_g 2095, u_g -> vo_n 2166,
u_ids -> vo_n 1775), u_g -> xtier_o0 1218, landing FIFO -> u_bin 728-816, rst_n_t33 fanout 2103 (Astra).
All 11 data buses are on the S face in two banks 2.8 mm apart (W x 1134-1437, E x 3960-4322); the hub (u_vm, u_g, u_tx,
u_ids) talks to both, so face-bus stations are needed in any layout.

Density: the block is 99.5 % empty (fill 0.0049). The 0.999 bin at [2479,99] is the u_ids / vn register cluster (about 196
async-reset flops) that the placer pulled to one point between u_g and the east bank; the smear along the south strip is
the buffer chains of the long nets. It is a consequence of the unstationed nets, not a capacity problem. No density row is
needed once the stations give the placer anchors; check it again on the re-placed form.

LEC blocker of the u_c re-harden: not an A2P fault and not a new class. Both failed kits (ucore/dsdv_bksel_c_rfda2p and the
no-A2P control ucore_ctl/dsdv_bksel_c_rfdqctl, 5 of 57,418 points: u_ctl.rep_req, st[2:0] and c_rep removed) were generated
from a D8h overlay whose ot_s81ph_sel_pipeline.sv lacks the 11-17 `(* fsm_encoding = "none" *)` on st (grep count 0 in both
kits). Main has it (line 292). A kit generated from main carries it.

## 2. bk_sel__t2 rows (for J6; gate = signed u_c view)

1. BK-PLACE (0 cycles) + station profile: `lanes/handoff/FABLE-FIX-S81-BKSEL-R2-rows_bk_a3p.json` (sha 53956fe8b195).
   Made by bk_rows_a3p.py on the J5 candidate 8cf9560f3978: 7 core origins, 7 core taps, 15 taps moved, tap_um, and
   verilog_defines += OT_BKSEL_A3P. Private plan epyc10 lane dir plan_j5base_bk_a3p.json (3f5744c62256). Geometry is the
   S81-GEOM-OPUS r2 layout (G0 bk3: street_gap 2 -> 0), unchanged.
2. OT_BKSEL_A3P (RTL, inert unless defined): RC 5, RS 5, RO 7, RLN 5 = every quarter hop <= 283 um on BK-PLACE
   (A2P RC3/RS3/RO4/RLN3 gives 398-453 um hops). Control XDX 2 -> 7. Bench in flight (epyc7).
3. hard_cores u_bk_sel.u_sel.u_c lef/lib -> the A3P view once signed (kit intel1/epyc7 lane dir ucore/dsdv_bksel_c_rfda3p,
   kit_hash 583e3ea9b4b18b48, from main, with the fsm_encoding fix).
4. Still open after 1-3, to be sized on the private placed form (not ready as rows): face-bus internal_stations for the 11
   buses (estimate on BK-PLACE: W bank ca/cb/xtier_i0/xtier_o0 3 each, tl_o0 6-7; E bank tp_i0 7-8, idx_i0 9, xtier_i1 7,
   xtier_o1 7, tp_o0/tp_o1 10-11), the u_g.vo_s -> u_tx.vo link (308-488 um; needs u_g MX or a 130-um shift to get under
   300), the u_tx.lo -> lp_q -> u_vm loop around the 562-um macro, and the Astra same-depth reset anchors, which must be
   re-derived for the new core sites.

## 3. slice_station__t41: root cause and rows

J3 placed (epyc8 j3_geometry_pilot/results/geom_review/placed_slice_station__t41): the only pairs over 405 um are the START
broadcast: u_cland_origin and u_rrl_153 -> u_cland_fstart_ft{0,1,7..12}_o 470-1248 um, and u_cland_origin ->
u_cland_reader_start_ft6_i 842-892 um. The J3 and J4 plans have no clock.landing_writer_start / landing_reader_start on this
type. The J5 candidate 8cf9560f3978 already has both: writer depth 6, 8 branches (ft0/1/7-12), worst hop 255.0 um; reader
depth 6, 11 branches, worst hop 235.7 um, each stage with a local raw reset. All 9 measured endpoints are covered. So t41
needs no new row; it needs J5 bound and a private place + GRT. Everything else over 300 um on t41 is the planned 380-um
hop of the J3 bind (ft stations 376-394, reset relays 380), which the J5 reach 300 changes die-wide.
Other t41 flags are advisory: local density 0.848, col_v 0.674 at [720,397], pin_reg_max 201 (cland_fstart_in_ft3_i).

## 4. State 11-20 12:30 PST and next steps

Done:
- OT_BKSEL_A3P on main d174c71d874. Bench BKSEL_A3P PASS (epyc7 lane dir bench_a3p: eco3 PASS, a3p PASS 6/6 variants 0 errors,
  a3pxdm FAIL 802 errors, a2p PASS).
- u_c A3P kit (epyc7 lane dir ucore/dsdv_bksel_c_rfda3p, recipe recipes_a3p.json, kit_hash 583e3ea9b4b18b48): LEC EQUIVALENT
  31,696 / 31,696, 0 differ.
- Per-type private GEN is not possible for bk_sel__t2: prepare-stations stops at KIT_TOPOLOGY_BIND_STALE and
  bind.py component-proof fails the type even as an identity control (17 errors). A native bind is required.

In flight (all on epyc7, clients on intel2 ~/fable-fix-s81-bksel-r2):
- u_c A3P kit to sign-off: unit oth-ubuntu-2237101-1795198176, log ucore_a3p.otrun.log (run_kit.sh finish 48 16). In GRT at 12:15.
- Private native bind of plan bbd8567d93b1 (J3 300c06c6dda4 + rows 53956fe8b195): unit oth-ubuntu-1952795-1795205595, log
  bk_build1.otrun.log, script bk_build_e7.sh = the die lane's build_tree.sh on tree_b (hard-linked copy of j3src), outputs in
  build_b1. HARD_CORE_PARAM is expected to flag u_c (XDX 7 against the bound qrx view) until the A3P view is in the plan.

Next, in order:
1. u_c signs (DRC 0, TT >= -42, internal FF hold >= 0, LEC done): export the view (LEF, tt/ff lib, built params) as
   cores/views/bksel_c_a3p_1120, archive to AGIdock /archive/opentallas-signed-1114/s81/ and rtx-pro
   ~/signed-export-1114/s81/ with INDEX rows on both (as dsdv_bksel_q__fx6_hei3_1116 was), and add the plan row
   hard_cores u_bk_sel.u_sel.u_c lef/lib -> that view to the J6 rows.
2. Bind out ready: private bk_sel__t2 GEN with gen_pilot_e7.sh on tree_b (S = tree_b, B = its native_bind/out), then
   run_kit.sh place, geometry review (the r2r.py scan in the lane dir lists every pair over 300 um by family), then GRT TT.
3. From the placed form: size the face-bus internal_stations (draft counts in section 2 item 4), check the
   u_g.vo_s -> u_tx.vo link (308-488 um; u_g MX at the same origin gives 135-316 um, c.vd -> g.vd 167-335 um, RLN 5 hops
   <= 294 um; needs a PINBAND / G0 check of the MX track offset), and re-derive the Astra reset anchors.
4. slice_station__t41: when S81-DIE-R4 has a J5 bound out, GEN + place + GRT the type privately; no row is owed.

Stale paths: intel1 kw45/src_s81_pin_3c913dbdfb23_d8j_1119_j0 was removed by ot-auto-retire at 11:31:46; intel1 lane dir
tree_bk has dangling links into it and is unused. Use the epyc7 lane dir (j3src = full copy, completed from d8j_1117_work).
