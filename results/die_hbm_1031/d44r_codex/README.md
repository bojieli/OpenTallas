# HBM L730 input-facing station repair (PREP, not adopted)

The actual S0 boundary audit exposed two failures hidden by nominal `regs_um[0]`: SU00 L730x1 input→first bank755um and B001 L730x2 input→first bank556um. SU00's W647.648..924.8147 pins face a hard core spanning y449.28..907.20; no <=405um station chain starts there.

This keyed candidate shifts both B113 E output/SU00 W input window copies down511.52um to136.128..413.2947. Its seven physical internal SU00 banks run across the free south street; actual1662data+valid per-bit hops270.309..287.280um. B001's two internal banks use the existing top/right streets, distributing bits in order: worst native hops276.683/381.510/354.295um. No outlines, hard-core positions, clock/reset ports, mission arithmetic, pipeline count or schedule cycles change. SU00 remains8 stages, B0013 stages. The compact delta touches6 types (two source bus copies and four FT copies), and must fold into the single HBM d44r event; it never activates a plan by itself.

Reproduce with current tools:

```
python3 results/die_hbm_1031/d44r_codex/su00_entry.py INPUT.json SU00.json
python3 results/die_hbm_1031/d44r_codex/b001_entry.py SU00.json OUTPUT.json
```

The first helper rejects a changed source width/stage/window epoch. The additive keyed delta records each replaced field's expected SHA256, including null for newly explicit B001 bit sites.

Native `check_abutment`+`check_faces` found0 relevant before/after findings. Current actual-normal-FT `check_hops` removes both SU00 failures and both B001 failures, and reports0 L730/L730m reach/station failures after the repair. Whole-plan `check_cuts` has0 errors both before and after. Original failures remain in the before records. This is not whole-plan G0C PASS: separate clock lattice/PG-safe tap defects and current child/source joins remain open.

LOOK: images use `tools/geom_review/plan_review.draw_base` and actual plan macros/bank sites, NW R0/NE MY. Banks occupy open south/top/right streets with no macro intersection; the paired seam stays aligned and pin density/layer allocation is unchanged. Scoped geometric verdict PASS-COND. Independent reviewer concurs for SU00. B113 actual output-flop/local-source placement and re-kitting must be checked after the511.52um output-window shift; no old physical view or timing credit transfers. Clock/PDN are unchanged by this candidate and are separately unqualified in d44r; no route/STA submitted.
