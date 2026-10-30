# KV plan of record: event28w_c (data only, DIE-KV-43 2026-10-30)

Frozen KV plan (OWNER 12.20 hard freeze). These files are byte copies of the fleet files that the freeze evidence,
the kit wave (plan_sha 16980115aa4a...) and the signed core views use. Main did not hold them before this commit.

| file | source (intel1) | sha256 (16) |
|---|---|---|
| plan_c.json.gz (gunzip -> plan_c.json) | /srv/opentallas-scratch2/claude/die-kv-40-1029/kv40/event28w/plan_c.json | 16980115aa4afb56 |
| eW_sidecar.json.gz | .../die-kv-40-1029/kv40/eW_sidecar.json | 428608171b7629f4 |
| kv_e26a_w243.yaml | .../die-kv-40-1029/kv40/cfg/kv_e26a_w243.yaml (die clock, ot_clk) | - |
| recipe_eB3b_wc.json | .../die-kv-40-1029/recipe_eB3b_wc.json (bind recipe) | - |
| refs/ + paths.json | the 33 absolute files plan_c.json names (core pins_file etc.); paths.json maps each absolute path to its repo copy + sha256 | - |

The die clock kit plan (kv_e26a_w243.yaml inputs.plan) is .../die-kv-40-1029/plan_e26a_w243/plan.json (sha ebe51013da36ae7c), the
clock-side view of the same plan; it is not copied here (36 MB). The region map is main results/locality_1027/kv_land128_regions.json.

Freeze evidence: DIE-KV-40/41 die GRT0 incl clock + KV-019 clock check PASS; DIE-KV-43 10-30 rerun with exact
abutment (die_trial b462b6cd050): GRT0 overflow 0 TT/FF, clock check unchanged (max |d arrival| 0.0 ps).

Known open item: 10 kv3_head_eighth_e0 entries (kv3_hg_v1p2..v1p6 head0/1_e0, orient MX) name
kv3_head_eighth_e0_pins_r25_r26q4.json. The other 28 MX entries and the signed e0 view use the N/S mirror
kv3_head_eighth_e0_pins_fMX_r25_r26q4.json. The plan is left byte-identical here; any pins_file fix is a separate one-block delta.
