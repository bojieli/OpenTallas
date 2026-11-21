# FABLE-FIX-KV-PV-1121 handoff (Fable FIX lane, KV pv family direction; works beside OPUS-FIX-KV-PV-R5)

Written 2026-11-21 08:3x PST. Posts lanes/posts/FABLE-FIX-KV-PV-1121.md (finding + direction 08:2x). Hub dir intel2 ~/tmp/ffkpv1121.
Lane dir epyc8 /srv/opentallas-scratch2/claude/fable-fix-kv-pv-1121 (tools/, db/, out/, tmp/). No kit, no bind, no plan install, no git.

## State
- No job of this lane is running. Two read-only ot-run jobs ended rc 0 (oth-ubuntu-3943288-1795274857 hops, oth-ubuntu-3955241-1795274899 STA).
- One background wait in my session on R5 bind 7 (epyc8 split28/bindgate_7/gate.out); it launches nothing.
- Nothing signed off. The goal (one pv half to the gates) is NOT reached; the split bind (R5 bind 7) was still running.

## What was measured (V)
- db/v7_3_place.odb + .sdc = copy of wave kit kv3_pv_v7 KV-D25e3 attempt_3 3_place (394k at floorplan, 654k non-tap at place, R5 cancelled it 07:34).
- out/v7_ends.tsv: 6,557 negative TT setup ends at placement RC (slack, endpoint, ., pins, ., startpoint). `python3 -I tools/an4.py v7_ends.tsv`.
  5,339 under -42; 4,327 of them are port -> landing core d[] on fclk half cycles (pre-CTS artifact: ideal fclk, core setup up to 364 ps);
  1,012 real clk ends: sel_q fan-out 600 (worst -561), vport out -> first station 140 (worst -541), T/Q tails 240 (-182), pad lines 34 (-127).
- out/v7_hops.tsv: 37,454 zero-logic hops >= 330 um (`python3 -I tools/an7.py out/v7_hops.tsv`): 27,741 at 300-400 (plan), 4,690 at 400-500, 3,320 over 500;
  the classes over 1,100 um all start at a u_vport_W / u_vport_E output register or at a ring dsel flop feeding a u_bin eq bit.
- tools/leaf_first_hop.py PLAN.json TYPE BOUND.sv: static first hop of vport outputs to station 0. On split 10 bind-4 RTL (epyc8
  opus-fix-kv-pv-r4/split28/tree plan_of_record): kv3_pv_v3 715 vport_W bits over 405 um (639-1,345), u_vport_E bound in w with no anchor (811 bits),
  4 u_bout buses with vport bits and no plan row. kv3_pv_v3e: no vport instance in its bound text.

## Direction posted (rows R1-R5, for the single D28 R8 rebind)
R1 verilog_defines OT_PV_VPORT_SELREP32 on every pv type and half (today: kv3_pv_v1n only). R2 u_vport_E into the piece of its ring / rows, type_split
fail-closed on a leaf bound in one piece and anchored in the other. R3 vport-fed lanes: polyline port -> leaf anchor -> face, stations <= 300 um;
plan rows for the 4 u_bout buses; fault lanes from the anchor. R4 relay_sites pin the vport out / d_q banks at the anchor. R5 gate = LEAF_FIRST_HOP 0 / 0.

## Not done / not checked
- R1-R5 are proposals: no row file was generated, no bind or kit has run with them. Whether relay_sites may name u_vport_*.out_* flops under
  SELREP32 names (qkd_pv16_selcp copies) was not tried. Whether internal_stations rows are legal for a bus that today has only a u_bout was not tried.
- The fclk landing classes (4,327 ends) have no post-hook read on any pv kit of this lane; bit-to-bit arrival spread on slg_W was 135 ps at place.
- The T/Q tail class (240 ends) and pad lines were not traced to rows; they are the 405-era station class of OPUS-FIX-KV-PV-R4 resite rows.
- leaf_first_hop.py uses the d-bank anchor for every vport port; the vq lanes have their own from_um, so its vqN_d1 line (797 um) overstates.
- 6 KV-D26 unsplit pv rows (v2n, v3n, v4n, v5n, v6, v8) were RUNNING at 07:34 (R5 post); the stop list says no unsplit pv kit. Not mine; not touched.

## Next for whoever continues
1. Run leaf_first_hop.py on bind 7 bound RTL (tree5 plan_of_record/bind_of_record/rtl/kv3_pv_v3_part.sv, kv3_pv_v3e_part.sv).
2. Generate R1-R4 on split 12, one R8 refresh, bind 8, then the w half by kit_wave.py private-spec; at 3_place run tools/run_hops.sh and
   tools/run_sta.sh (ot-run --hosts epyc8 --dir <lane dir> --stage <kit dir>) and compare with the v7 tables above.
3. Read the fclk landing groups only from the post-hook CTS report.
