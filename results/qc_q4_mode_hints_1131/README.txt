Q4 scale_wait write-data correspondence closure (2026-11-01)

Actual source: intel2 /srv/opentallas-scratch2/claude/codex-qc-q4-spill64.
Its original out/lec.json is NOT EQUIVALENT at the real 64-edge contract:
115054 compare/hypothesis outputs, 72 differs, 0 undecided. The failed 72
are r5/r6/r7 scale_wait SRAM wd_in high bytes for local groups 1..3.

All four stations have identical cfg_mode, cfg_v and rst_n bound inputs.
Each u_m2 mode register implements the same reset/enable/hold transition.
Gold preserves a representative per station; gate correspondence selects
r4 for some groups. The former profile did not relate those free gold
representatives. The six new hints supply that missing invariant.

Proof uses the EXACT original gold/gate AIG and map bytes plus hyp.json,
reconstructing the original 78142 matched points / 153566 shared inputs.
normalize.py applies the original source-memory alias normalization first;
propose_normalized.py retains the original proved profile and adds only six
untrusted equalities. The archived engine/lec.py is the original kit engine.
Use PYTHONPATH=engine and place original gold/gate AIG/maps, hyp.json and
gold.aliases.json next to these scripts to replay. run_normalized.sh uses
the pinned ORFS ABC through ot-run (4GB,1CPU). Inputs are retained in the
remote diagnostic directory; large source models are not duplicated here.

Formal results (ABC swept graphs included, counts independently parsed):
- Original baseline: 115054 outputs, 72 nonzero/SAT, 1712 ANDs.
- Six-hint joint induction: 36380 outputs, all constant zero.
- Full candidate: 115060 outputs, all constant zero (0 SAT/undecided).
- Invert one proposed equality: one SAT output, caught.

No compare point is waived or deleted. RTL, cycles, reset contract,
black-box model and timing constraints are unchanged. Every generated kit
must re-prove the untrusted hints with its own actual source/netlist.
Affected east types: sle_st_b_v1 and both sle_st_b_v2 landing cohorts.
The deterministic delta script preserves every other type field and hint.
