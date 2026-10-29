# S81-LP-2 (2026-10-29): LP lane cut census + compact lane kits

## Census (census/census.json; recipe = S81-LP-1 flat_lanebb; method check reproduces 322,070)
| type | inst | lanes | flat std | cut parent std | x1.10 | verdict |
|---|---|---|---|---|---|---|
| lepw_mus_LP__t2 | s_0S_LP | 4 w | 556,766 | 322,070 | 354k | CUT (COORD adopted) |
| lepw_mu_LP__t2  | s_0N_LP | 4 w | 519,266 | 284,420 | 313k | CUT |
| lepe_mu_LP__t2  | s_7N_LP | 4 e | 510,216 | 275,202 | 303k | CUT (e master) |
| lepe_nh_mus_LP__t1 | s_7S_LP | 2 e | 299,350 | 181,806 | flat 329k | no cut needed |
Counts CHECKED (own mapped_stat.json); +10 % growth UNCHECKED.

## Lane kits (lane_kit.py -> lane/{A,B}; gen_core_kit_legacy recipes lane/recipes.json)
- A 345.6 x 561.6 (4-across 1382.4 of 1442.88), B 302.4 x 630.72 (1209.6); 55 SRAMs on one column lattice, channels >= 12 um.
- Pins: rx/tx S face, lo_*/li_* N face, ck M5 0.048x0.48 N centre, flt/chb/rs E face M4. [0:0] ports named x[0].
- Kit-local rtl_patch: drop (* keep *) on 1-bit l_credit / l_valid output regs (Yosys left an unloaded BUFx2 to the kept alias -> RAW face_guard shared FAIL on lo_r[0], li_v[0]); zero logic change.
- Both kits KIT_PREFLIGHT PASS 0 issues; PLACE launched 06:34 PDT (intel2 /srv/opentallas-scratch2/claude/s81-lp-2-1029/kits).
