# Final FFN combine placement, before implementation

Actual xs_place down partitions output rows, 1280 per TP4 rank, 80 per
source slice. This is not the attention wo_b input-column reduction.
Canonical FFN arithmetic is six routed BF16 down vectors in ascending expert
ID order, sequential FP32 adds, shared last, BF16 once at the end.
Existing VS op13 implements this chain: 56 eight-word reads, eight
eight-word writes, 448 input words and 64 output words per owning leaf.
No new RTL, MAC, memory port, storage macro, or physical interface is needed.

Allocate phase leases in the existing 1024-row leaf store:
capture128..239, assembled320..431, combined448..463. These reuse the VPX
allgather region only after its last consumer. They cannot coexist with a
live VPX/gain lease. FFN pre1008 and coefficients1009..1013 never overlap.
Seven capture phases each reserve16 rows, but only source leaves0 and1
contain data (64 and16 values). Move real eight-value row pairs via existing
RD transport to the unique global64-value owner (sid=beat//5, leaf=beat%5).
The move map has1120 pairs/rank,4480 acrossTP4,143360 data bytes before
headers. Exact line cycles require actual paths and reservations; no price
is claimed from the map alone. No write may precede its source completion.
The four HC residual copies are replicated on each TP4 rank. Therefore each
rank combines only its20 owned beats; the combined result must then reach
all three peer ranks before their POSTs. The explicit result allgather adds
480 full1024-bit RD beats (61440 data bytes). The destination rank is part
of every transport record. The current local-command binding admits only
the arithmetic-owner rank; peer POST calendars remain blocked on actual
allgather paths and bounded arrival proofs.

VS arithmetic issues56 pairs at one per edge and performs448 FP32 adds
(including the implementation's first add of negative zero), no MACs.
One op per owner leaf; measured command-to-final-write is required before
calendar admission. POST uses a0=1009,a1=448, reads16 combined rows and
updates four residual copies through the actual VP/VN path. The old63-edge
POST observation is not a new qualification. All80 beats, actual transport
ages, lease/drain witnesses, G8/NX/XB/gain binding and physical timing remain
required. The new compiler is opt-in and refuses missing residency evidence.
