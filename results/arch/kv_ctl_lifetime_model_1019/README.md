# CTL lifetime and predecessor copy model: HOLD before implementation

This continues `efca20ca6` against source `c5fbbded9`. No RTL, macro family,
clock, schedule, running gate or physical view changed. All fleet jobs in this
packet finished. Existing mu5/mu5b remain diagnostic. Full source realization,
physical access and token composition remain open.

## Actual graph, including predecessor costs

Read-only OpenROAD exports use the same placement ODB SHA256
`fcbc77429404faa5ab91981c1901b93dfb43f5b254bc0992e0d9cdd38460af0a`.
Unlike the previous census, every root retains its endpoints, including roots
initially below 32. Unique endpoints are BUF/INV/HB transparent; clock and PG
are excluded. Graph and input/master inventories are compressed here.

The monotonic native capacity model replicates every input pin of each copied
instance, propagates those extra loads upstream, and partitions each root into
groups of at most 32. Multiple outputs of one instance share the largest copy
multiplicity. Four rounds converge: 584, 601, 602, 602 extra instances.

| Native driver kind | Copied roots | Extra instances | Existing master area, um2 |
|---|---:|---:|---:|
| FF | 114 | 278 | 91.47492 |
| Combinational | 76 | 323 | 29.64114 |
| Tie | 1 | 1 | 0.04374 |
| Total | 191 | 602 | 121.15980 |

Sixty reset-only roots need 149 extra FF after predecessor propagation, versus
the earlier 148 lower bound. Six previously safe roots now require copies.
The model adds 278 actual FF clock contacts, all on native `ck`; it also records
each additional async input by native net. No input port or macro driver needs
replication in this fixed point.

This is an exact demand calculation for the **old mapped graph**, not an
implemented source copy forest. Equivalent combinational copies may merge;
identical state copies need kept functional provenance and reset/update proof.
Changing storage changes this graph. Resynthesis, Liberty capacitance, routing,
clock insertion and source functional-copy realization remain unpriced. The
121.1598 um2 figure cannot be treated as final successor synthesis area.

## Writer collision and actual observation

The source's writer macro reads on raw `start_p`; writes use the preceding
accepted boot request `wq_v`. A legal config word 0 followed by an invalid
start for stage 1 causes a real same-address row-0 collision. The unchanged
source/minimum-component Icarus witness records this event before fault becomes
sticky; the rejected start stays inactive. This disproves blanket no-overlap.

The collided read result is nevertheless unobserved by the writer's functional
state under the registered-read contract:

1. `configured -> !wq_v` is inductive. An accepted table write sets `wq_v` but
   cannot set `configured`; the distinct seal request sets `configured` and
   clears `wq_v`. Writes are refused once configured. Reset clears both.
2. `ld` is set only by an accepted start. Such a start requires `configured`,
   no active transaction, no prior fault, no simultaneous config request, and
   a valid stage. Its macro read therefore has no pending write.
3. `t0..t3` and `stop_q` consume macro Q only on the following `ld` edge. They
   sample the preceding accepted read before any new raw-start read NBA updates
   Q. No other state consumes `rt0..rts`. Invalid raw reads cannot set `ld`.
4. A boot collision's rejected start makes fault sticky. Further starts cannot
   be accepted before reset. Reset clears `ld` and all enables, without assuming
   SRAM initialization. Ordered `next_cfg` checks require all 180 table words
   followed by the separate seal before the next accepted start. Every used
   word is rewritten, so collided/stale read Q does not survive to first use.

`consumer_proof.py` explores a conservative finite control abstraction: 15
reachable states and 1,920 transitions, arbitrary initial/collided read Q,
arbitrary completion and table validity, and even early seals. Both invariants
pass. This is an explicit abstraction with a source mapping, not a generated
whole-source formal equivalence receipt. The exact source collision witness
and abstraction output are preserved separately.

The candidate n64 behavioral model's read function only reads array cells;
`word_write`/`cell_write` never depend on `rd_out`. Its fault-free modeled writes
therefore survive simultaneous reads, although OLD/NEW read order is undefined.
**A physical dual-clock primitive contract guaranteeing write integrity during
same-address access remains required.** The control proof only permits arbitrary
read Q; it does not permit an arbitrary damaged stored word. Thus accepted-read
safety alone does not yet authorize the candidate family.

## Layer programme lifetime

LPRG reads on `|e_begin`, not raw start. Its pending writes are accepted table or
gap words; accepted config requires unconfigured, no active context and no fault.
Seal is a separate final address 470 after 324 row words, digest/epoch and 144
gap words. On the seal edge the last pending gap write can land, but configured
is still false before the edge, so no accepted start/read can occur. Subsequent
stage events arise only from an accepted configured start; config writes are
then refused. Reset clears pending write enables, events, active contexts and
configured together. This source induction establishes no logical concurrent
read/write for LPRG under its shared `rn`/`ck` semantics; independently skewed
physical copies are not assumed equivalent by this argument.

Useful storage remains 20,736 boot bits plus 288 derived gap flags: 20,888
macro bits and 136 stage-1 gap register bits. Row widths 256/168/160 imply
4+3+3 n64 slices, if the macro and source contracts are subsequently qualified.
No reset of macro payload is needed for first use after a successful full boot;
uninitialized macro Q and unused padding cannot be used as validity.

## Existing n64 contact proposal is not access-qualified

Exact `bc42f77a8` n64 LEF SHA256
`737a650260dfd52a14003b0e0aad97378b81ebc1adb0b6b9383c256c67ea92d6`
has 105 contacts on each W/E face. Both sides occupy centers y0.780..10.764,
only 9.984 um of the 27.576 um face, at 0.096 um pitch: **10.4167 contacts/um
locally**. The 3.808 whole-face average hides this cluster. No n64 access PASS
is claimed. Exact pin coordinates are in `contact_audit.json`.

The shared S81 wider-pitch access work is only a geometry pattern: its qualified
scope is single-clock 512x128, not this dual-clock 128x64 topology. A CTL family
needs its own terminal/via/OBS/PG and parent grid proof, two clock contacts per
macro, and earliest/latest timing. No duplicate compiler was created.

## Release dependencies and schedule

The proposed 345.6 x 475.2 tile still cannot fit the current 1123 x 172.8 parent
slot. No fit, utilization, 405 um wire, pin-registration, clock-spread or full
SAFE claim follows from this model. Existing source shares native `ck`; actual
landed parent phases and reset-edge delivery remain required.

Same-edge copies and one-edge registered SRAM reads target zero new token edges.
That remains a target. Keep existing mu4 quiet/abort and boundary prices; whole
SU and MU token deltas remain NULL pending whole-source lockstep, production
throughput, native timing and actual die-calendar composition.

Next owner must choose either a dual-clock physical write-integrity contract
plus proved unobservable collision Q, or a source-qualified legal-read enable;
complete the actual kept source copy forest; reuse the common wider-pitch access
method with CTL's topology; and regrant the parent slot before any new gate.

Fleet receipts: graph `oth-ubuntu-1536985-1792442090`, fixed-point/collision
`oth-ubuntu-1541295-1792442128`, input/master inventory
`oth-ubuntu-1545790-1792442158`, consumer abstraction
`oth-ubuntu-1556239-1792442230`; all terminal exit 0 on ot-epyc6, unpinned ot-run.
