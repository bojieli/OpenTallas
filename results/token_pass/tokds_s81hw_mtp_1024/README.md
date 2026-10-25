# TOK-DS: S81.HW scope note + S81.MTP cycle breakdown (2026-10-24)

Lane TOK-DS (DeepSeek token pass), release tree items **S81.HW** and **S81.MTP**. Analysis only. No plan, RTL or
compiler change is made here. Every number below is a MODEL number from the composition of record
(`results/token_pass/tokds_compose_r8pad_1024`, plan digest 87f0256809a93f1e, R8 pads folded). It is not a token pass.

Files: `README.md` (this note), `what_if.py` (reruns the composer + 241-stage calendar model with patched inputs; it
writes no outputs of record), `what_if.json` (the cases below).
Reproduce: `python3 -I what_if.py <tree at e7d749213 or later> what_if.json`. Each case takes about 40 s and fits in
under 4 GB; no fleet job is needed. The `record` case reproduces 1,520,806 / 1,973,703 exactly.

---------------------------------------------------------------------------------------------------------------------

## Part 1: S81.HW. What the exactness gap needs in hardware

Source: the fc31 layer compile (`lowering.json` of L2, epyc3 `tok-ds/fc31c2/layers_fc31/prog_L2_su`). It has 83 ops:
18 LOWERED, 47 PARTIAL and 18 GAP, so **65 ops are not fully lowered**. Their classes:

| class | ops | side |
|---|---:|---|
| field cfg_d descriptors / frame placement (hc.fn/sumsq, a_proj, wq_b, cmp.wk, wo_a, wo_b, router, shared_gu, experts_gu, down) | 13 | compiler |
| SUKV kv_program binding (kv/cmp/k norm, rope, pool, row_qdq) | 13 | compiler |
| norm 16-slice NX snake / XQ all-gather (attn/q/ffn norm + quant) | 12 | compiler (the gaps sub-agent's NX work, claude/tok-ds-gaps-1024) |
| lower_svc compressed-row selection (own_row_write, window_load, scores, max, exp, den, pv, sink, normalize) | 9 | compiler (RTL exists: dsdv_svc_att WIN_LOAD nsel / SEL_IDS / ROWS) |
| end-slice row placement (a_allgather, rows_allgather, out_allreduce, router_allgather, combine_allreduce, substage_hop0/1) | 7 | compiler (RD endpoint ABI benched, bench_vpx) |
| HC pre/post row binding | 4 | compiler |
| **indexer + gather (idx.q, idx.newkey, idx.score, idx.topk_local, idx.topk_final, idx.topk_merge, gather)** | **7** | **6 need RTL or plan work (idx.q is a field op)** |

The lowering text blames hardware for these ops ("no index-score unit", "no runtime-index row read", "no IDX path to
an end slice"). That text was written against the **fc31 / bind_p4l3_g8 vehicle die**. The current S81 plan v4.8
(`physical/die_plan/s81/die_plan.json`) and the RTL tree already hold most of the hardware. What is really missing:

### H1. Index-score unit: RTL exists, it is planned in v4.8, and it is missing only from the vehicle die
- **RTL:** `dsdv_idx_rg3` (rtl/dsrom_sys/s81_dv/idx/dsdv_idx_rg3.sv) is the paired non-inline index reader and scorer.
  It is a static-slot client of the pair's two `dsfd_ctrl_rg3` controllers (4 x 46-b request lanes and 4 x 272-b
  response lanes; budget DQR <= RFD, no credits). It sits beside `dsdv_idx_qf` (query frame, `iqf`) and
  `dsdv_idx_tx_n32` + `dsdv_idx_vmux` inside `dsdv_bk_sel_vmtx`.
- **Plan v4.8 (already there):**
  - `irg_k` is flattened into the lower svc partition of each pair: types `svc_lo_dsdv_svc_rs__t1..7` and
    `svc_lo_dsdv_svc_rs_w__t1`, 8 instances. It is planned as a hard core (57.5-79.9k cells, 45 SRAM; basis
    `ctrl_etap_irg` 79,867).
  - `iqf` is placed (`iqf__t1`, 11,296 cells).
  - Index chain lanes: `idx__s_3S_C__iqf` (513 b, 46 cyc), `idx__iqf__svc_0`, then `idx__svc_{0..12}__svc_{2..14}`
    (789 b = q 513 + s 276, 2-3 cyc), then `idx__svc_14__bk_sel` (276 b, 68 cyc) into `bk_sel.idx_i0` = `vi_idx` of
    the vmux.
  - These cost **0 new pins and 0 new area** against the plan of record.
- **Remaining RTL work (S81):**
  - (a) **Reset rule.** Re-kit rg3, qf and tx_n32 under OWNER DECISION 13. rg3 has its own async 2-flop landing plus
    an `ot_rst_relay` forest, and tx_n32 has 5 relay leaves with 2-stage synchronisers. Both must take the delivered
    neighbour-wavefront reset (registered in, registered out) with no local synchroniser. Reset only control state.
  - (b) **Pin registers.** Register every partition pin of the irg/iqf/idx-chain feedthroughs (OH/IH/RH/KR hops are
    already parameterised).
  - (c) **Plan pricing.** Confirm the reader-slot calendar of `dsfd_ctrl_rg3_native32` is in the svc_lo kit.
    `IDX_LAT` +40 a job (REL241) is the price in the model.
- **Cycle impact vs model:** 0. The compose prices idx.score at 29,573 MTP-critical cycles (8 instances), from
  measured-old RTL.
- **Compiler (TOK-DS):**
  - `lower_idx`: rg3 job descriptors (walker header, slot / cell / kc / base).
  - The iqf query frame on the two 276-b lanes.
  - The run-ahead window T0 and the chain edges (OH/IH/KR uniform shift).
  - bk_sel arming (CTL uid 0x5C op 2) and the tx slot grid (TX_SM 1600).
  - Emitting the GAPS producer (`lower_bk`) from the scan instead of the bench stimulus.

### H2. New index key append (attn.idx.newkey): NEW RTL, small
- **What is missing:** no job writes the token's index key row into the HBM index-key region that the rg3 walker
  reads. rg3 is read-only. dsdv_svc_att writes only window rows (OWN_ROW, type 3).
- **RTL (S81, svc):**
  - Add one q frame type to `dsdv_svc_att`: IK_ROW = {pos, user, key row}.
  - Reuse the OWN_ROW write path, but address the index-key region with rg3's key layout: position s goes to PC
    `((s>>2) ^ (s>>7) ^ (s>>12)) mod 32`. Exactly one svc owns that PC and writes it; the others drop the frame.
  - The key row reaches the svc on the existing q / attn stream from the slice. IK comes out of the kv_leaf / SU-KV
    path.
  - Writes go before reads per PC, as the window writer already does.
- **Cost:** 0 new partition pins; est. < 3k cells per svc (decode + address generator); 1 row write per token per
  indexer layer.
- **Compiler:** emit IK_ROW in the static schedule before the next token's scan of that layer.

### H3. Runtime-index row read (attn.gather): RTL exists in svc; the missing piece is the on-die SEL_IDS producer
- **What exists:**
  - `dsdv_svc_att` already reads rows by a runtime index list. SEL_IDS (type 7) records per rank whether the row is
    held by this stack, and fetches the own rows from the slice's 2 PCs (nsel <= 512, `sel_held[511:0]`).
  - Rows held by the other stacks arrive on ROWS frames (type 6), and WIN_LOAD carries nsel.
  - Today SEL_IDS comes from the host q stream. Nothing on the die turns bk_sel's final top-k into SEL_IDS.
- **Recommended RTL (S81):**
  - The SEL_IDS encoder goes in the bk_sel tx: same block and clock, and the IDX buffer SRAMs are already there.
  - It streams on the existing lane `xtier__bk_sel__seqhost` (276 b, 65 cyc) to seqhost.
  - Seqhost gets a static relay into `unit__seqhost__svc_5` / `__svc_11` (13 / 18 cyc). The entries merge it into the
    q stream in a compiled window, and a collision raises a sticky fault (no arbitration).
- **Cost:** 0 new partition pins. Est. ~140 cycles a gather instance (65 + 18 lane, ~39 beats, dn tree ~20) on the
  critical path, about 1.1k cycles MTP-critical (<0.1 %). Price it in the lat table when S81 fixes the relay.
- **Open (S81):** the plan still carries `bk_col` (dsfd_bk_collector: row collector on the column-1 V rung, 4 xtier
  lanes). With the svc-local fetch plus ROWS frames, nothing consumes bk_col. Its old gather path also costs >= 2 V
  beats per 512-b word. Please confirm whether bk_col has a role in v4.8. If not, drop the partition and its 4 lanes
  from the plan; an unused hardened block is dead area.
- **Compiler:**
  - Emit SEL_IDS from the static schedule, WIN_LOAD with nsel > 0, and ROWS frames for rows held by other stacks
    (rows_allgather placement).
  - Do the 9-op `lower_svc` compressed-row selection.

### H4. Cross-die top-k merge path (attn.idx.topk_merge): a PLAN gap and a port-bind violation in waiting
- **The problem:**
  - `dsdv_bk_sel_vmtx`, the bk_sel master in plan v4.8, has rank-tree ports `ca[275:0]`, `cb[275:0]` (child lanes,
    inputs) and `tl_o[275:0]` (lane to the parent die), plus `tx_st` / `fault` / `vm_fault`.
  - The plan gives bk_sel only `xtier_i0/i1`, `idx_i0` and `xtier_o0/o1`. No lane exists for ca/cb/tl_o.
  - If the die GEN binds as planned, ca/cb are **open inputs** and tl_o is unconnected. That is a "no stubs / no open
    inputs" FAIL at the port-bind gate. It is also exactly the missing "IDX path to the end slice".
- **Option A (recommended): dedicated lanes.**
  - Add three registered die lanes between bk_sel and the LP end slice that owns the TP4 peer links (s_7N_LP or
    s_0N_LP): `tl_o` bk_sel -> LP, and `ca`, `cb` LP -> bk_sel.
  - Each is 276 b, about 10 mm, so ~26 stations / ~26 cycles. They run as feedthrough on <= M7 (decision 12).
  - The LP lep gets a static slot mux of the 276-b IDX beat into its 512-b coll tx word on the TP4 circuit, and the
    rx demux to ca/cb.
  - **Cost:**
    - 828 b of new feedthrough through the N slice band, ~2k station flop bits.
    - LP partition +276 in / +552 out pins.
    - lep ~2-4k cells.
  - bk_sel ports are unchanged. The rank-tree crossing stays inside the lower_bk LEG bound (<= 729 edges): ~26 + 44
    link_end + 251 PHY + 26 ~ 350.
- **Option B: reuse the existing lanes.**
  - Remove ca/cb/tl_o from the master; vmux i_a/i_b inputs come in over vi_s.
  - Carry the IDX beats over `xtier__bk_sel__s_4S_C` -> xring -> end slice C -> LP coll, with a distinct beat kind in
    rstop/xrt. Today xr RD header bits collide with the BK lane / part / type fields.
  - Cost: 0 new lanes, but kind decode in 3 RTL types (slice C rstop/xrt, LP lep, bk_g), and the V-rung and ring
    slots are shared with control traffic.
- **Both options:**
  - The merged list must come back to every die, because each die's SEL_IDS needs the final top-k. Either the root
    broadcasts down the same tree lanes, or the TP4 all-gather carries it.
  - **S81 decides.** The plan must add the lanes, or remove the ports, **before the v4.8 die GEN binds bk_sel**.
- **Cycle impact vs model:** ~0. The compose prices topk_merge at 4,024 MTP-critical cycles (8 instances).
- **Compiler:** `lower_bk job_rank_tree_rd` (exists), the LP coll tx/rx slots on the TP4 link calendar, and the
  broadcast of the result.

**Hand-off.** The RTL/plan parts of H1(a-c), H2, H3 and H4 are requested from S81 (lanes/S81.md). TOK-DS keeps the
compiler parts: lower_idx, IK_ROW emission, SEL_IDS / ROWS emission, the lower_svc compressed-row selection, and the
rank-tree slots. These follow the gaps sub-agent's NX/norm work (claude/tok-ds-gaps-1024), which is not duplicated.

---------------------------------------------------------------------------------------------------------------------

## Part 2: S81.MTP. Where the MTP verify step goes, and what would recover it

**Record:** 1u MTP 1,973,703 cycles/step at tau 4.159 = **2,528.6 tok/s**.
**Owner floor:** ~3,000 tok/s, which means a step of at most **1,663,600 cycles (-310,103, -15.7 %)**.

### 2.1 Which MTP law binds

`dv_mu_calendar_phys.build` (REL241) takes `T_mtp_step = max(6f law, causal pipeline)`:

| law | T step | tok/s |
|---|---:|---:|
| **6f "stretch" law (binds)**: composer MTP DAG + map terms | **1,973,703** | **2,528.6** |
| causal six-position pipeline (calendar checker PASS, 6 users): step_end 1,786,344 + AR tail beyond head 19,929 | 1,806,273 | 2,763.0 |

The 6f law **is the record**. It is 167,430 cycles above the pipeline graph that the same tool builds and checks.
Neither law is measured.

**6f law decomposition:**

| term | cycles |
|---|---:|
| composer MTP DAG, switched 453 legs (calendar input) | 1,851,197 |
| direct cabling + release node terms (G4 attention +19,200, idx +320, collectives / hops on direct D -79,626) | -60,106 |
| cal2 structural | +2,556 |
| added stage hops: 241-stage map vs the 120 hops of the DAG record = 121 x HOP 820 (HOP = 652 link serialisation + 265 direct PHY - ...) | +99,220 |
| forward-x chain (map vs legacy) | +40,001 |
| wave physical (5 x the bottleneck stage occupancy) - composer wave | +40,835 |
| **T step** | **1,973,703** |

**Pipeline law decomposition:**

| term | cycles |
|---|---:|
| first position through all 241 stages (chain_end[0]) | 1,489,800 |
| positions 2..6, increments 29,997 / 49,420 / 54,590 / 54,590 / 54,590 = the bottleneck stage occupancy | +243,187 |
| head hop + head (one position) | +808 + 10,269 |
| draft tail (draft.head = 5 x lm_head) | +42,280 |
| AR tail beyond head (token return / host) | +19,929 |

**Bottleneck stages.** R121 / R085 / R049 / R013 have occupancies of 55,267 / 55,138 / 52,473 / 51,740. They are the
dense stages of **L20 / L14 / L8 / L2, the layers that carry the indexer**. The next stage is 36,417 (R169). The
ordinary dense stage is 26,515.

### 2.2 Composer MTP DAG on the critical path (1,785,611 cycles; the calendar adds +5,480)

| category | cycles | share | largest items |
|---|---:|---:|---|
| ROM field matvecs (layers) | 795,861 | 44.6 % | wo_a 207,468 (measured-OLD), experts_gu 152,960, wq_b 143,970, down 122,440, router 61,455, wo_b 59,137, a_proj 36,809 |
| MTP wave composite (wave.busy: verify waves) | 226,630 | 12.7 % | logic 200,795 + links 25,055 |
| collectives (TP4 allreduce / allgather / merge) | 138,292 | 7.7 % | out_allreduce 44,204, combine_allreduce 44,204, a_allgather 20,812, router_allgather 19,952 (offchip 65k + xdie 43k inside) |
| SU vector ops | 131,598 | 7.4 % | quant 20,120, norm.scale 17,748, q_quant 17,720 |
| extra ledger terms | 120,131 | 6.7 % | price_of_record_residual 32,925, scan_d 18,465 + 27,680 + legs, dv_p4l 23,256 |
| stage / die hops (links) | 119,974 | 6.7 % | unplaced_hops 55,986, substage_hop0 36,120, substage_hop1 15,351 |
| indexer (score / topk / q_field) | 111,585 | 6.2 % | topk_local 47,945, idx.score 29,573, topk_final 27,059 |
| attention svc (scores / pv / window / gather) | 52,959 | 3.0 % | scores 30,760, window_load 17,024 |
| head die (lm_head, draft, argmax) | 52,545 | 2.9 % | draft.head 42,250, lm_head 8,450 |
| control (mc.*) | 30,651 | 1.7 % | p2.selected_path 15,357, wfc_kit.ar_pass 13,560 |
| other (top6_order, embed) | 5,384 | 0.3 % | |

- **By kind:** logic 1,344,034 / off-chip PHY 118,238 / xdie legs 117,157 / layer terms 87,204 / plan lanes (wire)
  71,937 / adjust 32,925 / tail 7,975 / edge 6,140. **All link-type terms together are 313,472 (17.6 %).**
- **R8 landing pads:** +2,670 cycles/step (-3.5 tok/s) against the same plan without pads. They are inside the lane
  terms (field_round 112 -> 118).
- **Grades:** measured-current 25.8 %, measured-old 54.3 %, priced 13.3 %, PHY model 6.6 %.

### 2.3 Recoveries (what_if.py on the record model; tok/s as record law / pipeline law)

Each case changes one input and reruns both laws.
**"Plan/compiler"** = no RTL change. **"RTL"** = needs RTL (and usually area or kits).

| # | change | side | MTP tok/s (record max law) | delta | under the pipeline law | AR tok/s |
|---|---|---|---:|---:|---:|---:|
| R1 | MTP rate of record = the causal pipeline law instead of max(6f, pipeline) | model of record (COORD/owner) | 2,763.0 | +234 | 2,763.0 | 789.1 |
| R2 | indexer off the critical path entirely (idx.score/topk/merge/q_field x0); upper bound | RTL + plan | 2,814.1 | +286 | 3,051.6 | 854.3 |
| R3 | indexer 2x faster (idx.score + topk_local + topk_final x0.5) | RTL (more bk_sel quarters / rg3 engines) or plan (more readers) | 2,669.4 | +141 | 2,907.0 | 817.1 |
| R3' | split the 4 indexer dense stages (L2/8/14/20) onto 2 stages each, DENSE2-style; bottleneck 55.3k -> ~38k, +4 hops (analytic, not run) | plan only (+4..8 dies) | ~2,670 | ~+140 | ~2,855 | ~788 |
| R4 | ROM field matvecs x0.8 (all 8 field ops) | compiler (frame/phase placement) or RTL | 2,778.2 | +250 | 3,060.0 | 878.5 |
| R5 | attn.wo_a x0.5 (largest single op, 4.2k/layer, measured-OLD BF P231 x 20 phases) | compiler (spread the BF pairs over more frames) or RTL | 2,685.9 | +157 | 2,935.7 | 841.3 |
| R6 | collectives on-die part x0.5 | RTL (fewer rstop edges / ring links) + compiler (overlap) | 2,665.6 | +137 | 2,894.0 | 829.6 |
| R7 | stage-hop message on 2 circuits (H_MSG 652 -> 326) | plan + compiler (LINK5 striping; lep check) | 2,580.2 | +52 | 2,824.7 | 810.1 |
| R7' | stage-hop message on 3 circuits / FP8 x (H_MSG -> 217) | plan + compiler (numerics review if FP8) | 2,597.9 | +69 | 2,846.0 | 817.3 |
| R8 | G16 attention service instead of G4 (scores/pv 289/596) | RTL / plan (more svc groups) | 2,559.8 | +31 | 2,830.7 | 809.5 |
| R9 | head lm_head + draft.head x0.5 | plan (2nd head die) / RTL | 2,561.5 | +33 | 2,802.4 | 791.3 |
| R10 | draft tail x0.5 | compiler/plan | 2,556.0 | +27 | 2,795.8 | 789.1 |

**Combinations (run, not added up):**

| combo | MTP tok/s (record law) | under the pipeline law | AR tok/s |
|---|---:|---:|---:|
| A = R7 + R3 + wo_a x0.75 | 2,815.8 | **3,072.7** | 868.3 |
| B = A + collectives x0.75 + G16 | 2,939.7 | 3,240.4 | 918.5 |
| C = B + wo_a x0.675 and the other field ops x0.9 | **3,090.6** | 3,426.9 | 973.8 |

### 2.4 Reading

- **The floor is reachable without new hardware only if the pipeline law becomes the rate of record (R1).** The
  model, plan and compiler recoveries R7 and R3' plus a compiler wo_a respread (~x0.75) then give about 3,000-3,070.
  Under the current max law the same set reaches about 2,800.
- **Without R1, 3,000 needs RTL work on two fronts.**
  - The indexer layers: R2/R3. These are also the S81.HW items H1-H4 above, which must be built anyway.
  - The field matvecs (R4/R5): wo_a is measured-OLD at 4.2k/layer against wo_b 1.3k.
  - Combo C is about the smallest mix found that clears 3,000 under the max law.
- **The 4 indexer stages set the pipeline increment (54.6k)** and the 6f wave term (5 x 54.6k).
  - Any change that leaves those stages at ~55k occupancy cannot pass ~2,800 under the max law.
  - **Splitting or speeding the indexer layers is the single highest-leverage item.**
- Small items: the R8 pads (-3.5 tok/s), the pipelined-reset boot (0 per token), and the S81 +1-cycle 2-flop stations
  (a few hundred cycles).
- **Caveats:**
  - All of this is MODEL. 80 % of the critical cycles are measured-old or priced, and there is no v4.8 die layer
    replay.
  - The analytic R3' estimate needs a stage-map rerun (dv_mu_calendar_phys on an edited 241-map) before anyone
    relies on it.
