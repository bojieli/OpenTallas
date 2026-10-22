# GEN safety coverage metadata review

Source c96ac5c89 cherry-picked as77b1e408c. Main base c6f137b4c. This adds explicit C1/C2/W1/W2 coverage and scoped/full labels without changing PASS/FAIL or exit behavior. A reach-only HBM summary cannot claim crossing/root/channel coverage; diagnostics stay ineligible. The eligibility flag denotes GEN safety preconditions only; source-bound facts and native/clock/route/IR signoff still required.

Unpinned fleet ep6 unit2175456-1792562586 exit0, full paired die_safety suite: baseline22PASS, candidate28PASS, zero failures. This includes the two S81 source-import cases omitted by the proposer's sparse run; exact main tools/common_flow/memory-model fixtures were supplied identically to both sides. No live frozen chain or closure daemon helper changed.
