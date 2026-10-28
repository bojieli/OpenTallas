# DIE-HBM-9 (2026-10-28) — ESTIMATES only (no build, no adoption)

Basis: plan C20j (intel2 codex-hbm-die-1028/c20j), hbm8 A+B face model (B = {SU,IDX,HC,FUSED}, hard-core spans subtracted,
SA on net capacity, 4x3 grid, 3 seeds). Tool runs CHECKED; models UNCHECKED. Shared model for crossings: main 689554dda3
tools/die_plan/locality.py + cap_reading, unchanged (snapshot /srv/opentallas-scratch2/claude/die-hbm-9/mainsnap).

## (1) Strict bind sbind_canon — COLLECTED (CHECKED tool run; finished 08:02, 37 min, not stuck: sbind_cs took 30 min)
/srv/opentallas-scratch2/claude/die-hbm-7/sbind_canon/bind_report.json: 86 partitions, 78 types, 350 crossings / 153,179 bits,
FAIL-CLOSED with 473 errors (as expected):
- UNMAPPED 32,810 cells: all hb_idx__s_* (the open idx slices: scorer prims + keybuf).
- TIED 10,656 bits on 638 leaf pins (21 classes), e.g. hb_idx__selector.in_line[1184..] = 0: inputs of the unmapped idx slice.
- UNPLANNED 30 partition pairs: as-built crossing bits with no plan lane path (hub<->hub 2.7k each way, hub<->root 0.5-2.7k,
  spb0/vsN0 615-632, sm->hub 37 each, su ring 1 b each) = the fold provider nets + root-slot nets.
- TYPE_SPLIT 28: NW/NE twins (b0xx, b1xx, su*, spu*, spb*, spt*) differ in their ft lane order (mirror lane index) or conns.
- LOCAL_NAME_CLASH 10: calendar / hb_idx op,q,qctl / hb_vms N and S role leaves both named u_*_Q (fold halves need __q0/__q1 local names).
- EMPTY_PARTITION 2 (NW_mca, NE_mca) + EMIT 1 (wavefront reset carriers need NW_mca/NE_mca bound).

## (2) Fan-out core replication per hub half — rep/ (hub_replica_est.py, summary.json)
Premise check: every hub ALREADY holds 2 full-outline copies of each fan-out core (PATH-HBM-R9 service quadrants q0/q1, same
module, one per segment): pgp, cxij_q, calendar, sucore, smw, coll body/reduce/edge/vm/ring. calendar and smw are already
half-local (all edges L-L / R-R). So "replicate per half" = re-align clients to the copy in their half (no area), or add copies.
Variants (S5 = pgp,cxij_q,calendar,sucore,smw; S6 = S5 + coll body; S12 = S6 + coll reduce/edge/vm/ring, cij, hcollg):
| variant | added hard area / hub | worst face NW | worst face NE | x-bisection v1 bits/net pins | quarter cuts v0/v2 |
|---|---|---|---|---|---|
| base (hbm8, reproduced 1.678/1.702 s1) | 0 | 1.48-1.81 | 1.47-1.70 | 1.16-1.64 | 1.24-1.54 |
| half S6 (re-align to existing copies) | 0 | 1.09-1.81 | 1.23-1.50 | 0.89-1.19 | 0.97-1.45 |
| half S12 | 0 | 1.26-1.48 | 1.16-1.54 | 0.88-1.49 | 1.06-1.35 |
| col S6 (4 copies/hub, +2/group) | +3.03-3.09 mm2 (12 copies) | 1.41-1.68 | 1.37-1.44 | 0.94-1.67 | 1.12-1.40 |
| col S12 | +4.28-4.32 mm2 (20-22) | 1.29-1.39 | 1.36-1.63 | 0.81-1.30 | 1.13-1.43 |
| UPPER BOUND: fan-out edges deleted (S5/S6) | - | 1.35-1.62 | 1.30-1.47 | 0.84-1.57 | 0.97-1.27 |
| half S6 + half-local VM banks (vmb/vmdel k<->k^4) | 0 | 0.996-1.34 | 1.30-1.46 | 0.57-0.87 (0.87-1.39 NE) | 0.82-1.21 / 1.05-1.15 |
VERDICT: replication of the fan-out cores does NOT close the faces; even deleting all their edges leaves 1.30-1.62. Fan-out
bits are only 5-8k of the 20-37k bits on each vertical cut. The cuts are dominated by SM <-> VM bank traffic (face:SM,
core:VM, SM/VM, DMA/VM: ~23k of 32.6k on NW v1). With half-local VM bank allocation the x-bisection itself passes
(v1 0.57-0.87 NW), and the failure moves to the in-half quarter cuts v0/v2 (0.82-1.38).
- Area: half = 0 (copies exist; all groups already have one copy per half, 0 moves needed). col = +1.9/3.0/4.3 mm2 per hub
  and cell hard utilisation 1.0-1.21 (> 0.80 cap): FAIL physically. Per-kit cells: no new kit; copies are existing signed
  masters (pgp 78k, sucore 169k, calendar 24k, smw 49k, cxij_q 39k, coll body hard pieces), all <= 400k; hub soft regions
  unchanged (<360k, hbm7). Types: +0 (same masters; ID straps tied per 1.8 if a copy needs a position id).
- tok/s: half re-alignment = 0 % (no schedule change, links shorter or equal; B set cost 0.24-1.91 % unchanged).
  Half-local VM allocation: NOT estimated (needs a ds S2 rerun with half-local bank allocation; capacity per half halves,
  shared tensors need a double write or a scheduled crossing read). If > 5 % -> owner.
- Coherence / ordering (single state): with a static schedule there is no runtime arbitration, so copies stay consistent by
  construction if (a) both copies start from the same release (start sync on the spine at the fork tap, 12.16 b(iv)),
  (b) every input that changes copy state reaches each copy through a fixed-latency CA crossing, (c) same master + same
  programme (LEC per strap variant). State that must stay SINGLE: the calendar's ownership of a bank (each calendar copy owns
  only its half's banks; a bank is never served by both), the collective reduction order (body q0/q1 -> reduce combine order
  fixed by the schedule, so FP sums stay bit-reproducible; the cross-half combine stays one scheduled crossing), the global
  programme/step counter (one source at root, distributed via the start tree), and any tensor both halves read (one owner
  bank + scheduled crossing read, or a scheduled double write).
- What else closes it (next estimates, no build): (i) half-local VM allocation in the schedule (above; tok/s owed);
  (ii) on top, per-SM-row bank affinity inside a half or channel-aligned non-uniform cuts for v0/v2 (hbm8: channel cuts alone
  0.79-1.15); (iii) a taller hub (vertical cut length scales: ~1.2-1.4x needed, i.e. 4.32 -> ~5.2-6.0 mm, die-plan change).
  SA spread between seeds is +-0.3 (noisy objective), so each pass claim needs >=3 seeds plus a constructive placement.

## (3) Re-tree of the hub loops (local form) — retree/ (hub_retree_est.py)
A 4x3 grid has 17 faces; a spanning tree has 11, so 6 face pairs (12 crossings) are ALWAYS off-tree; the plan can only make
each close the SHORTEST loop. All 2,415 spanning trees x 12 roots enumerated on the shared spine hop delay; min-bottleneck
tree = COMB: spine along the middle row (c01-c11-c21-c31, root c11), vertical teeth per column. Every off-tree face (row 0/2
horizontal neighbours) closes a 4-cycle (3 tree hops). Scored with the shared model unchanged (hbm8 net_noSM_s2 ports):
| tree | worst unshared off-tree (ua+ub) | tree hops | min CA margin | max p_tt | depth | fail | max lat |
|---|---|---|---|---|---|---|---|
| hbm8 spine MST (root c10 / c21) | 5.64 / 5.87 ns | 3-7 | 138.7 / 235.7 ps | 266 / 271 ps | D4 34 | 0 | 5 |
| COMB re-tree (root c11) | 3.08 / 3.08 ns | 3 | 235.7 / 235.7 ps | 166 ps | D4 34 | 0 | 3 |
Plan event: depth D8 standard (all fit D4 on the bound -> >=4 T spare), start sync ON the spine at each fork tap (hbm8:
width 20 ps, clean), reset release on the same start port. The 12 off-tree crossings remain direct 4-cycle loops: allowed
per COORD 07:52 (a) >=100 ps at D8 on the plan bound (235.7 ps), (b) built-arrival recheck after CTS.
Die level T059<->T060 (CLK-LOCAL-EST-1: 18.55 ns, 9 hops via T029): T059 = NW top-row region, T060 = NE top-row region, joined
in the die tree only at the NE hub root. Plan: feed the top row as its own spine from the centre column (T010 -> T054 -> T057),
with T059 and T060 as tree children of T057, and route the T059<->T060 lanes (L8_5, L21_0, L22_0; 2,456 + 2 x 2,048 b) as 2-hop
chains T059 -> T057 -> T060 through fixed-latency crossings (both tree edges). The loop then moves to the vertical
T055-T059 / T056-T061 links; their residual bound must be computed in the plan event (not estimated here: needs the
CLK-LOCAL map inputs; next step).

## (4) Partition map
14 slices (12 census + 2 fold hb_idx__s_SW/SE). Rule format: asbuilt.map parts "<leaf>.<child prefix>" -> [partition, local]
(longest prefix) + the slice module in `dissolve`. Proposed per-child rules: slice_rules_proposal.json. BLOCKER found:
in the canonical elaboration the 8 SU slices bind ot_hbm_su_static_pgslice_lg_s (alias) = tap + stub, and the 2 SFU slices
bind ot_hgi_sfu_core_split3_sp2 = 1 cell: the child bodies (u_slice.g_lane[*].u_lane, g_side*.u_side, g_pretree.u_pt,
g_leaf.u_leaf, g_bank..; u_core.u_engine/u_vm/u_rst) are not elaborated, so per-child rules cannot bind until the manifest
prefers the full RTL for those 2 masters. IDX: canonical ot_hnx_idxn_quarter_with_keybuf has ONE scorer with 2 tails
(ge[0], ge[1]) + keybuf, while the plan has 4 quarter partitions b100-b103 each holding a full ot_hbm_idx_score_quarter_static:
the RTL owner must say which source the plan quarters stand for (the rules file proposes ge[0]->b100, ge[1]->b101, glue/fault
-> b100, b102/b103 open, keybuf -> the hub keybuf slots).
Root slots (proposed plan contents, root partition): hb_ckgen (hfd_ckgen_nolink) = the clock source at the local-form feed
root, placed at the die centre-column tap (T010) so the forwarded spine starts there; u_mu_fused_programme
(ot_hnx_fused_host_program) and u_mu_fused_root (ot_hnx_fused_hub_n4ext) = soft root contents next to the host endpoint,
with their lanes to u_mu_fused_n4 in each hub as planned lanes (the UNPLANNED root<->hub bits above). Cells/outline from the
canonical RTL synth (not run here).

## (5) hnx_lane_x plan view (COORD 08:16, HBM-CORES-REBAL-5)
Add plan view hnx_lane_x: outline 289 x 320 um, 1672 pins, centre clock entry, one master (no parameters), ~227k cells.
Child placement per half (each hnx_rp3lp3h_n 631 x 1210 and hnx_rp3lp3h_s 631 x 1037, 16 + 16 per SM, 256 halves): P = 3,
PW = 2, so lanes 0-1 take the W x-store face and lane 2 the E face; the N face carries the shared block-dot operands.
Proposal: u_lane0 at (0, H-320), u_lane1 at (0, H-640) in the W column, u_lane2 at (342, H-320) in the E column (H = 1210 /
1037); 53-um centre channel for the parent face-select and gather glue, operand face on top. UNCHECKED against the
legal3 SRAM placements of the hnx parents (REBAL-4): the next REBAL lane renders and checks the macro + halo clearance
before the child kit.

## (6) ds S2 tok/s for half-local VM banks (COORD 08:2x; ESTIMATE, model UNCHECKED)
Script: `rep/vm_halflocal_cost.py` -> `rep/vm_halflocal_cost.json`. Basis: ds S2 (accepted_cost g25 rank0, 4,120 records),
cost fn unchanged, plus a per-record crossing-read term. Each tensor has ONE owner half (the producer's); the other half
reads it with a fixed-latency crossing read (no double writes). Far share f = 0.5 of a record's VM input bits.
Crossing latency Lx = 4/8 cycles, link width Wx = 2048/4096 b/cycle.
- Realistic scope (SM matvec inputs far, 1,095 records, 73 Mbit; SU reductions pay Lx once):
  - streaming overlaps the op: **+0.36..0.72 %**;
  - serial read: +1.85..5.0 % (Wx 4096: 1.85..2.52 %).
- Blanket bound (every record's VM inputs half far, 3,638 records, 198 Mbit):
  - overlapped: +1.6..3.2 %;
  - serial: +6.6..14.6 %.
- Verdict: <=5 % on the realistic scope, so this stays below the owner bar. Only the blanket serial bound is >5 %.
- Condition: the crossing read must stream under the op (Wx >= 4096 b/cycle, read issued with the record), not be
  serialised in front of it.

## (7) What closes the quarter cuts v0/v2 (ESTIMATE, 3 seeds)
- Tried: column-level bank affinity (`hub_replica_est_q.py --affine-col`, runs `qaff_*`). No effect, because every
  vmb/vmdel bank sits in grid columns 1 and 3.
- Tried: bank-spread (12 even-k banks moved 1 column out) + column affinity (runs `qspr_*`; repointed bits 11.8k -> 36.8k):
  - worst face NW 1.10..1.38, NE 1.18..1.35;
  - v0/v2 0.60..1.22;
  - so, within seed noise: **bank affinity does not close the quarter cuts**.
- Breakdown of v0/v2 (all 6 runs):
  - Face-entry traffic: 4.3..13.8k bits per cut (face:SM / face:COLL / face:VM: hub-face buses that enter in one column
    and serve a client in another).
  - Hard cores straddling the cut line: net capacity 18.2..24.4k vs 25.9k full.
- What closes them (arithmetic on the class breakdowns, UNCHECKED):
  - (a) face windows over the client's column (or the client placed under its window), plus a constructive placement
    that keeps hard cores off the v0/v2 lines;
  - with (a): v0/v2 <= ~0.65 (worst s2 NW v0 (22.3k - 5.5k) / 25.9k);
  - face alignment alone: 0.40..0.92;
  - full capacity alone: 0.56..1.02.
  - A taller hub needs about +38 % height (4320 -> ~5960 um), so it is not proposed.
- Next estimate: a face-window/column assignment in `hub_replica_est`, >= 3 seeds.

## (8) idx quarter partitions: git and plan history (CHECKED from git/plan)
- Plan q_b100..b103 (NW and NE, 8 partitions):
  - each holds "as-built hb_idx__s_NW (1/4 slice)": 15-17 hard pieces `r?c?_k?h?` (ot_hbm_idx_score_hcol_h0/h1, ~190k
    cells each);
  - origin: the HBM-P4-SPLIT twin ot_hbm_idx_score_quarter_static_h (bcc0334cd0, 837c608795), where leaf = chunk_rt_h with
    4 key cols x 2 half-cols;
  - 128 hcol pieces in total.
- Canonical four-role top (bf95306929 / ce19d80797):
  - 4 native quarters hb_idx__s_{NW,NE,SW,SE} = ot_hnx_idxn_quarter_with_keybuf;
  - each is keybuf + scorer (_h), containing 2 tails ge[0..1], fault, 2 meta, delay glue;
  - the hcols are hard cores.
- e15f211e9b (results/hbm_keybuf_binding_1027/source_plan_split_contract.json) already reports this, status UNBOUND:
  - SCORER_CARDINALITY: 4 native quarters x 64 hcols = 256 required vs 128 planned;
  - QUERY_PROXY_KEY_PORTS: 32.
- So: the 4 plan quarters per hub are the hcol pieces of one native quarter per hub. The SW/SE native quarters (their 128
  hcols and 4 tails) have no plan home. This is the RTL/plan owner's cardinality question, not a bind-rule detail.
- Per-child rules (proposal, added to slice_rules_proposal.json idx block):
  - hb_idx__s_X.scorer.ge[e].gc[c].leaf.* -> the b10x partition that holds piece r(e)c(c);
  - tails / fault / meta / delay -> b100 (scorer endpoint);
  - keybuf -> hub (beside the u_mu_keybuf_* already placed);
  - X in {SW, SE}: UNPLANNED until the cardinality is decided.

## (9) Duty-cycle risk sweep for the hub clock (COORD 08:4x, from DIE-QC-11; ESTIMATE)
- Basis: QC measured fall-rise on the forwarded clock (CHECKED there):
  - trial8 BUF-only, <=170 stages: 3.8 ps/stage median TT, ~3.1 FF;
  - trial9 `--clock-cell inv`: duty TT 0.473..0.524, FF 0.4375..0.512; residual <= 22 ps TT / 52 ps FF at ~170 stages.
- HBM stage count:
  - die feed 11 hops / 10.8 ns + region insertion 2.29 ns = ~13.1 ns;
  - at ~17 stages/ns (QC 170 / KV 165 at ~10 ns) that is **~220 stages to the deepest tap**;
  - hub comb in-hub depth: spine eccentricity 2.03 ns = ~35 stages.
- BUF form: fall-rise ~840 ps TT at the deepest tap, so the low phase vanishes and MPW FAILs (same as QC trial8). The
  in-hub spread across comb taps alone is 0..133 ps TT. **Not usable.**
- Inverter form (`die_trial --clock-cell inv`, plan INV at each odd-parity tap, priced in DME), residual scaled linearly
  x220/170:
  - deepest tap TT <= 29 ps (duty 0.465..0.535) **PASS**;
  - deepest tap FF <= 67 ps (duty ~0.42) **outside 45-55 %**;
  - in-hub spread across comb taps: FF <= 11 ps, TT <= 5 ps.
- MPW (lib ~42 ps), both edges, inverter form: worst phase ~350 ps FF, so PASS with ~300 ps margin.
- Risk 1: the deepest HBM taps (T059/T060 top row, far regions) may miss 45-55 % at FF. The fix is a shorter feed (the
  accepted comb and spine-tap feed cut the hub chain 5 -> 3 hops); re-measure with the QC fall/rise readout on the first
  HBM clock-only GRT.
- Risk 2: start syncs on the spine tap use the rising edge, so they are not affected. Any EDGE_FALL start edge or half-cycle
  path must budget the fall-edge error, +-67 ps FF.
- Plan: the hub clock is planned as an inverter tree (`--clock-cell inv`).
