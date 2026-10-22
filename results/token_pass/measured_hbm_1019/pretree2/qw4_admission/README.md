# Exact four-head production shape admission

Compiled on the fleet from the existing model-order compiler with explicit
rows4 entries. max_r4 passes model reduction assertions, serial378/stream504
at compile time only. Runtime exactness is pending the already-running build.
No compile-time timing enters a release rate.

exp_sum_r4 fails all QPR1/2/4 allocations:512store rows exceed the500row
admission. The diagnostic NoneType traceback was the unhandled all-infeasible
case; own compiler now reports an explicit admission error. This does not
relax storage admission. A valid four-row implementation needs a real2+2phase
programme with proven store reuse or a physically priced storage change.
Halving an eight-row affine law does not supply that implementation.
