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

Follow-up: preserving escaped SRAM instance identifiers fixes phy_adp's 512
spurious qp equivalence mismatches. The generator now recognizes escaped
instance names when finding reached macro masters, rather than renaming them
and losing same-instance identity in the proof. Actual phy_adp nominal post and
emitted RTL proofs PASS and inverted-D mutant is caught; emitted proof used
1263 MB peak. Its remaining r_cr logic-before-capture boundary is still FAIL;
this proof is not physical qualification. Source inputs: the five reached
current-repo source files from KVHR2, copied unchanged into the admitted job.

memory_share before memory_map consolidates the per-bit write ports reconstructed
by write_verilog/read_verilog. Without consolidation cdc_ch expanded a depth-8,
546-bit memory into 2,384,928 write muxes and the emitted proof died with rc137.
The repaired cdc_ch proof is running on intel2 unit2117761-1793006272; its nominal
post proof passed in 92.7s at 282 MB, with mutant/emitted stages still pending
when this note was written. No passing result is inferred for those stages.

Placement then exposed a separate representation error: plan/io.tcl requests
ck[0], but the original wrapper's scalar clock survives emission as ck. Preserve
Yosys single_bit_vector metadata on all width-one top ports, matching canonical
plan p[0] pin identity. The emitted host_qm clock is now input [0:0] ck and that
metadata survives actual synthesis (epyc2 unit1395055-1793006690). No bit widths,
logic or cycles change. Placement repair/trial is owned by CORES legacy_vqvs.

Generic exactness guard: capture merging also distinguishes initial state, and
private output duplication retains known init values on both internal and
private Q nets. Otherwise moving an initialized output name to the private copy
could remove the original internal state's init. Six focused controls pass,
including different-init rejection and preservation of both copies' init.
