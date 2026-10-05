# Chip architecture review: fixes and worker handoff

This report covers the architecture review begun from `1b492a4` and the corrections on `codex/architecture-review-fixes`. Work was isolated in a sibling worktree while the main workspace’s RTL/compiler implementation continued. The resource and reference fixes below are implemented; the proposed chip is not fully implemented or performance-qualified.

Read [CHIP_RESOURCE_BUDGETS.md](CHIP_RESOURCE_BUDGETS.md) for generated numbers and [CHIP_ARCHITECTURE_DESIGN.md](CHIP_ARCHITECTURE_DESIGN.md) for the revised specification. `configs/architecture/chip_design_v2.json` is the input contract, `src/opentallas/chip_architecture.py` derives resources, and `tools/check_chip_architecture.py` checks retained JSON/Markdown. The historical roofline study is a separate artifact and was not rewritten into a chip performance claim.

## Disposition of the seven findings

| Finding | Correction now present | Evidence / remaining integration |
|---|---|---|
| Four ranges could silently omit a fifth object | Four same-object-unioned ranges plus a sticky global wildcard. Check the entire candidate footprint before atomic reservation; release after acknowledged writes. Six operand views and separate input/output scale planes are collected. | `runtime/abi3/dependence.py` is an executable reference, not an installed asynchronous backend. Randomized byte-set checks and real descriptor audits pass. RTL integration still needs the tests below. |
| Qwen x5 KV used average layer ownership | Exact stage cuts own 6, 8, 9, 8, 5 attention layers; reserve 320 MiB KV SRAM per die. The largest owner needs 304,349,184 B at 8,256 positions. | Exact checkpoint accounting includes norm gains and covers 16,381,470,720 B. Compiler object/bank placement must implement these cuts and prove all emitted bytes fit. |
| SRAM-KV source rate bypassed the SDN limit | Delivered service is min(source, SDN, staging); x5 source 26,112 B/cycle is capped at 4,608. Ordered stages need 262.144 µs cumulative KV service at context 8,192. | No overlap is credited. This is service time, not automatically extra TPOT. A finite-buffer schedule determines overlap with compute. |
| Scalar RE8 was treated as a vector tree | Seven adders reduce one column/cycle; 64 columns need 448 adds and 64 cycles. Two endpoints per eight-tile cluster fund lower/upper-tree capacity, with 4 KiB per endpoint. | Minimum BF16/FP8/MXFP4 pass intervals are 128/65/64 cycles at assumed N5 L=1. New RTL tree mapping, buffering and transport must be tested. |
| INDEX_SCORE required unsupported grouped BF16 | BF16 keys × BF16 query at g=1; AM-E7 disabled. | Current lane rejects any grouped BF16. Historical Flash sensitivity becomes 84 µs dots + 13 µs combine at the old 201-tile point; this is not a revised TPOT. |
| Mesh and link budgets did not match the ports | Qwen meshes grow to 12×12, 13×13 and 16×16 with router area charged. A 512-bit endpoint supplies 64 B/cycle, eight supply 512 aggregate. | A 48 KiB payload needs at least 768 cycles on one endpoint. An actual collective algorithm must account for rounds, fan-in, shared injection and credits. |
| Physical prose cited obsolete lane results | Generated snapshots retain record/source hashes, full verdict, cell/core area and macro count; stale routes cannot establish the current source’s closure. | Concurrent physical corrections are included: lane clean at 6 ns ASAP7; LQ8 at 16 ns has 292 slew violations; the retained 4.4 ns microsequencer has 49. See current JSON if the worker has since repaired them. |

Other corrections remove unsupported 100% port duty and throughput claims, charge MXFP4’s 256 scale bytes per 64×128 pass, reserve 1% spare rows plus 1% quarantine and a 16 MiB miscellaneous image budget per die, retain the HBM twin’s PHY cost, and require independent vendor-oracle qualification for numerical amendments. The main design’s old TPOT, MFU, prefill and ROM/HBM ratio tables have been withdrawn; Appendix A/B remain labeled historical. The worker’s numbered items 11–14 are preserved with the later full-verdict correction.

## Checked Qwen implementation proposals

| Profile | Tiles/die | Lanes/die | Raw ROM/die | KV SRAM/die | Mesh | Maximum twin endpoints / mesh positions | Area/die |
|---|---:|---:|---:|---:|---|---|---:|
| x4 tensor, HBM KV | 488 | 31,232 | 4,197,129,405 B | 0 | 12×12 | 113/144 | 814.845 mm² |
| x5 pipeline, SRAM KV | 649 | 41,536 | 3,372,847,021 B | 320 MiB | 13×13 | 150/169 | 814.777 mm² |
| x8 tensor, SRAM KV | 1,211 | 77,504 | 2,107,734,727 B | 160 MiB | 16×16 | 220/256 | 814.738 mm² |

Tensor-parallel profiles retain 616,448 B of normalization gains on every die and shard only matrix storage. That replication fits the existing aligned allocations, so the tile counts stay the same. These counts maximize tiles within the stated assumed 815 mm² budget; they leave almost no unassigned area. Any block-area, density or routing change must rerun the derivation. They are not physically closed floorplans. The model checks aggregate per-unit alignment/reserves; per-tensor and per-bank padding, ROM bit-column repair, metadata and constants must fit the reserved payload in the actual allocator. KV bank geometry is still an assumed implementation. Every row keeps `qualified_tpot_us: null` and `production_ready: false`.

The HBM twin preserves tensor/reduction, mesh and baseline KV allocation. At SRAM-KV points its additional 50 mm² HBM PHY comes from the replaced ROM slot; it does not reduce the baseline KV SRAM or silently change tensor count.

## Immediate tasks for the concurrent worker

### 1. Integrate dependency safety with the asynchronous front end

The main workspace already contained work on `ot_a3_dependence_table`, IRS, resolver bank, symbols, shared divider, scoreboard, microsequencer and `ot_a3_device_top`. This review did not overwrite those edits or claim their tests passed.

Use the Python reference to check the RTL protocol. Every operation needs a complete footprint before younger operations can issue. Multi-cycle insertion is allowed only behind a reservation lock that prevents younger admission. Include input/output scale planes, LINK destination/source ranges, STATE resources, BOOLEAN_OBJECT/EOS predicates, and TOKEN_APPEND’s read-back/host writes. The supplied collector deliberately refuses non-OPERATOR descriptors; it must never stand in for those other collectors.

Acceptance cases:

- Four reads plus a fifth output; a later read of that output stalls until completion.
- An incoming fifth/sixth range conflicts with an older write, even when the first four do not.
- RAW/WAR/WAW across loop trips despite already-signaled level events; multiple ranges of one object union correctly.
- Overflow remains sticky through further insertions; only completion clears it. Empty ranges and read/read overlaps do not spuriously conflict except where wildcard policy intentionally serializes.
- No younger issue during partial insertion; reservation failure changes no table entry. Define simultaneous release/reinsert of one slot.
- Delayed bank acknowledgements keep the entry live after arithmetic completion; faults drain consistently before slot reuse.
- Receiver rendezvous with skew/backpressure never commits a remote write over a still-live local read.

`results/architecture/deployment_dependencies.json` audits the actual Flash wafer and HBM token descriptors: 75 and 74 wildcard operators respectively, with **16 in each touching more than four mutable objects**. It contains program/descriptor/reference hashes. It is not evidence for LINK/STATE coverage or integrated RTL safety. Regenerate it when bundles change.

### 2. Implement exact placement and unified SCHEDULE emission

Use x5 cuts after `layer.5.attention`, `layer.13.gate_up`, `layer.22.attention`, `layer.30.gate_up`, `head`. Keep each attention layer’s KV on its owner; on tensor profiles replicate the input/post-attention/head normalization and Q/K head-normalization gains on every die. Generate both weight-store variants from the same operator partition and SCHEDULE rule. The concurrent worker’s `compiler/backends/schedule_rule.py` work is complementary; these fixes do not duplicate it.

Acceptance must enumerate every tensor, scale, gain, constant and runtime arena per node/bank; prove no overlaps and all capacities including repair/padding; invert the ROM image exactly; check the 8,256-position maximum KV owner. Emit explicit collectives and stage SENDs. Re-run C2 against newly emitted programs, not only machine-file parity.

For Flash/Pro, derive exact node/field placement before choosing new tile counts. Uneven stage bands and replicated objects make aggregate bytes divided by device count insufficient. Re-cost scalar reduction, BF16 index scoring, all mesh endpoints and PHY placement. No corrected full-chip DeepSeek throughput is available yet.

### 3. Finish RE8/T64 and the transport schedule

The worker has begun `ot_a3_tree_endpoint_fp32.sv` and its harness. Keep RE8 scalar width explicit. Test 64-column vectors, tails, 32/96-leaf pairwise associations, backpressure and multiple tree levels. Two endpoints per cluster are resource capacity, not two columns/cycle through each node. Report first and last result separately; prohibit unbounded accumulation of vectors behind a faster producer.

Charge weight scales on the existing port. Enforce 4,608 B/cycle aggregate SDN arbitration and real staging write limits. Test serial x5 stages versus concurrent tensor shards and log per-tile buffer high-water marks. Leave frontier/prefetch overlap disabled until final-byte visibility and bounded-buffer scheduling prove it.

Widened link/mesh endpoints need source-current RTL and physical evidence. Bind one collective algorithm consistently across reference, cycle model, RTL and counters. Do not combine ring message counts with a two-hop latency shortcut. Charge headers, receiver commit bandwidth, credits and retries as well as payload serialization.

### 4. Preserve numeric qualification and close the physical/boundary gates

Keep BF16/BF16 g=1 INDEX_SCORE. Any future grouped BF16 or packed-key mode needs explicit lane support, scale/subnormal/refusal cases, and independent pinned vendor-oracle token qualification. A simulator changed alongside RTL is only a block comparison reference. Retain sequential qualification and the external oracle.

Repair the reported LQ8 and microsequencer electrical violations before restoring their closure claims. The physical driver now checks slew/capacitance/fanout; positive setup slack and DRC 0 do not override that verdict. Integrate a memory macro and hierarchical compute/control pilot before claiming G2. Record control-plane cycles and measure a two-tile dependent chain through last output/write acknowledgement; replace the historical 39/120-cycle guesses only with that evidence.

### 5. Refresh all identities and publish performance last

Source-lock changes invalidate affected block, deployment, numerical and physical evidence. Rebuild bundles, parity reports and execution identities together. Do not relax governed gate budgets. End-to-end G1 tokens, G2 integrated routing, G4 cycle calibration and a correctness-qualified timing trace are prerequisites to a new G3 TPOT or ROM/HBM speedup claim.

## Reproduction and verification

Run from the repository root:

```sh
make test-chip-architecture
make check-chip-architecture
make chip-architecture-report
python tools/audit_deployment_dependencies.py \
  build/abi3/deepseek-v4-flash-rom-tokens \
  build/abi3/deepseek-v4-flash-hbm-tokens \
  --output results/architecture/deployment_dependencies.json
python tools/check_redesign_gates.py --out /tmp/chip-review-gates.json
```

The report check intentionally fails if source hashes or retained numbers change. Regeneration records new evidence; it does not turn failed physical or release gates into passes. The dependency audit requires existing deployments and reads descriptors/manifests, not model payloads. Broad derivation tests also need the generated neutral IR and existing deployment directories.

Verification during the review: **34 focused tests passed**, including 2,000 seeded footprint cases against an independent byte-set oracle; the checked resource report passes; both real deployment audits complete. The release-gate snapshot reports **8/13 passing, with G1–G4 and C2 failing**. D1–D5, C1, C3 and C4 pass for their retained evidence, which does not qualify this new chip proposal. The integrated run passed **251 tests in 31.53 seconds** across architecture/dependency, network, machine derivation, G2 gate, comparison boundary and physical-driver suites. The final gain-replication regression then passed with the complete 34-test focused suite; the 218 related regression tests were unaffected by that local arithmetic change.

The first integrated run exposed the worker’s in-progress `schedule_rule.py` source-map mismatch. The worker updated `tools/audit_abi3_asap7_comparison_readiness.py` before the successful rerun; this review did not stage or overwrite those edits. Isolated-worktree failures from missing generated IR or outside-root deployment symlinks were resolved by testing in the main workspace with its real build inputs.

Final broad command:

```sh
PYTHONPATH=src python -m pytest \
  tests/test_chip_architecture.py tests/runtime/test_dependence_contract.py \
  tests/test_noc.py tests/test_derive_cycle_machine.py \
  tests/test_check_redesign_gates_g2.py tests/test_abi3_comparison_boundary.py \
  tests/test_asap7_physical.py -q -o addopts=''
```

`make check-chip-architecture` and `git diff --check` passed after the final changes. The physical snapshot was regenerated against the main workspace: lane and LQ8 source hashes match; the historical microsequencer route no longer matches five actively edited RTL sources and is explicitly marked stale. Future worker changes can intentionally make a checked report stale again. No RTL integration, full model-token run or chip route was executed by this review.

## Organized commits

| Commit | Change |
|---|---|
| `a007d80` | Derive legal memory placement, ROM reserves, meshes and delivery budgets. |
| `43907fc` | Specify hazard overflow, scalar reduction service and supported index mode; add tests and descriptor audit. |
| `8ea4251` | Conservatively reserve writes to output scale planes. |
| `e3e234f` | Generate deterministic checked JSON/Markdown and source-bound physical summaries; add Make targets. |
| `13e6a5a` | Reconcile the architecture specification and remove unsupported chip performance tables. |
| `75867e2` | Publish worker handoff, preserve concurrent closure findings and reconcile remaining documentation. |
| `fd06a98` | Replicate normalization gains correctly on tensor shards; refresh the main-workspace physical snapshot. |

Merge commits preserve concurrent physical-record work, including `7ae6bd3` and `44552eb`; later documentation commits finish this handoff and refresh the physical snapshot. Main-workspace implementation changes remain owned by the concurrent worker. Full-chip routing, model-token campaigns and deployment regeneration remain implementation tasks with the acceptance criteria above.
