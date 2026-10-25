# TYPE-REDUCE 2026-10-25: distinct hardened designs on the release dies

Owner rule 10-15: dedupe/quantize tile variants; replicated clusters are hardened once.
Inputs: origin/main@0f5d931c2 plans (plans unchanged since 6a6fc12dd). Lane plan branches s81-plan2-1025r, qc-plan3-1025 and hbm-b2o-1025r (B2o) have the same type and core counts.
This is read-only analysis: no plan was edited and no job was run. Census: `analyze.py` -> `types.csv`, `cores.csv`, `summary.json`. Proposals: `proposals.csv`. Family scripts: `scripts/`.

## 1. Exact census (distinct-design count)

Each column below loosens the key further: first exact netlist, then names ignored, then ft slots ignored, then RTL only.

| die | types | exact netlist (dedup.netlist_key) | netlist with names ignored | ft slots ignored | RTL only (contents + cores) | core modules / instances / pin tables |
|---|---|---|---|---|---|---|
| s81 | 177 (398 parts) | 166 | 156 | 48 | 34 | 52 / 4094 / 58 (2 are memory macros; 6 leaf cores have an extra `_xm` view) |
| s81_head | 16 (326) | 16 | 16 | 10 | 8 | 2 / 5 / 2 |
| qwen_compute | 56 (377) | 56 | 56 | 54 | 51 | 10 / 68 / 24 (su_lane_e/w have 8 tables each; 80 bound modules) |
| qwen_kvsys | 49 (160) | 45 | 39 | 35 | 25 | 34 / 584 / 34 (76 bound modules = 20 logic signatures) |
| hbm B2n | 49 (88) | 49 | 46 | 49 | 46 | 210 / 436 / 280 -> 66 RTL masters; 174 (master, normalised pin table) pairs |

OWNERS.tsv has 655 items, which undercounts the real kit work: HBM is 226 designs in the HBM-KITS census and QC is 19 core kits.

**What drives the counts**
- **S81:** ft-slot population. The leaf family has 72 types for 75 instances, slice_station 35 for 46. The leaf carries 226 kb of ft: 31.6 kb of system "misc" lanes plus 3 regular lane systems (dn/up 0/1/2, x+rt 0/1/2/4, xtier 0-3). That gives 32-51 population classes, plus station-count differences.
- **QC:** stale contents labels. 7 W/E slice pairs have identical bound RTL, windows and ft. The rest are W/E window and ft asymmetry and narrowed chain-end ports.
- **KV:** per-row R8 alignment pads (hg), ft population (hgi, 9 types of one logic), and lane-numbered bus names (pv N/S pairs, pc_v1/v2).
- **HBM cores:**
  - Per-instance pin tables: the plan pins every instance toward its own neighbours.
  - Constant straps: tile_tid, map_lane_j and lane_lane_id turn one master into 16-32 netlists.
  - Split pieces named per position: 64 idx hcol pieces = 2 RTL masters.

## 2. Quantization proposals

Rules applied to every proposal: no superset pins or slots (R7), so classes keep every slot in use, and mirroring is used only as a whole-instance orient.

| die | types now -> proposed (cons / max) | cores now -> proposed (cons / max) | main mechanism | cost |
|---|---|---|---|---|
| s81 | 177 -> 104 / 100 | 56 views -> 48 / 46 | leaf 72->12-16 ft classes (see S81 below); serdes 11->5, c1x 9->4, kv_leaf 5->3, col 12->8; drop `_xm` views; LLfu=LLfd, NNfu=NNfd by MX | 0 area; +2..4 cycles on the moved misc lanes |
| s81_head | 16 -> 16 | 2 -> 2 / 1 | real chain-end differences; elemB -> elemA optional (both closed) | - |
| qwen_compute | 56 -> 34 / 30 | 19 kits -> 13 / 12 | 7 exact W/E merges (fix labels) + 4 after symmetric re-pack; fw/fe 10->2-4; CB S2 transit out (-2); coll_ft grid; su_lane e=w with 4 interface classes x orient | 0 cycles; small ft wire |
| qwen_kvsys | 49 -> 32 / 20 | 34 -> 26 / 13 | hg 8->3 (R8 pads -> published latency); hgi 9->6->1; pv 13->8->3; head_eighth 8->3 and astk 4->1 via boot-config ID registers | about 1.1k config flops; 0 datapath cycles; hgi strip about 360 um if fully taken |
| hbm | 49 -> 45 / 41 | 226 designs (210 modules) -> 71 | one hardened core per RTL master and interface with one pin template; straps -> driven IDs; q_sm0-3 -> 1 | 0 cycles mostly; +1 relay on outlier pins (p90 >405 um: su lanes4, bankq lanes6_7, sm_group_rel_id, kshare) or re-place the parent |
| **total** | **347 -> 231 / 207** | **337 real (308 items) -> 160 / 143** | | |

At about 1 sign-off/h, the queue goes from about 655-685 to about 350-391 sign-offs, roughly 11-13 days less serial sign-off.

### S81 (S81-PLAN / LEAF3, S81-PLAN2, S81-CORES)
- **(a) Recommended: fixed ft classes.**
  - Move the misc system lanes (ctrl, seqhost, attn/idx/vid, gunit/bk_sel/eng xtier, sid; 31.6 kb, found in 47 of 75 leaves) out of the leaves into the edge station columns 6/15 and the C rows.
  - Use the corridor-first fixed leaf template (LEAF3 is already building this): a fixed window per lane kind.
  - Re-pack x+rt to 2|0 per leaf and xtier to 1|0; dn/up stays 0/1/2 (the star from C).
  - Result: 3x2x2 = 12 classes, every slot used. Leaf 72 -> about 12 (16 if some re-packs fail).
  - Risk: station N/S face load (today max 4,997 of 8,657 pins), so check per column before adopting.
- **(b) Rejected: separate FT strip partitions.** Worst leaf 5,158 b N-S needs an 860 um strip at 6 pins/um, which adds 1.9-6.9 mm of die width.
- **(c) Mirroring and (d) common outline:** about 1-2 types each; outlines are already uniform (1442.88 x 1226.88).
- **Cores:**
  - `_xm` leaf-core views (ve_m/ve_s/vn_a/vn_b/vq/vs) become 1 table + instance MY. N/S pin order reverses inside the leaf: -6.
  - LLfu=LLfd and NNfu=NNfd (RTL differs only in name): one design + MX: -2.
  - LLd needs a real fault-chain `fi` driver to merge.
  - Everything else is truly distinct.
- **Dedup tool caveat:** `dedup.netlist_key` keeps `bit_sites_um` in the ft slots, so register-site geometry counts as netlist.

### QC (QC-PLAN)
- **No-plan-change merges:** slw/sle hc0-3, st_a, st_b, su_l0 (+ `_v1`). gen_plan.py:476 labels east contents "s6b", but the bound RTL is the same.
- **Symmetric W/E re-pack:** sc (+514 b), stm, su_l1, su_c (crh_rp1 -> crh).
- **fw/fe 10 -> 2-4:** neutral port names; chain ends get real lanes.
- **cbf_q00/q01 `_s2`:** take the S2 transit out of the CB, -2.
- **su_lane:** e=w, then 4 interface classes in 2x2 orient, giving 16 kits -> 4-5. A single table for all is impossible without superset pins.
- **Re-bind first:** bound_r8 is older than plan3, so re-check every merge on the new bind.

### KV (KV-PLAN, KV-CORES)
- **hg_v1_r1..r5 + v2:** one logic signature; only the R8 pads (267/0/267/5/272 delay bits) differ. Publish per-row latency to the compiler (static schedule) instead of padding: 8 -> 3. OWNER ruling needed (open since TYPE-DEDUP).
- **hgi:** E/W-balanced lane re-pack 9 -> 6; end rows = mid rows 2; N-S FT strip 1 (about 360 um, not recommended).
- **pv N/S pairs:** neutral chain-bus names 13 -> 8. Per-row fixed-width reduction of the growing 1-bit S->N slots -> 3; this assumes they are OR-reducible fault/idle bits (unverified).
- **pc_v1 = pc_v2:** rename.
- **head_eighth e0..e7:** BSEL/HID are 4 constant bits compared with the beat number. Replace them with a boot-config register per core loaded over the ectl config chain (a real lane, not a tie): 8 -> 3 cores (MX pairs upper/lower).
- **astk EN/ES/WN/WS:** 2-bit quadrant register, 4 -> 1.
- **hub_Wi qkd_hr_*:** 15 truly distinct functions. Optionally make 3-4 clock-domain clusters of <=400k cells each (needs measured cells).

### HBM (HBM-PLAN, HBM-KITS, HBM-CORES)
- **Master groups:**

  | group | today | proposed | note |
  |---|---|---|---|
  | idx hcol HALF0/1 | 64 modules, 12 xy tables | 2 | |
  | tkm tile | 32 | 2 | end tile has no up_in; never tie it |
  | sfu lane | 16 | 1 | |
  | su exp lanes | 15 | 2 | |
  | su lanes4 | 12 | 2 | one outline for pv0/pv8 |
  | hcp_lanes x3 | 8 | 3 | interface classes |
  | hc_root tails | 6 | 3 | |
  | multi-table singles (pc_ctrl h9b, vms_bank, vmdel, ...) | 46 tables | 13 | one table each |
  | **total** | 210 modules / 226 designs | **71** | |

- **Straps:** become driven IDs (chain-derived i = i-1 + 1, or a config register). Never tie at the parent (R7). Re-prove each with LEC / lockstep.
- **Kits:** HBM-KITS batch1 runs 14 CTS kits for 3 designs (11 redundant). 1065 kits were already made per module/table (stopped at yosys). Batch2 plans 33 TKM + 19 SFU kits before the strap delta. **Stop per-piece kitting:** kit one per master/interface after the template delta.
- **ownership.py:** key core items by (rtl_top + params, sha(normalised pin template + outline)) with a replica count. Until then, count per distinct table (HBM-KITS `design` column), because today a signed hcol clears none of its 31 replicas and pc_ctrl (10 tables) counts as 1.
- **Types:** q_sm0-3 are identical apart from lane-numbered bus names, already placed R0/MY. Neutral names + symmetric windows give 4 -> 1. q_b001/003/012/013, b002/b011 and spb2/spt0 could save 2-4 more.

## 3. Hard cores: replicas hardened once?
- **s81:** yes, except the 6 `_xm` views and 2 name-only node duplicates.
- **qwen_compute:** su_lane is kitted per placement (16 kits for 1 RTL).
- **qwen_kvsys:** head_eighth has 8 modules for 3 logic classes; astk has 4 for 1.
- **hbm:** NO. Kits are per plan module and pin table: 210 modules / 280 tables for 66 masters, and batch1 CTS is 11 times redundant.

## OWNER? (need rulings before the delta)
1. **Constant straps -> boot-config / chain-derived ID registers** (a real lane, not ties) for HBM tkm/sfu/su lanes and KV head_eighth/astk. Is this acceptable as "no tie-off"? It costs 1 boot cycle and a few flops per core.
2. **KV R8 per-row alignment pads -> compiler-visible per-row latency** (static schedule) so that hg 8 -> 3.
3. **S81 misc lanes moved from leaves into station columns:** +2..4 cycles on those lanes. Within the accepted-cost ledger?

## Risks
- Every merge needs a re-bind + G0/G0C + GEOM PASS.
- Pin-template moves raise face density (hcol and pc_ctrl change face on about half their pins): face_guard and pin_track must stay <= 0.6.
- Displacements over 405 um add relay stages, which go into the latency table.
- Equivalence claims rest on RTL diffs; LEC must confirm them.
