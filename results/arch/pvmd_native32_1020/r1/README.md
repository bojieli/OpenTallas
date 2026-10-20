# R1 caller proof and mandatory census failure

Frozen source38d6aa515 imports the reviewed distributed PVM source on MAIN8608,
with the approved shared wrapper ea1b1aa64 (local cherry f9f397fe9). FAN32=0
remains the original source; FAN32=1 chooses LAT7/DRST0/CUTS=-1, zero new edges.
No old shared adder file changed. Model identity is checked by the shared helper.

Caller qualification is separate from component SAT/coupons: these production
benches compose real PVM RTL with the exact couponed native cell model for the
16 selected adders. The default-off campaign uses the original pure RTL adder.
Both compare valid/fault every edge and payload when valid under random init;
the independent fixed-order golden checks every valid FP32 merge/publication.
No full-caller SAT or unsupported parameter qualification is claimed.

Default-off and native-on with tight fold, in-flight reset and random initial
state both PASS192 golden payload checks /597 every-edge comparisons. Native
STOPCLOCK reset campaign PASS192/598; causal MUT10 synchronously resets a second
reset node, and fails the stopped-clock assertion at68ns. Fold MUT4 fails valid
payload/age comparison at499ns and golden reports64 mismatches. The first
MUT10 REASSERT1 run PASSED because the clock kept running: that undercoverage
receipt is preserved and is not counted as a caught mutant.

Actual full-caller mandatory042aa171b census FAIL:21 COMBINATIONAL roots,
maximum1056, zero role errors and no FF violations. It reads actual fiveTT cell
Liberties plus the real SRAM Liberty, all hashes in native_summary.json. The
component's old160 overlimit FF roots are gone, but that alone never admitted
the caller. Native32/complete map/source-frontier trace are compressed here.

The1056-load root is the global finish predicate for wide result capture.
The other20 roots are shared barrel decodes/state-read D-input predicates,
including the64 kept q-state copies. R2 changes source control provenance and
finish predicates, preserving edges and reset semantics; R1 is never gated.
