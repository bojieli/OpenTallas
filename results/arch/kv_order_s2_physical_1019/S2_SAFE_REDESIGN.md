# S2 physical precursor audit

Actual source-bound fleet synthesis has 17,501 register outputs, six real SRAMs, and 11,967.97842 um² of standard cells. The proposed 302.4 × 259.2 outline gives 61.1% in its documented full-width north band, above the 40–60% requirement. Neither the arithmetic estimate nor the old floorplan is a placed-band proof.

The candidate is rejected for SAFE CTS: 64 register outputs exceed 32 loads. RAW bypass flags drive 580/566 loads; issue-PC fields drive 263–268; map head fields drive 116–233; front indices drive 39–88; final reset copies drive 237, and their first-stage driver drives 36. Exact names and examples are in mapped_census.json. Correct the architecture before a new gate; adding ordinary buffers does not satisfy kept registered-copy requirements.

The actual canonical 32x128_p192 LEF is legal: 199 west / 198 east signal pins over 39.96 um; full-face 4.980/4.955 and active-span about 5.23 pins/um. No cosmetic LEF change or bank split is needed for this primitive. This is a pin-density census, not a routed access proof.

A model-only footprint candidate is 302.4 × 267.84 um with unchanged six macro origins and a full-width band y=194.4..267.84. Measured precursor standard cells use 53.89%; reserving another 1,000 um² for structural copies/repair gives 58.39%. Its 403.96 um diagonal is below 405. Area is +3.333% against the precursor and external functional edges must remain unchanged. The model must be refreshed from the actual redesigned synthesis. Parent placement, all actual register reaches, real row/region and placed cell occupancy, clock root position, TT setup/FF hold, and native pin spread remain open.

Reset requires a true balanced two-stage copy structure. The inherited API only replicates the final stage, permits at most 64 copies, and has max_loads=256. Changing that number alone cannot produce ~32-load first AND final stages. Keep both registered landing edges and prove asynchronous assertion/release and exact copies; do not add an unpriced reset edge.

The original sizing job source is frozen. Its local client disappeared, but remote floorplan repair continues at the recorded path. The obsolete local receipt is a historical sparse-input refusal; it is not the actual result. All S1 order, guard, and prompt writers were untouched. Quiet182 is unadopted and no quiet RTL changed. No REVIEW, submit, CLOSED, or performance adoption is authorized by this audit.
