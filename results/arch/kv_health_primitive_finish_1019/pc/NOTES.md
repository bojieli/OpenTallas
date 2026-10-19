Selected GEN7 PC controller and return source expansion

Source revision 4db097403 and die SHA 18464a8b31042bea03b3fc5779d42803ab7b05bebbaab733a4d83d4a714c1ea6. Read-only analysis; no RTL edits, simulation, synthesis or gate. The 128 selected wrappers bind all controller HBM child clocks to hck and all core children to ck. Source snapshots are immutable SHA256-pinned in source_manifest.json.

primitive_inventory.json expands 20 sticky detector registers plus one valid-qualified embedding SECDED UE channel per PC. Aggregate fo, registered er_f, completion synchronizer fs, and return fault pin exports are propagation state and must not be added as independent causes. The existing four chain/ES detector rows per PC remain separate; this packet does not duplicate them.

er[260] is core er_f, a registered OR of native_intake_fault and embedding down-FIFO pulse rejection. er[258] is the separate return payload UE channel from actual PCport SECDED decode through the HBM-to-core up FIFO. Neither is a new detector at the er bus. PCport UE is not the KV landing ECC sticky detector: the PCport class FIFO selects embedding vs KV returns; KV uses its own PIPE2 landing ECC detector.

Old return exports each have an internal sticky *_s detector, and a plain synchronous-reset output flop loaded with sticky OR same-edge predicate. Counting export and *_s twice is incorrect. Publication/consumption use two-stage domain synchronizers; 288-bit bank data are fixed slices on four delivered HBM clocks. Actual phases, resets, collision exclusion and physical exposure remain unqualified.

The selected generic FIFO wr_overflow/rd_underflow outputs are reset to zero and never set. Completion fault originates in real u_static_commit.hf on pulse rejection; fs is two core edges of synchronization. The generic FIFO outputs add no separate primitive here.
