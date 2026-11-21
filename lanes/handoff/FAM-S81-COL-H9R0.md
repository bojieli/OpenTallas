# FAM-S81-COL-H9R0 handoff (started 11-21 04:2x PST, split from FAM-S81-COL-R3; updated 04:5x)
Family: S81 col_h9_r0_p1..p6 (~60 unsigned). R3 keeps col_h9_r1/r2 + shared J7 col relay/ft rows; COL-H10 has col_h10_*.
## State
- J6 (dc92652f0d5) applied 04:15; every col_h9_r0 J6 row is in hold_items (S81-J6-ASSEMBLY-R2 "J6 reps first"). Old-plan (J5 224567138ab) kits keep running and count (any-plan).
- 13 J5 route jobs live (autopilot queue). Closest to sign-off (GRT TT setup / hold before final hold ECO):
  - col_h9_r0_p2__t1__cl9f71e63d__pva4376595 job 0d6487d7a8c6 intel1: GRT -15.6 ps, DRT running  <- REPRESENTATIVE
  - col_h9_r0_p3__t1__cl8ce97bcb__pvd2159f4a job 4e4323c4d5b1 epyc10: GRT -24.5, DRT running
  - col_h9_r0_p2__t1__cl0045af7b__pva2793873 job 3283f16cae2b epyc10: GRT -37.6, DRT running
  - col_h9_r0_p2__t1__cl9f71e63d__pv11b73b67 job 64e24c10ad78 epyc10: GRT -39.5, DRT iter2 (148k->25.7k viol)
  - CTS-only so far: p1 pva2e3974f -214, p1 pvb49c16c8 -262, p3 pv1489a898 -125, pv625eef47 -121, p5 pveda1ecc9 -215, pvc6e5797f -211 (epyc9), p6 pv0012ba28 -46, p2 pv5752c4ff -275, p2 pv2744f675 in CTS.
- Route work dirs: /srv/opentallas-scratch{2,3}/claude/ot-jobs/<item>-route-<host>-*/work/run (metrics logs/asap7/*/base/*.json).
## Done
- 04:4x pv697f40c9 gen overlap (OT_MACRO_MOVES u_r0.u_c3_6 / u_r0.u_e3.u_e): the __pv* glob 4-move set moves u_e3 onto u_c3_6. Set exact item_env OT_MACRO_MOVES = Codex three-move set (e1/cf/t0, no e3), coord 36b66310fdc. Codex E8 2930371 placed that set clean (geom PASS-COND; geom rc1 = GRT dump timeout only). Placed scan still: 26 groups > 405 um, 413 bits > 580 um (u_lpad_x_i0 -> u_y_xo3 630 um) -> needs relay stages (xo family; R3's J7 rows cover the h10 xo chains; check same rows apply).
## Next
1. Waiter on the 4 DRT jobs; on sign-off of any: export, credit, hand row/settings to S81-J6-ASSEMBLY-R2 (J7) and relaunch siblings.
2. If a rep fails: read the post-route reports; hold <0 after ECO -> structural hold; setup -> stations.
