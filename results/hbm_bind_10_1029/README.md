# HBM-BIND-10 (10-29): HBM-040 S-role vmdel fold STOPPED, the S-role producer is not defined by source or plan (ASK)

Sub-lane HBM-BIND-10 of DIE-HBM-22. COORD ruling 17:2x: HBM-040 fix = opt-in SOURCE fold of the 28 S-role producers +
bind map vmdel_S* -> u_vmdel_Q*__q0. Lane brief: if the S-role producer function is not determined by existing
source/golden (the fold would invent logic), STOP and ASK. That is the case. No source, tool or plan was changed; no bind run.

Evidence: `srole_census.py` (read-only) -> `srole_census.json`. Inputs (sha256[:12]): source top
`intel1:/srv/opentallas-scratch2/claude/codex-hbm-bind-0300/top_native.sv` c0eadd4c5f5f (manifest netlist of HBM-BIND-7 c1),
plan d22b `hbm-bind-9-1029/plan/d22b/die_plan.json` c564e8942374, map `hbm-bind-7-1029/c1/map.json` d0f839b00eef,
Codex `codex-hbm-sourcefull-0310/results/codex_hbm_bind_1028/fold_producer_closure.json` 12c8e2f686dd.

## Findings (all CHECKED from srole_census.json)
| item | fact |
|---|---|
| S-role delivery lanes in source | none: vmdel_SE0..7 / SW0..7 absent; vmb_SE*/SW* `.dq` = 16 open top inputs `vmdel_S*__dq[280:0]` |
| begin/start producer (vmdel `begin_*`/`start_*` = vmfc payload[51:0]) | vmfc_SE / vmfc_SW (`hfd_hgi_vm_calendar_f20_role`) absent. The S hubs carry `calendar_SE/SW` = plain `hfd_hgi_vm_calendar_f20` (no payload port), configured from hleaf_S* port a |
| fill producer (vmdel `fill_*` = 2 vmks lanes) | the 8 key-sharers are vmks_NW0..7 (8-SM release, all SMs north); **32/32 fill lanes are consumed, each once, by the 16 N-role vmdel**; vmks_SW* absent (no S SMs) |
| Codex closure of the 28 template clones | 128 nets still undefined after all 28; for vmdel_S*: vmfc_SE/SW__payload + vmks_SW0..3 fill (the NE->SE rename of vmdel_SE keeps vmks_NW4/6 = NE's own lanes, i.e. a duplicate) |
| plan d22b | u_vmdel_Q0..7__q0 per hub (16 hard cores, note "C25c existing native S-role producer vmdel_SE/SWk; independent q0 copy") have **0 stations** (only contents/hard_core/clock-tap refs); **0 stations** on the S banks u_vmb_Q*_mu1.dq; one u_vmfc_Q per hub (N role) |
| origin of the plan copies | the d4g 16-SM die (`physical/die_plan/hbm/inputs/dumps/dump-hbm/blocks.tsv`: vmdel_SE/SW*, vmfc_SE/SW, sm_SW*, svg_SW*) -- not the current 8-SM source |

So neither the source nor the plan states what feeds the S-role delivery lanes in the 8-SM release. A fold would have to
choose the begin/start calendar and the K fill lanes of 16 new lanes = new architecture, not composition (HBM-BIND-6/7
precedents composed source-defined reference wiring; here no reference exists).

## ASK (COORD / OWNER?) -- what feeds the S-side VM banks' dq in the 8-SM release?
- (A) **default, recommended**: plan follows source (HBM-034/035/037 pattern). Drop the 16 unwired S-role copies
  u_vmdel_Q0..7__q0 + their 16 clock taps from q_hub_ne/q_hub_nw (no station refers to them, so a fail-closed drop like
  quant_ne_drop.py); vmb_S*.dq stay explicit `native_required` top-input obligations (never tied), then strict re-bind
  for the next masked EMIT. Cost: none on tok/s (no planned station); frees 16 x 142.56x116.64 um.
- (B) mirror source: vmdel_S{E,W}k = vmdel_N{E,W}k inputs (vmfc_N* payload, same vmks lanes), own queue -> S banks get the
  same K fills as N banks. Exact only if the architecture wants duplicated K in S banks; doubles vmks fill fan-out; needs
  an owner decision + golden/TOK pricing.
- (C) restore the d4g S-side producers (vmfc_SE/SW + vmks_SW* + S SMs): conflicts with OWNER "HBM 8 SM this release".
Default (A) after 30 min without reply (12.14e).
