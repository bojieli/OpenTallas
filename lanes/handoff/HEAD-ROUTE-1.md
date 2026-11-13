# HEAD-ROUTE-1 handoff (HEAD rp18 DRT-0255 class fix; COORD is the coordinator) -- 2026-11-12 22:10 PST

## State
- Worktree: epyc9 /srv/opentallas-scratch2/claude/head-route-1/wt (branch claude/head-route-1-1112 off origin/main 7073a6b4a5).
- Diag dir: epyc9 /srv/opentallas-scratch2/claude/head-route-1/diag_turn_b (rp18 hd_turn_b 5_1_grt.odb + m8_grant.json).

## Finding so far (UNCHECKED)
- All 4 crashes fail on M8 (DRT maze z=7) at route-box boundary points; DR violation counts scale with M8 wire
  (turn_b 4734 / M8 1.3 mm; turn_a 14486 / 13.7 mm; wshim_rx 39903 / 90 mm; wshim_tx 82581 / 207 mm).
- rp18 is the first HEAD kit with the M8 grant (LAYER-BUDGET-1, tools/die_plan/m8_grant.py): MAX_ROUTING_LAYER M7 -> M8,
  pdn.tcl obstructs every run of die M8 tracks with ONE rect. A PG run of 8 tracks -> 0.60-um-wide rect (real PG stripe 0.48).
  ASAP7 M8 SPACINGTABLE: width >= 0.49975 at PRL >= 1.79975 needs 0.5 um spacing -> DRT keeps 0.5 um from every
  obstruction on long runs: ~7 of the 19 granted tracks per 2.16-um period are usable, GRT counts 19.
  m8_grant.py assumes MIN_SP 0.04 for its own merged rect.
- Running: diag A (as-built, 1 DR iter, DRC types) and diag B (per-track 0.04 obstructions, full DR on the same guides).

## 2026-11-12 22:19 update
- Diag B (per-track 0.04 obstructions, same guides) FAILS at the same net/box as A (t_i[104], iter 1). The wide-obstruction
  spacing is real (m8_grant.py change kept in the worktree, tests pass, HEAD grant sha unchanged) but it is NOT the crash cause.
- Failing nets (t_i[104], u_ft_t_s1/net8427) have NO M8 in their guides (M7 vertical column); the failing source ap is
  an M8 boundary point at the guide-column edge = route-box edge, boxed in (M7 RIGHTWAYONGRIDONLY, off-track x).
- Running: A2 (DRC types per iteration), C (re-GRT M2-M7 then DR), proof_turn_b (full kit with the m8 change, route goal).

## 2026-11-12 22:30 update (diag matrix on rp18 hd_turn_b 5_1_grt.odb, epyc9 diag_turn_b/)
- A as built: DRT-0255 t_i[104] iter 1. A3 iter-0 DRC: 166 M8 shorts to the grant obstructions (DRT boundary pins on
  obstructed die tracks), 162 V7 cut spacing, 142 M7 PG short/spacing, plus the usual M1-M3 EOL.
- B per-track narrow obstructions: same crash. proof_turn_b (full kit, narrow obstructions): same crash t_i[104].
- D no M8 obstructions at all, same guides: DRT-0255 on clock nets in the land-ring strip (other place).
- C re-GRT M2-M7 (no M8, no -resistance_aware): DR 3612 -> 606 -> 459 -> 3 -> 0. CLEAN.
- E3 re-GRT M2-M8 -resistance_aware (= flow): M8 demand 4281, M7 5999 (flow 4284/7951) -> control.
- E1 re-GRT M2-M8 WITHOUT -resistance_aware: M8 demand 272, M7 2516. DR running.
- F2 re-GRT M2-M8 -resistance_aware + layer adjustment M7-M8 0.5: running.
- Working cause: ENABLE_RESISTANCE_AWARE=1 (ORFS asap7 default) + the new M8 grant (M8 R 0.0084 vs M7 0.0125 ohm/um)
  -> GRT promotes many short nets to M8/M7 (turn_a M7 212 mm vs 7 mm pre-grant) -> via stacks through dense land-ring
  columns, M7 PG columns and fragmented M8 rows that DR cannot realise.

## 2026-11-12 23:16 READY claude/head-route-1-1112 @ ad61fd322b (off origin/main 7073a6b4a5) -- lane stops here, COORD decides re-kit
- CAUSE (one class, all 4 rp18 DRT-0255: hd_turn_a, hd_turn_b, hd_spn_wshim_rx, hd_spn_wshim_tx): LAYER-BUDGET-1 M8 grant
  + ORFS asap7 default ENABLE_RESISTANCE_AWARE=1. M8 is the type's lowest-R layer, so resistance-aware GRT (incl. the
  -end_incremental re-routes after repair_design / hold buffering) promotes short nets to M8/M7; guides stack vias through
  land-ring columns, type M7 PG columns and the obstruction-fragmented M8 rows -> DR unrealisable. DR violations scale
  with M8 wire (turn_b 1.3 mm / 4734 .. wshim_tx 207 mm / 82581). rp17 = max layer M7, no grant, routed clean.
- FIX (source, gen_phys.write_type_kit): kit with an M8 grant writes 'export ENABLE_RESISTANCE_AWARE = 0'; M8 stays granted.
  Secondary (m8_grant.py): M8 obstructions / abstract OBS one narrow rect per track (merged runs >=0.5 um tripped the
  wide-metal spacing row and ate granted tracks; turn_b M8 GRT capacity 1.28M -> 1.52M). Alone it does NOT fix the crash.
  Tests: test_m8_grant 12 pass, test_tapbal_grt pass; 4 pre-existing gen_phys-suite failures identical on base.
- PROOF hd_turn_b (rp18 kit copy, epyc9 proof2_turn_b): GRT M8 demand 4284 -> 272; DR 3408 -> 610 -> 349 -> 4 -> 0,
  route goal through finish + abstract + fixlef: LEC 0, pin audit 1152/1152, TT setup WNS 0 / TNS 0. Multi-corner
  sign-off NOT run. Negative controls: narrow obstructions alone (proof_turn_b) crash on the same net t_i[104].
  Diag note: a fresh full re-GRT with -resistance_aware on the final netlist also routes (E3/E4 -> 0), so the
  incremental RA re-routes are the realised trigger; RA=0 removes both.
- SWEEP (read-only): 70 current kits carry an M8 grant, all RA=1: hbm hcut1111 26, qwen_compute hcut1111 14, qwen_kvsys
  14 (kvN2 8, event28w_c 6), s81 e9eda32d41c 7, s81_head rp18 7 + l48uj 2. Only the 4 HEAD rp18 kits reached DR (all
  DRT-0255). 6 QC hcut1111 sle/slw_st kits are through GRT (M7 demand 0.83-1.07M) and not yet in DR = same exposure.
  Earlier DRT-0255 (9 between 10-25 and 11-10) predate the grant, different class.
- Re-kit: any M8-grant kit regenerated from this branch picks up RA=0; existing kits can take it as a config.mk line.
