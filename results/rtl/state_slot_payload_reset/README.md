# Private slot payload reset experiment

Allocation initializes descriptor, cursor, capacity, row size, policy, generation
and retained remaining capacity. The resettable slot_used vector makes those
fields inaccessible until allocation. This candidate moves allocation and
retirement writes to a synchronous-only block with identical control priorities,
removing reset from private payload. Public counters, slot validity, protocol
state and cancellation behavior retain their existing reset semantics.

The allocation guard preserves allocation on refused operations. The retirement
guard excludes active modulo steps and new modulo initialization, and requires
apply_phase==2, matching the original branch priority exactly. The retained
capacity field is updated only for non-saturating policies as in the baseline.

See comparison.json: area decreases, prelayout timing worsens. Production is
unchanged, and this experiment is not selected as a clock improvement.
