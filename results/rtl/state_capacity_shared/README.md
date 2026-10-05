# Reuse stable capacity during apply

Relative to state_remaining_capacity, remove next_capacity_q. The selected slot
and its capacity cannot change between apply_phase 0 and 1: apply_busy excludes
new operations, and retirement is later. Clear/discard/reset cancel validity;
the next operation recaptures its cursor before computing remaining capacity.
No cycles or public behavior change. Both simulators and the containing campaign
pass. See comparison.json for the area/timing tradeoff; production is unchanged.
