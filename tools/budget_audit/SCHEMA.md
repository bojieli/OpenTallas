# Budget-audit fragment contract (budget-audit-1010)

Each sub-agent writes ONE file: /home/ubuntu/claude-takeover-20261007/budget-audit-1010/<fragment>.json
{
 "fragment": "<name>", "target": "hbm_ds|hbm_qwen|hbm_dflash|hbm_ds_mtp|qwen_rom|ds_rom|...",
 "target_rates": {"<mode>": {"tok_s": X, "source": "file:path#key"}},   # the rate the budget is derived at
 "clock_ghz": 1.2, "cycles_per_token_budget": {...},
 "rows": [ {
   "id": "short_unique_id", "target": "...", "mode": "AR|MTP|DFlash|all",
   "unit": "SM|ATT|HC|SU|SFU|IDX|QDQ|DMA|VM|SVC|KV_READ|COLL.ALL_REDUCE|CP.fetch|CP.dispatch|LINK|CG_WAKE|...",
   "resource": "what exactly (port / datapath / queue / link)",
   "metric": "bytes/cycle | ops/cycle | records/cycle | outstanding | cycles/record | ns latency ...",
   "work_per_token": number|null, "work_unit": "...",
   "required": number, "required_basis": "how derived (formula) + source file(s)",
   "designed": number|null, "designed_basis": "RTL file:line / spec section / param",
   "measured": number|null, "measured_basis": "bench report path / commit",
   "margin": designed_or_measured / required (>=1 is OK; null if unknown),
   "critical_path": true|false  (is this unit on the token critical path, or hidden/overlapped),
   "tok_s_if_as_designed": number|null,   # the target's rate if this unit runs at its designed/measured rate, everything else at budget
   "tok_s_impact": number|null,          # tok_s_if_as_designed - target (negative = loss)
   "flag": "OK|GAP|UNKNOWN|INFEASIBLE",   # GAP when margin < 1.1
   "known_gap": "row_gather|su_sfu_staging|all_gather|vm_banks|svc_dma_width|topk_qdq|sm_att_hc_meas|" or null,
   "new_gap": true|false, "owner_stream": "hgi-1010|hbm-phys-1010|qwen-1010|ds-1010|bf-mtp-1010",
   "fix_hint": "one line", "confidence": "measured|derived|modelled|assumed"
 } ],
 "notes": ["..."]
}
Rules: cite files (path + key or line). Be quantitative. Do not guess a designed number you could read from RTL.
"Required" = what the unit must sustain so the token meets the target rate given the program's record schedule (critical path share), NOT the simulator's own price
unless the price is what defines the target. Flag margin < 1.1. Units whose designed throughput is unknown -> flag UNKNOWN with what is missing.
Known gaps already owned by hgi-1010 (mark known_gap, new_gap=false): software row gather, SU/SFU 32 B staging + bit-serial span (Qwen ~225 tok/s),
serial ALL_GATHER (2.26x), VM banks / 1 KB WP = 32% HBM BW, svc DMA width 256 B/cyc/stack, TOPK/QDQ many-record re-measure, SM/ATT/HC throughput measurement (stub in e2e).
Do NOT edit the repo (read-only; use `git show origin/<branch>:path` to read branches). No heavy jobs on localhost. Do not commit.
