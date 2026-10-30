# DIE-HBM-23 (HBM die owner, 2026-10-29 17:47- PDT)

## HBM-040 (A) -- COORD 17:44 ruling: plan follows source, 8-SM release
`vmdel_s_drop.py` on d22b (c564e8942374, intel1 hbm-bind-9-1029/plan/d22b) -> **d23a die_plan 4133ce1e4e0d**
(intel1:/srv/opentallas-scratch2/claude/die-hbm-23/plan/d23a). Removed from q_hub_ne and q_hub_nw each: 8 hard cores
u_vmdel_Q0..7__q0 (S-role copies from the 16-SM d4g die), 8 contents (79,928 cells per hub), 8 clock taps; 0 stations /
buses / pins referred to them (script fails closed otherwise; whole-plan string check). N-role u_vmdel_Q0..7 stay. South VM
bank dq stay open native_required inputs (nothing tied). Report hbm040/vmdel_s_drop_report.json.

| check | result (CHECKED) |
|---|---|
| G0 d23a | PASS, 0 errors |
| G0C d23a | FAIL 8 = the 8 inherited d22b errors, 0 new, 0 gone |
| strict bind b2 (HBM-BIND-7 c1 manifest/netlist unchanged, tools = hub main 92f899057c3, 2:49 min, 7.2 GB) | 93 errors = the same 92 UNPLANNED (82,285 b) + 1 EMIT; **HBM-040 cleared** (no u_vmdel_Q*__q0 EMIT) |
| next masked EMIT (HBM-041) | `glue cell hc_NE.u_cen.$div$ot_hbm_hc_qcen_static.sv:85$54922 type $div (in a dissolved parent) is not supported: map that parent whole` |

Reproduce: `vmdel_s_drop.py hbm-bind-9-1029/plan/d22b die-hbm-23/plan/d23a`; `tools/die_plan/check.py plan/d23a/die_plan.json [--completeness]`;
`hbm040/run_bind.sh b2 plan/d23a/die_plan.json` (b2/asbuilt.json + b2/out/asbuilt.json = copies of hbm-bind-9-1029/b1).
