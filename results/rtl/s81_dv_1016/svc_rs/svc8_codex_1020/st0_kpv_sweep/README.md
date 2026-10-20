# ST0 LP stationary drain sweep — collected 2026-10-20 07:24 PDT

Original job unit3016016-1792497666 on ep9 completed exit0. Exact SOLP0 release libraries and source are reused read-only; only top-level KPV changes. Top commands and reused input SHA256 manifest are preserved. Each setting runs tail46 with seeds1/2.

| KPV | SO | Full SVCRS | P.V errors per seed |
|---|---|---|---|
|64|PASS both|FAIL both|16|
|66|PASS both|PASS both|0|
|68|PASS both|PASS both|0|
|70|PASS both|PASS both|0|

No constant is adopted. KPV65 is untested, so the minimum is bracketed 65..66. Full300/1m/skew cases and compiler price remain pending before an implementation change. Simulator process RC0 alone does not imply a PASS: the explicit SVCRS verdict controls the result.
