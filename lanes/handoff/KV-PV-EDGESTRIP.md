# KV-PV-EDGESTRIP handoff (2026-11-24 04:14 PST)
JOB: pv face-strip taps over the cap (kv3_pv_v12e/v7e/v2ne/v6n/v5ne/v1n). ROW-REBASED on A5t3 posted 04:13. DONE; evidence is kept until FABLE reads it.
ROW: ROWS_KV-PV-EDGESTRIP.py aff53806cf56 (epyc9 and epyc10 kv-pv-edgestrip/row/) with ES_RESETS=anchor. resel is void: it rebuilds collector trees, and the bind fails with EMIT "reset tap absent".
A5t3 cbee82715bca -> 65ce3ae015fd = epyc9 /srv/opentallas-scratch2/claude/kv-pv-edgestrip/a5t3/anchor/final.json (rt e348b919dd39, asbuilt 43d1bd9691bc, R8 f41eecdfdcf8).
STRICT (epyc9 a5t3/gate_t3base, gate_t3row): scoped --strict --all-gaps on the 6 pv types; base and row rc 0, EMIT 6/6, 0 errors, error sets equal.
PRE in gate form (plan in tree plan_of_record next to bind_of_record): 117 = 117. The diff is 2 ENTRYFOOT STALE-EXPORT-TAP lines (v12e, v7e) that are already on base; only the renamed tap names differ.
PRE 27-vs-23 gap (A5t2): the plan location, not the tree. derived_drop reads <plan dir>/bind_of_record; my out-of-tree plan fell back to plan-only WARN.
TAPS: v12e 1789->839, v7e 1859->917, v2ne 1376->1165, v5ne 1145->966. v6n 1136 > its bank_sinks cap of 1000 -> KV-TAPSPLIT-HGPV (placed-sink class).
DISK: epyc9 kv-pv-edgestrip/tree (50 GB fork) and epyc10 kv-pv-edgestrip (~5 GB, A5t2 evidence) are KEPT until FABLE reads the result; then ot-delete both.
