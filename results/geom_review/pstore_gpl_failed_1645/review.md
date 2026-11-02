# Native Pstore failed GPL: numerical repair diagnostic, no physical clearance

Personally LOOKED actual_failed_gpl.png from one read-only OpenDB dump of the
actual3_3_place_gp-failed.odb. Intel2 unit1534858-1793582122 exit0,4GB/2T;
no cells moved, no DB written, no STA/placement rerun. Raw outputs retained at
Intel2 /srv/opentallas-scratch2/claude/codex-pstore-failed-look-1645 and local
/home/ubuntu/coord/tmp/pstore-failed-look-1645.

All51 INCLUSIVE/VOLTAGE_DOMAIN regions contain real cells; none empty, member
centres inside boxes. Actual row-segment capacity minus fixed nonmacro cells
gives max member/available area5.05%, not a forced overfull box. The failed
checkpoint is not DPL legal: ungrouped cells still overlap macro bodies.
Several region overflows rebound while HPWL worsens29.2658%; numerical guards
correctly stop. The two GPL warning region IDs are not emitted or persisted
in the ODB; last overflow/rebound lists cannot uniquely identify them, so no
names are guessed. Overlapping region boxes and their final combined legality
remain part of the actual subsequent placement diagnosis.

ONE cached original-I/O MAX_PLACE_STEP_COEF=1.01 retry is a justified numerical
diagnostic with identical source/netlist/I/O/face/pins/macros/all51guide boxes,
density0.5 and ordinary GPL/divergence guards. No synthesis repeat, widening,
new FF/stage or geometry/gate waiver. HBM owns fan32_phi101;1.02 not launched.
A converged result still needs actual placement LOOK, legality, reach, channel,
PG/clock and all caller/source gates before later stages.

Independent low-fill issue is retained: actual complete standard area11134.95012,
macro295935.74208, outline541508.1984 (macro54.6503%), outline-free245572.45632,
standard/free4.53428%; core-free4.78137%. These are complete-master footprints,
not the GPL movable-area statistic. Numerical convergence cannot by itself
clear fill/empty or make this a SIGNED design. No filler is proposed.
