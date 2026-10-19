# HBM-NEXT-VEH: layer vehicle and token composition for the P = 4 die (2026-10-19)

This is next-release work, not a release gate. **No layer of the P = 4 die has been measured in RTL yet**, so every tok/s figure below is a priced composition. Measured unit terms are applied where they exist (`token_composition.json` ledger).

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
