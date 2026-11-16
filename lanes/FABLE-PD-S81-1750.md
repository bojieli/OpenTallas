# FABLE-PD-S81-1750: S81 plan event B6gG3, structural PD review

2026-11-15 18:35 PST. Fable PD review for COORD; cc DIE-S81-92, S81-PHYT1, S81-BANDTAP-1115, S81-TAPROWS, WAVE-HOLDS-1115, KIT-OPS-5.
Read on epyc10: composed plan ev/B6gG3.json (compose rc 0, 01:34 UTC), log/B6gG3.log, the bind tree run/b/B6gG3/src, B6gE.json, the B3v plan.
Scripts and outputs: epyc10 /srv/opentallas-scratch2/claude/fable-pd-s81-1750/ (x2..x6.py, l2.py, l2.out; l1.py on epyc7). Read-only, nothing written to a plan, kit or wave file. The G3 bind was still running; no bind or LATCHECK result is used here.

## Verdict

The G3 plan is sound as a plan (compose OK, 0 placement failures, 0 landing errors, no released type over the tap cap). Adopt it when the gate passes. But the release list is wrong in one place and it will fail at kit generation on the first launches:

**58 non-col types still fail sdc_lint on G3: all 46 slice_station, all 11 serdes, kv_leaf__t2.** The drop removed 120 tables; 275 remain (216 col + 59 non-col). The lint failure is not caused by stale tables. The S81 kit tool tree has a gen_phys.py that writes the offsets form and an sdc_lint.py that does not know it, so every type that keeps a table fails, stale or not. Dropping a table cures that type; keeping one does not.

## Measured

1. sdc_lint on the G3 plan with the G3 tree (gen_phys.sdc + sdc_lint.kit_context + sdc_lint.lint, l2.py):

   | type | offset table in G3 | lint errors | window the SDC gets |
   |---|---|---|---|
   | slice_station__t8 | kept | 53 | offsets, span 52.9 |
   | slice_station__t45 | kept | 16 | offsets, span 27.6 |
   | serdes__t4 | kept | 43 | offsets, span 59.7 |
   | svc_hi_dsdv_svc_rs__t2 | dropped | 0 | flat 79 |
   | iqf__t1 | dropped | 0 | flat 80 |
   | phy__t1 | kept (1 row, clk = 0) | 0 | none: W = 0 on all 32 taps |

   Error text, every row port: "clock port clk_t1 window early 15.5 / late 15.5 ps, plan clock.tap_window -52.9 / 0". Same text on the failed wave kit serdes__t15__cla3d02796 attempt_5 (epyc7, 59 errors, re-run with the kit's own sdc_lint.json). `grep -c tap_offset`: gen_phys.py 22, sdc_lint.py 0, in run/b/B6gE/src and in run/b/B6gG3/src.
   Tested 3 of the 58; the other 55 carry the same table form (not run).

2. The 59 kept tables are not "unchanged" on G3. Taps B3v -> G3: 26 slice_station types gained 1-18 explicit taps (t49 69 -> 87, t38 54 -> 65, t8 53 -> 61, t24__cl64811a5d 36 -> 44); phy__t1 went from 1 tap to 32. No tap moved. The earlier comparison was B3v vs B6gE_pre, before the eventG rows.

3. What replaces a dropped table (120 types): the window form. 16 svc types, iqf, c3x_C, iq_C, lepw_mus_C: flat per-type W on every port (svc 62-98 ps). The rest: the older per-port table, and a port without a row takes the per-type W: leaf 1,855 of 4,273 tap ports, c1x_C 200 of 464, kv512_C 48 of 50. Largest window per family: leaf 208, c1x_C 156, kv_leaf 148, gunit 139, eng 98.
   Two types fall to the die flat 208 ps on every port: dsdv_slice_c3x_C__t1 (53 ports) and dsdv_slice_iq_C__t1 (59). Four LP types have at least one port at 204-208.

4. svc_hi t2 taps (36 glue, 64 core): the 7 new taps clk_t29..t35 sit 4.32 um from the nearest attnh_i0 piece (the cut window) and 4.32-6.0 um from the nearest core or macro edge (t29 4.32, t35 4.38). Tap to tap spacing is 63 um or more. Ten older taps on the y = 17.312 row (clk_t2..t10, t12) lie inside a band rect with no window, and clk_t13/15/17 are 0.48 um from hbm_i0. tap_reserved_um of t2 lists only the 7 new squares.
   tap_clear_um is read by schema.py and taps.py only (0 hits in gen_phys.py and clock_taps.tcl): it is a plan legality rule, the kit does not use it.

5. Bands (93 in band_fixed_um over 10 svc types): 14 have a pin-to-band hop of 401.98-402.81 um (BANDTAP counts 23 on the die). All 14 are input rings. Nearest glue tap count per band: attnh_i0 16 (hi t1), 14 (hi t2), 13 (hi t3), 18 (hi t6); attn_i2 13-15; attn_i0 hi t6 12. The pin's nearest tap is among the band's taps on 10 of 14. No svc type has a clock.tap_group, and all 16 svc types have a flat window with no per-port table.
   Ring split by clock role, attnh_i0: 8,704 forwarded-write flops on fclk_in_attnh_i0, 2,176 local-read flops on the taps. Largest: attn_i0 on hi t6, 16,128 write flops on one fclk port.
   Area: 12 multi-rect bands are 0.3-2.0 % below their own area_reserve_um2 after the cuts (hi t2 attnh_i0 9,446 of 9,634; attn_i1 7,294 of 7,395). Thin pieces: hi t6 attnh_i0 has a 2.16 um piece, hi t4 rsv_i0 3.09 um. 16 multi-rect bands carry no band_use value.

6. Tap cap, compose log: no tap over 1,500 in svc, slice_station, serdes or phy. Over the cap only in col (held) and leaf: t14 clk_t35 1,891, t51 clk_t31 1,546. In the kit an over-cap tap is a WARN (clock_taps.tcl line 638), not a stop. Leaf radius over the 200 target on 46 lines, up to 300.6 um (t45).

7. ev/B6gG3.json was not on epyc7 at 18:10 PST. The wave kits link kit_tools to run/b/B6gE/src, whose schema does not know the BANDTAP keys (the G1d gate failure).

## Answers

(1) Tap-offset drop. The 120 dropped types get valid window SDC and pass lint (2 of 2 tested). slice_station__t8 / t45 and serdes__t4 are not in the drop and still fail. Setup at the gate for the dropped types: the offsets form (tol 0) charged a cross-port pair only the offset difference; the window form charges the capture port's window on setup and the launch port's on hold. So cross-port paths are tighter by 62-98 ps on svc, up to 208 on leaf ports without a row, 208 on c3x_C__t1 and iq_C__t1. This is the correct charge for an unmeasured tree (the old offsets described a different tap set), but it is not free: the two 208 types repeat the col window problem (416 of 833 ps on a cross-port pair). The cure is a measured per-port table on the G3 tree, not a kit setting.

(2) tap_clear 4.32 on svc_hi t2: low risk (INFERENCE). A tap is an M9 drop plus one root buffer; 4.32 um is 16 rows. The older taps of the same type already sit inside bands. The place to look on the first kit is the core side: t29 and t35 are 4.3-4.4 um from a core edge in a channel that also holds the band column.

(3) 401-403 um hops: low risk as distance. The hop is on the forwarded clock (write side), so it does not pay the tap window (INFERENCE from clock_roles). The exposure is elsewhere: the 2,176-4,032 local-read flops of one ring are spread over 12-18 taps with a flat 62-91 ps window on setup and hold between them, and the fclk tree of a 13-18 piece band spans about 520 x 290 um. Lever 8's "pin flop and ring stage on one tap" is not in G3 and cannot be done by position for these bands. Read on the first svc_hi kit at CTS: fclk insertion spread per band, ring cross-tap setup TT and hold FF.

(4) First-wave kit failures: (a) sdc_lint on the 58 types, certain; (b) schema refusal if any gen host still links B6gE/src, certain on such a host; (c) nothing on the tap cap.

(5) Not fixed by G3: below, items 3-7.

## Ranked fixes

1. **Lint for the 58 kept types. Owner DIE-S81-92, before the release line.** Add the 58 non-col tables (and phy__t1, item 2) to the drop as a one-key delta on G3: plan-key only, no bind input, partition or lane change. 43 slice_station and 8 serdes types then use their per-port tables (t8 23-52 ps, t45 10-36, serdes__t4 57-109). Until then WAVE-HOLDS keeps slice_station__*, serdes__* and ot_s81sl_kv_leaf__t2 held; the "sdc_lint core-tap class" release covers only the 120 dropped types. Alternative: an sdc_lint.py that accepts the offsets form in the kit tree. Not recommended for these types: 27 of the 59 tables no longer match their taps.
2. **phy__t1 window. Owner S81-PHYT1 with DIE-S81-92.** Its one-row table gives W = 0 on 32 taps (MEASURED), so no cross-tap pair is charged anything while the kit CTS measured 249-400 ps tap insertion. Drop the row (W becomes 20, clk 10) in the same delta as fix 1. The 405 ps root tap against the 270 check stays open in PHYT1.
3. **Measured per-port windows on the G3 tree. Owner S81-TAPROWS** (die-proof STA, die_sta_related --kit-window-out). Order: c3x_C__t1 and iq_C__t1 (208 flat), the 16 svc types (flat, no table), leaf (1,855 ports without a row), then the 26 slice_station types with new taps. This is the same run the col delta needs.
4. **Replicate before release. Owner DIE-S81-92 / KIT-OPS-5.** ev/B6gG3.json, the sidecar and run/b/B6gG3/src on every gen host; the wave S81 src switched to the G3 tree in the same commit as the release.
5. **svc first place and CTS read. Owner S81-PHYT1 (pilot svc_hi t2 and t6).** No svc type has been past synthesis on a landed plan. Read: ring cells outside their band; fclk spread per band; ring cross-tap slack; DRC near clk_t29 / t35; OT_CLOCK_TAPS dropped taps (the hole and t2 taps show load 0 in the plan estimate because band flops are not in it). If ring cross-tap hold fails: a per-ring tap_group, new lane or S81-PHYT1.
6. **Band generator order. Owner S81-BANDTAP-1115 / CLKSITE-RESERVE-1115**, next compose only: windows for the existing row taps (10 inside bands on t2), restore the cut area so no band is under its reserve, no piece under 4.32 um.
7. **Not in G3, next blockers of released types:** col (Event F part 2: per-port window + IFN 0 + ROM tap rows, 216 types); `DRT-0255` on leaf t25 / t54; FF hold at the gate (23 of 38 S81 kits at 17:15); leaf taps over the cap or radius (t14 1,891 sinks, t45 300 um); the svc attn core tap insertion 364.38 / 291.94 comes from a view its own plan note marks NOT SIGNED (REPORTED).

## Stop list

- Releasing slice_station, serdes or kv_leaf__t2 on G3 adoption without fix 1.
- Reading the sdc_lint class as "stale table": it is offsets form against a lint that predates it.
- Bypassing sdc_lint in the kit, or widening the lint by hand per type.
- Re-floor or band moves for the 401-403 um hops.
- A tap_clear change or tap moves on svc_hi t2 before a kit DRC result.
- Judging c3x_C__t1 / iq_C__t1 setup at the gate with the 208 flat window, or repairing against it.
- Raising tap_max_sinks to clear the leaf over-cap lines.

## Limits

Lint run on 6 types. No STA was run: the setup and hold statements in answers (1) and (3) are SDC arithmetic and plan geometry, not slack. Band tap sets use the nearest glue tap by L1 distance on a 20 um sample, not the kit's assignment. The 23-band count is BANDTAP's; I see 14 in band_fixed_um. Bind and LATCHECK of G3 not finished when this was written.
