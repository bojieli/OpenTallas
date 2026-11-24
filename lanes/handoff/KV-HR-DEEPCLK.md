# KV-HR-DEEPCLK handoff (11-24 01:4x PST) -- DONE, successor KV-ALLFIX
Question (FABLE-RC-KV): do hub_Wi deep hr core clocks (ingest 340.40/273.09, order 307.93/248.19 TT/FF) close at the boundary?
- A5r/A5s base: hub_Wi core_taps=internal, early 0 -> +114..+201 TT late. Does NOT close.
- Row ROWS_KV-HR-DEEPCLK.py (epyc11 /srv/opentallas-scratch2/claude/kv-hr-deepclk): 21 core rows -> signed means, core_taps=early.
  On A5s 8227d9519faa -> plan_A5s_hrdc.json 03439f30e22c. Needs install_hr_signoffs.sh TREE first (signoff.json beside each hr lib).
- Clean-tap read, routed hub_Ei SPEF (ff/): TT 243.0 mean, FF 189.8, ratio 0.777. Residual with early taps: median TT +17 / FF +21, p90 +40 (limit 40).
- Die clock tool (dme_probe.py, hub_Wi region, delay DME, model ps): merge mode delivers ingest 90.4, order 57.7 (rep 450); rep 150 ingest 92.1, order 63.4.
- Scoped strict hub_Wi (gate_A5s_HRDC2, DIAGNOSTIC under COORD 01:0x ruling): elab 0; bind 30 R8_STALE = A5s bind1 set; PRE 27 RSTREACH = A5s set; TAPOFF PASS;
  signed latency 21/21, mean mismatch 0; plan_timing_audit hub_Wi FAIL 13 -> 9 (remaining = core boundary-arc clk->q+setup budgets).
- Fallback (FABLE): lockup at ingest/order boundaries if routed residual > 40.
- Caveats: hub_Wi never placed (sibling basis); order/peer/prompt/ingest views linked by content only; shallow cores rely on tap_balance pads (cdc_pc overshoot risk).
Running units: none.
