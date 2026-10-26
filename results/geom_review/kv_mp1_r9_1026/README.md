KV MP1 constructive geometry candidate, not adopted or routed.

Runtime: epyc1:/srv/opentallas-scratch2/claude/codex-kv-mp1-1026/r9/die_plan_repaired.json.
The r5 candidate repairs original shifted and implicit station sites. `kv_mp1_windows.py`
then fits actual replica/neighbor windows and exact endpoint reach with existing station
counts (r7/windows_plan.json). r7 row allocation passed 60/62 selected slots. Retry ONLY
kv3_hgi_v6/ft8 and kv3_hgi_v7/ft4 at solver budget403.5 while reserving every surviving
r7 placement produced r9, PASS2/2. The final physical gate remains405um for every bit.
No stations or mission cycles were added. Failed predecessor results are preserved.

Canonical audit: 493028 actual per-bit FT internal/output hops,0over405,max405;
0macro footprint hits and0geometry errors in this scope. Corridor capacity, shared
clock/reset, complete-masterplan closure, wide-bus partitioning, and physical builds
remain separate gates. No freeze/signoff claim.
