# S81-COL-STREET handoff (lane started 2026-11-14 ~22:00 PST; FABLE-PD-S81 lever 3)

## Where
- Work dir (epyc7, mirrored to epyc8/epyc10): C=/srv/opentallas-scratch2/claude/s81-col-street
- ot-run client logs: intel2 ~/cs/*.log (gen_base, gen_street, run_base, run_street)
- Base plan: B6e0 (0f313b18747e) = C/plan_base_B6e0.json. Street plan p2: C/plan_street_p2v3.json (core_place event C/v3/ev.json, SVG C/v3/svg).

## p2 prototype delta (col_h9_r0_p2__t1__cl9f71e63d__pva4376595; moves only, core shapes kept; eq OK; 30 cores moved)
- E1 row, R2 ROM row and their banks stay (E1->cf links are 700-1570 um; any E1 move lengthens them).
- E2 row (+bs2/bs3/t1) down 12.96, E2 row 4.32 east (glue clock taps clk_t23 / clk_t33 need 8.65 clear).
- R3 row = bn2/bn3 + c4 ROMs + s4 + t2/t2p merged into one row 7.56 over E2 (E2 N face 132 pins); ROM pitch 43.2;
  holes kept at glue taps clk_t36 (x 393) / clk_t32 (x 639); t2/t2p (S faces 566/536 pins) at 872.64.
- bf wall down 60.48 (993.6 -> 933.12): N strip 86.4 -> 146.88 um for ft0 (1,104) + frame_int_o0 (1,167).
- E column: n7 846.72 (off the lowered wall), n9-n11 down 60.48 (clears the NE corner for ft0).
- Mid street (R2 top -> E2): 127 -> 114 um. Fable's second 130-um street is NOT met in p2: E2 is boxed by clock tap
  (725.76,613.44) and clk_t33 below, and E1 cannot move without lengthening E1->cf. N strip took the space.
- W face clear 60.5 for element rows NOT done in p2: clk_t33 sits in the e2/e3 break, a 43-um east shift covers it.
- ft windows unchanged (die abutment chain); the wall row no longer lies under the ft0 horizontal run (ft0 regs y 1257.8).
- core_place model (route_supply): cutV 0.887 -> 0.544, core_H 0.995 -> 0.664, p99 1.471 -> 1.417, bit-mm -0.7 %.

## Tool findings (core_place.py, not edited; worked around in C/cp_wrap.py)
1. core_conns lookup misses every __pv type (tries name, __cl-stripped, __-stripped; key is NAME__clXXXX): col types
   scored with model 'none' (5 links instead of 928). Wrapper aliases the __pv name.
2. overlaps() counts the plan's abutted element halves (0.54 um overlap) -> applied=False for every col type. Wrapper
   counts only new overlaps.
3. Link limit: wrapper CS_LINK_TOL=0.05 (base limits +5 %); v3 needed 0 violations at the end (tviol 0) anyway.

## Proof (running)
- Kits: C/kit/{base,street}/kit/gen/<T> (kit_cs.sh = DIE-S81-92 kit_b6e.sh recipe, B3x2b bound tree + ovl_b6e, no M8 grant, M7 top).
- Driver C/cs_drive.sh: place -> plain GRT probe of 3_place (M2-M7, uniform 0.25, 50 it) -> kit grt (CTS + GRT).
- Compare: overflow per layer (M6 first, COORD ruling), cell count place vs GRT, post-CTS estimate; reference attempt_7.

## 11-15 00:1x restart after limit
- First A/B gens (B6e0 plan + B3x2b bound out) BOTH failed in gen.py phys: "physical collector_tree differs from captured
  bound reset identity" (plan/bind mismatch, baseline too: not the street delta). B6e bind itself ended BIND_RC=1 (no out).
- Rebased: base = B3x2b's own plan (C/plan_base_B3x2b.json a68fa6ace27a) + B3x2b sidecar; street = same seed on it
  (C/plan_street_p2v4.json, core_place applied True, identical metrics). Gens relaunched unpinned (--dir B3x2b, --stage C);
  logs intel2 ~/cs/gen2_{base,street}.log. Then cs_drive.sh per kit (logs ~/cs/run_{base,street}.log).
- p2 seed applied to all 12 col_h9_r0_p2 types (C/v3all): applied True on 12; 5 report e3.u_w 'no legal spot' (fixed
  taps differ per pv) -> needs per-pv check before B6f.
- Generic S-gravity compaction (C/gravity.py) gains only 8.6 um on p2 (taps + link limits): generalisation = one hand
  seed per layout. 216 col types = 12 families but only 7 distinct core layouts (p3=p1, p4=p5=p6 share).

## Next
- If street wins: generalise (seed rules per col family, 216 types), B6f delta to DIE-S81-92 with G0, then PLAN-READERS-1 audit.
