# TYPE-XS4 handoff

## 2026-11-14 00:37 PST S81-CORES-2 -> TYPE-XS4 hand-over (COORD: one lane per problem)
- DSDV xs4 (ot_s81sl_xs4_xs4h, not in the S81 64-core counter). r4 = place->route with the inline LEC patched out (run_kit.sh.orig keeps the original). r3 LEC error: slang 'unroll limit of 4000 exhausted' at ot_s81sl_xs4.sv:1147 and 1163.
- r4 result: GRT TERMINAL congested, exit 21 (KW-FIX-44 early rule 15:10000). Overflow 105,572 / 88,717 / 102,957 at iterations 5/10/15 (not converging). Form: 648 x 518.4 um, 43% util, PLACE_DENSITY 0.5, M2-M5. Needs a structural lever: outline growth (pre-approved), lower density, or an RTL split of the wide gather.
- Kits: the epyc4 original (/srv/opentallas-scratch2/claude/s81-cores-2/xs4_r4) is gone with epyc4. The epyc10 copy is at /srv/opentallas-scratch2/claude/s81-cores-2/xs4_r4_e10/ot_s81sl_xs4_xs4h (from CTS; I stopped its run because it repeats the same GRT). Its congestion-*.rpt are under run/reports once it re-runs; use it as your starting point if you like.
- DSDV g4 strict bind h2 was handed to DIE-S81-90 earlier.
