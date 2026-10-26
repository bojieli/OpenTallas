KVHR zero-cycle private Q recut, 2026-10-26

Source: codex/kvhr-faces-1026, inherited 7540d0411b and fix 23f438f48.
The original host_qm recut passed pre/post equivalence but synthesis merged its
private output register back into the internal sticky-fault register. A kept
alias also added a real buffer load to the output net. Preserve the actual
internal Q and output-port Q nets instead, without a separate kept output alias.
Cost: one added flip-flop, zero added schedule/data/reset cycles, unchanged pins.

Smallest host_qm vehicle: two real source modules, nominal post and emitted RTL
both equivalent; inverted-D mutant rejected. Actual ASAP7 synthesis then passed
raw and ODB-exported face preflight (8/8 data bits), port gate (10/10 pins),
DONT_USE check, and kit LEC (25/25 compare points, zero undecided/different).
No placement, route, timing, or SIGNED claim.

Jobs through ot-run:
- epyc2 oth-ubuntu-1262636-1793005830 generic re-synthesis, PASS.
- epyc2 oth-ubuntu-1277267-1793005938 nominal/emitted/mutant proofs, PASS/caught.
- epyc2 oth-ubuntu-1289678-1793006008 actual ASAP7 synth/preflight/LEC, PASS.
Run root: /srv/opentallas-scratch2/claude/codex-kvhr-faces-1026
Actual kit: kits2/qkd_hr_host_qm__77.76x77.76

Also make capture-merging distinguish bitwise asynchronous SET/CLR and AD load
data. Otherwise two registers sampling the same input but carrying different
asynchronous controls could be merged. Three focused controls pass, including
different-clear rejection and identical-clear acceptance.

Inherited large KVHR2 proofs remain active in cores-kits/kvhr2. Do not restart
those jobs. Other raw cuts still report unregistered outputs, dead pins and
feedthroughs; this zero-cycle mechanism does not waive those obligations.
