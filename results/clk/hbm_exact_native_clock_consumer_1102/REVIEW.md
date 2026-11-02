# Exact native clock consumer — disabled source PREP

This consumer closes the source/API gap between the32 actual-row BUFx24 root reserves and the named20,842 FF +44 SRAM clock sinks in the programme candidate8 model. It is **off by default, not installed into any kit, and not native-vehicle qualified**. It invokes no CTS, placement, source generation, simulation, timing or save command. No RTL, public clock port or source cycle changes.

`tools/die_plan/exact_native_clock.py` generates literal Tcl data from the exact pin-aware clock model, source clock map and macro geometry. It refuses centre-only metrics, changed250/202.5 budgets, duplicate/missing/aliased sinks, bad native row poses and actualY-to-CLK radius violations. The frozen actual32/20,886 dataset parses in plain Tcl; its uncompressed SHA is `7c571851153c90887bf5985495683399394d74a2952f46eaea62a084cde3ae43`. The compressed data is retained here; no ODB was loaded by this parse.

`tools/die_plan/exact_native_clock.tcl` is a separate opt-in post-COMB-PLACE/pre-CTS consumer. It requires the data SHA, current native budgets, exact outline/entry metal, actual source root membership, typed CLOCK terminals, exact actual pin/macro poses, matching native rows, all current COMB/FF/macro body exclusions, root-island clearance and full realY-to-CLK corners before mutation. It consumes only32 native hard blockages with property `ot_exact_native_clock_reservation=<modelSHA>:regional_N`; all foreign reservations remain obstacles. The preGPL reservation hook belongs to the token lane. No4.32 anchor rounding, nearest-group reassignment or detailed placement is used.

The canonical `native_pg_binding.tcl` and real native PG constructor module must already be available with the actual libraries/ODB/flat VDD/VSS rules. The consumer requires initial nativePG0 through `ot_pg_native_birth_begin`, creates only the32 owned BUFx24 cells through the callback-bound native factory, reconnects only enumerated clock inputs, rechecks actual inserted output metal, ends/uninstalls the callback and requires inactive0/nativePG0 before protecting new roots. It has no `global_connect` or post-hoc PG repair. Both primary and local clock nets stay open for later CTS. Existing strict refusal of unqualified CTS/placement stages remains intact; callback state is not inherited into another process.

On any nonzero body completion, including nonlocal return/break/continue, it restores logged original clock connections/protection, destroys only the preflight-empty owned cells/nets, restores exact consumed blockages/tags, detaches the callback, appends cleanup failures without replacing the primary error, and throws an explicit error. A failed cleanup requires discarding the process; no save follows. Reapplication to an already modified tree refuses rather than guessing its state.

The PG owner independently reviewed this lifecycle and concurred at source scope after two corrections: force non-error Tcl completion codes to errors after rollback, and catch the final status query itself. This is not a native constructor, postCTS or saved-ODB PG qualification. Nine directed generator/default-off/signal-protection tests pass. No fake native PG implementation is used as a production capability test.

Future reviewed caller shape, after genuine preflight inputs and a separately authorized native vehicle:

```tcl
source /work/native_pg_binding.tcl
source /work/exact_native_clock.tcl
set ::env(OT_EXACT_NATIVE_CLOCK_PLAN) 1
set ::env(OT_EXACT_NATIVE_CLOCK_PLAN_SHA256) 7c571851153c90887bf5985495683399394d74a2952f46eaea62a084cde3ae43
ot_enc::apply /work/exact_native_clock_review_data.tcl /actual/pinned/nativepgbirth.so
```

The helper and module must be the actual reviewed flat-literal native PG implementation (PG owner562/e19 helper and real8c9 module, or its later qualified replacement). This example does not activate a kit. Actual32-root vehicle, OpenDB API/body rollback behavior, source/ECO proof as required by the normal flow, saved-ODB independent PG, ordinary CTS stage admission, TT/FF arrival/related-pair skew, data timing, reset/START and parent adoption remain held. The geometry packet is `results/clk/hbm_programme_internal_clock_model_1102` at9636952c7, with corrected pin-aware independent LOOK concurrence; its earlier centre-only failure remains preserved.

Later integration must replace the legacy density installer for this same scalar root, preserving other required flow hooks. Running both installers would change the inventory. After ordinary CTS/F4/repair, a fresh actual graph must show each original CLK endpoint descending from its planned regional driver, with unchanged driver pose and current actual pin geometry. A downstream local CTS tree may add buffers; transferring a sink to another regional root changes this model's ownership and requires a new census/model. The present consumer does not qualify later F4 moves, clock inversion/phase, or CTS-created cells.
