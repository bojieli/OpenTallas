# HBM-BIND-9 (10-29): HBM-037 cleared, the plan's phantom NE quantiser is removed (plan follows source)

Sub-lane HBM-BIND-9 of DIE-HBM-22. Plan of record d21h (die_plan 53b6d7beccd3). Strict bind uses the HBM-BIND-7 c1
manifest and netlist unchanged (`intel1:/srv/opentallas-scratch2/claude/hbm-bind-7-1029/c1/asbuilt.json`, netlist
`c1/out/asbuilt.json` = e1/spliced.json ce2560d35809, compose 6fbd87215718, map d0f839b00eef).
Run dir `intel1:/srv/opentallas-scratch2/claude/hbm-bind-9-1029`.

## Results (CHECKED = run and verified here; UNCHECKED = estimate)
| step | result | evidence |
|---|---|---|
| d22a = d21h + HBM-BIND-7 `coll_plan_drop.py --keep q0` (unchanged script) | die_plan **b6fc3ff23d54**; G0 PASS 0 errors; G0C 8 errors = the 8 inherited d21h errors, 0 new, 0 gone (CHECKED) | `plan_d22a/drop_dup_report.json`, `g0/*_d22a_summary.json` |
| strict bind d22a (b0) | 93 = 92 UNPLANNED + 1 EMIT HBM-037 `q_hub_ne/u_hb_quant_Q__u_dec__q0.rst_n: found 0` (CHECKED, 2:56 min, 7.2 GB) | `b0/bind_summary.json` |
| d22b = d22a + `quant_ne_drop.py` | die_plan **c564e8942374**; G0 PASS 0 errors; G0C 8 inherited, 0 new, 0 gone (CHECKED) | `plan_d22b/quant_ne_drop_report.json`, `g0/*_d22b_summary.json` |
| strict bind d22b (b1) | 93 = the same 92 UNPLANNED + 1 EMIT; **HBM-037 cleared** (CHECKED, 2:55 min, 7.2 GB) | `b1/bind_summary.json` |
| next masked EMIT | `wavefront core reset q_hub_ne/u_vmdel_Q0__q0.rst_n: expected one bound leaf, found 8` | `b1/bind_summary.json` |

## HBM-037 root cause
The as-built source has ONE hub quantiser, `hb_quant_NW` (17 top cells `hb_quant_NW__*`; `hb_quant_NE`/`_SE`/`_SW`
occur nowhere in the source top or the r18h5 bundle). The source `hb_quant_NW__u_dec` (ot_hgi_qw_dec) talks only to
the NW quant transport (xp_ctl header/v/vo/fault, rslice x 4x256 b, wslice y 4x128 b). The plan type `q_hub_ne` was
cloned from NW: it carries hard cores `u_hb_quant_Q__u_dec__q0/__q1` (260x260) and 17 soft contents
`u_hb_quant_Q__*` whose notes read "as-built hb_quant_NW__*". No source leaf exists in NE_hub, hence `found 0`.
This is not the HBM-036 single-source cause (that is two plan copies of one existing source instance, NW dec q0/q1).

Fix (precedent HBM-034/035, plan follows source): `quant_ne_drop.py` removes from q_hub_ne the 2 dec hard cores,
their 2 clock taps and the 17 quant contents; type.cells 6,343,070 -> 6,054,352 (-288,718 phantom cells). No bus,
pin or internal station referred to them (the script fails closed otherwise). q_hub_nw is untouched (NW dec q0/q1
stays HBM-036, ruling pending).

## Plan arithmetic for TOK (counts CHECKED, tok/s UNCHECKED)
- d22a coll q1 drop on d21h = exactly the HBM-BIND-7 numbers: NE 225 stations retargeted, 127 up, max +12 cycles,
  +839 regs; NW 264 retargeted, 144 up, max +15, +1069 regs; 1 r9tree combine station + 2 taps removed per hub.
- d22b NE quant drop: 0 stations, 0 cycles (the removed copy had no planned station).

## Next EMIT (not a same-pattern step; stopped here)
Plan hubs carry S-role copies `u_vmdel_Q0..7__q0` (TOK-HBM-4 C25b "existing native S-role producer vmdel_SE*/SW*").
The c1 source has no vmdel_SE*/SW*: vmb_SE*/SW* `dq` (281 b) are open top inputs, so the wavefront falls back to the
module and finds the 8 N-role vmdel_NE* leaves. Codex `results/codex_hbm_bind_1028/fold_producer_closure.json`
(base worktree codex-hbm-sourcefull-0310) already lists the 28 S-role producers the source lacks (vmdel_SE/SW0-7,
hcollks_SE/SW_p0-3, hcollrs_SE/SW, hleaf_SE/SW). Dropping the plan copies would leave S-role VM banks without a
delivery producer, so the fix is source-side (materialise the folded S-role producers in the bind netlist, then map
vmdel_S* -> u_vmdel_Q*__q0), not a plan drop. Needs a ruling / Codex-source lane.

## Reproduce (intel1)
`coll_plan_drop.py die-hbm-21/plan/d21h plan/d22a --keep q0 --repo <wt>` (results/hbm_bind_7_1029) ->
`quant_ne_drop.py plan/d22a plan/d22b` -> `tools/die_plan/check.py plan/d22X/die_plan.json [--completeness] --out g0[c]_d22X`
(die-hbm-21/plan/tmain tools, as DIE-HBM-21) -> `run_bind.sh b0|b1 <plan>` (tools from this branch base 96e7c6c9ba4).
No shared tool was changed.
