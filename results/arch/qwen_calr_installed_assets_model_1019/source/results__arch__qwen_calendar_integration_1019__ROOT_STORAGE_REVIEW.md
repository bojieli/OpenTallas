The selected typed16/PW400..438 witness contract has two finite storage models.
No storage RTL, physical gate, clock assignment, FIRST or runtime ABI is enabled.
Both preserve all required slice witnesses and protect held profile/epoch/user.

| Candidate | Template store | Additional FF bits | Raw area lower bound | Raw FF clock pin capacitance |
| --- | --- | ---: | ---: | ---: |
| Native single-clock32×64 | One2048-bit macro,28 packed rows |2185 |1189.553um² including552.407um² macro |1037.298fF plus9.346fF macro |
| Finite FF control |13×134=1742-bit sealed block |3288 total including templates |958.781um² |1560.932fF |

These areas use one pinned DFF cell's0.2916um² as a lower bound. They exclude
reset-cell uplift, mux/decode/enable logic, buffers, CTS, route and placement.
They are not mapped area, fit, timing or power signoff. The model enumerates all
state components and the remaining logic obligations. Each indexed block stays
below2kb. The FF template read mux or SRAM record aligner needs134×12=1608
2:1 mux equivalents; enabled data has2942 FF-option or1775 SRAM-option feedback
mux bit obligations. Select/decode and actual mapping remain unqualified.

Native32×64 source is b65718325, confirmed by active kv_safe; receipt7549.
It has one common clock and independent1R1W ports, registered read output and
read-before-write same-address behavior. The raw source was tested directly
with silicon initialization disabled: all32 rows explicitly written,38 read,
hold, old-word collision, masked-write and external-capture checks passed.
Driving CE/address before the read edge produces registered output after that
edge. A consumer FF captures it one further edge later; no immediate data or
zero-cost boundary is assumed. Same-address behavior does not authorize
installation while prefetch/execution is active: the MODEL faults that phase.

The39 padded incoming PW records cannot be written directly as39 SRAM rows.
The executable bitpacker installs1742 useful bits into28 rows, explicitly zeros
unused tail bits/rows, uses a maximum three64-bit FIFO words,128-bit partial
assembly,63-bit carry and registered write boundary. Relative to PW400 sample0,
PW438 is sample38; first native write is4, final write42, seal publication43,
and first sealed consumer sample44. Complete physical-copy authentication is
an additional requirement; it is not replaced by that local seal.

Record start offsets are0,6,...,60,2,8 modulo64. The record starting at bit60
crosses four SRAM rows; the others cross three. This costs40 native read slots
for13 groups/context and160 for four contexts, without row reuse. The model
prices a registered request, native read, external capture and256-bit shared
assembly. A worst four-read record is usable at request+6. It reserves two134-bit
active-template slots/context, tags, seen masks, generation, stage and clocks.
The SRAM option includes505 loader FF,1355 active/cache/control FF and325
prefetch FF. The FF option includes1742 template FF,157 loader FF,1355 active
FF and34 prefetch FF. Conservative resettable control loads are410 and346;
data arrays are unreset and remain inaccessible until their validity guards.
All FF clock pins are counted; no clock gating is assumed.

A four-context simultaneous-origin storage stress has one read port, fixed
four-slot service reservations per context,20-source-edge lookahead and at
least2-edge slack. It needs at most two active/prefetch slots per context. These
are runtime unit-phase source offsets; they are separate from installation's
sample0 and do not establish an absolute production clock. Simultaneous source
commands would collide on a single calendar output, so this is strictly a
storage-service stress, not full-MU execution admissibility. A new B4 source
calendar or physical landing assignment must regenerate the deadlines.

Eleven executable MODEL mutants reject installation/prefetch phase overlap,
write-during-execution, missing or undrained records, duplicate/out-of-order PW,
header mutation, wrong profile digest and incomplete physical-copy auth.
Storage RTL guards remain unimplemented. Native macro geometry31.968×17.28um
is source-qualified only; pin escape/PG/GRT/DRC and TT/FF clock/route are open.

The concrete model, packed rows, per-request service ledger and source hashes
are in witness/witness_storage. Native reproduction is native32_port.sh after
extracting the exact b657 source to run/native32_source.v. The public PW,
calendar1009, INIT800,88-read loader,103 caller window and all footers are unchanged.

The updated WTN1 PW packet has now passed the actual calendar-copy receiver
with the unchanged native binary: commit1044/digest198f7708b478a667, firstBOOT
CMD1050. The earlier400-useful-PW test already transmitted all1024 PW words
(including zero400..975), then8DW. New useful words410..448 replace those zeros;
they add zero transfer edges to that full ascending image. The sidecar MODEL
native writes finish452/seal453/usable454, before finalDW1034..1041 and calcopy
commit1044. These sidecar sink times remain MODEL values; actual sidecar seal,
other ME/XPF copy authentication and production L/player startup stay unbound.
The fresh calcopy receipt preserves that distinction.
