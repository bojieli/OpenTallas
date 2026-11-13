# DIE-KV-100 handoff (KV qwen_kvsys die owner; successor of DIE-KV-99 / KV-VN2-FIN) -- 2026-11-13 03:28 PST
## Scope (COORD brief 11-13 + owner directive 03:4x)
1. train-34 check: regenerate kv3_hub_Eo / kv3_hub_Wo kits PRIVATELY from current main and measure the cland_origin fanout/reach (GEOM-VIS-13 BAD 03:08).
2. cland_origin fanout fix + kv3_sys_c ROM register stage: apply EXACTLY the RULEBOOK R-REACH rule (RULES-REACH-1, ~/coord/lanes/RULEBOOK-1113.md) once posted; RULES-REACH-1 uses kv3_hub_Eo as a proof kit -> coordinate, no duplicate builds.
3. kv3_sys_SD: SD-GROW outline (as kv3_sys_SD_v1, E strip ~149 um).
4. reset relay collapse (hub_Eo 272 / hub_Wo 198): check vs RELAY-PLACE-1 FT-LANE class (train 36).
5. One KV event branch off origin main, READY; adoption after the 48 h freeze (11-15 04:00). Stop after READY.
## Worktree
- epyc7 /srv/opentallas-scratch2/claude/wt/die-kv-100 (blobless clone of hub, sparse minus physical/ref_tile, results/roofline, results/uarch). Clone in progress at 2026-11-13 03:28.
## Findings so far
- train 34 (CLAND-RELAY-3) reach default = ONE reader-START relay per WIDE soft ring at the ring's own reset-relay site (clock_landings.reader_start_reach). It cuts origin fanout but NOT the origin->relay distance (one flop hop, up to ~2 mm on hub_Eo). Narrow rings still take cland_start straight. Expectation: does not fix; to be measured on a private place.
- Explicit plan form clock.landing_reader_start {depth, branches{bus:{stages:[{xy_um,raw_reset}]}}} already exists (K - depth, boot + depth, data exact): a candidate carrier for relays <= 405 um, pending R-REACH.
- Baseline hub_Eo a1 geom copy: localhost scratchpad base_Eo/ (r2r_max 2381.5, 3869 > 405, relay_collapsed 272).
- private kit recipe: kit_wave.py run-item with a private spec/job dir (VISLAYOUT3-KVHEAD pattern; needs future_lec/ in the job dir, plan on gen host).
## Running jobs
- none yet (clone only).
## Next
- clone done -> strict bind of plan_of_record with current main tools (model epyc8 dkv99/bind_e.sh) -> private run-item hub_Eo + hub_Wo -> view place -> post RESULT.
