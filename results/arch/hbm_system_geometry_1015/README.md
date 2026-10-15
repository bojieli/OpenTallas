**Subsequent whole-system source work:** [SYSTEM_GRAPH.md](SYSTEM_GRAPH.md) supersedes any interpretation of these initial macro-only precursors as complete ATT designs. It adds P source memory, 589,824 mandatory transposer FF bits, shared native HBM controllers, actual SM children and explicit physical-interface gaps.

# HBM system geometry: structural work, 2026-10-15

The earlier 54-child ATT figure was a bounded local translation of a historical parent. Its 8.31% result does not establish a good system arrangement. The new scope is the complete HBM accelerator and its actual communicating groups. These artifacts are an initial structural ATT subgroup comparison, not a complete die floorplan or a routing recommendation.

A concrete underlying issue is the serializer bank permutation: `bank=(tile*4+head//4) XOR ((c&3)|((c&12)<<2))`. Across the 16 dimension beats, each tile communicates with banks shared by four feature tiles with the same `tile%4` within a 16-tile lane. Thus placing the existing banks beside one contiguous tile does not make the writes local. Moving complete bank-affinity groups is a real topology alternative. Another alternative changes the storage architecture so every tile has its own banks for every dimension phase; this costs actual SRAM area and local fanout.

The reproducible generator uses the literal existing 514.89 × 562.95 µm quad LEF, **128 quads / 512 functional HG1 groups**, 64 query SRAMs, 34 staging SRAMs and one programme SRAM. It preserves every known macro in this inventory and uses only R0 orientations. Existing serializer alternatives use 128 data SRAMs; the enlarged alternative uses 2048. It does not substitute standalone 294.782 µm head-group macros for the actual quad inventory. Proposed logical tile to physical pair mapping still needs a source-bound successor.

| Structural precursor | PV affinity distance over all 16 beats, M bit-µm | Worst source-to-bank distance, µm | Macro envelope, mm² | PV SRAMs |
| --- | ---: | ---: | ---: | ---: |
| Tile-major comparison | 894.957 | 7472.55 | 46.670 | 128 |
| Head-major comparison | 1675.385 | 12898.42 | 44.822 | 128 |
| Eight bank-affinity groups | 507.486 | 3856.11 | 50.145 | 128 |
| Tile-local enlarged storage | 119.262 | 959.28 | 51.927 | 2048 |

These are **PV-only adjacency screens**, not final rankings. They use actual quad `oy` pin centres and SRAM `wd_in` pin centres for 262,144 bit-beat source/destination relations. The current parent pipeline, selection/capture circuits and status paths are not included. Summed activity covers one complete 16-beat PV capture, rather than weighting all declared buses equally. The source-to-bank distance is an optimistic architectural screen and does not claim that the corresponding combinational route is legal. Even the best screened arrangement needs explicit register stations: 131,072 bit-beat relations remain above 500 µm. No timing, throughput or token-rate improvement is claimed.

The enlarged option changes the bank mapping to `(tile*16+c)*4+head//4`, with epoch-only address. It uses 2048 real 32×128 SRAM macros, 1 MiB allocated for two 32 KiB records, versus 64 KiB in the current 128-bank option. Additional SRAM area is **2.052043 mm²**. Capture still writes 128 distinct banks per beat; canonical head-major drain still reads 64 distinct banks and commits the same 128 aggregate VM edges. A complete independent Python memory scoreboard checks three records, 24,576 FP32 words and both epochs; omitting the dimension from the bank mapping causes read-port conflicts and is rejected. This is a model proof, not native RTL qualification. Actual local 16-way input fanout, all flags, decoder placement, clocks and physical SRAM access remain required.

The generated envelopes have no overlaps and preserve at least 5.4 µm between every macro rectangle. This is **macro clearance only**: the displayed streets are not sized from the full buses, PG obstructions or actual cut arithmetic, and are not evidence of routability. Added register/selection/fault roots, real channel widths and external connections can increase the footprint. Baseline and candidate do not imply accepted final die area.

`candidates.svg` shows all four precursors at the same scale with exact macro dimensions. It labels every quad and gives each rectangle an instance tooltip. Orange is quad arithmetic, pink PV storage, blue query memory, green KV staging and purple programme memory. The unchanged shared-memory shelves are inventory reservations; their placement has not been optimized. `candidates.json` includes every macro coordinate, all input LEF hashes, metrics and limitations. The canonical v2 staging LEF says 174.744 × **70.488** µm; the current functional proof uses a v1 memory model reported as 70.470 µm. Port/logic equivalence and exact physical binding remain explicit obligations.

## System constraints received from the owners

- Canonical attention is H16/D512, TD32/NL2, HG1, 32 full logical tiles / 32 half-pairs / 512 functional head groups; one engine has 34 staging, 64 query, one programme and the serializer's actual data macros. Do not multiply staging by 32.
- Query originates at NE VM read group 3; output is canonical FP32 `[head][dimension]` through **NE VM write group 1**, eight banks and 2048 data bits per edge. Four independent quadrant drains would be a new allocation, not the current contract.
- KV source is 8480 bits per issue edge; PV capture is 16384 data + 512 status bits. Current HBM service only delivers eight 256-bit sectors per edge, so actual multi-stack allocation/overlap must enter the geometry. Source positions cannot be selected without stack/PHY service ownership.
- Actual VM has four quadrants, each with eight bank leaves, a hub, two ring stops and replay. VM→SU→SFU→HC taps must be split into eight bank-local leaves per stage: 96 roots globally. Each stage/bank has three 556-bit bundles, 1673 pins including control. Existing two-edge tap ages are preserved unless a new explicit schedule is proved. Source pin manifest: `/home/ubuntu/wt/hbm-vm-static-1014/results/arch/hbm_vm_lg_split_1015/pin_manifest.json`.
- Source contract `/home/ubuntu/wt/hbm-die-feas-1014/results/arch/hbm_die_v15/source_contract/contract.json` has 68 nodes / 644 known edges, but omits current native ATT/SM/SU/IDX composition and complete physical pins. It is not an authoritative full-system placement graph. Historical slot/name matching cannot repair this omission.
- Fixed PHY shoreline must stay source-bound. Current SM successors have real larger outlines; the old 9.412 mm² packing is invalid. Four-home Engram allocation exceeds physical per-stack capacity; the new eight-home protocol changes the memory topology and must be included rather than hidden as a placement fit.

## Recommendation and next work

Retain the bank-affinity grouping as the lower-area structural comparison and advance the enlarged tile-local option as an explicit area-for-locality candidate. Reject the illustrated head-major arrangement for PV locality. This recommendation is limited to choosing which structural alternatives to develop; no candidate is ready for adoption.

Before ranking a whole-system floorplan, reconcile every current physical child/master and explicit missing source boundary; insert producer/consumer schedules and production transfer activity; bind NE VM, true HBM/PHY service homes, SU/IDX/collective/SM and all clock roots; size cuts to ≤0.60 with PG/pin access; place real registered stations and flags; then compare all incident critical paths, external wirelength, latency, area and fixed-calendar changes. An attractive local grouping that makes the NE VM or KV/collective paths worse can lose this comparison.

Reproduce: `python3 tools/hbm_system_geometry.py --root . --out results/arch/hbm_system_geometry_1015`. Substantive calculation used `ot-run --mem 2 --threads 1`, AGI unit `oth-ubuntu-3779164-1792053769`, terminal exit 0. Frozen inputs and outputs remain at `/srv/opentallas-scratch/codex/hbm-system-geometry-1015`.
