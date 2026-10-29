The actual selected-only die master is the serial source pinned at d34578d6f,
not the later pipelined selector. Its active k11 synthesis spends over 55 minutes
in EXTRACT_FA at about 18.5 GB RSS. The original job is preserved.

Two structures create unnecessarily large arithmetic/mux graphs:

* Each quadrant serially performs sixteen variable writes into a 1184-bit
  buffer, with `fill_next*37` as its index.
* Each of 64 histogram bins sums sixteen booleans using a 32-bit integer chain.

The opt-in STRUCT=1 candidate preserves the same master, ports, twelve SRAMs,
state registers and clock edges. It generates a bounded tie-prefix selection
mask, reuses the existing stable compaction tree at N=16/EW=37, and appends with
one bounded buffer barrel network. Unwritten/stale buffer words are preserved,
including out-of-range writes. A balanced five-bit population count replaces
the histogram integer chain. STRUCT defaults to zero; no recipe adopts it yet.

Before-build feasibility estimate (not a mapped-cell or timing claim): a naive
serial compaction graph has sixteen 1184-bit indexed-write mux networks per
quadrant. The candidate uses four bounded merge levels and one 1184-bit append
network. For the histogram, summing sixteen 32-bit quantities costs at most
512 adder bit positions per bin before optimization; the bounded 2/3/4/5-bit
tree uses 41. There is no added storage, clock load or scheduled cycle. Existing
floorplan and SRAM-escape work remains valid in outline/ABI, but a generated
candidate kit will require a fresh placement review because its logic changes.

The smallest mechanism proof uses four actual 37-bit records, arbitrary keys,
tie budgets, fill positions and stale buffer contents. Normal behavior and the
existing MUT=1 behavior both prove equivalent to the serial reference; comparing
the MUT=1 candidate against the normal serial reference fails as expected.
The full sixteen-input histogram arithmetic is independently proved for every
input pattern. These are mechanism proofs, not full-source LEC or sign-off.

The existing production selected-only bench is used for cycle lockstep against
the pinned canonical selector: three production frames, 4000 random legal ops,
fresh-reset op8 fault test, and threshold/op8-fault negative controls. The
candidate keeps procedural-if behavior for unknown SRAM predicates so reads of
uninitialised slots do not consume a tie or histogram count.

Jobs and results: intel1:/srv/opentallas-scratch2/claude/codex-selector-1028.
The first ORFS-image sim attempt failed because iverilog is absent from that
image; the corrected run uses installed host iverilog through ot-run. No source
or timing gate was waived.
