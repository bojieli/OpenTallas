# KV-RCOLL-REBASE handoff (11-23 21:4x PST)
Job (COORD 21:3x, FABLE-RC-KV 21:31): RELAY-INSERTION row for reset-collector reach on A3g (RCOLL2 re-attach = no-op).
Row: epyc11 /srv/opentallas-scratch2/claude/kv-rcoll-rebase/ROWS_KV-RCOLL-REBASE-RINS.py (new rst_cx_* relays below source node, kind cland_copy; plan collector_tree + sidecar copy + boot_budget).
Dry A3g: 221 sources/38 types -> 0; 244 relays; max +7; ready_at_glue 483 -> 504; raw copies <= 162 (155 base).
Gates (ot-run epyc11, gate_rins.sh TAG PLAN): gate_A3g (plain A3g) and gate_R1 (KV-RSTNAME-REMAP plan_R1 e186567f8dd6 + RINS, the compose to hand off). Logs logs/gate_*.otrun.log, dirs gate_<TAG>/.
Next: read RC_PRE / RC_BIND / BIND_ERRORS / COLLECTOR_REACH_INFO_LINES, post ROW-REBASED to KV-ALLFIX cc FABLE-RC-KV.
