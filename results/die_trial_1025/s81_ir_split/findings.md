# S81.IR split adopted on S81 + S81 head (coordinator ruling 2026-10-25 03:08), 2026-10-25

Branch `claude/s81-plan-ir-1025r` (base origin/main 794550c822). Delta, not a regeneration:
`physical/die_plan/s81/delta_ir_1025.py PLAN.json` edits die.io, die.pg.domains and the serdes types' u_phy slot.

## What the split is on main's plan
- Free area = `die_io.phy_zone` (63.64-um guard clear of every ft band and bus boundary-flop strip, S81-XDIE form).
- PHY macro = that zone inset by the guard on every partition side facing core (only the die-edge side is not
  inset), capped at 2.4 mm2 by trimming the inner side in 8.64-um steps. die.io window = macro; u_phy content slot =
  macro (type frame, checked identical over all instances of a type).
- Domain = macro + 63.64 guard, clipped to the serdes partition (no neighbour, no overlap); `core_strip_um` = rest
  of the partition; `core_edge_bumps: relocate`; `phy_area_target_mm2: 2.4`.
- By construction every ft band / station / bus boundary-flop strip lies outside the domain (inside core_strip_um).
- check.py `pg_domain` (die_io.check_pg_domains) new rules: macro inside domain, window on macro, domain inside its
  partition, strip outside domain, domains never overlap (ERROR); macro < target = PHY_SHORT (WARN).
- `pg_domains.py` split is the default (`--no-split` for the old form); run_v4.sh passes `--split`; head
  `gen_plan.py` now calls the same pg_domains + delta (re-run verified: identical io / types).

## Per-partition result (S81)
| part | type | orient | macro mm2 | status |
|---|---|---|---:|---|
| lk_WS2, lk_EN3 | serdes__t14 | MX / MY | 2.41 | OK |
| lk_WN2 | serdes__t2 | R0 | 2.41 | OK |
| lk_WN1 | serdes__t1 | R0 | 2.41 | OK |
| lk_ES1 | serdes__t6 | MY | 2.41 | OK |
| lk_WN3 | serdes__t4 | R0 | 2.16 | PHY_SHORT |
| lk_EN2 | serdes__t13 | MY | 1.94 | PHY_SHORT |
| lk_WN0 | serdes__t3 | R0 | 1.85 | PHY_SHORT |
| lk_WS0, lk_EN0 | serdes__t15 | MX / MY | 1.33 | PHY_SHORT |
| lk_WS1, lk_EN1 | serdes__t16 | MX / MY | 1.33 | PHY_SHORT |
| lk_WS3 | serdes__t12 | MX | (0.67) | left unsplit: 14 sites < 26 signals |
| lk_ES0 | serdes__t5 | MY | - | left unsplit: zone off-shore (ft strip on die-edge side) |

Head: all 12 windows (one type hd_serdes) 2758.48 x 872.64 = 2.41 mm2, OK. Its bus boundary-flop strip
(150 um behind the S/inner face) is in the 290.6-um core strip.

No neighbour types changed and no face windows moved: the delta only edits the serdes types' u_phy slot.

## Why 8 S81 windows are short (structural, not fixable inside "serdes + direct neighbours" without squeezing)
The coll chains run along the serdes rows (WS2-WS1-WS0-WS3 -> s_0S_x00, etc.), so a serdes partition carries its
farther neighbours' 512/514-b buses as E-W ft. An E-W ft band crosses the full partition width, so a 2.4 mm2 macro
(<= 2758.48 wide, >= 870 um deep) leaves <= 290 um of strip.
- t15 / t3 (WS0, EN0, WN0) carry 4 through-ft = 2052 bits + 1026 own bus bits on one face. 2052 bits alone need
  >= 342 um at the 6 pins/um budget, so they cannot fit in 290 um. Best case with the current 111-um windows is
  about 1.96 mm2.
- t16 (WS1, EN1) can reach 2.44 mm2 by re-laying its windows: ft at local y 6-228, buses at 231-452, macro
  x 63.6-2672 x y 292-1227. That moves face windows shared with t14 and t15 (all serdes types, plus their port
  window_um). Not done here, because t15 stays short anyway.
- t12 (WS3) has 6 L-route ft + 2 buses on 1443 x 2454: about 1.9 mm2 at most even fully compacted.
- t5 (ES0, MY at the south edge) has its ft strip on the die-edge side. The fix is ES0 + ES1 to R180, and that moves
  the E-face windows of neighbour s_7S_x10 (slice_station__t23).

Options for the coordinator:
- (a) Re-route the far links' coll buses off the serdes row.
- (b) Serdes partitions with through traffic 2 lattice rows tall.
- (c) Accept the smaller macros. In this IR model all but WS3 pass at 4.368 W, see below.

## IR on the new plan (window PDNSim, method + tool = claude/s81-ir-1024r@de34b76ca1 s81_ir_domains.py)
Gate 35 mV per rail. PHY load 6 x 112 Gb/s x 6.5 pJ/bit = 4.368 W per window, spread over the macro. Core 0.15 W/mm2.
Runs were diagnostic docker probes on epyc2 (8 threads, 64 GB cap): `epyc2:/srv/opentallas-scratch2/claude/s81-plan-ir-1025/<case>`.

| case | domain box | load W/mm2 | VDD | VSS | VDDPHY | VSSPHY | verdict |
|---|---|---:|---:|---:|---:|---:|---|
| S81 A core (WS2/WS1/WS0/WS3) | - | 0.15 | 29.6 | 30.3 | - | - | PASS |
| S81 A b0 | WS2 | 1.81 | | | 13.5 | 11.5 | PASS |
| S81 A b1 | WS1+WS0 | 3.29 | | | 21.4 | 19.7 | PASS |
| S81 A b2 | WS3 (0.67 mm2 sliver) | 6.52 | | | **50.4** | **40.3** | FAIL |
| S81 B core (EN2/EN0/EN1/EN3) | - | 0.15 | 28.0 | 29.5 | - | - | PASS |
| S81 B b0 | EN2 | 2.25 | | | 14.9 | 17.2 | PASS |
| S81 B b1 | EN0+EN1 | 3.29 | | | 22.0 | 17.4 | PASS |
| S81 B b2 | EN3 | 1.81 | | | 15.8 | 10.2 | PASS |
| head A core (WS1/WS0/HOST0/HOST1) | - | 0.15 | 29.0 | 29.9 | - | - | PASS |
| head A b0 | WS1..HOST1 (one abutted box) | 1.81 | | | 13.4 | 12.8 | PASS |

Notes:
- The S81 cases were generated before lk_WS3 was reverted to the unsplit main form. Its domain rect is the same in
  both, [9777.37, 103.68, 10203.84, 2407.44]. Main's window is 363 um wide instead of 299, so the load density is
  5.4 W/mm2 instead of 6.5. VDDPHY scales roughly linearly with that density, so WS3 would still be about 42 mV and
  still FAIL. The WS3 PHY does not fit at all: G0C reports 14 sites < 26 signals.
- Head A: the first b0 run, with the window to x 11837, failed setup ("no actual M9 metal for VDDPHY sources"):
  the clipped ES0 domain sliver at the window edge got a source with no M9 under it. It was re-run with the window
  ending at 11646.72, which excludes ES0. ES0 was not judged in the 10-24 run either.
- The maps (`ir_map_*.png`) are uniform up to the domain edges. Core VDD/VSS stay at or below 30.3 mV next to the
  domains, which confirms the edge relocation. VDDPHY peaks at the macro E/W ends.

## Checks
- S81: schema PASS. G0 PASS (0 errors). G0C PASS (0 errors, 178/178 types clean). 8 pg_domain PHY_SHORT WARNs.
- head: schema PASS. G0 PASS. G0C PASS (0 errors, 16/16).
- pytest tools/die_plan test_schema / test_xdie / test_xdie_io / test_check: all pass.
