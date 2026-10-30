# DIE-KV-39-SD-V2: KV-022 variant V2 - 6 explicit clock taps for kv3_sys_SD / kv3_sys_SD_v1 (plan delta via gen_phys)

COORD ruling DIE-KV-38-PARK (3): C/A (taps moved on 3_place.odb) failed the FF structural hold gate (-251..-379 ps);
V2 = plan delta built through bind + gen_phys, per-tap trees balanced to the 12.3 common latency, no ODB edits.

## Estimate (CHECKED on DIE-KV-38 varA 3_place.odb sink dump, kv39_dump_sinks.tcl)
- x6 PHY macro (17.28,54)-(1866.24,1026) covers 91% of the outline; sinks live only on the S strip (y<54) and E strip.
- 'clk' 6589 sinks (SD) / 6577 (SD_v1): S x1400-1900 ~4.4k, E y50-300 ~1.4k, E y600-700 ~0.5k; S x<1400 only ~110,
  all plan-placed reset/START relays rrl_/srl_ (they follow the stale reset.local_taps_um, 11/12 of which lie ON the
  macro because the bind plan had no PHY footprint) + cland origin/collector.
- Old grid (tap_edge_y_um) taps at x 190..1710 S left the SE load on one or two far trees (C/A: 213 vs 626 ps on the
  relay chain).  Planned 6 taps (explicit, load = kit split rule on the actual placed inventory, far = max sink dist):
  SD    clk(1110,21.6) 2/8.9um, t1(1490) 1012/121, t2(1690) 1552/122, t3(1855) 1978/105, t4 E(1892.16,160) 1317/220,
        t5 E(1892.16,640) 577/243
  SD_v1 clk 2/8.9, t1 955/139, t2(1730) 1395/145, t3(1872) 2214/97, t4 1285/237, t5 575/234
  Loads 0.6-2.2k within <=243 um: KV reference trees of this size/reach are ~200-280 ps TT (UNCHECKED estimate), so the
  existing tap_balance (OT_TAP_TARGET_PS 250 TT = 202.5 FF, window 20 ps) can pad the light taps (clk) up; a 2.2k / 97-um
  tree is the risk for exceeding 250.
- Reset tree (reset_tree.for_type on the delta plan): depth 5, 56 (SD) / 52 (SD_v1) relays, max hop 380 um, 0 relays on
  the macro; collector (mk_sd36 rule) 0 on macro, local sources 39-42 um from their taps, collector depth unchanged.

## Delta (fix-only, kv3_sys_SD/_v1 only)
1. main serdes delta first (results/die_kv_32_1029/serdes/apply_serdes_phys.py): x6 PHY footprint + VDDPHY domains.
2. mk_sd39.py: clock.tap_mode explicit + 6 taps (above), tap_max_sinks 2400, tap_radius_um 400, sink_bins_file =
   the placed clk inventory (sd39_bins_*.json, relays/collector excluded: their sites come from the plan trees);
   tap_edge_y_um dropped; reset.local_taps_um re-sited off the macro onto the actual async-reset consumer groups
   (count 12 unchanged).
3. mk_sd36.py (DIE-KV-36, unchanged): collector tree := reset_tree.for_type of the delta plan, sources re-tapped.
4. kitplan_sd39.py: kit plan = (3) + the existing SD kit forms (count_straps sites + clock.die_islands_um from
   DIE-KV-33 die_plan_sd33s, clk_clk_phy edge clock from DIE-KV-35 sd35 delta) - needed by port_bind (15 bits).

## Results (intel1 /srv/opentallas-scratch2/claude/die-kv-39-1029/sdv2, plans in bindroot37/kv39/)
- plan_sd39c.json sha256 e390078bd319.., kitplan_sd39.json 59e0f76740ef.., sidecar_sd39.json ad34a88af7e7..
- strict bind (eB3b recipe + sidecar_sd39): errors 0 / unbound 0 / undriven 0 / multiply_bound 0 [CHECKED bind.log]
- kit-rtl + specialize rc 0 (clk_t5 in the kit wrapper); gen.py phys rc 0; KIT_PREFLIGHT PASS issues 0 (both)
  [CHECKED]; SDC create_clock clk on clk..clk_t5, OT_TAP_MAX_SINKS 2400, OT_TAP_TARGET_PS 250 (no hand edits).
- place + CTS + FF structural hold gate: LIVE (sd39_chain.sh STAGE=place then cts; declared FDI CDC = DIE-KV-38
  kv38_cdc_fdi.sdc appended to 3_place.sdc). Collect kits/<T>/hold_gate.log + chain_cts.log.

## Open (not in V2 scope)
- clk_clk_phy domain: PHY macro clk pin arrival 349 ps vs rq_d capture 753 ps (-186 ps in varA) is a separate tree
  (5259 sinks from one E-face port); taps above do not change it.
- sink_bins_file path is kv39/... relative to the tool root (run copy); a main landing needs it under results/.
