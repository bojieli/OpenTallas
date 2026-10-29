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

Final source results: full production lockstep PASS 8079 cycles / 1018 selected
beats / 0 mismatches. A full-shape all-equal-key/k64 boundary frame also PASSes
1367 cycles / 171 beats / 0 mismatches. The threshold mutant is caught on that
frame (311 mismatches); the op8-fault mutant is caught by the reset/op8 test.
The original random-only threshold mutant survived because its stimulus did not
oversubscribe boundary ties; that receipt remains explicitly SURVIVED.

The first full run failed only on three reset-only cycles: the legacy/default
core left selected_line valid bits X while the bounded logic produced zero,
with selected_v=0 and fault=0 throughout. The startup triad reproduces this.
The final bench compares valid/fault on every edge, requires zero valid during
the existing two reset-release plus one output-pin startup edges, and compares
every payload bit from edge3 onward, including invalid mission beats. No design
cycle or mission comparison is removed.

summary.json and receipts/ contain the final results and surviving-control
diagnosis. recipe_struct.json is a concrete opt-in proposal for the existing
master, using STRUCT=1 and source-pinned helper files. It has not changed the
canonical recipe or running k11 job. Source gating does not claim timing,
mapped-cell fit, physical sign-off or die release.

The first STRUCT1 kit face-shell analysis completed, but a two-second live CPU
sample located its hour-long delay in ProcDffPass: repeated signal sorting and
extraction inside the large per-quadrant histogram process. The follow-on
process split keeps STRUCT0 unchanged and moves each STRUCT1 bin's predicate
mask into a combinational process and its 14-bit histogram into a separate
clocked process. All 3584 histogram bits, twelve SRAMs, clocks, ports and edge
priorities remain the same. In particular, simultaneous histogram clear and
read-return accumulation still accumulates from the OLD histogram value.

The split source passes the full production lockstep (8079 cycles, 1018 beats,
zero mismatches), the 1367-cycle/171-beat equal-key frame, and catches both the
threshold and op8-fault controls. An arbitrary 16-hit histogram-bin transition
proves equivalent; a clear-wins priority mutant is caught with op3 plus a
simultaneous op4 read return. Receipts are in procsplit_receipts/. Frontend
coupon and live sampling reports are in frontend_coupon/; the tiny coupon
only demonstrates eager default-parameter elaboration, not the actual delay.
There is no measured process-split frontend speedup or new kit/physical claim.
