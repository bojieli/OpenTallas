Selected HBM clock-enable source and physical face contract

Source driver: tools/hbm_b2/sk_ce_kit.py. Pass the ordinary gen_core_kit_hbm
arguments plus explicit --recipe-key MODULE --ce-shell-contract land1-cap3.
Native-trial is an explicit diagnostic choice and must never route.
The selected physical recipe keeps EN_LAND=1; step0 adds2 registered enable
edges after steady, and tail-rest CAP=299. No clock waveform, period or
arithmetic changes. The tail is508 external core edges: native503 plus2
external shell edges plus3 capture-calendar edges. Both tail-rest native cut
interfaces have separate plan wrappers. All4 current canonical c1 views generate
with no input drops or output constants/duplicates. Source wrappers must still
pass native bind and physical sign-off before release.

Mechanism: steady.load=in_ready&&in_valid is a narrow pulse. Output+input face
registers delay it2 edges. Same-phase step0 misses it. The selected2-edge local
enable phase catches that pulse; all other step0 controls and returns still fit
within the7-edge state cadence. Returning out_valid also crosses2 face stages,
so the rest capture calendar grows3 edges. Capturing later without the local
phase fix fails. Removing the native landing register advances steady onto the
input-face update edge and misses the first accept slot; that alternative is
rejected, not tuned.

Native split lockstep:40 results/21263 core edges/0 errors; early-enable mutant
caught20763 errors. Physical selected shell mechanism:40 results/21263 edges/0
errors. Identical capture calendar with phase0 fails20759; LAND0 lower-latency
candidate fails20760. Physical exploratory unit3339390 exits1 because that
second candidate failed. No failed verdict is overwritten. check_selected.sh
checks the actual completed positive and negative records, with no simulation
re-run. run*.sh files reproduce the exploratory vehicles through ot-run.

Timing remains833 ps, TT setup/FF hold,60/25 ps uncertainty. No multicycle or
other timing exception was added. The enable-qualified timing contract is an
OWNER? item in CODEX-LOG; P&R is held pending that contract and geometric review.
Enable-hop station count NSTA=0 is the scope of this proof. A final plan adding
actual enable stations must publish their count and price/re-prove their lead.
