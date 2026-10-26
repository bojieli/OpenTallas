# ST3 control clock demand

Inherited twelve runs stop with structural FF hold failure, not tool crash. inherited_cts.json records all thirteen outcomes. t47 returned zero with negative hold slack; it is not SIGNED. Only t24/t30/t46 have retained detailed hold_diag.tsv: their worst endpoints are arst_n to u_rst_in, with additional FT-entry/relay/removal violations. Do not assume the remaining types have a proven identical worst endpoint; their exact gate failure is known and detailed successor diagnostics remain required.

The paused reset_sinks draft excluded explicit START semantics and assigned prev immediately before testing its final equality, so its convergence flag could always become true. Per-type convergence is also insufficient because reset contract depths can depend on multiple type tap inventories. The corrected source enumerates actual RT physical relay aliases, computes simultaneous group rounds, detects oscillation/nonconvergence and applies nothing on failure. It rejects root sync/lock controllers, whose clock census needs proper multi-flop weighting, and rejects unaccounted existing extra inventories.

Current canonical c51 and paused ST3 plan both omit reset.start=broadcast. Their RESET-only census converges in three group rounds (reset_only_ledger.json), but does not qualify a START-enabled successor. The source defaults to require_start=True so this gap fails closed. The isolated broadcast diagnostic changes a copy only; an eventual S81 plan batch must pair START geometry and the generated RTL/parent forwarding/release tables/token calendar. No new physical wave or route token is authorized by this source result.

The broadcast diagnostic on canonical c51 geometry converges for all 13 selected types in three group rounds. broadcast_ledger.json records RESET+START physical DFF counts, initial/final reset depths and release_clocks. The control refinement changes release offsets by zero in this diagnostic; a later geometry/density batch must regenerate and price its own result. The diagnostic physical coordinates in broadcast_clock_payload.json are not an approved replacement for the final batch's geometry.

Exact use after the final geometry/clock edits and coherent START-enabled RTL/plan selection:

```python
import sys
sys.path.insert(0, "physical/die_plan/s81")
import delta_station_controls_1713 as D
ledger = D.apply(raw, types=D.STATIONS)  # requires reset.start=broadcast
# Preserve ledger with initial_contract, final_contract and release_delta.
# Each affected raw.partition_types[tn].clock.sink_sites_um is now complete
# for the generated non-root RESET+START controllers in that final geometry.
```

Do not merely add the START field to an otherwise incoherent released plan. Require generated actual RTL/reset-tree receiver and relay census, actual parent START forwarding/admission, fresh release/calendar/token witnesses, and actual DPL/CTS sink coverage and visual review before route. The helper does not inventory arbitrary leaf state or root synchronizer/lock DFFs.
