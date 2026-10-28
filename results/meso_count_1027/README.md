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
