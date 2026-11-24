# KV-SPINE-REWIRE handoff (Opus 5.5, started 11-24 02:33 PST). ONE job: rewire the data-lane die_rst_n cores (hroot / hub_Eo / hub_Wo) to the reset spine.
Brief: COORD scratch split_brief.txt + rules.txt + s81_open_brief.txt (row states, KV-ALLFIX = integrator). Target ROW-REBASED 05:30 PST.
## Cause (accepted FABLE-RC-KV 02:53)
bind.py build_buses pass 1a/2a: a reset-spine pin (asbuilt.reset_spines host.die_rst_n) rides a NAME-AFFINE plan lane. Plan lanes L656-L661 (tap_tree host.die_rst_n) carry it as DATA to hub_Wo, hroot_WS/WN, (hub_C ft22, hub_Ei ft50) hub_Eo, hroot_ES/EN. L662 (-> sys_c) untouched.
## Row
- ROWS_KV-SPINE-REWIRE.py PLAN_IN PLAN_OUT [--pins PINS.json]: drop 6 lanes/8 ports/latency/count_aligned rows + 103 derived type rows; reset_replicate rsync copy_depth 4 tail sync on 3 sink types; --pins adds reset_spine_pins (PORTPIN form).
- ROWS_KV-SPINE-REWIRE-AB.py AB_IN AB_OUT: sink_stages 6 for kv3_hroot/kv3_hub_Eo/kv3_hub_Wo. A5t3 asbuilt 43d1bd9691bc -> 910c47d294fa.
- pins_from_bind.py PLAN BIND_RTL OUT TYPES..: bound ri_/rs_ ports with no plan pin.
- Copies on intel2 + epyc11 + epyc9 /srv/opentallas-scratch2/claude/kv-spine-rewire/. Base A5t3 cbee82715bca (intel2 A5t3_plan.json). Row on A5t3 = fadf32b9e557 (no pins).
## FABLE conditions (02:53): (a) FULL strict + G0 + LATCHECK, R8 main re-derive, law tables untouched (checked 0 refs); (b) regen_constants before/after; (c) FLOW-OPS guard (posted 02:5x); (d) flush3 on row bind: 29 negatives -> 0, pv_v3 +1 unchanged; (e) release T_D+n per core vs producers.
## Dirs: intel2 /srv/opentallas-scratch2/claude/kv-spine-rewire: tree (ot-tree-fork of epyc11 kv-allfix/grow/tree), gate.sh TAG PLAN BASE ABN (FULL=1), d28_plan_c.json baseline.
## Log
- 02:33 TAKING. 02:48 DRAFT post. 02:5x epyc9 forks died (epyc11 ssh resets); intel2 fork started ~02:56 (3 streams, ~1 GB/min).
