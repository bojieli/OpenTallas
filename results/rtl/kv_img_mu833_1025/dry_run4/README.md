# KV MU833 image: dry run on the current-plan f5 bind (diagnostic, 2026-10-25 TOK-QK)

Why: the PATH-KV-BIND strict bind (0 TYPE_SPLIT) is not posted yet. This dry run checks the image flow of record
(`physical/die_plan/qwen_kvsys/boot_v36/run_mu833.sh`, all inputs in the repo) on the newest complete current-plan bind,
so the strict bind can be compiled as soon as it lands. It is NOT token evidence: the bind it reads
(epyc1:/srv/opentallas-scratch2/claude/codex-kv-bind-0719/run4, Codex native f5 run4, 14 TYPE_SPLIT families) is outside the repo,
and its sha256 is in `bus_groups.sha256`.

Run: `ot-run --mem 8 --hosts localhost -- bash physical/die_plan/qwen_kvsys/boot_v36/run_mu833.sh <run4> <out>` on epyc1
(unit oth-ubuntu-898833-1792985640). Prep 2 s, image 1 s, compile stops at once.

## Result: FAIL (boot ABI field overflow), structural, not a tool bug
| item | as-built rtl6 GEN | f5 run4 bound | boot ABI bound (kv_bootage.BOUNDS / RTL) |
|------|------------------|---------------|-------------------------------------------|
| KST (d2d_kv<->kvs_attn landed) | 34,34,32,32,32,31,31 (kv41) | **55,55,53,53,53,54,54** | none |
| PV RL / FIRST_INPUT_AGE | 112 / 113 | **129 / 130** | FIRST_INPUT_AGE <= 127 (ot_qwen_tp8_pv_wide_ctl_tbf_p parameter FIRST_INPUT_AGE=127, 8-bit fia_q) |
| V port RT (max over 16) | 18-19 | **43-50** | VPORT_RT <= 31 (qkd_pv16_vport_b parameter RT=31 = slot/sel line depth; cfg field is 8 bits) |
| V port DQ unpadded (max) | 8 | 74 | DQ <= 15: kv_pv_wreq_pads.py pads (DQ-15) on the W request lane, up to 59 stages here |
| QK_ISSUE_AGE / response | 91 / 80 | 34 / 12 (natural round trip) | - |

Compile error: `kv_bootage: PV_FIRST_INPUT_AGE = 130 outside [1, 127]`; V port RT 43-50 also exceeds its 31 bound.
Cause: on the current plan the PV request/return lanes landed at 405-um stations are ~17-19 stages longer per leg
(pvrs 1 -> 18-20, pvvq 4-9 -> 11-21; `depth_map.json.gz`) than in the rtl6 GEN die the boot ABI was sized for.
The image cannot be compiled until either (a) the KV RTL raises the hardware bounds (qkd_pv16_vport_b RT >= 50 plus margin = a deeper slot/sel line,
ot_qwen_tp8_pv_wide_ctl_tbf_p FIRST_INPUT_AGE >= 130; the 8-bit cfg fields already carry these values) and kv_bootage.BOUNDS follow, or (b) the plan shortens the PV lanes. To be re-checked on the
strict bind (it may change the PV lane depths); owner of the fix: PATH-KV (RTL/plan), priced by KV-TOK.
