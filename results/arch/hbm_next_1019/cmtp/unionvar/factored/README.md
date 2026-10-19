# UNIONVAR factored ordered-cardinality: capacity, selector bench, composed reprice (LH-P3UNITS/UNIONVAR, 10-19)

This continues the COORD 07:26 decision and the brief `lanes/HNEXT-FACTORED-NEXT.md`, built on the Codex unionvar
programme (507275709 / 329a54e44). It is a component plus a price. It is **not** a native-die adoption.

## 1. Mechanism (RTL `rtl/hbm_next/control/ot_hnx_union_prefix.sv`)

The dispatcher sits beside the IDX.UNION engine and passively taps its registered VM packet-write bus. IDX.UNION writes its row-table slots in ascending union order at data-independent edges, and word 0 of each slot is that expert's cardinality c_u.

**Prefix stage** (during the IDX write phase, with no extra VM traffic). Each expert passes through three registered stages:
1. E0: pin capture of the tap fields.
2. E1: a registered one-hot select of D1[c] and D2[c] (16 entries of 24 bits, flops).
3. E2: two exclusive prefix accumulators, then one masked write per expert of `{c, P2[i], P1[i]}` (69 bits) into an existing `ot_sram_1r1w_1024x256_m2_r2c2` macro (metadata over 2 kb is stored in SRAM).

The D-sector write closes the table.

**Dispatch stage** starts at the real IDX `union_v`. Let S be the edge that samples it. The launches are:

| Launch | Edge |
|---|---|
| loop 1, slot i | S + B1 + P1[i] |
| loop 2, slot i | S + B1 + T1 + G + P2[i] |
| tail (fixed suffix) | S + B1 + T1 + G + T2 |

Each launch carries `kref = KB[loop] + c - 1`, which selects a preinstalled per-cardinality kernel.

- **Port schedule:** the macro is written only in the tap phase and read only in the dispatch phase. Each event goes READ → CAP (capture rung) → FORM → WAIT, so launches are at least 4 edges apart, and B1 is at least 4.
- **Safety:** the dispatcher never waits. A late event, an out-of-order slot, a U that does not match IDX, a missing prefix, a new `go` while busy, or an illegal configuration each raises FAULT.
- **What it preserves:** ascending union order, the rho/kappa tables, and the per-position ascending-id combine, all unchanged. There is no reorder, no runtime code generation, no ready/credit, and no host involvement.

## 2. Selector bench (Verilator 5.050, fleet ot-epyc7)

The bench is `tb_hnx_union_factored.sv`, a fork of `tb_hnx_union_boundary`. It runs the actual IDX.UNION engine on the actual SW VM slice. Script: `tools/hbm_next/union_factored_bench.sh`. Golden: `tools/hbm_next/union_factored_vectors.py`, which uses the compiler IDX timeline plus `isa_rows.idx_union` and is written from the RTL spec, not read back from the RTL.

**Records** (23 in all):
- production shapes N1-N6, hot and disjoint (U up to 36);
- 8 random records (N ≤ 16, k ≤ 8);
- the two U24 counterexamples with equal U and different cardinality (balanced max c2; skew c6);
- 3 IDX fault records, which must produce no launch.

**Results:**

| Run | Expected | Result |
|---|---|---|
| PMUT0 | PASS | **PASS**: 20 unions, 748 launches, each on its exact golden edge with the golden (loop, slot, c, kref). IDX: 860 sectors checked, 0 errors. Prefix was ready **9 edges before** the real union done in every record (min 9 / max 9), including U36 and the skew case. Log: `run0.log`. |
| PMUT1 | FAIL | Uses the neighbouring-cardinality kernel. Failed with `UNION_FACTORED_WRONG_VARIANT ... c 1 kref 100 expected ... c 2 kref 101` (`run1.log`). |
| PMUT2 | FAIL | Inclusive prefix, so starts are wrong. Failed as `UNION_FACTORED_MISSING launch 0 expected edge 54` because the launch came late (`run2.log`). |
| PMUT3 | FAIL | U-only N-row kernel for every expert. Failed with `UNION_FACTORED_WRONG_VARIANT ... c 2 ... expected c 1` (`run3.log`). |

Source SHAs are in `sources.sha256`. The vectors, configuration and expected launches are `factored.json`, `cfg.txt` and `launch.txt`.

## 3. Program-store capacity (`tools/hbm_next/union_factored_capacity.py` → `capacity.json`)

The inventory is decoded from the committed P=3 whole images (MTP N6 and MU N4):
- 40 union layers per mode.
- Each layer has 2 expert loops: loop 1 has 2 SM.MATVEC records (w1/w3) and loop 2 has 1 (w2).
- Only 2 distinct body shapes appear per mode, so every layer shares the D1/D2 tables.

| Store | Holds | Size | Verdict |
|---|---|---|---|
| Dispatcher metadata | both start-offset arrays + c, U ≤ 128 words (36 used) | 1 macro (0.0123 mm²) | fits; overwritten per layer; port phases disjoint |
| D1/D2/B1/G/KB tables | per-c kernel spans | 868 flop bits (< 2 kb) | fits; cfg idle-only |
| Per-c kernel descriptors | 40 layers × c = 1..N × 3 records, MTP + MU resident | 1,689,600 b = 7 macros (92.1 % used) per copy | fits; **4 quadrant replicas** (kref broadcast instead of 1,408-bit descriptor wires) |
| Suffix | one U-independent suffix per layer: 199,424 B (vs the 10,158,080-B U-only bank) | in the baseline image store | no new capacity |
| VM programme calendars (4 × 1024 × 256), programme targets (PCW 10) | — | — | **not used and not claimed**: no HGI-1R → unit-calendar lowering exists, so the per-c word count cannot be derived |
| Legacy HGI-1 64 KiB credit CP | — | — | excluded (credit/ready) |

- **Boot installation:** 6,600 edges (5.5 µs at 256 b per cfg edge), paid once per kernel-store copy. If the four replicas share the write bus, it is 4× that, still once at boot.
- **Per-layer and per-token load:** 0, because everything is resident from boot.

## 4. Composed reprice on f4c_t9p3 (`tools/hbm_next/union_factored_reprice.py` → `reprice.json`)

The base is `key_profile_tight.json`: factored work at MTP 3,380.3 (step 1,476,415 cycles), 4 users at 4,158.4. The terms below are added on every main union layer (40 per step) and are charged as **not overlapped**. Draft and seed are U15 no-sharing, so c = 1 and they need no dispatcher.

| Term | Cycles per layer | Source |
|---|---:|---|
| prep | 0 | measured: ready 9 edges before union done (replaces the 108-cycle assumption) |
| dispatch | 5 | RTL timeline: sample edge + B1 = 4 |
| wire | 23 | dispatcher beside idx_sel → farthest quadrant (calendar_NE, 9,060 µm) at 405 µm, full-cycle hops |
| landed crossing | 4 | 2 + E with E = 2 (LANDING-CONTRACT L4) |
| kernel-store read | 2 | quadrant macro READ + capture |
| port / load | 0 | disjoint port phases; all kernels resident |

| Case | MTP tok/s | vs 3,364 | per user (4u) | vs 1,000 |
|---|---:|---:|---:|---:|
| old 108-cycle assumption (reproduced) | 3,370.44 | +0.19 % | 1,035.72 | +3.57 % |
| **this composed price (34 cycles/layer, full-cycle hops)** | **3,377.19** | **+0.39 %** | **1,038.38** | **+3.84 %** |
| half-cycle forwarded hops | 3,378.19 | +0.42 % | 1,038.77 | +3.88 % |

- **Area:** 4 × 7 kernel macros + 1 metadata macro = 0.357 mm² of macro. That is about 0.66 mm² as a slot at 55 % fill plus logic (an estimate, not gated). The die goes from 767.41 to about 768.07 mm², within the 858 mm² reticle.

**Verdict.** The factored scheme meets the MTP floor with **+0.39 % margin**: about 5,790 cycles per step (≈ 145 per union layer) of slack over the floor. That is thin. Any later unpriced cost above that takes MTP below 3,364.

**Next lever** if it falls below the floor:
- overlap the 34-cycle dispatch path with IDX.UNION's own 12-edge ACK tail and with the shared-expert work, which is union-independent and statically schedulable in parallel; or
- place a dispatcher replica per quadrant, fed by the forwarded tap stream, which removes the 23 + 4 wire/landing cycles from the critical path because the c_u stream arrives about 100 edges before done.

## 5. Still owed (not hidden)

- **TT/FF physical gate** of the dispatcher plus the quadrant kernel-store tile. There is no kit or gate yet. Safe-design checklist:
  1. Pins: the tap fields are pin-registered (E0). Reset landing is added in the kit wrapper.
  2. Reach: the tile is local beside idx_sel. The broadcast to the quadrants uses landed links.
  3. Fanout: the widest fanout is the c one-hot (16 loads) and the dst decode, both ≤ 32.
  4. Depth: the 32-bit adds and the 16:1 one-hot OR are each one stage. The macro output feeds only the capture rung.
  5. Storage: metadata and kernels are in SRAM macros. Only the 868-bit tables are flops (< 2 kb).
  6. to 7. Floorplan and clock: due at the kit stage.
  8. Schedule: every added cycle is priced above.
- **Lowering:** native HGI-1R → unit-programme lowering of the per-c kernels. The SM-side fetch is modelled as the 2-edge kernel-store read.
- **Exact model proof:** the pooled S2/histogram expectation is still the work price; there is no exact bank-by-bank proof. Rejected verify lanes use the decorrelated estimator.
