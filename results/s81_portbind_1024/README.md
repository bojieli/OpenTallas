# S81 port-bind gap audit (S81/PORTBIND, 2026-10-25)

Plan: v4.8 on `claude/s81-h4-1024r@48590fb90f` (H4 tree lanes in, bk_col retired). The `claude/s81-dec12-1024r` rebase
waits until DEC12 posts READY.
Run dir: `epyc1:/srv/opentallas-scratch2/claude/s81-portbind/bind48`.

## Method (existing tools only)

- `tools/die_plan/check.py --completeness` (G0C) passes 179/179 on this plan. It cannot see these gaps: every plan bus
  has a lane (0 buses without a lane). The gaps are leaf ports that have **no plan bus at all**.
- `tools/die_plan/bind.py` (BINDER4 as-built bind) can see them. Inputs:
  - the cached BINDER4 elaboration of the as-built die (cap30 `dv_die`, `b3r8/asbuilt.json`);
  - `asbuilt_s81_off.json`, with paths moved to scratch2;
  - a map from `mk_map_s81.py` on the v4.8 `instance_map.json`;
  - one transport rule for the retired `dsdv_bk_col` (vo_s <- vi_n, vo_n <- vi_s, as H4's census `retire_rung`).
- Result: `bind` gives unplanned (crossing) bits **0** (v4.6 had 1,347; they are all fixed in v4.8). What is left is
  this list.
- `physical/die_plan/s81/bind/portbind_audit.py` runs the same Binder (map, analyse, buses; no emit) and dumps every
  leaf port that is:
  - driven by a die-top port or by a literal;
  - an output that drives a die-top port, or has no load at all;
  - a plan lane with no as-built endpoint;
  - an empty partition.
- `classify.py` then sorts them into classes, giving `audit.json` (all items, pin by pin).
- Caveat: the as-built is the cap30 RTL. Newer RTL changes (H4 lep, H23, RTLC drops, KITS splits) are not in it. Port
  names and widths of the unchanged leaves hold.

## Gap count by class

Ports, with bits in brackets; ok items (SerDes PHY pma_* = modelled die IO) are not counted.

| class | inputs | outputs | plan lanes | meaning |
|---|---|---|---|---|
| needs_lane | 5 (525) | 71 (737) | 18 (74) | functional path with no plan lane: design items D-QTREE, D-CFG, D-FNET |
| planned | 2 (552) | 1 (276) | 11 (4,932) | the plan carries it, but the as-built or RTL has no endpoint yet: H4 tree lanes, XDIE reserve pair B |
| dead | 140 (195,352) | 49 (27,189) | - | no producer or no consumer: drop on both ends (RTL narrowing, as OWNER DECISION 8) |
| strap | 10 (10) | - | - | coll lane `chb` = the slice strap `ch_b`. Bind config gap: FIXED on this branch (asbuilt_s81_off/r8 straps += chb); `audit.json` is the post-fix run, so the 10 appear there as declared straps |
| tied (violation) | 0 | - | - | every literal is either a strap or the unused arm of a dead port |

Other findings:
- Empty partitions: `lk_WS2` and `lk_EN3` (XDIE PHY RTL owed), and `s_1N_x06` and `s_5N_x06` (station cells that no
  lane passes after the H4 col-1 rung collapse: drop or reuse in DEC12).
- INFO: 30 hard-core types have no `core_conns.json` entry, e.g. all C partitions, col_h* frames, gunit, bk_sel__t2
  (H4 renamed t1 -> t2 and the entry was not carried). Their core-pin binding cannot be checked from the plan.

## The real gaps and their fixes

### D-TOPK: final TP4 merge of the four rank roots (attn.idx.topk_final). No hardware path today.

**Where it runs.** The four rank roots are the TP4 dies of the root stage. Their links, from LINK5 (dv_mu_calendar
CIRCUITS):
- s_7N pair A = TP d+2 (one bidirectional EN<->EN circuit);
- s_7S pair A = TP d+1;
- s_0S pair A = TP d-1.
s_0N carries only stage NEXT/PREV, so the H4 lanes cannot reach a TP peer.

**Recommended (T-A): replicated butterfly merge-reduce.** No root is special. All four end with the same final list, so
there is no broadcast-back step.
1. Exchange over d+2 (s_7N). Each root sends its 512 (score, position) candidates. Each runs `bk_sel` over
   own + peer. The result is the top-512 of the pair.
2. Exchange the pair result over the ring: TX on s_7S to d+1, RX on s_0S from d-1. Each runs `bk_sel` over its pair
   result + the other pair's result. The result is the top-512 of all 4 ranks.
   - This is exact: top-k(A ∪ B ∪ C ∪ D) = top-k(top-k(A ∪ C) ∪ top-k(B ∪ D)), with lowest-index tie-break as in
     lower_bk.

**Hardware.**
- Four registered 276-b lanes, ft <= M7, stations <= 405 um:
  - `tp__bk_sel__s_7N_LP` ~28 cyc and `tp__s_7N_LP__bk_sel` ~28;
  - `tp__bk_sel__s_7S_LP` ~49 (TX only);
  - `tp__s_0S_LP__bk_sel` ~61 (RX only).
  - About 1,100 b in all, roughly 42k station bits.
- The three TP leps get H4's IDX slot mux/demux. It is the same `ot_s81sl_lep_mu_ab_idx` logic: a type-5 link frame,
  a static slot, and a sticky fault on a collision.
- `dsdv_bk_sel_vmtx` / `dsdv_idx_vmux` get two more registered inputs (tp RX from s_7N and s_0S). They also get an
  internal loop-back of `u_tx.lo` (no pin), so the root re-ingests its own candidates. Two valid beats in one cycle is
  still a fault: the compiler serialises own / peer.

**Back to every die's SEL_IDS.**
- After step 2, every rank root's `bk_sel` egress holds the final list.
- H3's encoder (claude/s81-h23-1024r@4ecbcda0a2) turns it into SEL_IDS. It goes `xtier__bk_sel__seqhost` (65 cyc) ->
  seqhost relay -> `unit__seqhost__svc_5/11` (13/18 cyc), and the svc entries merge it into q.
- The shard (non-root) dies only score keys. They hold no layer-L KV rows, so they need no final list.
- If TOK-DS says a shard die does need it, the root sends it down H4's tl -> ca/cb tree (H4 return path), one LEG per
  edge.

**Price (est., per instance).**
- Each step: lane + lep 3 + link ~295 + RX 2 + lane + vmux 2, about 360 (step 1) and 425 (step 2) cycles. Add the
  ingress of own + peer sets and TAIL_BUDGET 640.
- With the indexed13 sparse encoding (~80 beats a set): about 1.16k + 1.25k = **~2.4k cycles**. The model prices
  topk_final 3,382 + topk_merge 503 per instance (27,059 + 4,024 / 8), so this is **0 delta** (about -1.4k).
- With dense BEAT words at the worst-case TX grid (TX_SM 1,600 beats a set): ~8.5k a instance, **+4.6k a instance,
  +37k MTP-critical over 8 instances (~0.2-2%)**. The compiler must use indexed13 on these lanes.

**Alternative (T-B): reuse the existing lanes.** bk_sel vo_s -> `xtier__bk_sel__s_4S_C` -> xring -> s_7N/s_7S/s_0S
C -> lep. Zero new lanes, but a new IDX beat kind is needed in rstop/xrt/lep (the xr RD header collides with the BK
lane/part/type fields), and it shares V-rung and ring slots with control traffic. This is TOK-DS option B. COORD chose
option A for H4.

### D-QTREE: rank-tree query fan-out. `dsdv_idx_qf` ql (513 in) and qc0 / qc1 (513 out) have no lanes.

- The type-10 tree frame must reach every shard die of the rank.
- The shard dies are the k = 3/6 consecutive stages of the rank, so every tree child is NEXT-ward on s_0N pair A. A
  child receives on pair B, the same convention as H4.
- So one out link and one in link are enough. **qc1 is a copy of qc0: drop it on both ends (dead).**
  - Confirm with TOK-DS that the shard -> stage map in lower_bk is monotonic. If not, keep qc1 and route it the same
    way as qc0.

**Recommended (Q-A, the H4 pattern).**
- Two registered lanes `ql__s_0N_LP__iqf` and `qc__iqf__s_0N_LP`, about 55 cyc each (iqf col 7 row 0 -> LP col 6 row
  14, ~18.6 mm). Either 513 b each, or 276 b each with a 2-beat serializer in qf (+70 beats a frame, half the bits).
- The s_0N lep gets a Q link frame kind beside H4's IDX kind, plus a cut-through relay bit (pair B RX -> pair A TX) so
  pass-through dies do not detour via iqf.
- qf forwards only when this die is not the last uid in the frame's spec table. Otherwise the next stage, which is
  outside the tree, would raise "no entry".

**Cost.**
- 1,026 b (or 552 b) x ~53 stations, about 54k (29k) station bits.
- The col-6 cut is already 0.57 after H4. Adding 552-1,026 b on col 6 crosses 0.60, so the path must take col 7 or 5,
  which needs ft slots in col-7 types (svc_0, s_0S_C, s_0N_C). That means GEOM plus the DEC12 batch: OWNER?/COORD.

**Price.** Per tree edge ~55 + 3 + 295 + 2 + 55 + qf 3 ≈ 413 (+70-140 frame beats), under the model's LEG 729 a
depth level (lower_bk `tq_d = t_q + depth * LEG`).
- Delta 0 for 1-hop edges.
- Shard_tree edges that skip stages (0 -> 3, 3 -> 5) add pass-through hops of ~300 each (lep cut-through). The deepest
  die gets the query about +0.3-0.6k late, i.e. **<= +4.8k MTP-critical over 8 instances (<0.3%)**.
- Alternative 0 delta: a chain tree (every edge one stage hop) in lower_bk.

**Alternative (Q-C).** Move iqf to the free bk_col cell (row 19 col 8, top edge, 2 cells from bk_sel). The tree
lanes become ~22 stations each along H4's row-18 path. But `s_3S_C -> iqf` and `iqf -> svc_0` grow (+~20 cyc local
query path, ~same total bits). It is a floorplan change, so GEOM is needed.

### D-CFG: die-position configuration with no source

`iqf.uid[7:0]` (the die's rank-tree uid) and `eng.cfg_en`, `cfg_layer`, `cfg_rank[1:0]` were die-top inputs in the
as-built. They differ per die in the array, so they cannot be partition parameters (one mask).

- **Recommended (C2): boot-time config writes from the host. 0 new lanes, 0 cycles on the token path.**
  - eng sits on the col-6 V rung (`xtier` vi_s/vi_n). A CTL beat (kind 0, uid-addressed, a new op "cfg") loads a
    config register.
  - iqf takes a CFG frame type on its qs input (lane `idx__s_3S_C__iqf` exists) that sets its uid register.
  - The host sends both in the in-band boot sequence (WN2/3 -> s_0N_LP -> seqhost).
  - RTL: about 20 flops + decode per unit, with a bench and a mutant.
- **Alternative (C1): 12 strap bumps** (8 iqf + 4 eng). Both partitions sit on the die's bottom edge. This is a new
  non-PHY die.io class, so OWNER?.

### D-FNET: die fault/status network. 71 output ports (737 b) plus the 18 unused sid/vid ring lanes.

**What is affected.** Sticky faults and status that went to die-top ports in the as-built:
- `block_fault`: slice u_flt (12), etap (16), gunit, bk_sel, pvso entries;
- `land_fault`, the bk_sel vm_fault/tx_st, irg st (8 x 10 b), iqf st, eng st;
- seqhost t_mf/hostb_fault/hb_job_active, the s_0N hbc faults/arm state, pvso so_ready/done/fault_code, lnland k_st,
  phy_hbm k_oor.

Today none of these has a sink, so synthesis may remove the fault logic, and a fault is never observable.

**The plan already has the rings, but they have no RTL ends.**
- `sid_*` (5 b, slice id + fault OR, seqhost -> 16 C slices -> seqhost);
- `vid_*` (4 b, svc ring).

**Recommended.**
- Each unit ORs its fault/status bits into one sticky bit and puts it on the nearest ring, registered every hop:
  - C slices on sid; svc and irg on vid;
  - LP k_st/lnland into its C slice;
  - bk_sel / gunit / eng / iqf / phy_hbm on a 5-hop unit chain bk_sel -> gunit -> ... -> seqhost, or folded into vid
    at svc_0/svc_14, which are next to iqf/eng.
- Seqhost (sidr_i/vidr_i) latches a die fault word and returns it on its existing host return (t_host -> s_7N lep).
- The detailed status codes (irg st, tx_st, so_fault_code, hbc arm state) are dropped to the 1-b sticky OR, unless
  the owner wants them readable.
- Cost: under 100 ring bits. RTL in seqhost, the C slice wrapper, the svc wrapper, and 5 units. **0 cycles** (not on
  the data path).
- OWNER? because it fixes the debug/observability contract.

### Dead class (drop on both ends; RTL owners named, no plan change: the plan has no bus for them)

- **D-SVCARITY.** The 4-arm `dsdv_svc_rs` / `_pvso_entry` node ties the unused child arms: dn_i, up_i, ri, gi_*, si_*
  (191,430 b over 16 instances). Outputs `*_nc` open. q[514:513] is tied. Fix: a per-type arity parameter. Owner: svc
  (H23 lane).
- **D-CAPEND.** `capc5r` / `capc2` rt_e/rt_w at the slice-row ends (3,920 b). Fix: per-variant narrowing. Owner:
  KITS/RTLA.
- **D-XEND.** `col_h9/h10_l4_lp_r0.xo_o0` of the 24 row-end frames (26,496 b out). Fix: a row-end variant without xo.
  Owner: frames.
- **D-HBCDBG.** hbc boot_edge/receiver_edge (96 b).
- **D-MURT.** TP-end lep mu_rt (s_0S/s_7S, 64 b).
- **D-XWV.** xg xw_v (16 b).
- **D-GLUE.** The iq slice fault flop with D = const (and its Yosys not).
- **qc1** (D-QTREE).

### Planned (no design work; binding owed)

- H4 `tl`/`ca`/`cb`: the GEN or a fresh bind must use the H4 RTL (lep ca_o/cb_o/tl_i). The as-built still routes
  them to die-top ports.
- XDIE pair-B coll lanes (8): s_7N/s_0S lep pair-B ports owed by XDIE.

## OWNER? / COORD (posted in lanes/S81.md)

1. D-TOPK: T-A (4 dedicated lanes + TP lep IDX mux, ~2.4k cyc an instance with indexed13, 0 delta) vs T-B (no lanes,
   ring kind decode).
2. D-QTREE: Q-A (2 lanes to s_0N_LP via col 7/5, ft slots in col-7 types = DEC12 batch + GEOM) vs Q-C (move iqf to
   the bk_col cell).
3. D-CFG: C2 boot config writes (0 lanes) vs C1 12 strap bumps (new die.io class).
4. D-FNET: fault/status contract (1-b sticky per unit over the sid/vid rings into seqhost, status codes dropped).
