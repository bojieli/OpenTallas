# GEN2d reset carrier: exact terminal evidence and bounded continuation

MODEL / HOLD. No source prototype, forest replay, synthesis, physical run, shared activation or adoption. This succeeds 0d8e1bd89 only for terminal-state evidence and native source-contact accounting; it does not claim a routed reset tree.

All four original searches terminated with real exit 3. The two postchains stop before S4 splice: 14:11:52 and 14:26:57 PT. These are geometry/reach FAIL, physical OPEN, not jobs to wait on.

| Variant/source | Terminal PT | Rejected roots | No reachable relay / no sync home | Actual peak RSS |
|---|---|---:|---:|---:|
| ofly / 15e069307 | 13:59:52 | 40 | 29 / 11 | 2,694,424 KB |
| ofly57 / 15e069307 | 14:10:57 | 46 | 32 / 14 | 2,692,316 KB |
| hhpref / 1e3fbe31b | 14:25:44 | 46 | 32 / 14 | 2,713,500 KB |
| hhfb / 1e3fbe31b | 14:26:04 | 46 | 32 / 14 | 2,716,964 KB |

The exact 178 attempted sites/results, four immutable report hashes, command receipts, helper/RTL hashes and input hashes are in `evidence.json`. Source-label identity is distinct from the SHA256 of the actual archived bytes. Read-only collection used unpinned ot-run unit oth-ubuntu-532489-1792446813 on ep4, real exit 0; it did not call Geometry/build/chain or search the forest.

## What actually failed

The first domain is HBM, with 810 reset sink pins, and its first region is CN. Increasing candidate root positions and admitting same-domain hosted reach stages did not get past the same local reset predecessor coordinate (12761.158,19794.988). The first proposed CN home is near (18531,30455), Manhattan 16,429.854 um away. Even unconstrained Manhattan routing needs at least 41 spans of at most405 um, before the allocator's conservative pin/rectangle budget, actual detours, PG channels and branch loads. The seven-home local clock spur is not that missing reset path.

The native source preserves separate routing and placement grids: placed small relay tiles can be overflown by wires, while still blocking complete new relay homes. Hosted modes require same-domain unused stations; the log inventories 3,438 HBM hosts alongside19,318 stream and4,966 serial. This is evidence of a structural reach/home bottleneck under those frozen reservations, not proof of a particular offending cell or permission to borrow another domain. A new root-count retry has no causal justification.

**Exact failed reservation snapshots do not exist in the terminal outputs.** Each variant has an empty `loc`, a minimal report and frozen source; no layer or grid/reservation snapshot. `plan_region` snapshots before each candidate and restores reservations on GeometryError. The outer CLI catches the final exception, writes only FAIL/problems/unhomable, and exits before input hashes/spec/report success serialization. Thus reconstructing the exact in-flight homes, predecessor instance, branch ownership or PG conflict from these files would invent evidence. The logs preserve coordinates and rejection text, not the geometrical state. The read-only inventory confirms this absence for all four directories.

## Seven-home model, corrected native source contact

Retain the previously selected seven32.4um-square homes (7,348.32um² reserved outline) and all76,233 existing clock-cell envelopes. They remain a hard-block-plus-clock candidate, with speculative forest reservations and PG channels unknown. Do not convert that candidate to legal placement.

The existing dkh_P2 is R0 BUFx12f_ASAP7_75t_R at (11234.700,20124.720), native size .972×.270um. Its real Y has three M1 rectangles; their centers give source→first proposed clock-pin distances286.456/286.670/286.258um, replacing the old285.494um origin-to-reset-input number. All are below405 geometrically. Rectangle selection/access/vias and RC remain OPEN. The .972×.270 body fits the old1.62×.270 allocator envelope, but native PG rails extend9nm beyond the body and require actual row/rail/contact qualification.

The other six spans must be recomputed using a genuine new master's clock_out and clk contacts. Frozen hbfd_rrl_hop/sync LEFs expose clk and reset ports, with **no clock_out**. The old clock-spur model reused reset-output coordinates as proposed clock anchors; they are not native clock contacts. Its proposed final reset output12781.158 is20um east of the failed coordinate12761.158, so no predecessor-instance binding follows. The207-buffer noninverting source ancestry to real hb_ckgen/pll_hbm is preserved in the earlier clock_graph.json, but does not prove new load, clock slew, phase or min/max delivery.

## Phase, assertion lifetime and compiler price

The actual HBM metadata has period1024ps,3953sink pins,28regions and11087buffers; it explicitly says propagated STA is required. Model insertion9958.2ps and model pair insertion9845.3–11016.0ps are estimates, with native phase/ownership OPEN. GEN2c case_a/out is empty. There are no actual TT/FF source/landing phase extrema to substitute into a release equation.

For every predecessor i→successor j, prove both corners with actual edge identity and uncertainties:

`CQ_i(min)+reset_wire(min)−max(C_j−C_i) >= removal_j+hold_uncertainty`

`CQ_i(max)+reset_wire(max)−min(C_j−C_i) <=1024−recovery_j−setup_uncertainty`.

The existing hop is async-clear with D=1. Clock forwarding alone cannot force a full extra release edge; same-edge release remains possible under skew. A half-cycle contract must be implemented and priced if needed, with real generated-clock edge/polarity and duty-cycle bounds, never inferred from buffer count. Every raw assertion must propagate with clocks stopped, retain native minimum clear pulse at all leaves, survive reassertion in flight, and operate without zero initialization. Existing POR false paths cannot replace recovery/removal qualification.

Compiler POR age must be the maximum proven source-relative edge age across the final tree, including actual two-stage face release and all domain crossings. Each genuine added HBM edge costs1024ps; total edges and delta remain NULL until tree/phase binding. Token payload bandwidth and MACs remain0; runtime latency delta0 is conditional on startup completing before priced work, not a current proven value.

## Concrete inventory and next bounded work

Keep the dedicated HBM corridor choice. Minimum local MODEL inventory is seven kept clock forwarders, two face reset FFs and at least18 VDD/VSS terminal bindings, plus native ties, all signal/clock pin caps, recovery/removal cells, actual routing tracks and PG contacts/vias. The7,348.32um² is outline reservation, not native cell area. Do not map FF choice or clock_out buffers until their TT/FF Liberty, full PG MTerms and pin geometry exist. There is no coherent runtime storage or SRAM added.

Cap every reset driver at32 BUF/INV-transparent sinks, including trunk branches, not just810/32⇒26 minimum leaf drivers. Original commands omit --fanout, so their frozen default2048 is historical and cannot qualify a successor. An explicit complete native all-driver census is required after mapping; no name-based clock/reset exclusions.

The next source-only artifact should define a failure-snapshot schema and a bounded dedicated-carrier abstract: exact frozen input/helper hashes; pre-candidate and pre-restore grid bytes/hash; all reserved/host-used records with domain and branch owner; failed source instance/native contact and target; all clock-cell envelopes; PG/channel occupancy; genuine clock_out LEF/Lib/source equation; per-corner source/landing phase/wire bounds; assertion and compiler-age ownership. **An instrumented replay would require a new explicit grant and is not performed here.** Snapshot instrumentation alone is not recovered original evidence. Until a snapshot or a jointly reserved deterministic replacement is available, no source prototype or engine grant is justified. Root reviews this MODEL first.
