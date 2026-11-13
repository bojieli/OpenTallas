# S81-FORMS-1 handoff (S81 die-form owner; COORD lane) -- started 2026-11-13 ~11:20 PST

## Scope
- (1) S81 leaf family: macro too close to a pin face (t28 a3, t75 a1 BAD; t73/t29/t34/t44/t53 milder, routing under watch).
- (2) dsdv_slice c1x/c3x: macros u_cap/u_xr near W/S faces + cell count over the 400k/run cap (c1x t3 BAD, c3x t1 BAD, c1x t1 queued).
- COORD scope change (11:3x): the street rule (R-STREET, RULES-STREET-1) and the cap/split rule (R-CAP, RULES-CAP-1) are set in
  ~/coord/lanes/RULEBOOK-1113.md. Apply exactly those rules; no own numbers; no READY before both sections are posted.
- Not mine: serdes/seqhost (HARD-S81-SERDES-1), cross-tap hold (HOLD-TAP-1).

## Worktree / files
- epyc7 /srv/opentallas-scratch2/claude/wt/s81-forms-1, branch claude/s81-forms-1-1113 off origin/main fbfb4fc6a6 (no commits yet).
- Work dir epyc7 /srv/opentallas-scratch2/claude/s81-forms-1/{w,census.py,why.py,peek.py}.
- Base plan = ready12b-A plan 18c864518844 (events/s81_ready12bA_1112/plan_ready12bA_18c864518844.json.gz) -> w/plan_A.json.

## Findings so far
- Census (w/census_43.json, street 43.2 provisional): 71 of 89 leaf/kv_leaf/dsdv c1x/c3x types have a core < 43.2 um from a face
  with pins in its span. The generator norm is 34.56 um (core_place --gap auto default); a few go to 4.3-21.6 (t54 cl706, t37, t13,
  t17, t21, t58, t7, t45, t44, t75 ln).
- Tool: tools/die_plan/core_place.py --face-clear FACE:UM:REGEX (CORE-PLACE-1) already legalises cores off faces and keeps EQ.
  Trial --no-search at 43.2 on t28/t75: reverted. Blockers: (a) ft station fixed points above ve_s (128 pts at y~392 in t28);
  (b) the W ln column is packed at 6.48 um < auto gap 8.64. Timing (tviol) was not the blocker. Trial with search + --gap 4.32:
  w/try43s (pid see log).
- dsdv cells (kit logs, event 7073a6b4a59): c1x t3 synth 329,380; floorplan nontap 332,424 + tap/endcap 120,238; place repair
  +72,504 buffers; DPL 631,375 = 167,552 fixed + 463,823 movable. c1x t1: synth 317,830, place repair inserted 104,799 + 573,207
  + 119,576 buffers -> DPL 1,066,264 (166,945 fixed, 899,319 movable). c1x t6 a27: +367,937 buffers. c1x t10 a16: +224 buffers,
  254k movable. The excess over the cap is repair buffering on long nets (reach), plus 120k fixed tap cells from the outline area.

## Next
1. Poll RULEBOOK-1113.md for R-STREET and R-CAP; apply exactly.
2. Plan stage: core_place face-clear on the listed types (+ station re-route); private ot-run builds to place for t28/t75/c1x t3;
   view renders; route where possible.
3. READY: event branch (plan files only) + tool branch separately; adopted after the freeze (11-15 04:00).
