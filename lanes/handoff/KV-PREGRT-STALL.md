# KV-PREGRT-STALL handoff (11-23 21:05 PST)
- Cause: pregrt_ff_hold rr pass (OT_PREGRT_HOLD_R2R_MARGIN=40) was one uncapped single-thread repair_timing after the base pass had closed hold. 35k-88k violating endpoints at 500k-700k insts, 6-10 h with no output.
- Cancelled: oth-ubuntu-915540-1795434191 (kv3_pv_v3 E10), oth-ubuntu-2029835-1795446419 (kv3_hg_v3 E8), oth-ubuntu-2822186-1795440396 (kv3_pv_v6 E8). Pre-repair TT setup -738/-439/-548.
- Fix: main c40acd92e6 (pregrt_ff_hold.py: rr chunk default max(500, 0.5% insts), 3 chunks, setup guard). Lane clone: epyc10 /srv/opentallas-scratch2/claude/kv-pregrt-stall/wt.
- OPEN: lift the kv3_pv_v3 hold_items key (kit_wave eb9e50a, owner me) via kit_wave_edit once rt/current carries c40acd92e6 (check: grep pg_rr_chunks rt/current/tools/die_plan/pregrt_ff_hold.py).
