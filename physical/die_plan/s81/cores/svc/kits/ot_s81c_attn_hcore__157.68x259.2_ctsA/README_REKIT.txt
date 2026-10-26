CORES-KITS/HV 2026-10-26 05:07 PDT: input snapshot of the reviewed kit_ctsA (GEOM-REVIEW-13 PASS-COND [PATH-S81/HCORE-CTS02-REVIEW])
as re-kitted at epyc1:/srv/opentallas-scratch2/claude/cores-kits/hv/hcore/kit_ctsA_d75 on the released S81 canary flow d75b94c4c5ce.
Committed so the sign-off src commit contains the exact kit inputs (closure order rule 3; GEOM-REVIEW-13 cond 1).
Not committed (fleet only, hashed in IMMUTABLE_COHORT.json / FROZEN_SYNTH_CACHE.json): run/ synth cache (1_2_yosys.v sha 0890ad6f..), lec/, ff_repair/.
RTL/config = Codex native cohort (codex/hcore-profile-1309@07d10eb766 RST_TIMED + CTLA load stage) + PATH-S81 swr/CTS recipe
(claude/path-s81-hcore-2325@c2833afa83: hold_budget.tcl, post_grt_drv.tcl kit-local delta, CTS -dont_use_dummy_load).
Kit-local tool copies are the TOOL_COHORT_1713 snapshot; this kit reads no physical/common_flow or tools/die_plan file at run time
(the 4 common_flow files the canary gate named are not referenced: OT_PIN_REGS / OT_RST_COPIES_MAX unset).
Re-run (ot-run oth-ubuntu-2443387-1793014868, goal cts): 3_place sha 9aeea14ddae7, 4_cts_preff 0a5bdf0d0a36, 4_cts bd5d656756f6 = byte-identical to kit_ctsA.
