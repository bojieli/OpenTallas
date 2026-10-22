# GU_PROP consumer collection, 2026-10-21 00:31 PT

The completed EPYC9 consumer job `oth-ubuntu-3298570-1792565122`
passes all 63 leaves on each of the 98- and 84-frame inventories.
The collector verifies all 46 consumed source hashes against `82ef7a0d7`.
Ten incorrect source-row / swapped gate-up vectors and four routed-expert
drop-weight mutations fail with numerical mismatch witnesses. The unweighted
shared expert correctly remains unaffected by the drop-weight mutation.
The five overlapped-issue vectors are measurements, not additional qualification.
The historical runner always exits zero: use the individual named verdicts.

This proves capture-map layout and the real SW consumer with injected RD pairs.
It does not prove the producer-to-consumer XR transport, static reservations,
stage capacity or the production MU calendar. `gu_gather.py` explicitly leaves
XR configuration, ring/tier reservations and local loopback open.

The source of the ongoing original DENSE2 campaigns has unquantized GU sharing.
It differs from this consumer-qualified source, which aligns shares to quads,
places gate/up capture row pairs and prevents phase capture-slot collisions.
Do not bind an original-source capacity map to this source without qualification.
Corrected expert-only probes (both inventories, n=1,2,3,64) passed; these do not
replace dense-family capacity qualification on the selected physical inventory.

Both existing inventory filters retain seven frames per retained column:
five h9 (three normal, two MX), two h10. The 98-frame filter retains 14 columns;
the 84-frame filter retains 12. Neither is a six-row layout. Capacity source plan
is `/srv/opentallas-scratch/claude/s81-dense2-1020/dieref/results/arch/s81_dv_1016/p4l/plan.json`
on EPYC9, SHA256 `6c1d6d930c6b9d44850946e08862476f8cc9bd3c8dd0d24f3e216d375d75fd2f`.
Sorted `u_` frame-name hashes (the exact capacity inventory convention):

- 98: `653badb6086c78fbb905d0c1d5c5df75d996ec28037b12cb228748a197a2fc0e`
- 84: `f695519f3da23a54dc37d9549696340bb59bb3427b9d3647452759ca17172aa2`

No new capacity campaign launched. Physical inventory selection is pending.
The original f98r224gp probe produced 162 stages (648 layer dies), not 161;
six exact chunks are live. Total dies and token rates remain unqualified.
