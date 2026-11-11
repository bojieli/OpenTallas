# hbm-channels-1111 (DIE-HBM-97/98 HBM-CHANNELS, DO_NOT_COUNT)

**Scope (COORD 02:0x, via DIE-HBM-98).** This is an input to the ONE combined HBM plan event composed at 12:00 PST. It is not a standalone plan event: there is no standalone READY and no KW-FIX-43 relaunch. KW-FIX-43 builds one canonical bind on the combined plan. The strict bind of fd512301 was cancelled before it ran.

Replay:
- Command: `delta/replay_chan.sh BASE_DIR OUT_DIR REPO [BOUND_RTL_DIR]`. The base is 29333b2b.
- It runs mk_chan_event.py, then ccd_pending.py, then core_conns_batch.py.
- It reproduces plan/ byte-for-byte; this was checked on epyc7.
- Keys are disjoint from HBM-FTROUTE (q_b100..q_b103 ft and the L1220/L1200 windows) and from FTRES-FIX (die_share/core_share on existing die_ft_bands). Both were checked and agreed.

This is a gated plan event on plan_p11t_taps_cyc 29333b2b19c9.
- Result plan: plan_p11t_chan **fd5123010508864c82549536c8a04b4db9bc826cd60b945384f3f489c9c3e02a**, at epyc7 /srv/opentallas-scratch2/claude/die-hbm-97-channels/plan_p11t_chan/.
- The gzipped copy in this directory is plan/die_plan.json.gz. The plan dir SHA256SUMS was regenerated and all 515 files pass.
- Builder: mk_chan_event.py, run as `mk_chan_event.py BASE OUT REPO` (it asserts the base sha).
- Full report: channels_1111_event.json.

## Rulings applied
- COORD ruling on hbm-channels-ask (relayed by DIE-HBM-97, 11-11):
  - (1) SU-CHAN for q_su11/pv1 and q_su01/pv1.
  - (2) b-type stations move into the E street, and opposite-face crossings are straightened.
- DIE-HBM-98 rulings (11-11):
  - (C) kv_line grows south.
  - (D) q_mcb is split.
  - The core_conns sidecar is regenerated.
- COORD counted-plan items (via DIE-HBM-97):
  - full_x is NOT-IN-PLAN.
  - The static_front E/W switch. Both items are under "Counted plan" below.

## (A) SU-CHAN
Rows and columns of cores are pushed apart, on the 8.64 um lattice, to open routing streets. Content leaves within 60 um join a column or row band as rigid content.

| Type | Street | Columns, old x -> new x | Row shift (dy) |
|---|---|---|---|
| q_su11 | 69.12 um | 941.76/1356.48/1900.8 -> 708.48/1278.72/1892.16 | -43.2/-34.56/-34.56 |
| q_su11pv1 | 69.12 um | same as q_su11 | -17.28 each |
| q_su01 and pv1 | 120.96 um | 319.68/777.6/1235.52 -> 319.68/889.92/1460.16 | -103.68/-86.4/-60.48/-34.56 |

- Moved clock and reset taps: q_su11pv1 at (1205.28, 518.4); q_su01 and pv1 at (885.6, 470.88).
- 0 new geometry errors (net of the base's own).
- Stations were re-derived by the generator rule (b2n RelayRouter, HOP 360 / REACH 405). The finer routers and even chains are kept only where they do not raise the count.

## (B) b types (q_b000/pv1, q_b011/pv1)
All W-strip internal stations moved into the E street, with register counts kept:

| Type | Links moved | Bits | Registers | E street (x) |
|---|---|---|---|---|
| q_b000 | 15 | 19014 | 72 = 72 | 280.8-453.6 |
| q_b011 | 51 | 10696 | 192 = 192 | 280.8-375.84 |

0 registers are left in the W strip.

Straightened crossings:
- q_b011/pv1 L51x4 (612 bits, E->W, -167.232 um). Station counts are 2 = 2.
- The neighbour window changes. q_b002/pv1 L51x5 in_window goes from [796.608, 908.16] to [629.376, 740.928]. Both sides were checked: they match, and the station counts are kept.

Skipped crossings (listed in the event under straight_skipped):
- 46 overlap another window;
- 24 end at a bus on the neighbour side (moving a bus pin is out of scope);
- 2 would need more stations.

## (C) kv_line south grow (DIE-HBM-98)
- Applies to u_sm_front_kv (ot_hbm_sm_kv_line) in q_sm0..3.
- Outline 734.4x233.28 -> 734.4x388.8. Origin y 2004.48 -> 1848.96, which leaves 17.28 um clearance above the L1 cores at 1831.68. The W, E and N faces stay fixed.
- Slot check on the base: clear of all cores, leaves, ft slots, stations and bands, on all 4 types.
- The pins file was re-derived: cores/ot_hbm_sm_kv_line__734.4x388.8__kvs1111.json, 2158 pins (N 1024, S 1088, E 23, W 22, I 1). Non-S pins move y+155.52, so they stay at the same die point.
- The EQ gate checked that names, layers, directions and faces are the same, and that every E/W pin y is inside the old span.
- clock_entries u_sm_front_kv xy/island +155.52 local (the same die point).

## (D) q_mcb split (DIE-HBM-98, COORD fail_watch)
- Why: q_mcb has 2 instances with different S_u_refcfg_Q_tgt (NE 8'b10000001, NW 8'b01111111). That parameter drives u_refcfg_Q.tgt, and kit-rtl cannot kit a type parameterised per instance.
- The split:
  - q_mcb_ne (NE_mcb, module hbm_arch_q_mcb_ne);
  - q_mcb_nw (NW_mcb, module hbm_arch_q_mcb_nw).
- Each new type is json-equal to q_mcb apart from module and note. The EQ gate type_split check passes. Only the instance-to-type map changes.

## (E) root reset source text (DIE-HBM-98, note only)
- root u_tkm_SW_root (ot_hgi_coll_tkm_m_tp192__root): reset_from_master.source now cites the extraction the plan actually uses.
  - That extraction is rest_extract_mem.sh part 19 of ot_hgi_coll_tkm_m_tp192_pfdh32 (static_pdh, PTILE 32), minus the 64 half-tile cells (BIND-SUBTYPE-2).
  - Before, it cited the 10-23 static_p extraction.
- Only that key changes. The EQ gate lists it under note_text_paths.

## Cycle event (NOT EQ by construction): needs its own bind
The bind is plan_p11t_chan's own; see "Bind" below.

| Kind | Where | Change | Lane cycles |
|---|---|---|---|
| ft stations | q_su11 L8301mx1, L8302mx1 | 6 -> 7 | |
| ft stations | q_su11 L8314mx1 | 7 -> 8 | |
| ft stations | q_su11pv1 L8302x1 | 6 -> 7 | |
| ft stations | q_su11pv1 L8314x1 | 7 -> 8 | |
| ft lanes | L8301m, L8302, L8302m, L8314, L8314m | | +1 each |
| internal stations | q_su01pv1 bus:L5090_o | 3 -> 5 regs | L5090 48 -> 50 (fixed_cycles 3 -> 5) |
| internal stations | q_su01pv1 bus:L5091_o | 3 -> 4 regs | L5091 47 -> 48 (fixed_cycles 3 -> 4) |

- Bind native_istations requires fixed_cycles = source plus destination registers.
- latency.lanes keeps its param keys.
- Reset/native contract: the native internal-station lanes L5090 and L5091 change their fixed_cycles. That is a native-contract change, so this plan needs its own bind; the base bind does not carry over.
- Link classes:
  - L5090/L5091: native internal-station data lanes, NE_su01 (q_su01__physical_v1) .L5090_o/.L5091_o -> NE_hub (q_hub_ne) .L5090_i/.L5091_i; 21 b and 41 b. They carry bank_read_data.
  - L83xx: hub->SM data lanes through the q_su11 / q_su11pv1 ft slots, q_hub_ne/q_hub_nw .L30_o/.L31_o/.L98_o -> q_sm1 .L30_i/.L31_i/.L98_i; 1615 b / 1615 b / 22 b.
- latency_groups: no entry names these lanes, so it is unchanged.
- compiler_core_delta.json pending_not_folded[hbm-channels-cycles-1111] holds the HBM-TAPS price (RESULT hbm-channels-cycles):
  - The max SU->hub leg is L1271 at 66 (NE L5094 at 64), so the expected delta is +0 and the rate stays 1648.00 tok/s.
  - The bound is 1642.88 tok/s (-0.311%). The hub->SM lanes are also +0.
  - The affected types count only after the scheduler/token check on the new cycles passes.
- Stage-equivalence proof (sat-tempinduct or lock-step vs the shifted golden) for the extra stations: **MISSING**.

## Price (compiler S2, price_chan_cyc.py -> price_chan_cyc.json)
TOK-VERIFY-1:

| Case | tok/s | Change |
|---|---|---|
| ref | 1660.07 | |
| SM+1 (ft lanes) | 1659.55 | -0.032%, +211 cycles |
| SU+2 (upper bound covering L5090 +2) | 1654.89 | -0.313% |
| both | 1654.36 | -0.344%, +2287 cycles |

## G0 (tools/die_plan/check.py; g0/)
- Errors: 639 -> 629 (new 3, gone 13).
- The 3 new errors:
  - L8008 su00 S0->S1 737 um. This was hidden behind su11 742 in the base.
  - L8302 and L8302m hop 3 at 482 and 477 um. The base had 843 here.
- Warnings: 1423 -> 1432. Counting q_mcb_ne/nw as q_mcb, the changes by check are:

| Check | New | Gone | Note |
|---|---|---|---|
| core_faces | 12 | 6 | G0C, b types, from the E-street stations; advisory |
| clock | 4 | 3 | |
| reach | 3 | 5 | |
| schema | 3 | 0 | the q_mcb rows now appear for both split types |
| types | 1 | 0 | the q_mcb_ne/nw near-duplicate pair, expected for the split ruling |

- Errors by check: hops new 3 / gone 5; stations new 0 / gone 8.

## EQ gate (eqgate_chan.py -> eq_gate_channels.json)
- Verdict: EQ_BY_CONSTRUCTION_EXCEPT_CONTRACT, with 0 non-position paths.
- The contract paths are the ones in the table above.
- Outline/pins paths: kv_line only, with the pins check passing.
- type_split: q_mcb_ne and q_mcb_nw json-equal.

## route_supply (advisory; route_supply/)
Route_supply was rerun with the regenerated core_conns (route_supply/{base,new}.cc_regen.tsv, all types). p99 ratios, base -> new:

| Type | Base | New |
|---|---|---|
| q_su11 | 4.702 | 2.166 |
| q_su11pv1 | 4.622 | 2.348 |
| q_su01 | 2.200 | 1.921 |
| q_su01pv1 | 2.200 | 0.812 (ok) |
| q_b000 | 8.720 | 4.145 |
| q_b000pv1 | 7.107 | 3.965 |
| q_b011 / pv1 | 6.044 | 5.387 |
| q_b002 / pv1 | 6.108 / 6.164 | unchanged |
| q_sm0..3 | | unchanged |

- No type gets worse.
- Model: 64 types core_conns; 18 types have no hard cores (model none, including q_mcb_ne/nw). No type is on the centroid fallback.
- Earlier runs, from before the kv change and the core_conns regen, are kept as pre_kv.*.tsv.

## core_conns (DIE-HBM-98 (a))
- Built with core_conns_batch.py from plan-route-3 7a3db5b6b652 (delta/), `PLAN PICKS OUT`, with no --base. PICKS = plan/core_conns_picks.json.
- Bound .sv source: the strict base bind bind_p11t_taps_cyc_vK5d_c12/rtl. That bind is 29333b2b, the same bind recipe.
  - The event does not change any bound bus or core partner name, so the base bind's wiring holds for this plan.
  - Station counts and core moves do not rename partners. q_mcb_ne/nw have no hard cores. kv_line keeps its port names.
  - The fresh bind of this plan was cancelled by the scope change; KW-FIX-43's combined bind replaces it.
- 64 types traced; 281/2553 cores wired. The others get {}: their pins land on the type's own logic, which route_supply treats as glue escape.
- Stale refs (bus or core names not present in this plan): 0. The previous sidecar had 249 stale refs in 27 types.
- Centroid fallback: 0 types.

## Bind
- A strict bind of fd512301 was set up (kits/bind_chan.sh; recipe = the bind_taps.sh recipe with a cp -al overlay). It was **cancelled** per the COORD 02:0x scope change.
- Two bind findings were fixed in the plan along the way:
  - native_istations requires lane fixed_cycles = source + destination stations, which gives L5090 3->5 and L5091 3->4.
  - dead_input_proofs must resolve inside the repo; this concerns the overlay form only, not the plan.

## P&R checks (kit_wave run-item: place + GRT)
Not run as standalone checks. Under the scope change, KW-FIX-43 builds and P&R-checks the types after the 12:00 compose.

Types this event touches:
- q_su11, q_su11pv1, q_su01, q_su01pv1;
- q_b000, q_b000pv1, q_b011, q_b011pv1, q_b002, q_b002pv1;
- q_sm0..3 (kv_line slot);
- q_mcb_ne and q_mcb_nw (new types);
- root (note only).

## GRT calibration (q_su01, epyc2 scratch3)
- Arms on q_su01, base vs new, running at epyc2 /srv/opentallas-scratch3/claude/die-hbm-97-channels/grt/q_su01/{base,new}. Ideal clk and power nets are marked special.
- Routing resources M4-M7: base 33.6M / 46.2M / 31.4M / 44.7M vs new 53.1M / 57.3M / 51.8M / 58.3M. That is +58% / +24% / +65% / +31% original resources from the opened streets.
- Congestion iterations are still running (base at extra iteration 2/10, new at 3/10). The final overflow is not in yet.

## Counted plan overlay (count/nip, count/nip_sfs; for the 12:00 compose, not installed under plan_of_record)
- Built by mk_count_chan.py on the counted n4x plan (gz sha 4873c1b449fd).
- Design ids come from coord tools/release_tree_plan.py plan_designs.

Changes in the overlay:
1. full_x is NOT-IN-PLAN.
   - The 4 entries (q_su00, q_su10 and their pv1 types, u_su_Q*_lane_exp0__l) now point at the wave plan's exp_x core (319.68x207.36, cores/...__d44v_split__oneclk.json).
   - That pins file is byte-identical to main plan_of_record/d44v/cores.
2. kv_line south grow, the same as (C).
3. q_mcb split, the same as (D): types 81 -> 82.

The root note (E) and the cycle event do not change design counts.

Design counts:

| Overlay | Designs | Dropped | Added | gz sha |
|---|---|---|---|---|
| nip | 119 -> 119 | full_x_core, exp_x_core | exp_x_core#319.68x207.36/497e2cbc239497b1, exp_x_core#328.32x207.36/37e7d22da25189e4 | aad3501be3ff |
| nip_sfs (static_front E/W split) | 119 -> 120 | + ot_smh_static_front | + ot_smh_static_front_e, ot_smh_static_front_w | 585712e4d16f |

- The existing exp_x design id gets an outline/pins suffix, because exp_x now has two designs.
- The kv_line design id stays ot_hbm_sm_kv_line, but with the new outline and pins it needs the new-outline sign-off.

static_front E/W switch: NOT applied.
- Trigger: ot_smh_static_front_w AND ot_smh_static_front_e both signed off. They are not signed off now: W RR6 has TT -49.53 rst recovery, and E D04/D04R has a GRT broad band.
- To switch: install count/nip_sfs as the counted plan, or rerun `mk_count_chan.py ... --sfs`, and point PLANS['hbm'] in coord tools/release_tree_plan.py at it.
- Until then, the counted plan is count/nip.

## Rev 2 (11-11, for the 12:00 compose): die_plan 85df1184ecea…

Rev 2 answers the DIE-HBM-98 and HBM-COMPOSE asks (a)-(d).

The plan dir on epyc7 is `/srv/opentallas-scratch2/claude/die-hbm-97-channels/plan_p11t_chan` (532 files, `SHA256SUMS` sha256 b7ef1e90457bf52a…). Rev 1 is kept in `plan_p11t_chan_rev1_fd512301`.

Replay: `delta/replay_chan.sh BASE OUT REPO BOUND_RTL`. The expected die_plan sha is 85df1184….

**(a) G0 hops.**
- L8302 and L8302m are clean. Their station regs_um are re-sited, with no extra cycle, and all hops are <= 356 um.
- L8008 is a pre-existing lane error. The lane message now names the next base slot, NW_su00.L8008x6 at 737 um, which was already an error in the base. The G0 diff is in `plan/g0diff_channels.json`: errors go from 639 to 627.

**(b) Stage-equivalence proof.**
- `proof/eq_stations.json` gives ALL_EQ_CYCLE_SHIFTED on all 7 links: new == base delayed +k.
- In each case the negative controls (k-1 delay, and a data-bit bypass) fail.
- The tool is `delta/eq_stations.py`.

**(c) Intent sheet.** See `plan/intent/INTENT_SU_CHAN.md`, the 4 SVGs, and `intent_su_chan.json`.

**(d) q_b112pv1 0.778->1.18.** This was a model artifact of the trace-only core_conns. The plan does not touch q_b112. With the merged sidecar (`delta/cc_merge.py`) the value is 0.778 -> 0.778. On like-for-like route_supply runs, 26 types are better and 2 are worse; see `route_supply/route_supply_*_*.tsv`.
