# Optional T41 data/K observer: source PREP

Default OFF, bounded by an explicit data-path query limit. This emitter parses
the exact golden SDC generated export source bindings and the actual compiled
Verilog output widths; it never invents a single-owner rule. The enabled Tcl
reuses the existing source-by-path resolver from pair_skew.tcl as a library,
in a private Tcl namespace without calling its main or zero_unc or overriding
any native session pair functions. Existing library-only and method state are
restored. It writes the original constrained SDC
snapshot, then records every requested bit's actual FF/startpoint/endpoint,
clock pin/master/source/edge, native data arrival and native vclk STD slack.
Actual declared forwarded K uses its physical master-clock path/source and
both rising/falling early/late arrivals. No folding, clock constraint change,
GROUP_RE toggle or new CPPR credit occurs.

Data_min-K_rise_late and Data_max-K_rise_early are explicitly UNCORRELATED
CONSERVATIVE BOUNDS, not native forwarded-clock STD slack. Native vclk slack
is retained separately. Same-owner correlation is not silently assumed for
mixed owners; a failing conservative bound is not a reason to waive anything
or require one tap owner. Qualified receiver composition still needs explicit
F for F/R phase or the existing complete conservative tap hull, separate from
L/F data/K. No production coverage or routed qualification is asserted.

Seven tiny source/Tcl controls PASS: generated-source binding, mixed per-bit
owners, foreign root, wrong physical F, NO_PATH/budget/missing-generated
failure, literal bit names, and isolation from native session helper functions. The source generator was run on the actual
Anear SDC and1_2_yosys.v ONLY (text processing), not on OpenROAD/OpenSTA.
Actual request:8exports,4816bits,9632 max data-path queries. Clock lookups are
fixed at4 per export plus source validation, with2 initial native timing
updates; default OFF performs none. Execute only in the original loaded
post-CTS TT/FF state BEFORE uncertainty zeroing or exporter clock mutation.
Missing/error/limit observations fail clearly without changing native verdicts.

Prepared outside active kit on Intel2:
/srv/opentallas-scratch2/claude/codex-t41-export-observer-1640/T41A_observer.tcl
Its `.request.json` binds the exact source SDC and compiled interface. Future
scoped session output uses /out/t41_export_witness. Source/physical inputs and
GROUP_RE remain unchanged. ROOT/S81 own ONE normal baselineA CTS plus witness
admission; B stays fallback. No EDA was run by this worker.
