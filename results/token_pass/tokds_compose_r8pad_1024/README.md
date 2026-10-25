# TOK-DS/COMPOSE: DeepSeek S81 token latency on the S81 die plan of record (2026-10-24)

Analytical composition (AGENTS.md rule: simulate the minimum component, compose system timing). Tool: `tools/s81_dv/tokfunc/compose_tok_ds.py` (`--selftest`, `--check`). Clock 1.2 GHz (833 ps).

**Verdict: NOT MEASURED ON THE CURRENT DIE.** No stage was measured on the v4.8 die, which has not been assembled. The component numbers below were measured on p4l (10-19/20) RTL. Each one counts as `measured-current-RTL` only if every RTL module its record names is blob-identical on this tree's HEAD. That check is necessary but not sufficient: submodules a record does not name are not checked, and a die-level context change (stations, landing) is covered only by the lane substitution.

## Latency table of record

- `physical/die_plan/s81/lat/s81_latency.json`: plan_digest `87f0256809a93f1e` = digest of `die_plan.json` (`87f0256809a93f1e`), 834 lanes, 833 ps. **This table is of record.**
- Plan: v4.8 + 26-slot frame FT405 per-bit-site plan (90fd169e9) + leaf/svc/eng hard cores (e94d9bb32, G0 PASS + G0C PASS 174/174).
- R8 landing pads PRICED in the table (`gen.py latency --fold-r8`, `physical/die_plan/s81/lat/run_lat_r8.sh`): per lane `cycles` = `base` + `r8_pad` (largest R8 landing pad of the lane's members). Bus groups `8a83fac62b02c647` (BINDER4 b3r8 as-built bind, plan v4.7b; bound depths rebased by lane onto this plan: 1568 of 3364 members moved), landed rule {'rx': ['^(x|xo)_[WE][0-5]_', '^xring__', '^sid_s_'], 'window': 4, 'stage_cycles': 0.5, 'over_margin': 'keep'}. 76,485 pad flops, 67 padded members, 76 landed bundles (13 over the margin, kept per-lane). 26 lanes padded, max 13, mean 5.885 cycles, sum 153; bind paths outside the plan lanes: {'UNPLANNED': 1}.

| lane | base | R8 pad | cycles | min member pad |
|---|---:|---:|---:|---:|
| xo_E2_out_a | 2 | 13 | 15 | 0 |
| xo_W4_out_b | 2 | 13 | 15 | 0 |
| x_W1_in | 22 | 12 | 34 | 0 |
| xo_W2_out_a | 2 | 10 | 12 | 0 |
| xo_W5_out_a | 2 | 10 | 12 | 0 |
| xo_W0_out_a | 2 | 9 | 11 | 0 |
| xo_W4_in_a | 2 | 9 | 11 | 0 |
| x_E4_out | 36 | 8 | 44 | 0 |
| xo_E3_in_a | 2 | 8 | 10 | 0 |
| unit__seqhost__svc_11 | 11 | 7 | 18 | 0 |
| x_E2_in | 13 | 7 | 20 | 0 |
| x_E4_in | 18 | 7 | 25 | 0 |
| x_W1_out | 41 | 7 | 48 | 0 |
| xo_E1_out_a | 2 | 7 | 9 | 0 |
| unit__seqhost__svc_5 | 7 | 6 | 13 | 0 |
| attn__s_4S_C__svc_11 | 17 | 4 | 21 | 0 |
| idx__s_3S_C__iqf | 42 | 4 | 46 | 0 |
| attn__s_3S_C__svc_5 | 19 | 2 | 21 | 0 |
| attn__svc_10__svc_12 | 2 | 2 | 4 | 0 |
| attn__svc_8__svc_10 | 2 | 2 | 4 | 0 |
| attn__svc_4__svc_6 | 2 | 1 | 3 | 0 |
| ctrl__s_0N_C__seqhost | 44 | 1 | 45 | 0 |
| idx__svc_0__svc_2 | 2 | 1 | 3 | 0 |
| idx__svc_12__svc_14 | 2 | 1 | 3 | 0 |
| idx__svc_6__svc_8 | 2 | 1 | 3 | 0 |
| unit__svc_6__svc_8 | 2 | 1 | 3 | 1 |

Lane terms the composition uses (the pads they picked up):

| term | cycles | without R8 pads | R8 pad | padded lanes in the term |
|---|---:|---:|---:|---|
| field_round | 118 | 112 | 6 | xo_W0_out_a +9 |
| leaf_hub_rt | 24 | 24 | 0 | - |
| link_end | 44 | 44 | 0 | - |
| ring_link | 2 | 2 | 0 | - |
| svc_to_hub | 19 | 19 | 0 | - |

- `physical/die_plan/s81/r8/s81_latency.json`: digest `b8e46d3348066b83`, 820 lanes. NOT of record: BINDER4-S81 as-built bind on plan v4.6 (474d1c07a) + R8 landing pads on v4.7b bus groups; 13 shared lanes 1..2 cycles longer, 18 v4.8 lanes absent.

### Delta vs previous record (plan v4.8 b4ac6d49, no pads) (`results/token_pass/tokds_compose_1024`)

| quantity | then | now | delta |
|---|---:|---:|---:|
| 1u AR, 241-stage map: cycles/token | 1,495,133 | 1,520,806 | +25,673 |
| 1u AR, 241-stage map: tok/s | 802.6 | 789.1 | -13.5 |
| 1u AR, DAG: cycles/token | 1,353,373 | 1,379,167 | +25,794 |
| 1u AR, DAG: tok/s | 886.7 | 870.1 | -16.6 |
| 1u MTP, 241-stage map: cycles/step | 1,946,458 | 1,973,703 | +27,245 |
| 1u MTP, 241-stage map: tok/s | 2,564.0 | 2,528.6 | -35.4 |
| 1u MTP, DAG: cycles/step | 1,758,080 | 1,785,611 | +27,531 |
| 1u MTP, DAG: tok/s | 2,838.8 | 2,795.0 | -43.8 |
| MU AR: users | 50 | 50 | +0 |
| MU AR: aggregate tok/s | 40,130 | 39,453 | -677 |
| MU AR: period cycles | 1,495,136 | 1,520,808 | +25,672 |
| MU MTP: users | 6 | 6 | +0 |
| MU MTP: aggregate tok/s | 15,384 | 15,172 | -212 |
| MU MTP: period cycles | 1,946,460 | 1,973,704 | +27,244 |
| lane term field_round | 63 | 118 | +55 |
| lane term leaf_hub_rt | 13 | 24 | +11 |
| lane term link_end | 24 | 44 | +20 |
| lane term ring_link | 2 | 2 | +0 |
| lane term svc_to_hub | 11 | 19 | +8 |

Critical-stage table delta (AR, top-40 stages, cycles): attn.wo_a +8,800.0, attn.wo_b +2,200.0, attn.wq_b +2,200.0, ffn.down +2,200.0, ffn.experts_gu +2,200.0, ffn.router +2,200.0, ffn.shared_gu +2,200.0, attn.a_proj +1,925.0, attn.hc_post +440.0, ffn.hc_post +440.0, attn.q_rope +352.0, attn.normalize +320.0

Critical-stage table delta (MTP, top-40 stages, cycles): attn.wo_a +8,800.0, wave.busy +3,065.0, attn.wo_b +2,200.0, attn.wq_b +2,200.0, ffn.down +2,200.0, ffn.experts_gu +2,200.0, ffn.router +2,200.0, attn.a_proj +1,925.0, attn.hc_post +440.0, ffn.bias +440.0, ffn.hc_post +440.0, ffn.softplus_sqrt +440.0

### Delta vs current plan 87f02568, no pads (`results/token_pass/tokds_compose_r8pad_1024/nopad_87f0`)

| quantity | then | now | delta |
|---|---:|---:|---:|
| 1u AR, 241-stage map: cycles/token | 1,518,196 | 1,520,806 | +2,610 |
| 1u AR, 241-stage map: tok/s | 790.4 | 789.1 | -1.3 |
| 1u AR, DAG: cycles/token | 1,376,557 | 1,379,167 | +2,610 |
| 1u AR, DAG: tok/s | 871.7 | 870.1 | -1.6 |
| 1u MTP, 241-stage map: cycles/step | 1,971,033 | 1,973,703 | +2,670 |
| 1u MTP, 241-stage map: tok/s | 2,532.1 | 2,528.6 | -3.5 |
| 1u MTP, DAG: cycles/step | 1,782,941 | 1,785,611 | +2,670 |
| 1u MTP, DAG: tok/s | 2,799.2 | 2,795.0 | -4.2 |
| MU AR: users | 50 | 50 | +0 |
| MU AR: aggregate tok/s | 39,521 | 39,453 | -68 |
| MU AR: period cycles | 1,518,196 | 1,520,808 | +2,612 |
| MU MTP: users | 6 | 6 | +0 |
| MU MTP: aggregate tok/s | 15,192 | 15,172 | -20 |
| MU MTP: period cycles | 1,971,036 | 1,973,704 | +2,668 |
| lane term field_round | 112 | 118 | +6 |
| lane term leaf_hub_rt | 24 | 24 | +0 |
| lane term link_end | 44 | 44 | +0 |
| lane term ring_link | 2 | 2 | +0 |
| lane term svc_to_hub | 19 | 19 | +0 |

Critical-stage table delta (AR, top-40 stages, cycles): attn.wo_a +960.0, attn.wo_b +240.0, attn.wq_b +240.0, ffn.down +240.0, ffn.experts_gu +240.0, ffn.router +240.0, ffn.shared_gu +240.0, attn.a_proj +210.0

Critical-stage table delta (MTP, top-40 stages, cycles): attn.wo_a +960.0, wave.busy +300.0, attn.wo_b +240.0, attn.wq_b +240.0, ffn.down +240.0, ffn.experts_gu +240.0, ffn.router +240.0, attn.a_proj +210.0

## Single user

| workload | DAG composition cycles | tok/s (DAG) | on the 241-stage map: cycles | tok/s (map) | measured-current | measured-old | priced (incl. plan lanes) | PHY |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| AR | 1,379,167 | 870.1 | 1,520,806 | 789.1 | 29.35 % | 48.86 % | 15.38 % | 6.41 % |
| MTP (tau 4.159) | 1,785,611 / step = 429,337 / token | 2,795.0 | 1,973,703 / step | 2,528.6 | 25.79 % | 54.28 % | 13.32 % | 6.62 % |

The grade percentages are shares of the DAG composition. "Priced" splits as AR {'priced': 10.24, 'priced_edge': 0.42, 'plan_v48_lane': 4.73} and MTP {'priced': 8.94, 'priced_edge': 0.34, 'plan_v48_lane': 4.03}.
The 241-stage map figure is the dv_mu_calendar_phys single-user timeline on the same node cycles. On top of the DAG composition it adds the release node terms (G4 attention, idx +40, Engram 640), 99,220 cycles of stage hops on the map, a forward-x chain of 40,001.0 cycles and 2,418 structural cycles (all MODEL). It is the release-shaped single-user number.

Cross-check: the calendar tool, given the same node cycles, re-derives AR T after its node override = 1,379,166.6 (this tool 1,379,166.6). For MTP the difference is +5,480 cycles. This tool rebuilds the MTP wave composites from their members after direct cabling and G4. The calendar overrides only member nodes and keeps the composite at its input value. The calendar replaces the composer wave with its own physical wave term anyway.

## Multi-user (241-stage calendar, same inputs)

| case | users | T_user | period | per user tok/s | aggregate tok/s | status |
|---|---:|---:|---:|---:|---:|---|
| AR, qualified calendar | 50 | 1,520,806 | 1,520,808 | 789.1 | 39,453 | checker PASS, N+1 FAULT |
| AR at 46 users (formula) | 46 | 1,520,806 | 1,520,808 | 789.1 | 36,296 | subset of the 50-user calendar |
| MTP, qualified causal pipeline | 6 | 1,973,703 | 1,973,704 | 2528.6 | 15,172 | checker PASS (same-user included) |
| MTP at 10 users (formula) | 10 | 1,973,703 | 1,973,704 | 2528.6 | 25,286 | **NOT qualified**: the 10-user MTP calendar (mucal241 6f law) FAULTS the same-user check (calendar_sameuser_s81_1021 exit 2); the causal pipeline admits 6 users |

Measured inputs: per_user_cycles: compose_1u node cycles: AR measured-current-RTL 29.35 %, MTP 25.79 % (of the DAG composition); slot_issue: measured-old-RTL: HEADMU seq_host/fixed_issue slot issue (10-19, 19bf4121e); dsdv_seq_host changed on main since (blob 1c7a86d31 -> HEAD differs); mu_collectives: measured-old-RTL: XDIE u5 46/10-user collectives on MU die ceaed19c4 (WIN/INV PASS); not_measured: the 241-stage map calendar itself, stage-hop chain, forward-x, copy-B colouring, MTP pipeline law (MODEL); no multi-user RTL token pass.

The earlier 47,642 / 17,780 calendar (calendar_pipeline_s81_1021) ran on `--compose romopt`, which is the CALPIPE + ROMOPT PROPOSED compiled spans and not measured. This calendar uses the measured release-partial composition plus the v4.8 lanes.

## What is NOT measured (AR critical path, cycles not measured-current, by blocking ladder gap)

| blocker | AR cycles | MTP cycles |
|---|---:|---:|
| (no ladder gap: needs a v4.8-die bench) | 814,477 | 1,168,484 |
| G-COMPILER-ROWS | 150,981 | 111,106 |
| G-NORMALIZE-SO | 4,160 | 7,260 |
| G-HOST-CONTEXT | 2,961 | 5,670 |
| G-HEAD-DIE-TB | 1,849 | 32,651 |

Top AR stages that are not measured-current:

| op | cycles | grades | blocked by |
|---|---:|---|---|
| attn.wo_a | 188,880 | measured-old-RTL 168,960, plan-v4.8-lane 18,880, priced 1,040 | - |
| attn.wq_b | 141,240 | measured-old-RTL 134,360, plan-v4.8-lane 4,720, priced 2,080, priced-edge 80 | - |
| unplaced_hops | 55,986 | measured-old-RTL 37,696, modelled-PHY 16,430, plan-v4.8-lane 1,736, priced-edge 124 | - |
| attn.idx.topk_local | 47,945 | measured-old-RTL 47,945 | - |
| attn.pv | 43,040 | priced 43,040 | G-COMPILER-ROWS |
| attn.out_allreduce | 41,120 | measured-old-RTL 18,640, modelled-PHY 20,080, plan-v4.8-lane 2,240, priced-edge 160 | G-COMPILER-ROWS |
| ffn.combine_allreduce | 41,120 | measured-old-RTL 18,640, modelled-PHY 20,080, plan-v4.8-lane 2,240, priced-edge 160 | - |
| substage_hop0 | 36,120 | measured-old-RTL 24,320, modelled-PHY 10,600, plan-v4.8-lane 1,120, priced-edge 80 | - |
| attn.a_proj | 32,984 | measured-old-RTL 27,814, plan-v4.8-lane 4,130, priced-edge 1,040 | - |
| attn.scores | 30,760 | priced 30,760 | G-COMPILER-ROWS |
| attn.idx.score | 29,453 | measured-old-RTL 29,253, priced 200 | G-COMPILER-ROWS |
| attn.idx.topk_final | 27,059 | measured-old-RTL 27,059 | - |

## Critical-path stage table (AR, top 20)

| op | n | cycles | share | grades |
|---|---:|---:|---:|---|
| attn.wo_a | 40 | 188,880 | 13.7 % | measured-old-RTL 168,960, plan-v4.8-lane 18,880, priced 1,040 |
| ffn.experts_gu | 40 | 152,960 | 11.09 % | measured-current-RTL 147,200, plan-v4.8-lane 4,720, priced-edge 1,040 |
| attn.wq_b | 40 | 141,240 | 10.24 % | measured-old-RTL 134,360, plan-v4.8-lane 4,720, priced 2,080, priced-edge 80 |
| ffn.down | 40 | 122,440 | 8.88 % | measured-current-RTL 115,560, plan-v4.8-lane 4,720, priced 2,080, priced-edge 80 |
| ffn.router | 40 | 56,520 | 4.1 % | measured-current-RTL 50,760, plan-v4.8-lane 4,720, priced-edge 1,040 |
| attn.wo_b | 40 | 56,320 | 4.08 % | measured-current-RTL 50,560, plan-v4.8-lane 4,720, priced 1,040 |
| unplaced_hops | 1 | 55,986 | 4.06 % | measured-old-RTL 37,696, modelled-PHY 16,430, plan-v4.8-lane 1,736, priced-edge 124 |
| attn.idx.topk_local | 8 | 47,945 | 3.48 % | measured-old-RTL 47,945 |
| attn.pv | 40 | 43,040 | 3.12 % | priced 43,040 |
| attn.out_allreduce | 40 | 41,120 | 2.98 % | measured-old-RTL 18,640, modelled-PHY 20,080, plan-v4.8-lane 2,240, priced-edge 160 |
| ffn.combine_allreduce | 40 | 41,120 | 2.98 % | measured-old-RTL 18,640, modelled-PHY 20,080, plan-v4.8-lane 2,240, priced-edge 160 |
| ffn.shared_gu | 40 | 37,680 | 2.73 % | measured-current-RTL 31,920, plan-v4.8-lane 4,720, priced-edge 1,040 |
| substage_hop0 | 40 | 36,120 | 2.62 % | measured-old-RTL 24,320, modelled-PHY 10,600, plan-v4.8-lane 1,120, priced-edge 80 |
| attn.a_proj | 40 | 32,984 | 2.39 % | measured-old-RTL 27,814, plan-v4.8-lane 4,130, priced-edge 1,040 |
| attn.scores | 40 | 30,760 | 2.23 % | priced 30,760 |
| attn.idx.score | 5 | 29,453 | 2.14 % | measured-old-RTL 29,253, priced 200 |
| attn.idx.topk_final | 8 | 27,059 | 1.96 % | measured-old-RTL 27,059 |
| price_of_record_residual | 1 | 26,548 | 1.92 % | priced 26,548 |
| L*.dv_p4l | 41 | 23,256 | 1.69 % | priced 23,256 |
| attn.a_allgather | 40 | 19,360 | 1.4 % | measured-old-RTL 7,600, modelled-PHY 10,040, plan-v4.8-lane 1,120, priced-edge 600 |

## Lane mapping (DAG term -> plan v4.8 lanes)

- **xdie on-die leg (priced 134 / LEG p4l 140 a crossing)** -> `ring_link` = 2 cycles (xring__s_0N_C__s_1N_C, xring__s_0S_C__s_1S_C, xring__s_1N_C__s_0N_C, xring__s_1N_C__s_2N_C, ...); crossings x 2 ends x 7 x (ring_link + 5 rstop edges); AR critical delta -15,834
- **field op p4l die wire (r8 wire + s81 die tiles) / missing hub return** -> `field_round` = 118 cycles (x_W0_out, xo_W0_out_a, xo_W0_out_b, fi_W0_p6_r0r1, fi_W0_p6_r1r0 ...); rounds x field_round (FIELD_WIRE table); AR critical delta -8,220
- **SU leaf-op hub / die-tile station tails** -> `leaf_hub_rt` = 24 cycles (dn_s_0N_L4, up_s_2N_L4)
- **softmax normalize SO -> XS tail** -> `svc_to_hub` = 19 cycles (attn__svc_11__s_4S_C)
- **end slice <-> link (kd/ku + coll lanes)** -> `link_end` = 44 cycles (coll__lk_ES1__s_7S_LP, kd_s_0N); NOT substituted: inside the measured(-old) xdie co-sim lane legs
- Off-chip: switched 453 -> direct D_cycles_max (tp_mesh 251 / stage_hop 266 / head_hop 257). AR critical cycles saved: {'tp_mesh': 51914, 'stage_hop': 22372, 'head_hop': 200}.
- Release node terms (priced), AR critical delta: {'attn.scores': 19200.0, 'attn.idx.score': 320, 'attn.pv': 0.0, 'eng.hbm_read': 0.0}.

Edges and terms that could not be mapped (kept with their old grade):

- field-node-old: `attn.a_proj`. node keeps its old DAG number (old r8 wire + tiles embedded, not separable)
- field-node-old: `attn.cmp.wk`. node keeps its old DAG number (old r8 wire + tiles embedded)
- field-node-old: `attn.idx.q`. node keeps its old DAG number (old r8 wire + tiles embedded)
- field-node-old: `eng.wkv`. node keeps its old DAG number (old r8 wire + tiles embedded)
- tail: `embed`. embed priced 751.3 (TP4 owner->4 ranks all_gather + SU expand + board leg; not a layer-die lane)
- tail: `head.lm_head`. head die wire +34 (head die is not on the S81 layer-die plan; no head plan of record)
- extra: `L*.dv_p4l (41 layer terms)`. p4l DV die deltas (landing, half-cycle hops, pin registers) on the critical nodes; per-layer sums only, no per-node split -> kept priced (partly double counts the v4.8 lanes above: an upper bound)
- extra: `price_of_record_residual / scan_d legs / reindex`. ledger terms with no lane content of their own; kept priced
- xdie: `measured xdie co-sim part (rstop + lep + lane legs, G8R2 p4m)`. lane legs are inside a measured span; v4.8 end-slice<->link lanes (kd/ku + coll) not separable; kept
- xdie: `token.return (modelled-PHY 2194)`. no per-crossing split in the base record; kept as modelled-PHY (ladder token_return D = 251 a crossing)
- node: `SU / select / hbm measured spans`. spans measured on p4l RTL include p4l on-die stations internally; not re-timed to v4.8 (needs the v4.8 die = layer replays)

## Regrade (measured records vs HEAD rtl/)

| record :: op | from | to | why |
|---|---|---|---|
| a_allgather: current S81 die RTL (G8R2 p4m: rstop + lep + la ::  | measured-current-RTL | measured-old-RTL | RTL changed since the measurement: ot_s81_rly, ot_s81sl_rstop |
| allreduce_20480: current S81 die RTL (G8R2 p4m: rstop + lep  ::  | measured-current-RTL | measured-old-RTL | RTL changed since the measurement: ot_s81_rly, ot_s81sl_rstop |
| argmax_merge: current S81 die RTL (G8R2 p4m: rstop + lep + l ::  | measured-current-RTL | measured-old-RTL | RTL changed since the measurement: ot_s81_rly, ot_s81sl_rstop |
| cand_merge: current S81 die RTL (G8R2 p4m: rstop + lep + lan ::  | measured-current-RTL | measured-old-RTL | RTL changed since the measurement: ot_s81_rly, ot_s81sl_rstop |
| composite wave.p2 <- a_allgather: current S81 die RTL (G8R2  ::  | measured-current-RTL | measured-old-RTL | RTL changed since the measurement: ot_s81_rly, ot_s81sl_rstop |
| composite wave.p2 <- allreduce_20480: current S81 die RTL (G ::  | measured-current-RTL | measured-old-RTL | RTL changed since the measurement: ot_s81_rly, ot_s81sl_rstop |
| composite wave.p2 <- idx_topk_merge: current S81 die RTL (G8 ::  | measured-current-RTL | measured-old-RTL | RTL changed since the measurement: ot_s81_rly, ot_s81sl_rstop |
| composite wave.p2 <- router_allgather: current S81 die RTL ( ::  | measured-current-RTL | measured-old-RTL | RTL changed since the measurement: ot_s81_rly, ot_s81sl_rstop |
| composite wave.p2 <- rows_allgather: current S81 die RTL (G8 ::  | measured-current-RTL | measured-old-RTL | RTL changed since the measurement: ot_s81_rly, ot_s81sl_rstop |
| composite wave.p2 <- rstop logic 5 edges a stop (LEG law) :: substage_hop0 | measured-release-RTL | measured-old-RTL | RTL changed since the measurement: ot_s81_rly, ot_s81sl_rstop |
| composite wave.p3 <- a_allgather: current S81 die RTL (G8R2  ::  | measured-current-RTL | measured-old-RTL | RTL changed since the measurement: ot_s81_rly, ot_s81sl_rstop |
| composite wave.p3 <- allreduce_20480: current S81 die RTL (G ::  | measured-current-RTL | measured-old-RTL | RTL changed since the measurement: ot_s81_rly, ot_s81sl_rstop |
| composite wave.p3 <- idx_topk_merge: current S81 die RTL (G8 ::  | measured-current-RTL | measured-old-RTL | RTL changed since the measurement: ot_s81_rly, ot_s81sl_rstop |
| composite wave.p3 <- router_allgather: current S81 die RTL ( ::  | measured-current-RTL | measured-old-RTL | RTL changed since the measurement: ot_s81_rly, ot_s81sl_rstop |
| composite wave.p3 <- rows_allgather: current S81 die RTL (G8 ::  | measured-current-RTL | measured-old-RTL | RTL changed since the measurement: ot_s81_rly, ot_s81sl_rstop |
| composite wave.p3 <- rstop logic 5 edges a stop (LEG law) :: substage_hop0 | measured-release-RTL | measured-old-RTL | RTL changed since the measurement: ot_s81_rly, ot_s81sl_rstop |
| composite wave.p4 <- a_allgather: current S81 die RTL (G8R2  ::  | measured-current-RTL | measured-old-RTL | RTL changed since the measurement: ot_s81_rly, ot_s81sl_rstop |
| composite wave.p4 <- allreduce_20480: current S81 die RTL (G ::  | measured-current-RTL | measured-old-RTL | RTL changed since the measurement: ot_s81_rly, ot_s81sl_rstop |
| composite wave.p4 <- idx_topk_merge: current S81 die RTL (G8 ::  | measured-current-RTL | measured-old-RTL | RTL changed since the measurement: ot_s81_rly, ot_s81sl_rstop |
| composite wave.p4 <- router_allgather: current S81 die RTL ( ::  | measured-current-RTL | measured-old-RTL | RTL changed since the measurement: ot_s81_rly, ot_s81sl_rstop |
| composite wave.p4 <- rows_allgather: current S81 die RTL (G8 ::  | measured-current-RTL | measured-old-RTL | RTL changed since the measurement: ot_s81_rly, ot_s81sl_rstop |
| composite wave.p4 <- rstop logic 5 edges a stop (LEG law) :: substage_hop0 | measured-release-RTL | measured-old-RTL | RTL changed since the measurement: ot_s81_rly, ot_s81sl_rstop |
| composite wave.p5 <- a_allgather: current S81 die RTL (G8R2  ::  | measured-current-RTL | measured-old-RTL | RTL changed since the measurement: ot_s81_rly, ot_s81sl_rstop |
| composite wave.p5 <- allreduce_20480: current S81 die RTL (G ::  | measured-current-RTL | measured-old-RTL | RTL changed since the measurement: ot_s81_rly, ot_s81sl_rstop |
| composite wave.p5 <- idx_topk_merge: current S81 die RTL (G8 ::  | measured-current-RTL | measured-old-RTL | RTL changed since the measurement: ot_s81_rly, ot_s81sl_rstop |
| composite wave.p5 <- router_allgather: current S81 die RTL ( ::  | measured-current-RTL | measured-old-RTL | RTL changed since the measurement: ot_s81_rly, ot_s81sl_rstop |
| composite wave.p5 <- rows_allgather: current S81 die RTL (G8 ::  | measured-current-RTL | measured-old-RTL | RTL changed since the measurement: ot_s81_rly, ot_s81sl_rstop |
| composite wave.p5 <- rstop logic 5 edges a stop (LEG law) :: substage_hop0 | measured-release-RTL | measured-old-RTL | RTL changed since the measurement: ot_s81_rly, ot_s81sl_rstop |
| composite wave.p6 <- a_allgather: current S81 die RTL (G8R2  ::  | measured-current-RTL | measured-old-RTL | RTL changed since the measurement: ot_s81_rly, ot_s81sl_rstop |
| composite wave.p6 <- allreduce_20480: current S81 die RTL (G ::  | measured-current-RTL | measured-old-RTL | RTL changed since the measurement: ot_s81_rly, ot_s81sl_rstop |
| composite wave.p6 <- idx_topk_merge: current S81 die RTL (G8 ::  | measured-current-RTL | measured-old-RTL | RTL changed since the measurement: ot_s81_rly, ot_s81sl_rstop |
| composite wave.p6 <- router_allgather: current S81 die RTL ( ::  | measured-current-RTL | measured-old-RTL | RTL changed since the measurement: ot_s81_rly, ot_s81sl_rstop |
| composite wave.p6 <- rows_allgather: current S81 die RTL (G8 ::  | measured-current-RTL | measured-old-RTL | RTL changed since the measurement: ot_s81_rly, ot_s81sl_rstop |
| composite wave.p6 <- rstop logic 5 edges a stop (LEG law) :: substage_hop0 | measured-release-RTL | measured-old-RTL | RTL changed since the measurement: ot_s81_rly, ot_s81sl_rstop |
| eng_rows_allgather: current S81 die RTL (G8R2 p4m: rstop + l ::  | measured-current-RTL | measured-old-RTL | RTL changed since the measurement: ot_s81_rly, ot_s81sl_rstop |
| extra L14.scan_d_reader | measured-release-RTL | measured-old-RTL | unverifiable: no resolvable source revision or no RTL module named |
| extra L2.scan_d_reader | measured-release-RTL | measured-old-RTL | unverifiable: no resolvable source revision or no RTL module named |
| extra L20.scan_d_l20split_k6 | measured-current-RTL | measured-old-RTL | base layer term, no element record: not verifiable against HEAD |
| extra L8.scan_d_reader | measured-release-RTL | measured-old-RTL | unverifiable: no resolvable source revision or no RTL module named |
| idx_topk_merge: current S81 die RTL (G8R2 p4m: rstop + lep + ::  | measured-current-RTL | measured-old-RTL | RTL changed since the measurement: ot_s81_rly, ot_s81sl_rstop |
| results/token_pass/measured_s81_1019/elements/FGU.json :: ffn.shared_gu | measured-release-RTL | measured-current-RTL | every found module blob-identical to HEAD |
| results/token_pass/measured_s81_1019/elements/FSDN.json :: ffn.down | measured-release-RTL | measured-current-RTL | every found module blob-identical to HEAD |
| results/token_pass/measured_s81_1019/elements/FSEQ.json :: ffn.router | measured-release-RTL | measured-current-RTL | every found module blob-identical to HEAD |
| results/token_pass/measured_s81_1019/elements/FSGU.json :: ffn.experts_gu | measured-release-RTL | measured-current-RTL | every found module blob-identical to HEAD |
| results/token_pass/measured_s81_1019/elements/FWOA.json :: attn.wo_a | measured-release-RTL | measured-old-RTL | RTL changed since the measurement: dsfd_bf_front_roots |
| results/token_pass/measured_s81_1019/elements/FWOA.json :: attn.wo_b | measured-release-RTL | measured-current-RTL | every found module blob-identical to HEAD |
| results/token_pass/measured_s81_1019/elements/GATH.json :: attn.gather | measured-release-RTL | measured-old-RTL | RTL changed since the measurement: dsdv_svc_att, dsdv_svc_rs |
| results/token_pass/measured_s81_1019/elements/GATH.json :: attn.window_load | measured-release-RTL | measured-old-RTL | RTL changed since the measurement: dsdv_svc_att, dsdv_svc_rs |
| results/token_pass/measured_s81_1019/elements/HCL.json :: attn.hc.pre_post | measured-release-RTL | measured-old-RTL | RTL changed since the measurement: dsdv_gunit |
| results/token_pass/measured_s81_1019/elements/HCL.json :: attn.hc.rsqrt | measured-release-RTL | measured-old-RTL | RTL changed since the measurement: dsdv_gunit |
| results/token_pass/measured_s81_1019/elements/HCL.json :: attn.hc.sinkhorn | measured-release-RTL | measured-old-RTL | RTL changed since the measurement: dsdv_gunit |
| results/token_pass/measured_s81_1019/elements/HCL.json :: embed | measured-newest-element-RTL | measured-current-RTL | every found module blob-identical to HEAD |
| results/token_pass/measured_s81_1019/elements/HCL.json :: ffn.hc.pre_post | measured-release-RTL | measured-old-RTL | RTL changed since the measurement: dsdv_gunit |
| results/token_pass/measured_s81_1019/elements/HCL.json :: ffn.hc.rsqrt | measured-release-RTL | measured-old-RTL | RTL changed since the measurement: dsdv_gunit |
| results/token_pass/measured_s81_1019/elements/HCL.json :: ffn.hc.sinkhorn | measured-release-RTL | measured-old-RTL | RTL changed since the measurement: dsdv_gunit |
| results/token_pass/measured_s81_1019/elements/HCL.json :: head.hc_pre | measured-release-RTL | measured-old-RTL | RTL changed since the measurement: ot_s81sl_vn, ot_s81sl_vp |
| results/token_pass/measured_s81_1019/elements/HCL.json :: head.norm.scale | measured-release-RTL | measured-old-RTL | RTL changed since the measurement: ot_s81sl_vn, ot_s81sl_vp |
| results/token_pass/measured_s81_1019/elements/IDXQF.json :: attn.idx.q_field | measured-release-RTL | measured-old-RTL | unverifiable: no resolvable source revision or no RTL module named |
| results/token_pass/measured_s81_1019/elements/MTPD.json :: draft.fixed | measured-newest-element-RTL | measured-current-RTL | every found module blob-identical to HEAD |
| results/token_pass/measured_s81_1019/elements/MTPW.json :: wave.handoff | measured-release-RTL | measured-old-RTL | RTL changed since the measurement: dsdv_seq_host |
| results/token_pass/measured_s81_1019/elements/SMX.json :: attn.den | measured-release-RTL | measured-old-RTL | RTL changed since the measurement: dsdv_svc_rs |
| results/token_pass/measured_s81_1019/elements/SMX.json :: attn.exp | measured-release-RTL | measured-old-RTL | RTL changed since the measurement: dsdv_svc_rs |
| results/token_pass/measured_s81_1019/elements/SMX.json :: attn.max | measured-release-RTL | measured-old-RTL | RTL changed since the measurement: dsdv_svc_rs |
| results/token_pass/measured_s81_1019/elements/SMX.json :: attn.normalize | measured-release-RTL | measured-old-RTL | RTL changed since the measurement: dsdv_svc_rs |
| results/token_pass/measured_s81_1019/elements/SMX.json :: attn.sink | measured-release-RTL | measured-old-RTL | RTL changed since the measurement: dsdv_svc_rs |
| results/token_pass/measured_s81_1019/elements/SU.json :: attn.hc_pre | measured-release-RTL | measured-old-RTL | RTL changed since the measurement: ot_s81sl_vn, ot_s81sl_vp |
| results/token_pass/measured_s81_1019/elements/SU.json :: attn.kv_norm.rsqrt | measured-release-RTL | measured-old-RTL | unverifiable: no resolvable source revision or no RTL module named |
| results/token_pass/measured_s81_1019/elements/SU.json :: attn.kv_norm.scale | measured-release-RTL | measured-old-RTL | unverifiable: no resolvable source revision or no RTL module named |
| results/token_pass/measured_s81_1019/elements/SU.json :: attn.kv_norm.sumsq | measured-release-RTL | measured-old-RTL | unverifiable: no resolvable source revision or no RTL module named |
| results/token_pass/measured_s81_1019/elements/SU.json :: attn.norm.rsqrt | measured-release-RTL | measured-old-RTL | unverifiable: no resolvable source revision or no RTL module named |
| results/token_pass/measured_s81_1019/elements/SU.json :: attn.norm.scale | measured-release-RTL | measured-old-RTL | unverifiable: no resolvable source revision or no RTL module named |
| results/token_pass/measured_s81_1019/elements/SU.json :: attn.norm.sumsq | measured-release-RTL | measured-old-RTL | unverifiable: no resolvable source revision or no RTL module named |
| results/token_pass/measured_s81_1019/elements/SU.json :: attn.q_norm.rsqrt | measured-release-RTL | measured-old-RTL | unverifiable: no resolvable source revision or no RTL module named |
| results/token_pass/measured_s81_1019/elements/SU.json :: attn.q_norm.scale | measured-release-RTL | measured-old-RTL | unverifiable: no resolvable source revision or no RTL module named |
| results/token_pass/measured_s81_1019/elements/SU.json :: attn.q_norm.sumsq | measured-release-RTL | measured-old-RTL | unverifiable: no resolvable source revision or no RTL module named |
| results/token_pass/measured_s81_1019/elements/SU.json :: ffn.hc_pre | measured-release-RTL | measured-old-RTL | unverifiable: no resolvable source revision or no RTL module named |
| results/token_pass/measured_s81_1019/elements/SU.json :: ffn.norm.rsqrt | measured-release-RTL | measured-old-RTL | unverifiable: no resolvable source revision or no RTL module named |
| results/token_pass/measured_s81_1019/elements/SU.json :: ffn.norm.sumsq | measured-release-RTL | measured-old-RTL | unverifiable: no resolvable source revision or no RTL module named |
| results/token_pass/measured_s81_1019/elements/SU.json :: ffn.route_w | measured-release-RTL | measured-old-RTL | unverifiable: no resolvable source revision or no RTL module named |
| results/token_pass/measured_s81_1019/elements/SU.json :: ffn.swiglu | measured-release-RTL | measured-old-RTL | unverifiable: no resolvable source revision or no RTL module named |
| results/token_pass/measured_s81_1019/elements/WQBG.json :: attn.wq_b | measured-newest-element-RTL | measured-old-RTL | RTL changed since the measurement: col_h10_l4, col_h9_l4, ot_s81sl_cap, ot_s81sl_slice |
| results/token_pass/measured_s81_1019/elements/zz_curation.json :: attn.a_proj | measured-release-RTL | measured-old-RTL | unverifiable: no resolvable source revision or no RTL module named |
| results/token_pass/measured_s81_1019/elements/zz_curation.json :: attn.hc_post | measured-release-RTL | measured-old-RTL | RTL changed since the measurement: ot_s81sl_vn, ot_s81sl_vp |
| results/token_pass/measured_s81_1019/elements/zz_curation.json :: attn.idx.score | measured-newest-element-RTL | measured-old-RTL | RTL changed since the measurement: dsdv_idx_rg |
| results/token_pass/measured_s81_1019/elements/zz_curation.json :: attn.idx.topk_final | measured-release-RTL | measured-old-RTL | RTL changed since the measurement: dsdv_bk_v, dsdv_bksel_c, ot_s81ph_sel |
| results/token_pass/measured_s81_1019/elements/zz_curation.json :: attn.idx.topk_local | measured-release-RTL | measured-old-RTL | RTL changed since the measurement: dsdv_bk_v, dsdv_bksel_c, ot_s81ph_sel |
| results/token_pass/measured_s81_1019/elements/zz_curation.json :: attn.q_quant | measured-release-RTL | measured-old-RTL | RTL changed since the measurement: ot_s81sl_vp |
| results/token_pass/measured_s81_1019/elements/zz_curation.json :: attn.q_rope | measured-release-RTL | measured-old-RTL | RTL changed since the measurement: ot_s81sl_vs |
| results/token_pass/measured_s81_1019/elements/zz_curation.json :: attn.quant | measured-release-RTL | measured-old-RTL | RTL changed since the measurement: ot_s81sl_vp |
| results/token_pass/measured_s81_1019/elements/zz_curation.json :: attn.z_quant | measured-release-RTL | measured-old-RTL | RTL changed since the measurement: ot_s81sl_vs |
| results/token_pass/measured_s81_1019/elements/zz_curation.json :: draft.head | measured-newest-element-RTL | measured-current-RTL | every found module blob-identical to HEAD |
| results/token_pass/measured_s81_1019/elements/zz_curation.json :: draft.markov | measured-newest-element-RTL | measured-current-RTL | every found module blob-identical to HEAD |
| results/token_pass/measured_s81_1019/elements/zz_curation.json :: eng.add | measured-release-RTL | measured-old-RTL | RTL changed since the measurement: ot_s81sl_slice |
| results/token_pass/measured_s81_1019/elements/zz_curation.json :: eng.dot | measured-release-RTL | measured-old-RTL | unverifiable: no resolvable source revision or no RTL module named |
| results/token_pass/measured_s81_1019/elements/zz_curation.json :: eng.gate | measured-release-RTL | measured-old-RTL | RTL changed since the measurement: ot_s81sl_slice |
| results/token_pass/measured_s81_1019/elements/zz_curation.json :: ffn.bias | measured-release-RTL | measured-old-RTL | RTL changed since the measurement: ot_s81sl_vs |
| results/token_pass/measured_s81_1019/elements/zz_curation.json :: ffn.hc_post | measured-release-RTL | measured-old-RTL | RTL changed since the measurement: ot_s81sl_vp |
| results/token_pass/measured_s81_1019/elements/zz_curation.json :: ffn.norm.scale | measured-release-RTL | measured-old-RTL | RTL changed since the measurement: ot_s81sl_vp |
| results/token_pass/measured_s81_1019/elements/zz_curation.json :: ffn.quant2 | measured-release-RTL | measured-old-RTL | RTL changed since the measurement: ot_s81sl_slice, ot_s81sl_vs |
| results/token_pass/measured_s81_1019/elements/zz_curation.json :: ffn.softplus_sqrt | measured-release-RTL | measured-old-RTL | RTL changed since the measurement: ot_s81sl_vs |
| results/token_pass/measured_s81_1019/elements/zz_curation.json :: ffn.top6 | measured-release-RTL | measured-old-RTL | RTL changed since the measurement: dsdv_gunit, dsdv_gunit_l1 |
| results/token_pass/measured_s81_1019/elements/zz_curation.json :: ffn.top6_order | measured-release-RTL | measured-old-RTL | RTL changed since the measurement: dsdv_gunit, dsdv_gunit_l1 |
| results/token_pass/measured_s81_1019/elements/zz_curation.json :: head.argmax | measured-newest-element-RTL | measured-old-RTL | unverifiable: no resolvable source revision or no RTL module named |
| results/token_pass/measured_s81_1019/elements/zz_curation.json :: head.lm_head | measured-newest-element-RTL | measured-current-RTL | every found module blob-identical to HEAD |
| router_allgather: current S81 die RTL (G8R2 p4m: rstop + lep ::  | measured-current-RTL | measured-old-RTL | RTL changed since the measurement: ot_s81_rly, ot_s81sl_rstop |
| rows_allgather: current S81 die RTL (G8R2 p4m: rstop + lep + ::  | measured-current-RTL | measured-old-RTL | RTL changed since the measurement: ot_s81_rly, ot_s81sl_rstop |
| rstop logic 5 edges a stop (LEG law) :: substage_hop0 | measured-release-RTL | measured-old-RTL | RTL changed since the measurement: ot_s81_rly, ot_s81sl_rstop |
| stage_hop: current S81 die RTL (G8R2 p4m: rstop + lep + lane ::  | measured-current-RTL | measured-old-RTL | RTL changed since the measurement: ot_s81_rly, ot_s81sl_rstop |

## Inputs to come (re-run commands)

- `--layer-cycles F.json`. Schema: `{"L0": {"cycles": <int>, "verdict": "PASS", "receipt": "<host:path or repo path>", "die": "fc31 35ba1ef7", "rtl": "<rev>", "applies_to": ["L1", ...]}}`. Only `verdict == "PASS"` is admitted. The cycles are the single-die layer replay span. They replace that layer's on-die (non-xdie) node cycles, scaled so that the critical-path sum equals the measured value, and the layer's `dv_p4l` term is dropped. The grade is measured-current-RTL with the receipt. `applies_to` is explicit and never implied.
- `--components DIR` (COMP receipts `results/token_pass/tokds_comp_1024/*.json`). Each receipt holds `verdict` = "PASS", `mutant` = "CAUGHT" (or `mutants` {name: "CAUGHT"}), and `op` (DAG op or list) with `cycles` (or `per_layer`), optional `old_cycles_per_instance` (shape match), `replaces` "logic"|"node", `receipt`. A rstop receipt can instead carry `leg_rstop_edges` (edges a ring stop).
- Command: `python3 tools/s81_dv/tokfunc/compose_tok_ds.py --layer-cycles <F.json> --components results/token_pass/tokds_comp_1024 --out results/token_pass/tokds_compose_1024`.

- This run: `python3 tools/s81_dv/tokfunc/compose_tok_ds.py --out results/token_pass/tokds_compose_r8pad_1024 --compare 'previous record (plan v4.8 b4ac6d49, no pads)=results/token_pass/tokds_compose_1024' --compare 'current plan 87f02568, no pads=results/token_pass/tokds_compose_r8pad_1024/nopad_87f0'` (`--check` with the same arguments re-derives both JSON files).

Files: `compose_1u.json` (all tables, lane map, unmapped list, regrade receipts) and `calendar_mu.json`.
