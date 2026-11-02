# Native PG cell-birth mechanism

Pinned runtime: ORFS image `16470cea1d346bfa245e402108995a4f04a1e54fe7c7bb7441774d7f6a2ece29`,
OpenROAD `26Q3-1510-g6cb3f2b704`, executable SHA `21eda99e...`.
Owned fleet directory: EPYC2 `/srv/opentallas-scratch2/claude/codex-pg-birth-0045`.
No source kit or progressing job was modified.

Two native resizer workloads on isolated copies of the reviewed PG0 Tnode235
input establish the factory behavior:

| Workload | Native creations / swaps | Control PG opens | Callback PG opens | Native terms |
|---|---:|---:|---:|---:|
| TT `repair_design`, fanout8 / max-wire20 mechanism stimulus | 5,786 / 19 | 11,572 | 0 | 39,054 |
| FF routed-RC `repair_timing -hold`, margin10 | 1,719 / 0 | 3,438 | 0 | 30,920 |

Each workload's control/callback pair has byte-identical functional connectivity,
instance masters/locations/orientations/status/protection/source flags, net flags,
DATA/CLOCK wire opcodes and guides, and BTerm geometry. Independent fresh native
reads of saved callback ODBs pass with zero PG failures. The explicit strict-v1
adapter repeats the first native workload with the same final guards and PG0.
No late `global_connect` is used to achieve these positive results.

Seven native negatives reject ambiguous supplies, regional rules, a supply rule
on a signal pin, an existing wrong-domain cell, protected unbound cells, a new
unknown PG pin, and a master swap with a wrong PG role. Existing-state guards
are unchanged; the rejected new-master case is cleaned only after uninstalling
the hook, with no analysis of the rejected design. Strict-v1 also rejects a fake
Tcl capability, an inactive hook, an unvalidated CTS command and a DB reload;
error cleanup leaves the callback inactive and the original DB unchanged.

The exact pinned source makes `dbInst::create` invoke its native callback after
all ITerms and the instance region are established, before returning. `swapMaster`
has Before/After hooks before returning. The inspected EST callbacks only
invalidate parasitics; they do not estimate RC. This closes the target design's
native birth path rather than wrapping a Tcl command's return.

Runtime observations (one pair, not a general benchmark): design repair
14.74s control / 15.64s callback; FF hold18.06s / 44.57s. Peak memory remained
under556MB. The extra native notification work is real; no free-overhead claim.

Failures retained in the owned fleet directory: two missing-header compile
preparations, an initial overbroad disconnect guard blocking legal deletion,
a dynamic toy-master negative that lacked STA registration and SIG11ed before
the PG callback (replaced by a real loaded unused master), and a multi-read DB
reader refused by ORD-0047 (fixed to separate native readers). No target timing,
route, or hardware verdict was inferred from these harness failures.

No global module deployment, full GRT/MM production canary, CTS/GPL admission,
source EQ, routed target qualification or SIGNED view is claimed. The default-off
adapter and ABI-pinned module are ready for a reviewed owned ordinary-flow canary.
The original failed/unbound snapshots remain intact.
