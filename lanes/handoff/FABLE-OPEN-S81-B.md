# FABLE-OPEN-S81-B handoff (Fable; items rc72, hg-S81-CLOCK-SKEW, x9; second S81 compose: rows 14:30, PRE-clean 15:30)
Lane dirs: <host>:/srv/opentallas-scratch2/claude/fable-open-s81-b (epyc10 romrow/ rc72/ x9/; epyc7/intel1/intel2/epyc2/epyc8/epyc10 lag/). Sub-handoff: FABLE-OPEN-S81-B-rc72.md.
## Tools (read-only what-if STA on a kit DB, ~3-9 min, ot-run --crit --stage KIT)
- lag/lag.sh KIT ODB SDC OUT MASTER_RE "LAGS": core clk_c port lag sweep (in/out setup+hold).  lag/core.sh KIT ODB SDC OUT x x: per hard-core master in/out slack.  lag/bus.sh KIT ODB SDC OUT MASTER_RE x: per input bus full path of first matching core.
## hg-S81-CLOCK-SKEW (14 items) - 11:3x
- col ROM-half (5 items): ROM halves capture inputs on the falling edge. No lockup: _hw in -34..-72, _he OK. planR2 lockup (Wave A): _hw OK (+50), _he fails setup -77..-95 and hold -70; _he cfg_d has no window behind a latch (rise setup <=901.9, fall hold >=939.0), lag cannot fix.
  ROW COL-ROMIN-EW-1: epyc10 romrow/romrow.py; ops_ew1.json 1d48c1429335; plan_ew1.json d38f42da603e on Wave A 4662b734580b; PRE PASS 0. _he rows: no lockup, D 2; _hw rows: lockup + lockup_cycles 1.
- col bs0 (2 items): HC-INPUT-REACH v3 in Wave A (relay_depth u_bs0 i_x0/1 D 3 verified).
- leaf: t71 = tap clk_t33 1719 sinks/750 ps; t23/t67 vp + lpad->crr = intra-tap skew 60-138 + long data; Wave A taps 63bafd10e3c5 (+2946 leaf taps). lpad->crr x3 need CRR_PRE2 (leaf C3), not in Wave A asbuilt -> asked S81-LEAF-J9.
  ROW LEAF-VSW-LAG-1: romrow/vswrow.py; ops_vsw.json b35a870ca2d3 (79 types, core_pin_lead_ps ot_s81sl_vsw clk -120); combined plan_ew1_vsw.json 652edd0502be PRE PASS 0.
- hd_lep0N_w x2: HEAD-R18 LEP-WTAPOFF-1 (ledger GATED).
- Posted ROWS-READY 2b89f3db; GAPMAP rows filled 47ac1262. NOT done: strict bind + LATCHECK + placed probe of both rows (second composed gate).
## rc72
- (V) row 3i in J9 tree, sync check OK x4. (C) COL-H9R0-UCF-MX (u_cf R0->MX, 48 types) is IN Wave A 4662b734580b (96/96 keys identical to rc72/ops_ucf_mx.json a820825accbe). Placed/GRT probe not run (needs the Wave A bound tree).
## x9
- Fork a62c454ee103a4b68 owns it: census on J8/J9 input = 157 types / 1,167 ports missing; Wave A final: TAPOFF-ALL fill ports 6549 / types 200 / stale 826 / skipped 0 (wavea_gate.otrun.log); census on 4662b734580b running epyc10 x9/wavea_4662.log (expect 0 missing).
## Next
- Read replies of S81-COL-J9 (row 1 function/cycles), S81-LEAF-J9 (row 2 veto, C3), ASSEMBLY (intake). x9 census result -> ledger. After Wave A/second gate bind: ask S81-COL-J9 for one p5 + one p3 GRT probe (u_cf corridor, ROM E/W halves).
