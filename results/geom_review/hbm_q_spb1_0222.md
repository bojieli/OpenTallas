# HBM q_spb1 structural review 2026-11-08 02:22 takeover

Actual images VIEWED: intel1 `/srv/opentallas-scratch2/claude/autopilot/review/a722130c318e/{floorplan,density}.png`, local copies `/tmp/codex-hbm-spb1-0222/`. Outline 1745x1503um, no macros, sparse FT station grid. SMELLS: 4 (cross-tap launch/capture skew), 7 (polarity cells far from their planned station flop), 5 (weak signal driver wire reach). No macro-channel or PDN discontinuity observed in these views.

Measured existing route: TT+24.39ps, FF-187.88/1498 (1266 port,232 other; internal worst-56.27), TT slew1423, DRC0. FF read-only probe unit `oth-ubuntu-3884556-1794133702` completed normally: worst internal reset relay u_rrl19@clk_t11 -> u_rrl23@clk_t6 -56.27ps, FT L722x1s2@t7 -> s3@t12 -55.62ps, L117/L138s2@t9 -> s3@t14 -47..-50ps. Early launch window -160ps vs capture0 accounts for most hold burden. No second/large ECO allowed.

Verdict: FAIL, no unchanged route retry. Private structural pilot `OT_FT_POLARITY_LOCAL=1` groups direct single-load QN/inverter pairs at the existing planned launch stations, reusing face placement/release; no netlist,clock,cycle or plan change. PLACE only, HOLD_ROUTE. Actual pilot images and pair distances must be read before advancing. Separate cross-tap structural clock-follow-data or midpoint lockup solution remains required; no SDC phase waiver.
