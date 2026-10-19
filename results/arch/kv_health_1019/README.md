# KV health plane as die source — KV-HEALTH 10-19

Branch `claude/kv-health-1019`. Base: GEN8 v4 source `cda9d9f9d` merged with `claude/kv-retire-1019` `efb7381b1`
(357-source contract, sized reset counters, warm-reset guard).

Owner decision (10-19 12:41): **per-layer health retirement** is accepted at +7,680 edges/token (2.985 %). STATUS
moves after the complete closed fault path from every source. Continuous sticky health is never masked, and it blocks
subsequent admission.

## What is now die source

1. **Health-plane installer** `tools/qwen_kv_die/kv_health_plane.py install --run RUN`. This is a prep step:
   `kvsys_prep.sh` runs it under `OT_KV_HEALTH=1`, and `kvs14r.sh` defaults it ON for the MU release.
   - It runs after the forwarded lanes and before orientation, clocks and the strict bind.
   - It rewrites `case_kv/{die.v, place.tcl, elements.lef, die.v.pads.json}` (originals are kept as `*.prehealth`).
   - It adds the libs, views and expand leaves for its three masters.
   - Sources are found by generic rules on the laned netlist:
     - every landing `qkd_landsh*_W.fault`;
     - `kc_*.kf`, once the die KC master exposes `kf`;
     - the DCAL fault (`flt`/`fault`), unless it is already consumed;
     - the old `kvs_attn.ufh` net, as one leaf.
   - Any other unread fault-like output is reported as UNADMITTED. Nothing is silently dropped.
   - Topology is codex `kv_fault_topology.propose`: per clock root, a fold of neighbour pairs with every hop ≤ 405 µm.
     Cross-root transport uses spare payload bits of the existing stack→core forwarded lanes, so the bit rides every
     station and the landed ring and no new crossing is added. The final sticky sits beside kvs_attn.
   - **Structural change vs the codex model:** joins are `qkd_hp_or2` (new, no reset) and pipes are `qkd_rlys_1`
     (closed, no reset). Only the sticky cells are `qkd_astk_fault_join` with a reset. The plane therefore adds **one
     reset load** (the sink), where a resettable 1,342-cell plane would have added 1,342. After a reset the plane
     flushes by data, while the sink region is held for HOLD 273.
   - The final sticky drives `kvs_attn.ufh`, so faults enter the existing attention fault root:
     AFR → service_fault → RESULT/STATUS → link → compute STATUS.
   - The existing RTL keeps service_fault sticky and refuses later operations. Evidence: the kv-retire whole-path bench
     "late: next op refused".
2. **HOLD 273 reset root** `qkd_rst_region_pr_h273`: a wrapper of the sized `_pr` core with a 9-bit hold.
   - `kvsys_prep` binds it when `OT_KV_RST_HOLD=273` (the kvs14r default) and the closed view audits PASS.
   - Otherwise HOLD 128 stays bound and `RST_HOLD_DIAGNOSTIC` marks the run NOT a die result.
   - `kv_die.py RST_HOLD` selects the module.
3. **Two new tiles**, both gated WARN (util only); I reviewed the PNGs and both were submitted:
   - `qkd_hp_or2-o1-a11f46db5`
   - `qkd_rst_region_pr_h273-h1-a11f46db5`

## Actual plane on the GEN8 v4 laned netlist

Input: a copy of `kvs14r-cda9d9f9d-gen8v4mub/case_kv`; the historical run directory was not modified.

| Item | Value |
|---|---|
| Sources | 352: 351 landings + existing ufh (core c 106, EN 62, ES 61, WN 62, WS 61) |
| Cells | 1,342: 351 `qkd_hp_or2` joins, 990 `qkd_rlys_1` pipes, 1 sticky sink |
| Transports | 85 lane payload bits; 2,480 station bits rewired; 4,872 pad bits freed |
| Audit (on the emitted netlist) | sticky sink drives ufh; cone = all 1,342 cells; every source covered; 0 inputs > 405 µm; 1 reset load added |
| DMAX | **183** edges (worst: WS hroot landings) |

**Price** (`status_price.json`, from the link compiler `d2d_link_calendar --status-delay`, 36 per-layer tails):
- Every STATUS ≤ 2002 (delay ≤ 217) keeps the padded token period at **257,280**, i.e. the owner-accepted 2.985 %.
- 2003 jumps to 258,048 (3.274 %).
- KV-HEALTH reserves a **fixed STATUS 1998** (delay 213, compiled_end 1999). That leaves a DMAX budget of 198: the
  v4 plane uses 183, and 15 edges remain for the KC / DCAL / PC sources still to be exported. Zero extra token edges.

## Bench

Whole-plane logical bench, generated from the emitted netlist: `tools/qwen_kv_die/kv_health_bench.py`. It uses the real
masters and RTL; lane transports are abstract fixed delays. Run with Verilator 5.050 on ot-epyc6 (`logs/`).

- `none`: **KV_HEALTH_PLANE_PASS**, 352 sources, 112,596 checks, 217,282 cycles. Every check passed:
  - every source alone raises health at exactly its leaf latency and not one edge earlier, which is the STATUS
    boundary witness;
  - health stays sticky, and the pulse source (ufh) is retained;
  - random power-up state gives no false positive;
  - after a region re-assert with the sink held 273 edges, there is no stale re-latch;
  - all sources together and pairs pass;
  - a late fault is still observed.
- Mutants, each FAIL with a committed log:
  - `drop_join_b`: HEALTH_MISSING_AT_LATENCY.
  - `sink_nonsticky`: HEALTH_NOT_STICKY on the ufh pulse.
  - `hold128`: HEALTH_STALE_RELATCH. This is the causal witness that HOLD 273 is required.
  - `ufh_unhooked`: HEALTH_MISSING_AT_LATENCY.

## Open (owners)

- **KC `kf`** (4 sources): the die KC master has no `kf` pin. The closed `qkd_ctrl_kc` view exposes `kf`; the
  kv_die binding group and view bind are owed. KC `fi` is not sticky, and the installer adds the sticky latch.
  Owner: KV-PC2 / KV-GEN9.
- **DCAL**: fold `claude/kv-dcal-1019` with `OT_KV_DCAL_BC4=1` and `OT_KV_DCAL_FLT=1`. dcal flt then goes to afr d[8];
  the installer reports it as covered and the contract prices it with `--dcal-relay`. Owner: KV-DCAL2 / KV-GEN9.
- **PC chain fault**: `0cef4d573` FAULT_EXPORT (field 301 of o_grp / o_grp_h) is default-off. The group suffix reaches
  D2D.kv_flush_local, not health. To make it a plane source, the PC / GRP tiles must export a sticky bit that the
  installer can see (e.g. a `pcf` output on qkd_kvs_grp*); the installer picks up any unread `pcf` / `*_fault` output.
  Owner: KV-PC2 / KV-GRP2.
- **STATUS 1998 in the image** needs all of the following, at the same padded price: `compile_all(status_delay=213)`,
  attention tile `RETIRE_STATIC=1`, `qkd_attn_cal_gen_b STATUS_DELAY=213`, and the compute-die link calendar.
  Owners: KV-ATTN2 (tile), KV-TOK2 (image), KV-GEN9.
- Physical: GEN9 runs the plane in the real chain, which provides strict bind, GRT and STA on the 1,342 cells and the
  loaded reset window.
