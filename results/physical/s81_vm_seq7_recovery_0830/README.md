The recovered sequencer now retires each command seven stream edges after its pin edge. Command throughput remains one per edge; VM read latency remains sixteen stream edges. Compiler issuer calendars and whole-token cost still require adoption and measurement.

Claude's six dirty files were recovered without modifying the originals. Actual synthesis showed that all sixteen unconditional local state copies collapsed into one copy, including a diagnostic with keep/dont_touch attributes. The final source updates each group copy only when that group's observations advance into the next stage. A valid observation therefore sees the same state sample, while inactive groups may retain different values and remain distinct hardware.

Actual synthesis retains 12,400 FF bits, matching the model. The unprotected revision retained 8,920. All 3,712 group state bits are distinct; the largest generic load count on a low-bound bit falls from 68 to 8. These are generic synthesis measurements, not library area or timing results.

The four-state component gate passed three dense 1,500-job seeds, six fault cases, and rejection of four actual DUT mutants. The actual VM composition, using 128 physically mapped SRAM functional models at READ_PIPE=4 and CAP_PIPE=2, passed two seeds, eight fault cases, and rejection of three DUT mutants. Source manifests and complete logs are adjacent.

Native CTS is still running. The old sequencer view is not inherited. No die placement, related-clock delivery, issuer programme or full-token qualification is claimed. The source model is available through tools/uarch_model.py: dsrom_vm_seq_local_observation_model().
