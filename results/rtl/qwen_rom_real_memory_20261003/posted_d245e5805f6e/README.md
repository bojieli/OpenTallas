# Posted KV writes: measured runtime prefix

`POSTED_KV` defaults to zero. When enabled, an ordinary SU issue may proceed
without waiting for HBM write-done. SU idle, every barrier/END drain, and the
existing transaction tag, generation, address and context checks are retained.
The host checks actual write-drained and KV-ready at stage END before dumping
memory or reusing the layer context. The bridge still costs 425 cycles per layer.

The analytical model was priced before the build. The measured source is
`d245e5805f6efde99cd9d41288cc54f757b9220c`; all 47 measured source pins match
the integration source. Parent model changes are preserved. The original frozen
baseline records remain unchanged and are referenced by hash in
`qualification.json`. No baseline or golden generation was rerun.

Actual scope is embedding plus L0-L2, TP4, one position per run, using the same
stage images, populated KV history and exact oracle as the corresponding
REAL_MEM baseline. Raw result JSON and full simulator logs are preserved here.
`qualification.json` records all terminal cycle counts, input/source matching,
per-stage changes, prefix rate gains and the final verdict. `collected/summary.json`
includes the per-die memory and stall counters.

P0 takes 14,683 versus 16,152 cycles (+10.0048% prefix rate). P255 takes 15,881
versus 16,206 (+2.0465%). Ordinary write-drain stalls become zero, while fill
stalls change: P255 L1 takes 66 more cycles despite the 325-cycle prefix saving.
Treat removed drain counters as opportunities, not additive latency savings.

The candidate remains default-off and unadopted. Full-token mixed-clock
composition, contextual SS/FF and hub routing remain unqualified. These runs
do not qualify multiple-position overlap or rollback execution; retained fences
must be used by those integrations. Near-HBM is excluded pending its exact verdict.
