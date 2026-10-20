# LEP private executable hierarchy — hand-back 2026-10-19 17:45 PT

Private branch `codex/s81-lep-hierarchy-1019`, prerequisite bb66563eb3baf13c0e84afe37ee772dabcef0db5 (RTL eec2dca41). Import only reviewed intended paths, never merge the entire old ancestor branch over current main. No route/gate/submit/native synthesis was launched. Owner hand-back stopped new work.

The source now contains executable TX/RX lane modules carrying the exact former g_tx/g_rx state, SRAM, registered OLD-write forwarding and show-ahead equations. A/H tops select alternate core only with HIER_LANES=1 (default0). There is no additional edge. Existing IN_PIPE1 still charges its original +1 edge. This is an implementation prototype, **not hardened child views**.

## Version identity and verification limits

`tested_v1_source.sv.gz` is the immutable exact source run on the fleet. Verilator5.050 A seeds1/5 and H seeds1/5 passed full traffic, source regional-state assertions and existing causal faults. The matrix was still running at hand-back: inspect actual MATRIX_CASE records and terminal exit before crediting remaining mutants. Completed negative controls had real nonzero mismatch/fatal witnesses; BUILD_FAILED does not count.

Four-state v1 Icarus compared all22 public outputs over900edges/19,800 comparisons, including reset release/reassert and injected X controls/data: PASS. **The first output sample was after initial reset assertion; pre-assert observation was not checked.** Unreset payloads/invalid-cycle X values were compared using case inequality. Original Icarus parse attempt failed on mixed initialized/uninitialized net declarations; a disclosed four-declaration parser-only split enabled the actual comparison. Original Verilator source was not transformed. See portable manifest and exact copied bench.

The working RTL is **v2, not yet executed**: a follow-up preserves the original legacy core byte-for-byte and all original g_tx/g_rx macro hierarchy names, then defines a separate alternate core. This fixes a real v1 integration defect: wrapping old bodies in g_flat would break existing macro placement patterns. `legacy_core_identity.json` proves the original core bytes against bb665. The frozen v1 behavioral results do not establish v2 source qualification. Current v2 four-state bench additionally requests pre-assert sampling, but it has NOT run. Future owner must finish current immutable v1 matrix, then run final v2 before any source/kit adoption. Existing complete objects remain remote; no restart/cancellation.

## Actual memory contract and remaining physical work

TX uses `physical/asap7_memory_macros_v2/ot_sram_1r1w_512x128_m4_r2c2`: 174.120x29.736um, **single clk**, independent 1R/1W enable/address,9b address,128b data/mask,2 spare rows/2 spare columns. RX uses `physical/asap7_memory_macros/ot_sram_1r1w_32x128_m1`:51.408x20.790um, **single clk**, independent1R/1W,5b address,128b data/mask, no repair. Both registered read/hold-on-disable/OLD same-address simultaneous read/write; wrapper forwarding is separately required. Do not replace either by a different clock/RDW contract merely matching dimensions.

Each of two lanes has five TX banks and five RX banks:696,320 physical storage bits total versus575,120 logical FIFO payload bits (DT512/DR8/W553). Indexed arrays remain SRAM. No ECC was added. Shared SRAM owner is resolving qualified contact geometry: legacy_macro_contact_audit.json measures **11 actual signal contacts in a1um window on both E/W faces** of both old masters. Existing0.096um contact pitch violates<=6/um. Hierarchy does not waive this. New source-owned PG/OBS/vias/contact geometry plus same exact clock/RDW/repair semantics is required; no manufacturing GDS prerequisite is inferred.

No mapped all-driver/BUF-INV-transparent census, native child area, placed<=405um census, native clock phase/spread, PG bindings, current/IR, access, routes, TTsetup/FFhold, or DRC closure exists for this new hierarchy. Lane inputs currently receive original parent prelanded distributed resets, preserving the original three-edge tree release. A genuine physical composition must price and prove local reset/root/control distribution rather than treating these vector ports as free.

Do not reuse the old GPL core-shrink wrapper: its20 SRAM macros lie outside the artificial64.8um core, with+179%/+164% cell inflation and terminal GPL0305 NaN/Inf at17:18/17:19. Real lane-local macro+standard-cell geometry and central-control assembly remain owed. One table of measured native child areas and pin/route demands should determine concrete child/parent outlines at40–60% actual standard-row utilization; source-only hierarchy is not enough.

## Preserved live job

Fleet root `ot-epyc4:/srv/opentallas-scratch/claude/codex-s81-lep-hierarchy-1019`; v1 matrix unit `oth-ubuntu-4160557-1792456854`, controller4160557, local client778709, functions session75347. Logs matrix-*.log and out_matrix objects stay intact. Four-state unit4162061 and A unit4156875 are terminal0. No native synthesis, new physical engine or second matrix was started after hand-back.
