This packet describes an unadopted clock/reset mapping for HC source candidate
5bdf1a9c5 and profile 2138daccb. It preserves N017b32285 and launches no jobs.
Run `build_mapping.py CURRENT_SOURCE_BOUND_CONTRACT` to reproduce the JSON.

The source-bound interface delta f96d23c9b proves that all 79 existing hub ports
keep their widths and directions. Existing face-output edges stay unchanged.
Only input `clk_t[3:0]` is added to each of four hubs. The mapping copies the
existing real stream PLL source and reset source from each hub's contract;
it adds no clock domain, PLL output, target, reset port, or logical clock alias.
The existing generator gives each of the 20 literal clock entries its own
physical delivery branch and retains conservative entry-pair checks.

For each of the four child entries, the binding is to the actual
`u_cen.g_hard.g_qt[c].u_t/clk` of master `ot_hbm_hc_qtree16_static`.
The TT values 186.6/194.5/199.6 ps and FF values 152.7/160.9/166.5 ps are
respectively the measured boundary minimum/mean/maximum for this child master.
They are not three individual entry values. All four copies bind the complete
envelope; parent entry-wire delay and glue CTS insertion remain to be measured.
The raw child insertion snapshot and exact origin/main commit are retained.
The tree top-file SHA256 matches frozen e91f9005e; this comparison does not
qualify the full transitive source set of the new parent candidate.
The old failed C6 parent kit supplies an ABI/reset reference, not a qualified
phase-40 parent view or physical pin location.

The existing `rst_n` remains in the stream reset graph. The reference parent
lands it in two `clk` stages, then the kept local relay delivers separate hard
tree resets. The child has its own landing and regional relay. No universal
startup age, stopped-clock assertion guarantee, or physical reset proof is
inferred from this source description. Actual per-region delivery is open.

SAFE2/P40 source, parameters, programme/calendar, native census and physical
qualification are HC-owned prerequisites for adoption. Current helper scope is
one position of rank0 k31 HC_MIX_POST only; multi-position programme is not
generated or qualified. No current die source or phase-23 view is relabelled.
