# MESO-COUNT-1 (2026-10-27): count-aligned landed crossings

OWNER-approved study. Question: can a landed (mesochronous) crossing deliver at a whole-cycle latency that is the
**same on every chip** across the derated phase spread (HEAD ~950 ps > T = 833 ps; KV: 189 root-split crossings fail
even balanced)? Also: is LAND-KV-1's alternative (DEPTH6 on root-split crossings) cycle-fixed?

## Result

* **Count-aligned ring (`rtl/common/ot_dp_clk_landing_ca.sv`, new; `ot_dp_clk_landing` / `ot_meso_ring` unchanged)**:
  latency = K + 1 receiver counts **by construction, independent of phase**. It is correct for any lag
  L in [(GUARD_LO+0.5)T, (GUARD_HI-0.5)T], which is a 3T window at DEPTH 4 and a 7T window at DEPTH 8.
  Outside that window it **fails closed** (`fault`, `ready` low), never with silent wrong data.
* **DEPTH6 phase placement (LAND-KV-1 alt.)**: **not cycle-fixed**. Phase placement always picks the read slot inside
  one period, whatever DEPTH is. Latency therefore flips by one cycle wherever the derated phase interval crosses
  ±T/2. That happens on 17 HEAD and 553 KV crossings, which would see two latencies across chips.
  DEPTH6 is also illegal in the ring (power of two). Fixing the slot offset at design time instead of measuring it is
  exactly count alignment.
* **Recommendation: adopt count-aligned rings for landed crossings**, with start origins from a start wavefront over a
  spanning tree of the same crossings. All 427 HEAD and all 3915 KV crossings plan with 0 FAIL. Most crossings drop to
  latency 2 (from 3). The old ring's failures (HEAD 17, KV 598 failing the ±T/2 margin) get a fixed
  latency at DEPTH 4/8. Integration is a separate lane: the die schedule must take the per-crossing latency from the
  plan, as a compile-time constant.

## Timing model (tools/die_plan/count_align_plan.py)

* Every region v has a count origin a_v, its start edge. The sender writes word n into slot n mod DEPTH, with the
  write count reset by the forwarded sender start `t_rst_n`. The reader reads slot (receiver count − K).
  Lag of word n: **L = (K + a_dst − a_src)·T + d**, where d = arr_dst − arr_src derated (shared die model rows from
  `landed_phase_ocv.py`, union of TT_droop corelat250 and FF_droop corelat202.5).
* Conditions:
  * **K**: the smallest integer with L_lo ≥ (GUARD_LO+0.5)T + ap.
  * **DEPTH**: 4 if L_hi ≤ 3.5T − ap, else 8; otherwise FAIL.
  * **Guards**: the opposite-edge lap guards stay, with GUARD_LO = 0 and GUARD_HI = DEPTH.
  * **Aperture**: ap = T/8 = 104 ps, the same resolution as the formal model.
  * **Wander**: ±5 % of the unshared path, after start.
* **Lap tag**: a 1-bit lap aliases every 2·DEPTH counts, so a word shifted by 2·DEPTH·T would pass the guards with
  wrong data. The bench found this, at L ≈ −4.5T aliasing 3.5T.
  The fix is an extended tag: LAPX = 3 extra count bits are stored per slot and compared at read.
  The NO_TAG mutant brings the silent-wrong data back, and the bench catches it.
* **Start-up / reset**: the root region releases start. Each child origin is a 3-FF sync of the parent's
  forwarded start, plus PAD (`ot_dp_landing_origin`, rise- or fall-edge first stage).
  * The sync adds j_e whole cycles. j_e is **chip-invariant** if the edge's derated interval ±ap avoids the sampling
    boundary of the chosen edge: d ≡ 0 for rise, d ≡ T/2 mod T for fall.
  * The plan prefers clean edges in a Kruskal spanning tree:
    * HEAD: 311 of 325 tree edges clean.
    * KV: 152 of 159 tree edges clean.
  * Each tree crossing's L is the sync window plus wander. The bench checks this on the tree: 833 phases, 0 bad, on
    both sample edges.
* **Loops (non-tree crossings)**: a_v − a_u = Σ±(PAD + j_e) along the tree path. This equals the nominal value plus
  [−X, +Y] cycles, where X+Y = Σ(n_e−1) over ambiguous edges. That adds whole periods to the window, conservatively.
  * Maximum path ambiguity: HEAD 2, KV 3.
  * This ambiguity is what pushes some crossings to latency 4–5 and DEPTH 8.
  * A tree with fewer ambiguous edges, or chip-measured origins, would remove it (next step).

## LAND-HEAD-3 clock (spine_fishbone, ec4f9b4ac2) and the COORD 20:26 ruling

COORD's NUMBER-CHECK of LAND-HEAD-3 found that whole-cycle count alignment fails: worst −91.3 ps, 60 crossings
below 0. It ruled that MESO-COUNT-1 must evaluate count alignment with half-cycle placement. That check assumes a
**one-period** window, i.e. a fixed design-time slot offset on the old ring. The ring here has no placement step:

* The read slot is taken from the receiver count, and the data stays in the slot for DEPTH−1 periods.
* So the residual r = d − K·T only has to lie inside the (DEPTH−1)T window, which is 3T at DEPTH 4.
* One K per crossing holds at both TT and FF, because the plan works on the union of the two corners.

Results on the same rows (`intel2:/srv/opentallas-scratch2/claude/land-head-3/sfbR/landed_ocv.json`, joint TT+FF):

* **All 427 crossings fit at DEPTH 4, 0 FAIL**, with fixed latency 2 (349 crossings) or 3 (78 crossings).
* All 325 tree edges are clean, so path ambiguity is 0.
* The bench runs 1281 lag cases (low/mid/high per crossing) with 1281 PASS and 0 FAIL.
* The ruling's worst crossing, coll_EN1_u__0 (d_TT −437 ps), gets L in [1065, 1432] ps and latency 3 at DEPTH 4.
  On the old ring the same crossing has two latencies across chips.
* Worst margin to the guard edge is 104.1 ps on the low side (the aperture, more than 4× the 26.5 ps
  DFFHQNx1 setup+hold) and 902 ps on the high side.

Half-cycle placement is therefore not needed for this ring. It would only matter for a one-period ring with a fixed
offset. UNCHECKED: the slot→mux→RDREG path needs set_max_delay/min_delay constraints in die STA, with the window
edges as the bound. That is not done here.

## Proof (rtl/test/meso/formal_ca, SymbiYosys + abc in openroad/orfs:asap7lock; no SMT solver)

* The harness `fv_ca.sv` uses two clocks at T = 8 steps. The phase is static and arbitrary, with lag L from 5 to 27
  steps.
* Assertions:
  * A_SAFE: if `ready && !fault`, then q = sender word (rc−1−K).
  * A_NOFLT: no fault inside the window.
  * A_LIVE: ready by t = 600.
* Results:
  * mut_k, mut_freerun and mut_noguard are all **CAUGHT**. abc bmc3 found a counterexample for each, at frames 129,
    129 and 137.
  * The reach task fails as intended (non-vacuity): `ready` is reachable in-window.
  * `prove` (abc pdr, 2 h timeout) was **still running at hand-off**; see the lane line for status.
  * An earlier harness bug made the mutant results vacuous: 3-bit reset counters saturated, so `ready` never rose.
    Fixed with sticky 4-bit compares; every result above is from after the fix and uses the LAPX RTL.

## Verilator benches (rtl/test/meso/ca/run_ca_bench.sh)

| check | result |
|---|---|
| lag sweep, K ∈ {−2,1,2,5} × DEPTH 4, L = ±9T at 1 ps | clean window [418, 2916] ps = [0.502, 3.501]T, contiguous, silent-wrong 0 of 14995 (each K) |
| same, DEPTH 8, L = ±17T | clean [418, 6248] ps = [0.502, 7.501]T, contiguous, silent-wrong 0 of 28323 (each K) |
| mutant NO_TAG / K | CAUGHT (2915 / 2499 silent-wrong) |
| start tree, rise / fall sync, 833 phases | 0 bad; L ∈ [1.000, 1.999]T / [1.501, 2.499]T |
| HEAD 427 crossings (lo/mid/hi lag per crossing, joint TT+FF plan) | D4 1209 PASS 0 FAIL, D8 72 PASS 0 FAIL |
| KV 3915 crossings (claude/land-kv-1027@304c20fb8d lpo.json) | D4 10200 PASS 0 FAIL, D8 1545 PASS 0 FAIL |

## Cost

**Area** (yosys + abc, ASAP7 RVT TT, 64-bit, LAPX=3):

| variant | area | cells |
|---|---|---|
| old ring | 189.7 µm² | 1599 |
| CA D4 | 188.2 µm² | 1611 |
| CA D8 | 342.0 µm² | 2895 |

**Cycles** (joint plan):

| | latency histogram (crossings) | Σ latency vs old 3 everywhere | D4 / D8 crossings |
|---|---|---|---|
| HEAD | {2: 386, 3: 19, 4: 21, 5: 1} | −363 crossing-cycles | 403 / 24 |
| KV | {1: 1, 2: 2576, 3: 838, 4: 363, 5: 137} | −1941 of 11745 | 3400 / 515 |

* **TOK, KV** (UNCHECKED estimate): `tok/lane_delta_land_q5c39.json` pricing, with the d2d/tx chain maximum going from
  33 to 30 cycles. Added cycles per token go from 2499 to 2265, which gives **4767.6 vs 4763.2 tok/s** (loss vs
  no-landing 0.900 % vs 0.992 %).
* **TOK, HEAD**: not priced. Only the crossing-cycle change is given.

## Files

* `head_ocv_ca.json` (LAND-HEAD-2 rows), `head3_ocv_ca.json` (LAND-HEAD-3 rows) and `kv_lpo_ca.json`: the per-crossing plans.
* `*_cases.tsv`: the bench inputs.
* `bench.log` and `formal.log`: the run logs.

## MESO-COUNT-2 (2026-10-27 21:xx): plan fixes, emitted RTL parameters, start-up check

This section applies the COORD 20:48 ruling. Tool: `tools/die_plan/count_align_plan.py`, 9 tests PASS.

### Plan fixes

* **K comes from the derated lag on every crossing, including tree crossings.**
  * A clean tree crossing is planned like any other crossing: its path ambiguity is 0, so L = K_eff·T + [d−p_dn, d+p_up] ± wander.
  * MESO-COUNT-1 instead pinned L_lo to 0.5T+ap. That is where its "104.1 ps" came from.
  * An ambiguous tree crossing uses its sync window [off−sap, off+T+sap] − J_nom·T, with sap = 26.5 ps.
* **Start offset per tree edge:**
  * a_child − a_parent = **PAD + 2 + J(d)**, where J(d) = −floor((d−off)/T), off = 0 (rise) or T/2 (fall).
  * Counted from the parent's start *launch* edge (a_parent − 1), this is the ruling's "3 sync flops + PAD".
  * MESO-COUNT-1 used +1 per edge, which was wrong.
  * The RTL bench below checks this.
* **Emitted RTL parameters:**
  * Per crossing: `rtl = {ot_dp_clk_landing_ca, DEPTH, K, GUARD_LO 0, GUARD_HI DEPTH}`, with
    **K = K_eff − n0** and n0 = a_dst − a_src (nominal).
    The RTL uses K mod 2^(log2 DEPTH+1+LAPX), so values like 62/63 are equivalent to −2/−1.
  * Per region: `origin_cycles`, plus `start_from = {parent, port, edge, J_nominal, offset_from_parent, sync_dist_ps,
    rtl {ot_dp_landing_origin, PAD, EDGE_FALL}}`.
  * Per crossing, two latencies:
    * `lat_cycles` = K_eff+1, in the root count frame;
    * `rx_lat_counts` = K+1, in receiver counts, fixed by construction.
* **The start tree is now DIRECTED: the start travels src→dst only.**
  * MESO-COUNT-1's tree was undirected. It reversed the d of one-way crossings, which cannot carry the start backwards.
  * HEAD has 300 one-way region pairs out of 337.
  * The new tree has the fewest ambiguous edges: equal-ambiguity levels, clean edges first, best root over all regions.
  * KV: **7 ambiguous edges**, which equals the lower bound: 8 clean source-SCCs, so at least 7 are needed.
* **Monte-Carlo check of the emitted parameters (`--mc-chips`):**
  * Each of 3000 chips draws d per crossing in its derated interval (uniform, plus endpoints) and wander ±w.
  * Each tree edge's J comes from its own d; inside the sync aperture, either value is drawn.
  * Origins are summed down the tree, then L = (K + a_dst − a_src)T + d is checked against the guard window.
  * Tests also show the check catches mutants: K−1, and the PAD+3 start rule.

### Results

Joint TT_droop corelat250 + FF_droop corelat202.5, ap = T/8, wander ±5 % unshared on all crossings (default):

| die (rows) | D4 / D8 / FAIL | worst low / high margin (ps) | latency hist (K_eff+1) | tree clean / ambiguous / fall | MC 3000 chips |
|---|---|---|---|---|---|
| HEAD (LAND-HEAD-3 sfbR, md5 890b23fb) | 427 / 0 / 0 | 126.2 (sp_x5__0) / 885.1 | {2: 256, 3: 171} | 325 / 0 / 43 | 0 violations, worst 126.2 / 885.2 |
| HEAD, wander 0 | 427 / 0 / 0 | **173.6** (sp_b3__0) / 1401.6 | {2: 264, 3: 163} | same | 0 violations |
| KV (304c20fb8d lpo, md5 39657aaf) | 3392 / 523 / 0 | 105.1 / 162.9 | {2: 2676, 3: 763, 4: 382, 5: 94} | 152 / 7 / 138 | 0 violations, worst 105.1 / 162.9 |
| KV, wander 0 | 3686 / 229 / 0 | 104.7 / 104.7 | {1: 23, 2: 3248, 3: 311, 4: 259, 5: 74} | same | 0 violations |

* **HEAD matches the NUMBER-CHECK exactly**: 173.6 / 1401.6, 126.2 / 885.1 with wander, latency {2: 264, 3: 163}.
* **KV with wander**: D4/D8 3392/523, the same as the NUMBER-CHECK's "+5 % wander own".
* Every crossing is ≥ 100 ps on both sides.
* Minimum clean-edge sync distance (the derated interval to the sample boundary):
  * HEAD 142.5 ps; KV 105.4 ps.
  * This bounds the start-path skew δ: p_start relative to fclk at the first sync flop must satisfy |δ| ≤ 142.5−26.5 = 116 ps (HEAD)
    and ≤ 79 ps (KV). This is an STA constraint for MESO-INTEG-1.
* Start wavefront depth: HEAD 27 hops, KV 14 hops. Start-up only.

### Start-up check (`rtl/test/meso/origin/run_origin.sh`, Verilator, RTL `ot_dp_landing_origin`)

* Scope: every child phase at 1 ps (833), × parent launch edge 3/4, × PAD 0/2, × rise/fall, × start skew δ 0/40 ps.
* A first-stage sample within ±27 ps of the transition is run with **both** outcomes.
* Results:
  * **0 bad of 8 × 1666 phase cases.**
  * Every clean phase gives exactly a_c − a_p = PAD+2+J(d).
  * All 110 ambiguous phases per configuration take two values. Both stay inside the plan's sync window:
    [−27, 860] ps (rise) and [390, 1277] ps (fall). This is the ambiguous-edge handling.
* The ring benches also pass on the new cases (`bench_ca2.log`):
  * HEAD 1281 PASS, 0 FAIL;
  * KV 10176 + 1569 PASS, 0 FAIL;
  * sweeps unchanged, with clean window [0.502, 3.501]T / [0.502, 7.501]T and 0 silent-wrong;
  * NO_TAG and K mutants CAUGHT.

### Formal (MESO-COUNT-2, `rtl/test/meso/formal_ca/fv_ca2*`, yosys-abc in openroad/orfs:asap7lock; RTL unchanged)

* **Proven unbounded by k-induction** (abc `fold; strash; bmc3; scorr; dc2; ind`, seconds per config) for W = 1 (data independence, one
  watched word) and K = 2.
* The three properties, proven together:
  * **safe**: while ready && !fault, the delivered word is the captured word at latency K+1;
  * **no-fault**: no fault for lag L inside [5/8 T, (D − 5/8) T];
  * **fail-closed**: for L ≤ 3/8 T or L ≥ (D − 3/8) T, ready && !fault never holds.
  * 18 helper invariants are asserted and proven, not assumed.
* **Coverage**:
  * D4: 120/120 configs (phase 0..7/8 T × offset −3..11, L −1.9T..13T, which includes the 2·DEPTH lap alias), plus 30/30
    tag-range samples up to 63T.
  * D8: 184/184 configs (L up to 21T, including the 16T alias), plus 16/16 samples up to 127T.
* **BMC only** (all lags in one run):
  * liveness + safe + no-fault: D4 800/1100 frames PASS; D8 ≥ 939 / ≥ 768 frames, no failure (stopped);
  * fail-closed: D4 420 / D8 600 frames PASS;
  * ready at the maximum in-window lag is reachable (not vacuous).
* **Mutants caught**:

  | mutant | property that fails | frame (D4 / D8) |
  |---|---|---|
  | K | no-fault | 129 / 193 |
  | FREERUN | no-fault | 129 / 193 |
  | NO_GUARD | wrong word | 137 / 201 |
  | NO_TAG | wrong word | 180 / 308 (alias config 195 / 323 in the k-ind flow) |

* **Findings**:
  1. The wrapper default GUARD_HI = 4 is wrong for DEPTH 8 (no-fault fails). Bind GUARD_HI = DEPTH, as the plan's `rtl` fields do.
  2. At negative lag the reader never becomes ready and never raises fault. The guaranteed behaviour is fail-closed (never ready && !fault), not fault raised.
* MESO-COUNT-1's PDR on the 10-bit-time harness (mc1-prove) did not converge: 0 of 3 proven at about 40 min, UNPROVEN.
