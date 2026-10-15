# Native PV256 finalization component evidence

Frozen RTL source `620bb5628` ran under ot-run on ot-agidock128, unit
`207925-1791954523`, terminal exit 0. The source archive digest is retained in
`source.sha256`; vector hashes and their exact scope are in `vectors.log`.

Both steady and changing-backpressure runs produced one batch of 512 FP32 words,
all bit exact, in 121 observed cycles. Pair-data and reciprocal-data mutants
produced 1 and 128 actual wrong words respectively. Wrong pair epoch, wrong
reciprocal epoch, and restart during an active frame caused observed faults.

The inputs are actual RTL PV pair tree outputs, with canonical golden reciprocal
values supplied by the component fixture. This is a finalizer component proof.
It does not prove a joined QK/Z/PV attention service, whole-layer execution,
physical closure, or production throughput. Separate native phase evidence
proves actual reciprocal values for the same canonical operands; direct pipeline
integration remains a separate gate.

The earlier source `49e2b0aad` produced two output batches when ready changed.
The original receipts are preserved in sibling `finalize_failed_49e2`. Source
`620bb5628` retires outputs on the actual ready/valid handshake, and the changing
ready case now produces exactly one batch.
