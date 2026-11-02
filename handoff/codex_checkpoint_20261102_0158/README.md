# Checkpoint index

Start with the [coordinator summary](../codex_checkpoint_20261102_0158.md). This is an active recovery checkpoint requested by the user, not a Claude-reset handback. Workers and fleet jobs continue.

| Supplement | Scope |
|---|---|
| [flow_kits.md](flow_kits.md) | Resume/ECO, fleet admission, flow releases, S81 bind/canary, proof engines and tool crashes |
| [geometry_disk.md](geometry_disk.md) | Actual layout reviews, disk cleanup, Hroot/CTL/SC/BFQG geometry, live native SYNTH |
| [hbm_all.md](hbm_all.md) | All HBM clock/core/token/source lanes, root/cohort work and provider/programme frontier |
| [kv_qwen_token.md](kv_qwen_token.md) | Qwen stage37/HEAD, KV source/numerical/physical work, PC/HHP/AHUB/PV/q2/CTL |
| [qc_head_signoff.md](qc_head_signoff.md) | QC and DeepSeek HEAD die physical/source/proof lanes |
| [remaining_lanes.md](remaining_lanes.md) | Legacy-lane reconciliation, protection fix, independent reviews, PHY clock trace and cache guard review |
| [s81_ds.md](s81_ds.md) | All S81 cores, source bind/clock repairs, DS native arithmetic/source/token work |
| [pg_birth.md](pg_birth.md) | Exact native PG callback implementation, native tests, support limits and pending canaries |

Each supplement owns its job paths and collection commands. Read the relevant supplement before resubmitting or terminating anything. The coordinator summary distinguishes published main from disabled candidates and pending review. Source-only or diagnostic passes never imply whole-die release.

## Resume checklist

1. Confirm whether the user has actually said Claude's limit reset. If not, continue the takeover.
2. Read the coordinator summary, then the relevant lane supplement and latest lane tail.
3. Check actual controller/unit/result state; status changes while this snapshot is written. Preserve live jobs and failed artifacts.
4. Resolve pending scoped approvals/code reviews in the summary, then advance the next actual gate.
5. Owner questions stay plain text in CODEX-LOG; never open a blocking dialog.

