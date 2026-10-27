# KV-KITS-7/HR triage of the qkd_hr_* hub_Wi host cores (plan hm_r26q3 256600e2), 2026-10-27

Method: yosys pre (proc/flatten) + `hr_face_ports.py transform --kept-face` (no proof) per core, census/<core>.rep.json.
`--kept-face` = every face register bit in its own keep_hierarchy 1-bit cell (0 cycles; constant-D output flops and
SAT-dead input captures no longer removed by opt_dff -- core_tx shared299/dropped215 root cause). Residual counts below are
what a zero-cycle recut can NOT fix (CHECKED, from the rep.json files).

| core | after recut | residual (needs) |
|---|---|---|
| core_tx | ZERO_CYCLE (1752 private + 3764 kept bits) | none; proofs post 0 / mut 1, emitted_v running |
| phy_pad | ZERO_CYCLE (547 private + 1575 kept) | none; proofs post 0 / mut 1 / emitted_v 0 PASS; kit blocked by plan (below) |
| phy_adp | +1 | r_cr[0] -> $mux.S (credit in drives a select): landing flop on r_cr |
| core_rx | +1 | deferred[0] ($logic_or), fault[0] ($or) unregistered outs: output flops |
| core_queue | +1 | dropped_in 12, logic_in 200 (bootbarrier in_d -> mux), multi_in 4 |
| core_guard | +1 | unregistered_out 1, dropped_in 93, multi_in 64 |
| core_order | +1 | unregistered_out 1, feedthrough 4, dropped_in 4, multi_in 131 |
| cdc_ci | structural | unregistered_out 548 = logic_in 548 (combinational pass-through) |
| cdc_hi | structural | unregistered_out 580 = logic_in 580 |
| core_prompt | structural | unreg 1, ft 17, dropped 7, logic_in 610, multi_in 404, const_out 9 |
| core_peer | structural | unreg 78, logic_in 485, multi_in 1338, const_out 12 |
| ingest_eng | structural | unreg 324, dropped_in 256, multi_in 772 |
| cdc_ch, cdc_pc | Codex LEC dockers (not touched) | |

dropped_in = input bits with no load at all after synthesis: declared-dead pin or plan pin removal, not a register.

## Plan blockers found (KV-PLAN-DELTA)
1. qkd_hr_phy_pad: die_plan.json outline_um still [138.24,129.6] @ origin [25.92,120.96], but the pin file was re-cut to
   86.4 x 95.04 (KV-CORE-SLICE-1, SE anchor); in that frame ck_phy[0] sits on the N edge (43.224, 95.04) at 0.024x0.192,
   failing GEOM-21 (clock pin >= 0.048x0.48); the 12.8a centre-entry move named in the file's source text was not applied.
2. All 10-24 core_pins_hr.py pin files store pin EDGE points (y=0 / x=W); gen_core_kit_kv io.tcl and the r25 pin files use
   pin CENTRES (edge -/+ half the pin length). PREFLIGHT-2 pins_canonical therefore fails every hr kit
   (phy_pad: 1577/1577 pins differ by exactly 0.096 um along the face normal). Fix = either convert the hr pin files to
   centres in the plan delta, or let pins_canonical apply the generator's edge->centre inset; owner PREFLIGHT/KV-PLAN.
