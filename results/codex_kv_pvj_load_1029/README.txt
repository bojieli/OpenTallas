PV join output-load locality, 2026-10-29. SOURCE CANDIDATE; no P&R/signoff claim.

Actual current fR180 AP13576235cae1 failed TT -21.34ps/30EP, FF -25.55/2187EP,
DRV95TT/35FF, DRC0/antenna0, pair skew72.1TT/67.8FF. TT worst jrun ->
NORdecode -> fanout46/64 buffer cascade -> y_hold[398], data1023.86ps versus
required1002.52. Clock-gate passes; this is a shared output-load control cone.
Actual failed ODB/SPEF/netlist and raw reports retained on intel2:
/srv/opentallas-scratch2/claude/codex-kv-pv-resume-1029/pvj_fR180_failure.

New parameter OUTPUT_LOAD_LOCAL defaults0. Its opt-in branch registers
nrun && nage==J_OUT once per16bits, using the existing next-state expressions
already used by operand selection. At every edge the new load register equals
the current legacy jrun && jage==J_OUT predicate. y_hold and the separate y
port copies capture the same arithmetic result on the same edge. Existing
FP32 adders, reduction order, pins, IO/clock/reset contract unchanged.
32 extra control FFs; token/schedule cycles added0. No performance gain claim.

Full-shape smallest-join lockstep uses all4096inputbits/16actual FP32 adders,
J_LAT7, RESET_PIN1, 6400cycles, randomized data, immediate issue, repeated
reset, SF fault, late overlapping GO traffic. Nominal and default branch
both match the pinned old module:6391checks/118valid output beats. A wrong
lookahead J_OUT-1 mutant produces6373mismatches (CAUGHT). Verilator5.050.
The subsequent GENIF constant comparison was made explicit (!=0) to avoid a
new width warning; the elaborated opt-in branch is identical for parameter1.

Yosys0.68 fullshape synthesis through actual kit ot_keep_regs.tcl, flattened,
noABC:32 distinct load_q FFs retained with cell keep1, maximum16 mux-select
loads per copy (common D muxes of duplicate y/y_hold were shared). See
retention.json. Physical mapped/LEC/placed timing remain owed; source-level
fanout and retention are not a SIGNED view. New source is not adopted.

FF worst ts3[945]->t_r4017 data202.64 versus capture202.23+12.5+13.46=228.19
is a separate actual-RC/data-hold convergence issue owned by FLOW. Its shared
opt-in final_ff_hold.tcl must be qualified on a fresh successor before route.
No clock/IO/uncertainty relaxation and no blanket margin increase here.
