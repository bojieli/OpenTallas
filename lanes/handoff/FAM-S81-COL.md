# FAM-S81-COL handoff (started 11-20 23:4x PST, updated 11-21 00:5x)
Family: S81 col_h9_r0..r2 / col_h10_r0..r2 and all variants. Rep: col_h10_r0_p1__t1__cl574cc59d__pvb095fa2f.
## State
- Lever 1 (COORD/FABLE-CLOSURE 23:45): +1 stage on ROM input buses at the pin face. Private proof chain running unattended:
  intel2 /srv/opentallas-scratch2/claude/fam-s81-col/chain.sh (log chain.log) = strict bind+LATCHECK (intel1 unit oth-ubuntu-2902890-1795248665, tree intel1 same dir src2, plan = J5 + 104 input rows + 12 ROM-PVAL output rows) -> kit_wave run-item (wave/spec.json) -> CTS tg_cts.sh -> posts OT_CTS_POST_TIMING (post-hook). Pass = TT setup >= -42, no ROM-face path in worst list.
- Delta on candC3c for J7 (UNPROVEN): epyc10 /srv/opentallas-scratch2/claude/fam-s81-col-delta/delta_c3c.json (216 col types, 22,464 rows, gen_delta.py same dir). Goes to J7 unless proven before 11-21 13:00 PST.
- J5 a6 of the rep (intel1 ot-jobs col_h10_r0_p1__t1__cl574cc59d__pvb095fa2f-route-key-cardinal-3209518-1795232332) is in pregrt FF hold repair; post-hook TT -45.46 (after in-flow repair), FF hold -44.52 pre-repair. Do not touch.
- col_h9_r1 pv0bdbc3f3 (D8i a2) routed DRC 0 TT -274 FF -12: path read pending.
## Successor
Read chain.log; confirm or withdraw the J7 rows; then carry to siblings. Tools: run-item needs hub intel2; hardlink tree needs intel1 disk.
## 11-21 01:0x update (Fix A, COORD ruling)
- RD_EXTRA on main f9977af51c1 + 8a16e814dc5 (rtl/v41die/ot_s81_cfg7_seq.sv; bench modes rx1_* in tools/s81/fill2_cfg7_bench.sh). Bench: pr_pq1/pr_pq0/pr_bf and rx1_pq1/rx1_pq0/rx1_bf PASS, mutants pr_mut_prdl, rx1_mut_prdl, rx1_mut_tag FAIL. Masters take RD_EXTRA from +define+OT_S81_CFG7_RDX (default off).
- J7 rows: epyc10 /srv/opentallas-scratch2/claude/fam-s81-col-delta/delta_c3c_rdx.json (216 types: ROM-input + q-bus rows, 30,108 total of which 7,644 q-bus) + manifest define OT_S81_CFG7_RDX. BLOCKER for J7: ot_s81_cfg7_seq is a HARD core (cores/views/ot_s81_cfg7_seq_signed_1101 lef/lib + views/ot_s81_cfg7_seq/source copy): RD_EXTRA=1 needs a re-hardened view (same pins) and a view-source update before the define can apply.
- Private proofs on J5 plan (col_h10_r0_p1 pvb095fa2f): A = input stages (intel2 chain fam-s81-col/chain.log), B = input + q-bus rows (fam-s81-col/v2/chain.log); the seq stays the signed J5 view, so B proves the physical closure only, not the RTL compensation.
