# DIE-QC-19 (QC die owner) -- c_* A0-entry rooting + start-skew root cause (2026-10-28 16:04 PDT)

Runs: intel2:/srv/opentallas-scratch2/claude/die-qc19-1028 (trial13 kit, repro, fe12, chain13/gate13).

## Task 1: c_* region rooted at the A0 entry (trial13)
- Baseline (CHECKED, eval_trial12_meas.json = trial12 routed clock-only GRT with the MEASURED A0 insertion nk 665.8/576.5, nl 692.6/601.9):
  c_* A0 flop arrival minus glue mean = min/med/max 42.2/124.5/157.9 TT, 52.7/124.8/158.1 FF (A0 LATE), in-region spread med 172 / max 232 TT;
  glue-only spread max 105 TT. trial12 hangs every A0 tap at the region root (leg 600-700 um, ~197 ps TT), so A0 is not early enough.
- Form: new opt-in die_trial --region-dme-early-merge-only REGIONS: listed regions use the DIE-S81-14 early mode merge
  (A0 tap = DME sink with sink delay = declared early/ratio, so the zero-skew merge node sits AT the A0 entry and the glue
  subtree joins there, elongated by plan-computed snake); su_c keeps hang. c_* added to --region-dme-snake. Default byte-identical:
  repro of trial12 with main tools (3bf064d3f5 + this patch, flag off) gives tree.json and ctree.v byte-identical to trial12 (CHECKED).
  Tests: test_die_trial_region_dme_merge_only.py (3 new) + region_dme_early/early_merge: 10 PASS.
- trial13 = ev_a0meas.json (DIE-QC-18 measured insertion) + c_* merge-only + c_* snake. Kit RUNNING (>90 min under load 80-140 on intel2;
  trial12 kit took 23 min with hang mode). watch13.sh then runs chain13.sh: bays -> overlay -> clock-only GRT TT/FF (docker 48g probe,
  mk_clkfirst13 = QC-11 mk_clkfirst + node M rows) -> eval13 (c_* core_minus_glue) -> gate13 (lpo, CA, proof, measured fall merge,
  plan phase/width on proof0 and fall proof, bind width, die STA declared).

## Task 2: 104 start-skew FAILs -- root cause (estimate on the trial12 proof, same clock; fe12/summary.txt, CHECKED from plan JSONs)
- The QC-18 gate proof had NO measured fall arrivals. FLOW-ONEMODEL-1 then fails closed: no fall edge selectable and, in width mode,
  no port can be width-robust (width 0/489 clean; 104 ambiguous = rise interval holds a boundary).
- With tap_fall_merge.py (main) on the same proof: phase mode 516/516 clean, 0 ambiguous (was 19), 77 fall edges, 48 retimes, CA 104.2/212.0;
  width mode 133/489 clean, 79 ambiguous, 0 retimes (--start-retime-up identical).
- Remaining width-unclean ports are WIDE: width med 260 ps vs width-clean max 209 (= T/2 - 2 ap); unshared capture clock below the start
  fork med 643 ps (clean ports <= 468). Retime stages on tree nodes are never chosen in width mode because tree-node fall arrivals are
  not in the QC readout (mk_clkfirst N rows only) -> rise-only -> never width-robust. trial13 readout adds node M rows so
  tap_fall_merge --tree can give retime nodes measured fall arrivals (UNCHECKED until the trial13 gate runs).

## Task 3: AP db14fa47fb37 (a0k6) RUNNING since 15:03 (attempt 1, after AUTO-GEOM); not collected.
## Task 4: RM165 (CLK-INV-CAL-1) not on origin/main (checked 14:4x) -> gate mode stays declared/PREVIEW.
