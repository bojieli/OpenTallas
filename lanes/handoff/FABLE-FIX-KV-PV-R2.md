# FABLE-FIX-KV-PV-R2 handoff (KV pv family owner: kv3_pv*, pv_pair; successor of FABLE-FIX-KV-PV-2140)

Written 2026-11-20 12:3x PST. Posts lanes/posts/FABLE-FIX-KV-PV-R2.md. Lane dir epyc7 /srv/opentallas-scratch2/claude/fable-fix-kv-pv-r2
(repo = lane clone of main, tools/ = scripts, out/ = dumps, por_<tag>/ = private plan dirs, kit/<tag>/ = private kits).
Hub logs and chains: intel2 ~/tmp/ffkpvr2 (chain_r2.sh TAG LABEL, chain_<tag>.log, kit_<tag>.log, watch_r2.sh posts AUTO-KIT lines).

## Live
- v8m (epyc7, crit, goal route, 64 GB / 16 thr, launched 12:08 PST): D27 candidate = flip of the 4 upper near pairs + station 300
  + R3 split reserved rows of kv3_pv_v8 + form C, tools main 38cdd37cec9 (has c6ab8bd7be, b699b5b678).
- v8c: control, same without the flip.  Both: tree4c data + bind4c RTL (copy of v8k rtl), DO_NOT_COUNT, .keep_stage_odbs.
- GEN on this 405-um bind needs OT_RESET_HOP_CAP_UM=405 (tools/gen_r2.sh); without it the reset identity guard refuses.
- Inherited, untouched: v8k (epyc7, in place), v8h / v8j (epyc10; v8j finished CTS 11:15 PST, in TT repair).  v8j CpuShares 10240:
  set back to 1024 when it routes, fails or is cancelled (intel2 ~/tmp/ffkpv2140/restore_v8j_cpu.sh is armed).
- Cancel only with ot-run --cancel <kit path>.

## Found (all measured on the v8j CTS DB unless marked)
- kv3_pv_pair: 1,670 signal pins, all M5 on ONE long edge.  Stack per group: far pair / near pair / join / near pair / far pair.
  Lower near pair to join: 77.76-um strip.  Upper near pair (origin y 803.52) to join: 25.92 um.
- Net edges leaving the strip over the join sideways (E / W / through): g2 upper 2,779 / 2,172 / 390; g1 upper 1,382 / 1,705 / 328;
  g3 upper 713 / 1,166 / 15; g2 lower 2,458 / 2,357.  Content: near-pair pad tails with their last delay stages, the 579-bit near ts
  funnel, T/Q relay ranks, 258-bit o_pvw stations along y 777.6.
- GRT iteration 0 with the kit capacity hooks (out/v8j_it0b.cap.tsv, usage / tracks incl. blockages): g2 upper strip 136 %, g3 101 %,
  g2 lower 93 %, g3 lower 75 %; pair channel row3-row4 75 % / 62 %; centre street (x 1028-1131) y 800-900 H 106 % / V 116 %.
  Over the pair: M2/M3 full, M4 about 90 %, M5 83-89 %, M6 74-79 %, M7 74-85 %, M8 68-71 % used.
- The far pair bus (1,024 bits to the join W/E face) crosses the near pair on M5/M7: 7,281 forced crossings.  No pair -> join ts end
  is among the 14,305 negative setup ends, so that link needs no pipe stage.
- D23H it15 markers by position (I): H overflow 0-100 um from the upper near pair pin edge, capacity 0; V overflow on the pin row.
- Setup ends at CTS, placement RC, v8j (405 um, before the anchor): trunk terminal q 2,141 ends to -8,203 (wrong-side inverter;
  c6ab8bd7be), tail terminal q 10,953 ends, median -111 to -129, worst -456 (405-um hop; station 300), pair pe2 pins 486 to -759,
  ctl_cmd tails 367 to -506.
- Centre street carries ft0 (1,056 bits, stations x 1059) + the vport pad trunks: 2,579 to 4,720 vertical edges per cut in 103 um.

## Rows
- D27 row 1 (in proof): lanes/handoff/FABLE-FIX-KV-PV-R2-rows.py PLAN_C.json  (--check = report).  64 cores on 16 types:
  R0 -> MX, MY -> R180 on the pair whose pin edge is < 40 um from its join.  Same origin, outline, tap xy.  0 cycles, no RTL.
  Needs a rebind (tail K from the new pin edge).  Not proved until v8m reads GRT iteration 5.
- D27 row 2 (proposal, not built): ft0 vertical leg out of the centre street into the 253-um street x 1511-1764, then west in the
  top band; same station count.  Touches ft_slots regs / bit sites and the ft0_o START branch, so it needs the bind.
  Decide on the centre-street tiles of v8m / v8c at GRT iteration 5.

## Read order when the kits move
1. 3_3 hooks: OT_TAIL_SITE (max_hop, core_crossing), 3_4 OT_DLY_SPREAD (chains over station, fail count) v8m against v8c.
2. CTS: tt_setup_repair "before" wns; classify with tools/run_sta.sh + an4.py (trunk q class must be gone in both arms).
3. GRT iteration 5: congestion-5.rpt through scratchpad cls / tools/an5-style split (strip, pin edge, centre street, reserved rows).
4. Sign-off only if TT >= -42, FF hold >= 0, DRC 0; private kits never count; export comes from a wave kit on the applied plan.
