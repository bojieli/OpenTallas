# Selected parent boundary recorder (PREP)

Optional signoff flags `--parent-boundary-instance EXACT_HIST_INSTANCE` (repeatable)
and `--retain-child-clock-witness` retain each native register-startpoint data
relation before the existing clock-reference pair deduplication. The target
master is exactly `ot_s81ph_native_sel_hist_bank`. Default STD query budget is
zero: clock-reference relations do not assert data slack or hierarchy coverage.

An explicit `--parent-boundary-std-query-limit N` additionally queries the two
native max/min checks for each selected data relation inside the original
constrained STD session, before `ot_ps_zero_unc`. It copies exact source output,
capture input, separate setup/hold clock roles, actual clock/source/edge tags,
source-specific pin arrivals and native engine slack. It preserves native CPPR
state and grants no additional clock/CPPR credit. No global path coupon, reroute,
new process or constraint change is introduced.

NO_PATH, ERROR, LIMIT, missing targets or incomplete requested sets fail the
optional retained payload clearly. Native signoff verdicts remain independent.
The final payload requires exact setup and hold coverage of all retained data
relations and hashes the observer/session/native input artifacts. Existing
sidecar export copying preserves the new files. Hierarchical expansion remains
NOT_ASSERTED and requires the separate qualified child graph and actual parent
composition.

Targeted Python/Tcl checks exercise two macro output bits collapsing to one old
clock pair, actual multi-source clock tag selection, native slack versus absent
path, budget/error states, insertion before uncertainty mutation, and exact
payload/clock-role validation. This is source PREP; no actual histogram parent
STA was run. Actual parent placement LOOK is required before normal timing.
