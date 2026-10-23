# Selected-source pre-tree profile wrapper

`prepare_pretree_profile.py` reads the actual contract and flattened bundle
masters for su_SW0 and sucore_SW, extracts their real pre-tree instance names
and parameter expressions, and creates the minimum latency vehicle. It does
not rename an old profile to fit another source. All four selected SW slice
masters/timing parameters must agree, and mutant or unknown parameter/source
interfaces fail closed. The known registered e_v command interface is checked;
a different command-to-operand interface requires its own measurement.

Run the generated run.sh on the fleet. It compiles those actual two source
files with Verilator 5.050 and measures input, slice and join sample edges.
`--finalize DIR` checks the numerical/fault witness, source hashes and unique
edge events before writing a self-contained relative-path receipt for
NativePretreeTiming.load. The receipt carries the full parent parameters,
actual instance parameter expressions and contract identity.

Wrapper verification used the existing historical r18h case_b flattened
modules m164/m165, not the earlier m72/m73 names. Ep9 unit
2778935-1792734015 exited zero: input 8, slice 66, join 86, measured profile 77.
The source readset, template, output and receipt are retained here. The
current profile loader accepted their exact identities; a differing/mutant
parent was refused. This verifies the wrapper only. Current r18h5/r19b must
measure its own selected pair; it cannot inherit this historical age.

The token launcher also accepts ASSEMBLY_ONLY=1, which exits after assembling
the bundle/cut without emitting programmes, and SU_PRETREE_PROFILE, which
passes the measured receipt to the SU compiler. Both are opt-in. The emitter
fix and the current release profile remain separate gates. This helper does
not promote the still-pending full numerical PV replay.
