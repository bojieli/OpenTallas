ROMQ direct parent composition preparation
========================================

The old 536.76 x 221.4 ROMQ footprint is exactly two 268.38 x 221.4
halves. A wrapper at that outline has zero cell rows. Adding 8.64 um to
both dimensions still leaves zero usable rows after the native 4.32 um
core inset; row halo reduces space further. Larger private proposals
also collide with enclosing COL contents and existing capture bands.

`romq_parent_adapter.py` prepares an alternative: retain both half
footprints in the original union, and emit the existing registered shell
as ordinary logic in the enclosing COL parent. This tool is explicitly
invoked and has no generator, binder, plan or compiler call site.

The input is an immutable native bound type source and its captured
instance contracts. Source hash, unique instance, exact named overrides,
NB=2 and the accepted half parameter family are checked before edits.
Only the selected master/override text changes. All connections,
nonselected siblings, parent parameter declarations and INSTANCE
expressions remain unchanged, including quoted literals and symbolic
per-partition overrides. NB is removed only after its explicit seal2.
IOREG/OUTPUT_NEG/OLAT/IFN are selected1; the existing shell charges +2
interface cycles and +1 child-reset edge. The shell/split source must be
included before fixed-child assembly. Fixed child sealing is separate.

A read-only current `col_h10_r0_p4__t1` source trial adapted all four
selected ROMQ calls and retained their P_u_r0_u_e*_INSTANCE references.
Four focused tests cover identity/connection/sibling preservation,
foreign half parameters, source/instance drift and duplicate overrides.
The unchanged shell capability has its existing whole-word/reset-age
proof and mutants; this textual adapter adds no RTL implementation.

The output receipt says PREPARATION_ONLY. Activation still needs signed
same-flow half views, an actual COL capture/clock/buffer row budget,
post-frontend capture identity/reach (including reset/status/epoch), PG
and clock endpoint handoff, an explicit plan/compiler +2/+1 event, and
normal native final signoff plus routed equivalence. No physical fit or
parent qualification follows from a successful source preparation.
