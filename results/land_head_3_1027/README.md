# LAND-HEAD-3 (2026-10-27): data-following die clock, opt-in die_trial --tree-form spine_fishbone

Tool: tools/die_plan/die_trial.py --tree-form spine_fishbone (opt-in; the default htree is unchanged); tests tools/die_plan/test_spine_fishbone.py.
Evidence: routed_sfb/ (die GRT0 incl clock, TT+FF, 50 iterations), models/ and model_*.json (stage-model comparisons, UNCHECKED by construction), experimental/ (not adopted).

## NUMBER-CHECK note (added by ROOT-MERGE-84, 2026-10-27 20:47 PDT)
Independent NUMBER-CHECK (lanes/LAND-HEAD.md 20:26, COORD 20:26 coord 4785d2592):
- CHECKED: die GRT overflow 0 (TT+FF), tree cells/sites, insertion, entry slew, and the core numbers: current-ring landed margin TT -270.5 / FF -170.7 ps.
- MISMATCH noted: 14 internal tree slews 341-399 ps > 320 ps.
- The count-aligned margin TT +189.8 / FF +227.6 ps is NOT a gate number: its definition is unsound (arithmetic CHECKED only).
  Do not quote it as a gate pass. The count-aligned ring is evaluated by MESO-COUNT-1 under the COORD 20:35 margin definition.
