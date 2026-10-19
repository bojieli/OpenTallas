The live 128-row seam passes on Verilator 5.050: all 128 actual ROM logits,
token 21946 / 4173a558, owner47 and sequence64. SU and three sequential users
have the same measured 8416-edge go-to-return latency at fixed 9000-edge slots.
Sequences differ by 256, so the full sequence must survive despite equal low8.
Actual ten ROM4096x274 memories produce every logit; expected logits feed only
the checker. No expected roots or logits enter the RTL datapath.

Corrupted public stream, wrong returned owner, and one-edge late return all
fail. The last two mutants deliberately corrupt/delay the observed return
wires in the bench; these prove the endpoint checker detects identity/age
errors, not that a physical link or the RTL itself detects all such faults.
All failure logs are preserved. The return adds one actual capture edge;
8416 is a measured candidate component contract, not an adopted compiler price.
The source composes the public logit pins directly with the existing
explicit-ID argmax. It avoids replaying separately computed roots and avoids
performing the padded-tree join twice.

This is not a full SU or production multi-user token pass. The normalized input
is an explicit HEAD fixture boundary. Three sequential owners do not demonstrate
46-user AR or 10-user MTP occupancy. The older actual HC -> mapped head -> TP4
receipt covers 129280 rows, but uses files between independently simulated
components and random terminal gaps; its 36985 terminal cycles cannot establish
an end-to-end fixed compiler contract. Original retired-host data is not known
migrated; immutable receipts remain on main.

Next source-native integration: connect the existing actual production final
HCP/norm/VM output to this native bundle input through its actual static read
schedule; prove exact G+5+m arrival without a fixture replacing those producers.
Use the existing actual head parameter/gain ROM port job where applicable.
The present compute-die GEN inventory does not yet contain a head-die top, so
first establish the actual producer owner, root/clock/reset and legal lifetime
contract; do not create a numerical placeholder or invent a physical slot.
Then extend the live terminal to all physically parallel full-shape groups,
carry owner/sequence through the real TP4 link and measured token return, and
bind exact latency into the actual head compiler. Draft body/Markov/seed
ownership, IDX/helper query fanout/tree/HBM/slots, and non-head layer GAPs remain
independent requirements before any fulltoken run.

producer_inventory.json snapshots exact current HOP programme lowerings and
all unclosed operations with source hashes. L0:9 GAP/33 PARTIAL; L14:36/38;
L20:29/37 (same for the saved SU and MU variants). These programmes do not
represent a complete layer. The pre-existing HOP endpoint jobs4150465/6 and
chain449774 remain live and must be collected, not duplicated. Base L0 users012
must pass epcheck+strict; missing/wrongcopy/RTL tagdrop must fail.

Physical: no route, native setup/hold, clock/reset fanout, finite-storage safety,
area or legal die slot is claimed for the new composition. Existing research
ROM models are preserved unchanged. Physical admission needs the full SAFE
checklist and ROOT critical PNG review before any gate/submission.
