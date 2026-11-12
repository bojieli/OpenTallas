# HBM-CORES-B lane handoff (HBM hard cores, lane B). Updated 2026-11-12 07:05 PST.

Owner: DIE-HBM-101 (was DIE-HBM-100). Rules: safe/structural forms, two strikes -> re-form, one ECO on a near miss only,
NO --crit for core builds, no --owner-override, DO_NOT_COUNT until signed off, FF hold >= 0, renders before counts.

## 1 Scope
pv_merge (RDREG + TREG form), OPSA1 group1 SREG, kshare LCREP (abcr / pfr), b128 tie-clone re-form, plus renders/verdicts
of opsbg_E, q3bc_ISS2EM, dtap_rb, opsa0_B.

## 2 Worktrees / branches (all epyc2 /srv/opentallas-scratch2/claude/hbm-cores-b/)
- wt_pvm: claude/hbm-cores-b-pvm-treg-1112 @ 243ed13930 (TREG, pushed) on claude/hbm-cores-b-pvm-opreg-1112 @ 5ee32d7cc6 (RDREG, pushed). Base main bf14f7dda7.
  Proofs: physical/die_plan/hbm_arch_cores/proofs/pvm_rdreg_1112/ and pvm_treg_1112/ (RESULTS.txt each).
- wt_sreg: claude/hbm-cores-b-opsa1-sreg-1112 @ 3923360ebd (RTL+proofs d8c51ee924; merge READY was posted by DIE-HBM-100 for d8c51ee924).
- claude/hbm-cores-b-ksh-lcrep-1112 @ 1973ee13bd (kshare LCREP; READY held on LCREP=0 equivalence).
- claude/hbm-cores-b-ff-tieclone-1112 @ 1c4363f356 (OT_FF_TIE_CLONE for b128).

## 3 Running jobs (logs: intel2 ~/hbm-cores-b-logs/<name>.otrun.log; check: grep -a "SIGNOFF\|RAN on" ...)
Builds (kits under <host>:/srv/opentallas-scratch2/claude/hbm-cores-b/kits/<name>):
- pvm_F2T (F2+RDREG+TREG) epyc9 unit oth-ubuntu-2142781-1794488449. pvm_F2R ended NOT SIGNED (TT -87.42, all from bp -> TREG).
- opsa1_SREG epyc9 unit oth-ubuntu-3643811-1794483627 (outline 760.32x233.28; routing fail -> owner decides growth).
- ksh_abcrl3 / ksh_pfrvl3 epyc8 (single-layer pins). ksh_pfrvl2 (old 2-layer pins, data point) ended NOT SIGNED TT -4.69, FF hold -199.96 (sdc -152.46), DRC 0.
- b128_canonT (tie clone) / b128_canonU (+SLEW_MARGIN 50 fallback) epyc7.
- opsbg_E, q3bc_ISS2EM, dtap_rb, opsa0_B (renders + verdict when they land).
Formal (epyc2, docker names hbmcb_*):
- RDREG equivalence vs main: pvm_eq0/eq_p0d, eq_p1d (SRAM blackbox on both sides). Earlier p0/p0b/p0c/p1/p1c left cells
  unproven only downstream of the unpaired SRAM rd_out (ma/mb/fold_a_data/pub_buffer); source at RDREG=0 is line-identical.
- RDREG BMC: pvm_rdreg_fm/bmc_m0 (must PASS), m1..m3 RDMUT mutants (must FAIL; m1 FAILED as required).
- OPSA1 SREG MUT0 tempinduct: wt_sreg/.../proofs/opsa1_sreg_1112/eq_m0.{log,rc} (3 h timeout).
- Lane-local watcher: localhost scratchpad watch11.sh (not needed by a successor; grep the logs).

## 4 Fork lane
kshare fork (agent a99fe9538ce71ed45) owns the LCREP=0 equivalence on epyc2 .../ksh_lcrep_fm/: eq0f_{abcr,pfr} (keep on renamed
shared regs so they pair; the sound fix), backups eq0e (mem2reg) and eq0m (bounded miter, bounded only). Posts only on 0 unproven.

## 5 Next steps / decision rules
1. eq_p0d/eq_p1d 0 unproven and bmc_m0 PASS, m2/m3 FAIL -> append to proofs/pvm_rdreg_1112/RESULTS.txt as a new commit on the
   TREG branch, push, send sha to DIE-HBM-101 for ONE combined RDREG+TREG READY. Cells still unproven -> report, no READY.
2. pvm_F2T sign-off: view run/layout_review renders, classify setup/hold/slew (STA census reuse signoff/tt/session.tcl to read_db).
   Signed -> report; failed -> failure class to owner at once; second failure of the form -> re-form.
3. LCREP=0 eq 0 unproven -> owner posts READY for 1973ee13bd. Core-owned hold: one hold-buffer pass after ksh_*l3 structural builds; port starts NEEDS_PARENT.
4. opsa1_SREG: post MUT0 induction rc; on GRT congestion report and let the owner decide outline growth.
5. b128_canonT: confirm OT_FF_TIE_CLONE lines in the face-flops log; report sign-off.

## 6 Open items
- pvm hold class (F2s): 101/105 reg2reg in g_madd FF->INV->FF, worst -6.20 (structural; after TREG).
- ksh_pfrvl2 hold split (core-owned vs port-start) not yet done.
