PREPARED ONLY — no job submitted, old running gates unchanged.

These specs follow packaging commit 91291fd6f without modifying it. Both use the
same physical source/geometry/clocks as 206a3037e, with the gate-only successor
commit d108b33de on codex/w2-gate-acceptance-20261006. Calibration uses its own
_cal directory and --pnr-stop-after cts. The standalone S3 stage expects the
specific NEGATIVE_REJECTED marker and verifies compile_exit=0, runtime_exit=1,
outcome=REJECTED, failed=true in terminal.json. Compile errors, missing tools,
timeouts, killed simulators and unrelated assertions cannot satisfy this stage.
The full gate independently requires evidence-qualified rejection for each mutant.

Source commit d108b33de changes only tools/w2_station_rb_gate.py and its tests.
Hardware, clocks, uncertainty and numerical checks remain unchanged. Latency
added to RTL: zero. Evidence: results/rtl/w2_gate_acceptance_20261006/.

S8 contract: after tap_v[0] && q_r accepts the publication, all eight ready-high
SM consumers must accept the exact frame/data/owner. The fixture bounds this at
4 stations * (2 protected-bank update allowances * 40 edges + 8 link edges) =
352 edges. The 40-edge allowance is the existing tb_w2_bank_veto REPAIR_EDGES;
the two protected updates are payload and permission. This conservative fixture
progress bound is NOT a claim of system service latency. There is no corruption
injection before all SM accepts. Changed readiness is a distinct environment
assertion and cannot satisfy S8's rejection. Positive measured progress: 80 edges;
S8 forces rel_q high, accepts only mask 03, and fails explicitly at edge bound352.

Next action: parent review/integrate source and evidence, publish the pinned
source branch, wait for both old 206a jobs to be terminal, then submit ONLY via
the closure loop/admission after checking current reservations. No manual route,
no cancellation, no duplicate suite or route, no direct main merge. Specs are
outside watched jobs directories; merge_target=null. The full fixed-gate campaign
has NOT run; only focused positive/S8/build-failure/S3 checks have run locally.

Validation uses the existing closure-loop validator (reserved tooling unchanged):
 python3 /home/ubuntu/wt-codex-hbm-harvest-20261006/tools/closure_loop/closure_loop.py validate physical/hbm_w2_safe_gate_successor_20261006/no2.json
 python3 /home/ubuntu/wt-codex-hbm-harvest-20261006/tools/closure_loop/closure_loop.py validate physical/hbm_w2_safe_gate_successor_20261006/no3.json
 python3 tests/test_w2_station_rb_gate_acceptance.py -v
