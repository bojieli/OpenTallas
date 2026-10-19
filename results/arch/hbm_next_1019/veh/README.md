# HBM-NEXT-VEH: layer vehicle and token composition for the P = 4 die (2026-10-19)

This is next-release work, not a release gate. **No layer of the P = 4 die has been measured in RTL yet**, so every tok/s figure below is a priced composition. Measured unit terms are applied where they exist (`token_composition.json` ledger).

## Step 2 (10-19 ~02:10): measured unit terms IN the schedule (`token_composition.json` headline)

The headline point is now **L = 5, HC row II 250 (measured on the hnx RTL by UNITS), VM grown, DIE f4c_t5 relay stages and the SM4 lane latency, all inside the static S2 schedule** (compose_grid `phys` axis). The self-check still passes 10/10: the grid reproduces D1 and Phase-1 exactly.

| point (L5, HC II 250, VM grown) | AR | MTP | 4 users agg / per user |
|---|---:|---:|---:|
| d4g-class stages, no SM4 latency (earlier priced point) | 1,949.7 | 3,459.9 | 4,481.6 / 1,120.4 |
| **f4c_t5: all relay classes moved + SM4 latency (HEADLINE)** | **1,989.9** | **3,383.7** | **4,373.7 / 1,093.4** |
| f4c_t5_smhbm: only SM_HBM moved + SM4 latency (no credit for shorter SM_X / VM_HUB) | 1,944.2 | 3,288.0 | 4,236.2 / 1,059.0 |
| targets | 1,905.4 | 3,363.5 | 4,365.3 / 1,000 |
| CMTP compiler-of-record re-time x the f4c_t5 factor (cross-reference) | 1,989.9 | 3,423.0 | 4,316.6 / 1,079.2 |

- The headline meets all four targets, but only narrowly: MTP +0.6 %, 4-user aggregate +0.2 %.
- Against d4g-class stages, f4c_t5 gives AR +2.1 % (SM_X 11.25 -> 6.46 and VM_HUB shorten the fetch leg) but MTP -2.2 % and 4-user -2.4 %.
- On the CMTP chain (with its rpl / union histogram / M1 rules), the **4-user aggregate is 4,316.6, -1.1 % under target**. Per user still holds at 1,079.
- If DIE's shorter SM_X / VM_HUB do not survive relays + GRT (`f4c_t5_smhbm`), MTP falls to 3,288 (-2.2 %) and 4-user to 4,236 (-3.0 %).
- The SM4 lane latency costs 89.8k cycles a MTP step and 80.5k a 4-user step. The SM records are mostly short (L3: 70 of 86 MTP SM records are 32.6-43.6-cycle expert slices), so a fixed +26 a record shows. **Lever:** publish the 4 lanes without the +8p skew (parallel result slots), or let the compiler hide the skew under the next record.
- HC II 250 and COLL 3K/2 are each **measured = priced**, so the HC and COLL terms do not change.

### Per-unit P = 4 layer benches driven by one layer's records (`layer_units/`, `sm4_layer/`)
- `p4_layer_units.py records`: DS L2 + L3 at the headline point gives MTP 375 records (SM 174, COLL 69, SU 68, HC 4, IDX 5, FUSED 10, DMA 16) and 4-user 351 records. `plan` maps them to unit benches (`layer_units/plan.json`).
  - **HC** (N 6 / N 4): both counts are measured points of tb_hnx_hc_eng4 (2,248 / 1,748). No re-run.
  - **COLL** (N <= 6 trains): measured (s1/s2). The law is exact in F. No re-run.
  - **ATT**: the production attention shape is the ATT4 bench shape (s03). No re-run.
  - **SM**: the layer's short records were NEW shapes.
- `run_sm4_layer.sh` (fleet ot-epyc5, Verilator 5.050) ran the SM4 leaf at the layer's record shapes:
  - shapes: NCHUNK 9 / 20 / 32 (expert 2304x53, 5120x24, 8192x53), spacing K 4 and 16, P 1 vs P 4;
  - **all PASS. Delta = exactly +24 cycles at every shape.** The ratio is 1.072 for the shortest record (9 chunks, K 4) and 1.006 for 32 chunks at K 16. This confirms the per-record charge used in the schedule;
  - MUT1 lane alias: **FAIL as required** (LANE MISMATCH; witness `sm4_layer/mut1_k4/`).
- The value-exact layer benches (MTP accept / reject, 4-user vs the CMTP goldens) still wait on the CMTP binary record images (emitter + VM allocator), on records_mtp / mu4, and on the UNITS FUSED / IDX row RTL (`p4_intake.json`).

## AR layer path = the d4g path (`ar_repro.json`: PASS)

Single-user AR on the P = 4 die issues P = 1 records. Its layer path is therefore the d4g one.

The vehicle is forked by copying into `tools/hbm_next/vehicle/` and `rtl/hbm_next/vehicle/`. The copy is a 3-way merge of `claude/lb2-hbm-cds-1018@63ef9558e` and `codex/hbm-vehicle-recovery-1018@1da79c281`, and all 7 tests pass on the fork.

On the released-checkpoint DS L0 fixtures, the fork emits **byte-identical** slice payloads (`val/hdr/vm_pre/msk.mem`) to the d4g receipt (`d4g_receipt/`). The record counts, events (6,308) and VM preload (1,377 words) match too.

The RTL cycles of that replay come from the d4g SW-slice binary (sw5 on ot-epyc4, sw5e on ot-epyc5; the top Verilator pass is still running). We reuse that build rather than launch a second one.

## Combined re-time (`grid/compose_grid.json`, `tools/hbm_next/vehicle/compose_grid.py`)

The model is the D1 timing model, unchanged. The grid crosses:
- COLL lanes: L ∈ {4, 5};
- HC further-row II ∈ {250, 600, 950, 4,385, per-position fallback};
- VM: grown or as built.

Each job runs in a fresh forked child that sets its own knobs.

The self-check passes 10/10: the grid exactly reproduces the D1 AR of 629,775.1 cycles (= 1,905.4 tok/s), D1 MTP/MU P4, and the Phase-1 runs for COLL L5, HC II 4385 and VM as built.

| DS tok/s, P = 4, VM grown | AR | MTP (γ 5, τ 4.159) | 4 users agg / per user |
|---|---:|---:|---|
| target (D1) | 1,905.4 | 3,363.5 | 4,365.3 / ≥ 1,000 |
| L5, II 250 (HCP x6 form) | 1,949.7 | 3,459.9 | 4,481.6 / 1,120.4 |
| **L5, II 600 (headline: UNITS target)** | **1,949.7** | **3,240.8** | **4,344.9 / 1,086.2** |
| L5, II 950 | 1,949.7 | 2,993.3 | 4,066.6 / 1,016.7 |
| L5, II 4,385 (static engine, measured) | 1,949.7 | 1,694.6 | 2,497.0 / 624.3 |
| L5, per-position HC fallback | 1,949.7 | 2,874.2 | 3,926.1 / 981.5 |
| L4, II 600 | 1,905.4 | 3,186.8 | 4,272.5 / 1,068.1 |

With the VM as built (per-layer column swaps), the figures are 2.4 % lower for MTP and 3.2 % lower for the aggregate.

## Findings

- **The HC row II has to be ≤ ~400, not 600, to hold the MTP target.** MTP step cycles rise 278.7 per cycle of II (L5), so the MTP target of 3,364 needs II ≤ 398. II 600 gives 3,241 (−3.7 %). The ≥ 1,000-per-user floor holds up to II ≈ 1,041 at L5 (950 at L4). The HCP W256 x6 form (II 250) meets both. → UNITS gate #1 should aim at ≤ 400.
- **The 5th COLL lane (L5)** gives AR +2.3 %, MTP +1.7 % and aggregate +1.7 % at II 600.
- **Physical adders not in D1:**
  - SM_HBM gets +2.37 relay stages in DIE f4c_t5, about 1.19 cycles per record;
  - the SM4 broadcast tree adds +1 cycle per record.

  If every record sits on the critical path, the bounds become AR ≥ 1,922.7, MTP ≥ 3,208.8 and aggregate ≥ 4,289.4. AR also pays these on the P = 4 die.
- **Inter-die traffic** is in the schedule: 192 dies, one single-tier plane, 377.6 ns crossing, 741.7 cycles fixed per collective. COLL is busy 44 % of AR, 39 % of MTP verify and 42 % of the 4-user step.
- **SU reducer ingress (HH-5) is not in D1.** As built, it costs the d4g −5.71 % AR and −17.6 % MTP. The next die assumes the widened ingress (W32: ≤ 0.2 %).

## What gets measured next

`p4_intake.json` lists what each layer bench is waiting for:
- the **MTP verify layer** and the **4-user layer** wait for the CMTP records and goldens, the collision checker, the SM4 and ATT4 RTL and benches, and the UNITS N-row HC, FUSED, COLL and IDX engines;
- the **AR layer** waits only for the d4g SW-slice binary.

Re-run:

```
PYTHONPATH=tools python3 tools/hbm_next/vehicle/compose_grid.py --out DIR      (fleet, ~25 min, 26 jobs)
python3 tools/hbm_next/vehicle/token_compose.py --grid DIR/compose_grid.json --ar-repro veh/ar_repro.json --out veh
```
