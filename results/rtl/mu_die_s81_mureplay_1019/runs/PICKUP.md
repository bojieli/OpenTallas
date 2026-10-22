# Eight-leg terminal cut-7 replay

Original chain PID 2187128 completed 11:44 PT. All simulator benches PASS; strict SU L0 FAIL 1324, SU L2 FAIL 2628; all three nominal MU checks FAIL. Original mutant checks also FAIL, but baseline failure prevents qualification. Full run paths and source/replay hashes are in pickup_manifest.json; original source/objects and traces remain preserved. No new simulation or checker change.

All SU discrepancies are unscheduled changes on four elastic lt_lk_EN0/EN1/ES0/ES1 lanes: 331 each for L0, 657 each for L2. No expected output words were missed: these replays encode zero output checks, while 28 L0 off-die RD events are excluded from fixed-cycle encoding. Every other listed output lane passes strict check. This localizes an observation/coverage mismatch; it does not prove arithmetic correctness.

MU user0 stimulus and every observed output match SU exactly. Later-user held-value comparisons differ on ports236–239, the same four link lanes; shifted comparisons include initialization/held payload traffic without a typed valid/protocol filter. Do not waive these lanes or relabel PASS. Next executable is collect already-running HOP endpoint-lowered replay and endpoint checks; complete typed protocol/identity/calendar expectations before any rerun.

HOP original clients4150465/4150466 and chain449774 remain live on ot-epyc7. Both large C++ builds finished; base simulation started12:26, RTL-tagdrop12:35, traces growing12:37. Preserve exact objects and sources; no duplicate.
