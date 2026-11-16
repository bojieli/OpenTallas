# FABLE-PD-S81-F2s3: r199 structural review of S81 plan event B6gF2s3 (2026-11-16 09:1x PST)

Plan: epyc10 /srv/opentallas-scratch2/claude/s81-b3-clk/ev/B6gF2s3.json, sha1 012db35daaea (the file is NOT on epyc7; the brief's path is wrong).
Base: ev/B6gF2s2_B6gF2sv.json a623deec2d38 (adopted). Bind was in G0 on epyc10 while I read (no non-advisory G0 line at 17:01Z; no BIND_RC / LATCHECK yet).
MEASURED = my reads of the two plan JSONs, the row files and the F2s2 bound RTL (run/b/B6gF2s2/out/rtl). No render was made and no kit result exists on these rows.

## Verdict: ADOPT-OK (no measured number fails a released type)

Subject to DIE-S81-92's own gates (BIND_RC 0, LATCHECK 873/873, G0 new 0). Col stays behind the col-wave pilot reads as already ruled.

## What F2s3 changes against F2s2 (MEASURED, whole-plan diff)

| key | types |
|---|---|
| ft_slots | 3: leaf t34, t47, t62 |
| hard_cores (origin only) | 216 col: 372 hw + 372 he origins swapped, 282 cfg7_seq moved |
| clock.taps (name / owner / note swapped, xy kept) | 216 col |
| clock.core_tap_lead_ps 200 | 216 col |
| clock.core_pin_lead_ps + cfg7_seq clk[0] 100 | 132 (col_h9_r1 60, col_h9_r2 60, col_h10_r2 12) |
| reset_replicate (copy_depth 3, region_re, cf_rs regex) | 216 col |
| contents, note | 16 svc |

Unchanged: die, partitions, ports (2,330), lanes (873), latency, top clock / reset, every bus and window, col internal_stations, outlines. So no lane budget and no abutment input moved; LATCHECK must come back equal to F2s2.

## 1. Row conflicts (strip vs y-slot)

- The y-slot rows (rows/G_yslot_rows_t38fix.json, 13 types) are already in F2s2: all 13 ft_slots blocks are identical to F2s2. In F2s3 they are a no-op on 11 types and are replaced on t34 and t62.
- F2s3 ft_slots of t34 / t47 / t62 equal the strip row files (G_t34 / G_t47 / G_t62_rows.json) slot for slot.
- Slots that differ from the y-slot form: t62 ft1, ft4, ft8 (the flag named 1 and 8 only; ft4 changes too), t34 ft2 (one station x 322.45 -> 318.13, 4.3 um) and ft5, t47 ft3 and ft6 (t47 has no y-slot row).
- In every changed slot: faces, width, station count, in / out windows, layers and order are unchanged. Only station sites move. No added cycle, no pin move.
- Strip rows also correct a stale N-face point: t62 ft4 and t47 ft3 regs_um[0] y 1226.88 -> 1278.72 (the outline height).
- Station sites of the changed slots: 0 inside a hard core, 0 outside the outline, 0 duplicate sites across slots.
- Per-bit hops between stations, max per slot: t34 ft5 207.4; t34 ft2 394.5 (as in F2s2); t47 ft3 236.5, ft6 339.1; t62 ft1 345.6, ft4 352.9, ft8 291.6. All at or under 405.
- Not a conflict: the override is the intended one (the strip kits c_t34 / c_t47 / c_t62 were the GRT-0 forms). The slot note text "ft_throat_fix 11-15" is stale on the moved slots.

## 2. Reset-copy hops vs 405 um

- The rows carry no sites. A copy chain is 3 kept flops per region with 2-pin nets; where they land is the placer's choice. The plan cannot show a hop length, so "405 or less" is NOT proven here.
- Depth census on the F2s2 bound RTL, all 216 types: every driver over min_loads 20 has depth 7..15, so copy_depth 3 applies in full (common D(n-3), never capped). The D(1) / D(2) drivers of the same name pattern have under 20 loads and stay untouched.
- Regions: region_re '^(.*)$' wins for the sinks; the sink instances are glue (u_u_y_rt_*, lpl, payload), not plan hard cores, so grid_um 300 does not apply to them. r2 had 68 copies in F2s2 and gets more (one per relay leg). The common flop then drives about 70..110 chain heads on one net.
- INFERENCE: the measured one-cycle spans were 780..816 um (F2s2 r2 CTS, -100) and 1,246 um (F2r routed, -151). Over the new hops that is 195..312 um per hop if the placer spreads the chain evenly, 3 hops if the chain heads cluster at the common flop (260..415). An uneven chain can still leave one long hop.
- Pilot read: report the longest hop of u_d*_Y_r<k>_s0 / _s1 / _r<k> and the reset-copy class slack. If a hop is over 405 or the class is under -42, the next delta adds sites to the chain flops.

## 3. Tap lead vs measured insertion

- core_tap_lead_ps 200 gives early = insertion - 450 + 200 on all 216: halves 465.39 -> 215.39 (was 15.39), bf_col3_c 434.57 -> 184.57 (was 0), bf16_half 303.17 -> 53.17 (was 0). These are exactly the F2r-tree values, which measured 460 / 468 on the 465.39 halves and 447 on c0 / c3 (FABLE-PD-S81-F2s finding 3). Consistent with the only measurement there is.
- Sequencer lead 100 (132 types) and the swap have no measurement on these rows. The r2 evidence pilot (epyc7 fable-fix-s81-coltap/ev1) ended with KIT_TOPOLOGY_BIND_STALE, exit 4: the F2s2 bind cannot carry the moved cores. The first read can only come from a kit on the F2s3 bind.
- Core tap ports after the swap: xy is kept and the name swapped, but the clock pin offset differs between the two macros (hw 148.152, he 148.728 from the origin). 744 core tap ports are now 0.576 um in x off their pin. Electrically nothing; fix the xy in the next delta if a G0 or kit pin-alignment check reports it.

## 4. Swaps, moves and strip rows vs lane budgets and abutment

- Lanes, latency table, ports, buses, windows and col internal stations are byte-equal to F2s2: nothing for LATCHECK or abutment to lose.
- hw and he have the same outline (268.38 x 221.4); a swap exchanges two origins. Hard-core overlaps in col: 1,320 in F2s2 and 1,320 in F2s3, the same pairs (u_w / u_e 0.54 um, u_c / u_ha / u_hb 0.888 um; outline rounding, pre-existing). No new overlap, no core outside its outline.
- The 282 moved sequencers: 0 overlaps with any hard core, 0 internal-station register or added clock tap within 2 um of the new footprint.
- Die clock ports: the 744 swapped tap rows keep xy and insertion (465.39 TT / 361.26 FF on both halves), so no die clock port or budget moves.

## Next-delta items (none blocking)

1. Sites for the reset-copy chain flops if the pilot shows a hop over 405 um (owner FABLE-DIE-S81).
2. Core tap xy on the 744 swapped half taps: move 0.576 um to the pin (owner FABLE-FIX-S81-COLTAP).
3. Refresh the slot note on the moved strip slots; DIE-S81-92's flag should list t62 ft4 and t34 ft5 as well.
4. Process: the adoption gate "r2 CTS read on the rows before ADOPT" cannot be met on the F2s2 bind (BIND_STALE). Generate the r2 pilot from run/b/B6gF2s3 as soon as the bind passes, before the adopt, or adopt and hold col on col-wave1 as HOLDGEN already does.

## Not checked

- No render, no kit, no CTS / GRT number on F2s3 rows. The 84 r0 / h10_r1 types have no measured tile at all.
- svc macro sites (16 svc types, contents + note): diff seen, not reviewed; svc stays held.
- Bind result, LATCHECK and G0 of F2s3 itself (still running).
- FF hold after the lead change.
