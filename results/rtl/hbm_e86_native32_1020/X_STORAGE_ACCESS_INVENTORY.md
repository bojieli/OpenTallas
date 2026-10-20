# Actual e86 X state access inventory

Parameters EW86/PT64/GP8/NP68/PRE1/CREP1/FAN32=1; hardened synthesis top
`ot_hgi_coll_tkm_tile_e86`. Source hardware4aa724d4e; opt-in parent propagation
b0217eb74 changes default0 plumbing only. Logical X capacity64x86=5504bits.

| Active access | Actual elaborated positions | Role |
|---|---|---|
| SX[g]=X[g] | g0..63, constant generate index; g64..67 zero | 64 simultaneous comparator keys/data candidates |
| position key compare | X[g][85:1], g0..63 against four registered block keys | 256 parallel85-bit compare operands; tail4 comparator inputs are zero |
| insertion candidates | SX[d-k], d0..67/k0..4, constant d/k elaboration | bounded five-candidate local selection, no address port |
| shift | X[p+4], p0..59 | constant four-position neighbor; p60..63 use raw up_in capture |
| feedback | X[p], p0..63 | local enabled register hold |
| convey output | X[4+s], s0..3 | four fixed neighbor words into registered up_out |
| generic tau probe | X[p_tl%64] | absent from hardened top: wrapper ties tau controls0, tau_o unused |
| CREP0 updater | generic indexed expressions inside inactive generate | absent because CREP1 |

All active X reads and writes in the actual top resolve to constant generated
positions. X is a parallel comparator/shift compute state, rather than a
runtime-addressed RAM or a queued delay-line payload. Each edge can compare all
64 keys, update every position by local insertion/shift, and publish the fixed
four-word neighbor. A single-address SRAM replacement cannot implement this
parallel access contract; a proposed SRAM architecture would need explicit
ports/replication/reach/schedule pricing. This source-role classification does
not waive the storage policy or establish a physical pass.

The V1 actual mapped netlist (SHA pinned in v1_rejected/native_mapped_summary)
contains no tau_o/p_tl/p_tid identifiers. The final V2b mapped graph must repeat
that check; source pruning alone does not establish a final mapped receipt.
The duplicated p_bg/q_bg/compare capture and gt/control arrays are independently
kept per-region parallel operand/control state with constant generated indices;
they add capture/area/routing load and need measured area and complete regional
ownership. They are not extra retained top-k entries: sorted capacity stays64.

No layout gate, native32, SS/FF setup/hold, legal regional phase, complete
floorplan or token-rate claim follows from this access inventory.
