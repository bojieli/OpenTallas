# FABLE-FIX-HEAD-LEP0N-R4 (Fable, 11-21 19:0x-20:xx PST): hd_lep0N type split, step 1 (successor of R3)

Predecessor: lanes/handoff/FABLE-FIX-HEAD-LEP0N-R3.md (FINAL STATE) + lanes/FABLE-PD-HEAD-2000.md. Hub logs intel2
~/fable-fix-head-lep0n-r4/. Lane dir (intel2 AND epyc9, same path): R=/srv/opentallas-scratch2/claude/fable-fix-head-lep0n-r4.
Stood down on context, not on a blocker. No kit launched. Nothing applied to any live tree. No plan file written.

## In flight (1 unit, adopt it)
- oth-ubuntu-1136304-1795317736 (epyc9, ot-run --mem 40): R/parts/prove_parts.sh = 0-cycle equivalence of the six-content
  composition against Codex's proven split core. Hub log ~/fable-fix-head-lep0n-r4/parts_equiv_e9.otrun.log; proof log
  epyc9 R/parts/proof/parts_equiv.log. PASS line: "PARTS_EQUIV_PASS" after "Equivalence successfully proven". Codex's two
  proofs of the same size took about 70 min. NOT yet proven: do not quote the contents form as LEC-clean before that line.
  First run (unit oth-ubuntu-1082133-1795317650) elaborated cleanly (hierarchy -check PASS, all name maps hit) and died in
  the equiv read on my own name map (the two halves of a cut leg collided); fixed in proof/normalize_parts.py.
  If $equiv cells stay unproven, look first at same-named nets with a different function (add them to a blacklist copy),
  as Codex did for lo_* (base/eq_blacklist.txt).

## Facts found (read before designing further)
1. Codex's I/O relocation proof FINISHED PASS: 379,764/379,764 (epyc10 split1121/io_stage_split/
   io_relocation_transitive_equiv.log, 4,169 s). So TX extraction (356,004) AND io stages are both proven, 0 cycles.
2. HEAD is a gen-mode die (plan wrappers from gen.py rtl; "strict bind" = head_die_portbind + cohort + LATCHECK,
   F/strict_bind_immutable.sh). type_split.py was built for bind-mode dies. Two gaps for this type:
   (a) contents can only talk through type `nets` (gen_rtl: contents[].bind port -> "net:N", whole net, >= 2 leaf ports),
       and type_split.py fails closed on a type with `nets` ("unhandled type keys"); the documented spec key cut_lanes has
       no code. A net whose leaves fall in different pieces must become a cut bus pair (driver bind net:N -> bus:o_<n>,
       load bind -> bus:i_<n>) + port + lane. The plan-cell route queue (type_split.py pc_routes / _plancell_requests,
       route(frm, to, stem, width, kind, on_done)) is the mechanism to reuse. THIS TOOL EXTENSION IS NOT WRITTEN.
   (b) clock.landing_contract.native_stage_groups has ONE "content": "u_core" + module + params and 226 group prefixes.
3. Geometry allows only these cuts (pairs at x 69.12-846.72 and 967.68-1745.28, y 17.28-509.76 and 846.72-1339.2):
   x in the N-S street (907.2 = 105 x 8.64) and x = 1745.28 (the E strip); a y cut would run through the band.
   So "hub / lanes / io" are CONTENTS; the pieces are W | E (optionally | E strip), not six types.
4. The RTL already has the right seams (rtl/dsrom_sys/s81_head/ot_s81hd_lep0N_split.sv header, DIE-HEAD-76): every
   hub<->region net is a credit link, a push without back-pressure or a sticky flag. Stage counts today:
   TXI 16'h2442 (TX FIFO ingress stages inside the lane: lanes 1,2 = 4, lanes 0,3 = 2), KRX 16'h2660 (lanes 1,2 = 6),
   KTX 16'h1111, KTR 16'h3112, KCRED 28. A cut bus pair (2 boundary flops) can REPLACE 2 native stages on each crossing
   leg, so the W | E cut costs 0 data cycles: lanes 1,2 TXI 4 -> 2, RX leg 6 -> 2 (W) + 2 (boundary) + 2 (E).
   Only tx_ovf (sticky fault) gets +2. Do not add net cycles to the K links: the header says a longer round trip bunches
   beats and collapses the pair A/B release stagger.
5. Boundary flops (ot_dp_st) carry data and ctl bits without reset (flushed during the >= 64-clock reset hold).

## Done: step 1 RTL (generated, elaborates; proof in flight)
R/parts/parts_gen.py (input R/parts/base/split_tx_io_stages.sv sha ade1bb2f..., eq_tops.sv; real copies, nlink 1)
writes R/parts/proof/ot_s81hd_lep0N_parts.sv + eq_parts.sv:
- u_core = ot_s81hd_lep0N_noidx_hub (inner instance u: every hub path stays u_core.u.*): LEP hub, u_land, rst fan, lw,
  COL0 stages, PLW, hub side of the RX K legs. New parameter RXA[4i+:4] = RX stages of lane i that live in region i.
- u_io = ot_s81hd_lep0N_io (inner u = Codex's ot_s81hd_lep0N_io_stages): g_pin / g_pout banks.
- u_rg0..3 = ot_s81hd_lep0N_rgn #(K, KT, KQ, KR, RA): TX lane (u_txl, 5 SRAM), K TX stages g_txf / g_txr, RA stages of
  g_rxf / g_rxr, pair macro u_pair, coll_i / coll_o.
- Whole-net ports only. Nets: c0i[514], c0o[512] (hub <-> rg0), io_rs[14], pin[1150], pout[1137] (hub <-> io), and per
  lane h2r<i>[574] = {tx_wd, tx_pg, tx_psh, rkir, rkrx}, r2h<i>[558] = {rkid, rkf, rkiv, tx_ovf}, rs<i>[123] = reset
  leaves {k_rst, tx_rst, tx_rt}.
- Proof form RXA = 16'h0330.
Rename map old -> new (apply to plan strings, escaped regexes and assets):
  u_core.u.g_pp[i].u_pair -> u_rg<i>.u_pair | u_core.u.u_lep.u.g_tx[i]. -> u_rg<i>.u_txl.g_tx[i]. |
  u_core.u.g_kl[i].g_txf/g_txr -> u_rg<i>.g_txf/g_txr | u_core.u.g_kl[i].g_rxf.g_s[j] (j < RA) and g_rxr.g_s[j]
  (j >= KR-RA) -> u_rg<i>.(same) | u_core.u.g_pin./g_pout. -> u_io.u.g_pin./g_pout. | all else unchanged.
Plan references that carry these paths (v2 plan 00b2abf6e7a6, type hd_lep0N): contents 1, buses[].leaf 15,
hard_cores[].inst 49 (4 pair + 20 TX SRAM move, 25 stay), clock.taps core names 4, clock.tap_group.re 1,
landing_contract.native_stage_groups (content + 226 prefixes; families g_pin 8, g_pout 10, g_txi 12, g_kl rxf/rxr 28,
txf/txr 8, g_tx 40, rest hub), internal_stations capture/launch 5, relay_sites 133 (all hub, unchanged).
The sink bins asset is position-only (no names).

## Open design point the successor must settle
Reset leaves across the cut (rs1, rs2: 123 static bits each). Through a boundary pair they release 2 edges late. Either
prove that harmless (the lane's inputs are idle until START), or give the W regions their own fan (LOCAL_RST form of
ot_s81hd_lep0N_region_core, same RFAN depth off the W piece's gated tap). I lean to the local fan.

## Work order left (nothing below is started)
1. Wait for PARTS_EQUIV_PASS. Then move parts_gen.py + outputs into a lane clone (ot-lane-clone) beside
   tools/s81_head/head_lep_split_sources.py, with a --check mode and a test; push via ot-push-main.
2. Plan delta script on v2 plan 00b2abf6e7a6: six contents + nets + the rename map above; gen.py rtl must elaborate and
   the cohort / strict bind / LATCHECK must stay 26/26, 329/329 BEFORE any cut (0 cycles, same lanes).
3. type_split.py: handle `nets` (2a) and native_stage_groups per content (2b); tests; ot-push-main.
4. Split spec: family [hd_lep0N], axis x, cuts_um [907.2], keep = E piece (hub, io, rg0, rg3, START pins); W = rg1, rg2,
   coll_i1/o1/i2/o2. Post-split parameter delta: TXI 16'h2222 with boundary pairs on h2r1/h2r2, RXA so that W native 2 +
   pair 2 + E native 2. Expect E about 300k cells, W about 100k (shelf_we non-tap was 395,746).
5. PD rows as macro site moves (shapes fixed): (1) RX row y 637.7 x 1,008-1,620 broken (no SRAM row over ~250 um
   without a >= 40 um gap); TX SRAMs of lanes 1,2 go to the W band beside pairs 1,2, which also halves the TX rows
   y 555-606; (2) coll_i1 / coll_i2 rings out of the 65-um W channel (W piece owns them now); (3)
   OT_PREGRT_HOLD_R2R_MARGIN from the measured need (5 ps pass had 0 violating ends), as the --ab of private-spec.
6. Strict bind + LATCHECK + G0, then kit_wave.py private-spec on intel2 (hosts epyc7 / epyc9), wave env, config.mk diff.
7. Reseal r17a (event head_rp21z20NF15f_r17a) with split rows + HEAD-CTL-R1 WRCAP row (plan 28819946547a) on a PRIVATE
   live copy of v2 (561a1f11cf15). The shared live_s81_head is still at 81ac28d4 (neither r16 nor v2): reconcile first.
   Gate with --gen-host epyc7 or --hub (intel2 cannot resolve its own short name; FLEET-WATCH-R8).

## Infra seen
- intel2 ot-run HOLD at 19:1x PST: "disk-ETA: 465 GB free falling 483 GB/h" (no admission). --max-wait did not end the
  hold loop; I stopped my own client (exact pid). Private-spec gen on intel2 will meet the same hold.
- epyc9 admitted both proof jobs at once (scratch2 475 GB free).

## UPDATE: proof FINISHED PASS (after stand-down)
Unit oth-ubuntu-1136304-1795317736 exit 0: 351,685/351,685 equiv cells proven, PARTS_EQUIV_PASS (0 cycles, RXA 16h0330, vs Codex moved_raw.il sha 99888541...). 0 units in flight. The "In flight" section above is closed; work order step 1 wait is done.
