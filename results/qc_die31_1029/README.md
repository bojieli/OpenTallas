# DIE-QC-31 (2026-10-29) — A3 mesh pilot c1 re-route (2 variants), NK A0 V1 pick, BTAB F2 status

Run dir: intel1:/srv/opentallas-scratch2/claude/die-qc31 (base = copy of die-qc30/a3_compose; vK/, vT/ = variants).
Numbers are UNCHECKED by NUMBER-CHECK unless marked; "own" = read from this lane's own run outputs.

## 1. A3 fall-TT pair skew 82.56 > 80: root cause is a SHORT, not coupling
- Geometry (own, odb shapes, meshgap.py / rrcheck.py; render c1_reroute_KT.png VIEWED): in the DIE-QC-30 clip c1,
  n_P1u's M9 leg (x 546.396-546.476, y 1669-1833, then 546.556-546.636 to y 2029) OVERLAPS the ck_mesh M9 strap
  (x 546.40-546.56) for ~345 um, i.e. a physical short of the P1u output onto the mesh. DRT reported 0 design DRC.
  RCX turned the overlap into a 21.8 fF (43.7 fF summed both directions) "coupling" cap. n_B1's upper leg runs 357 um at
  0.244 um from the strap (< the 0.32 CK2W2S NDR spacing; GRT had logged "Disabled NDR" on every clip net).
- Cause in the clip harness (pilot_clip.py): the mesh strap is FIXED wiring of a REGULAR net that DRT also routes, so DRT
  did not hold other nets off it, and GRT dropped the NDR. Other clips: c0/c2/c3 only D-net stubs at 0.316 um (NDR
  within 4 nm), c1 n_D1ud 16.6 um at 0.244; n_in entry-port overlaps = known harness artefact. (info; no new check)
- Fix = ECO re-route of n_P1u + n_B1 in c1 only. All other c1 nets frozen as obstructions with their exact routed
  shapes (eco_prep.py), same GRT/DRT settings as the clip run (eco_route.tcl), spliced back into the clip DEF
  (splice.py), RCX + STA re-run with the clip recipe (rcx.tcl; control: RCX of the unmodified DEF reproduces the
  DIE-QC-30 SPEF net totals exactly), then compose + rec + MC 60 (TT/FF) on rise AND fall + pair U (post.sh).
  - vK (keep-out): M9 obstruction 0.32 um wide on each side of every mesh strap (legs >= 0.64 um from the strap),
    6-um window at the harness port. DRT 0 violations. n_B1 trunk at x 547.48, n_P1u at x 545.2-545.5 (clean, few jogs).
    rrcheck 0 (no overlap, all M8/M9 >= 0.32 to every other net). Mesh coupling from n_P1u/n_B1 = 0.
  - vT (planned tracks): M9 closed over x 543.2-548.0 except corridors at 545.236 (B1) / 545.636 (P1u). DRT 0 violations
    but it did not use the corridors: B1 detours to x 529.7, n_P1u has 129 M8 pieces (zig-zag) -> long wire.
  - (r1, discarded: obstruction shapes bloated by 0.28 -> NDR spacing counted twice, zig-zag routes; kept as
    c1_reroute_r1_bloat.png.)

| A3 pair U max (ps), limit 80 | rise TT | rise FF | fall TT | fall FF | mesh-driver input spread TT rise/fall |
|---|---|---|---|---|---|
| DIE-QC-30 (shorted n_P1u)   | 77.03 | 72.82 | 82.56 FAIL | 79.63 | 84.0 / 90.5 |
| vK keep-out (ADOPTED)       | 43.33 | 40.58 | 44.46 | 41.90 | 28.4 / 30.3 |
| vT planned tracks           | 77.86 | 73.21 | 83.13 FAIL | 80.05 FAIL | 85.3 / 91.5 |

vK numbers reproduced by two independent own runs (07:38 and 07:48, identical). Worst pair moves from L_clk/L_clk_t9
(column 1) to L_clk/L_clk_t15. vK agrees with A2 (pair U 43.35 / 41.36): A3 now confirms A2.
Note: a stray waiter re-launched post.sh T concurrently once (race); vT was re-run alone at 07:51 and those are the numbers above.

## 2. NK A0 floorplan: V1 chosen (plan_event_qc31.json)
QC-A0-KITS-13 estimate (b95168042 s2, nk_v1_v2_plan.png VIEWED): V1 has a legal node site (W edge, R0 (20.52, 688.656)),
rawfault macros +60.70 um, outline unchanged; V2 can open only 21.2 um (60 needed). V1 chosen; GEOM REQ before re-place.

## 3. BTAB F2 pin move: still PENDING
F2 routed sign-off NOT SIGNED (FF hold -1.68 ps/1, DRV TT slew 88, DRC 1; signoff.log 07:03, own read). No fix event,
no re-census; QC-FIX-2 owns the re-plan.
