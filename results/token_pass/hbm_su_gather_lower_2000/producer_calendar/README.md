# Source receipt calendar composition

The composer loads a hashed JSON authority for every native producer, allocation and control transport. Each receipt must carry status PASS, producer_kind, source_sha256, die_sha256 and clock_epoch_identity. Producer receipts additionally carry first_word, word_count, ready_edge and release_edge. Output allocations carry free_edge and release_edge. Control receipts carry configuration_start, calendar_epoch, launch_to_calendar_zero, ownership_release_tail and the actual endpoint parameters. All dates refer to the same selected stream epoch.

Requests contain the actual descriptor and earliest model issue only after physical producer placements are bound. The checked partial requests here contain logical descriptors because no current source placement/launch receipt is admitted. The builder returns before using them, retains null job dates, and lists the exact missing source authorities. It never uses fixture outputs, injected far ends or a component check edge as a producer date.

IDXSU owns the selected IDX native output and gather endpoint source proof; COLL owns the real GSC producer and four native run commits; chain owns final physical route ages. Their active work has no admitted absolute ready/retention dates yet. The diagnostic graph and source identities are recorded separately from an admitted die binding.
