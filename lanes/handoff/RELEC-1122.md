# RELEC-1122 handoff (Opus, started 11-22 22:5x PST by COORD)
Goal: routed LEC EQUIVALENT evidence for the 168 AT-RISK rows of lanes/COUNT-LEC-AUDIT.tsv (hub 0369b02b). Output lanes/RELEC-1122.tsv
(die, item, record, netlist sha, routed LEC result, evidence). Never write COUNT-REVOKED. Post NOT-EQUIVALENT + NO-NETLIST lists every 2 h + end.
Order: HEAD(6) > S81(18) > KV(52) > QC(92). Report to COORD (<250 words) after HEAD+S81 and at the end.

## Method
- Record -> origin kit: signed-store record (~/coord/signed-store/records/<id[:2]>/<id>.json.gz): origin, files[] (6_final.v path+sha), netlist_sha.
- Archive (AGIdock /archive/opentallas-signed-1106/<host>/<path>) holds 6_final.v but NO RTL/config.mk/lec.py.
- Routed LEC = autopilot signoff_chain form: env OT_LEC_SUPERSET_VEC=1 python3 -I KIT/lec.py KIT --netlist <6_final.v> --out KIT/lec_routed_relec1122 [--mem --jobs]
  via ot-run --dir KIT --hosts <origin>. Launcher: <host>:/srv/opentallas-scratch2/claude/RELEC-1122/tmp/rlec.sh TAG KIT NET HOST MEM JOBS
  logs: <host>:/srv/opentallas-scratch2/claude/RELEC-1122/logs/{runs.log,TAG.log}
- Work files (rtx localhost scratchpad relec/): meta.tsv (row->record->origin), out_<host>.jsonl (probe), sib.jsonl, hits_<host>.txt (sha search of 6_final.v across hosts).

## State
- 22:5x probe: of 153 rows with a store record, only ~55 have a live kit+netlist on the origin host; 15 rows have no record ("(none)").
- Already EQUIVALENT routed on same file (audit missed): qc sle_st_b_v1__pv0e7b1dcc, slw_st_b_v2__pva66d0f22__pv3d7bec84, sle_st_b_v1__pvc5a85fd4__pv38472fb8.
- KEEP FAIL routed (=NOT-EQUIVALENT class): qc slw_hc3__clccfc3e6b__pvcca9ff41 (epyc9 lec_routed_autopilot_1795360240568320193).
- HEAD: hd_spn routed LEC launched epyc7 23:1x. hd_host_w/hd_ctl/hd_mesh/hd_host_e/hd_serdes origin kits deleted; searching other hosts by sha.
- 23:5x KEY: 106 store records carry kit rtl/+config.mk+lec.py in AGIdock archive. Reconstructed 49 dead kits from AGIdock
  (fetch.py, only from rtx localhost: ssh -i ~/.ssh/agidock_ot ubuntu@155.103.253.53) into <host>:/srv/opentallas-scratch2/claude/RELEC-1122/ak/<tag>/kit
  on epyc8/9/2/10 (sha of 6_final.v verified = record), LEC batch b4 running. HEAD hd_ctl + hd_mesh included.
- Batches: b1 (51 live kits, 6 hosts), b2 (14 live candidates for "(none)" rows), b3 (S81 core views dsfd_su_t_rxsb + dsdv_eng_rr_h1 rebuilt from main views on epyc9 rk/), b4 (archive kits).
- Collect: bash collect.sh on each host (scratchpad relec/collect.sh) -> TAG|lec.json|verdict|...
- Known NOT-EQUIVALENT (existing): s81 ot_hdc_v41x_attn_tr_x (epyc7 s81-svcrs-4/prov/resign/trx0_120p96x259p2_ni/lec/lec.json, 502 differs); qc slw_hc3__clccfc3e6b__pvcca9ff41 KEEP FAIL.
- No RTL anywhere (expected UNPROVEN-NO-RTL): HEAD hd_host_w, hd_host_e, hd_serdes (archive has netlist only); S81 legacy core views dsfd_node_LL*, dsdv_gunit_l5f/l4r, dsdv_svc_sx_hrow (no netlist in view -> NO-NETLIST).
- 22:0x: b5 qkd_hr_core_order (epyc7 kw44/epyc4-move kit, earlier UNPROVEN 15 undecided); b6 sle_sc_v1__cl115da35f superset rerun (existing EQUIVALENT w/o superset at epyc9 opus-fix-qc-sle-r4-sc/reloc/lec_routed/kit/lec_routed/lec.json);
  b7 = 9 QC sealed ot-job routes: netlist from host ot-store (route-run artifact via gen/<t>/.ot-job-<job>.json), kit copied w/o run/ into RELEC-1122/oj/<tag>/kit (otj.sh).
  col774 (S81 col_h9_r2 p774): exporting 6_final.v from signed so_run ODB with ORFS write_verilog -remove_cells physical-only -> xk/col774 (epyc9).
- hd_spn routed LEC EQUIVALENT (epyc7 kit lec_routed_relec1122).
- TSV builder: scratchpad relec/build.py (inputs res.txt from collect.sh, meta.tsv, out_*.jsonl, l1/l2/fetched/otj_out).

## 00:0x 11-23 update
- RESUMED posted 130ce01a. Table pushed febb9399: 82 EQ, 4 NOT-EQ, 24 NO-NETLIST, 14 UNPROVEN, 44 PENDING.
- S81 group done (bksel_q EQ). HEAD pending: hd_ctl (epyc8), hd_mesh (epyc9); waiter b5v6leq07.
- Reruns at 96 GB: b10 slw_hc1 cle683a076 (OOM), b11 slw_hc2__cla3497502__cl16607c7a (epyc10, yosys -15; old out moved to lec_routed_relec1122_term32).
- Next: HEAD+S81 report to COORD when hd_ctl/hd_mesh end; 2-h post ~01:20.

## 01:4x 11-23 update (after 5-h limit; CODEX-LOG handoff had nothing for RELEC)
- build.py fix: skip res.txt lines with <7 fields (multi-line reasons).
- Table e16dfc14: 94 EQ, 7 NOT-EQ, 24 NO-NETLIST, ~19 UNPROVEN, ~24 running. S81+HEAD report + 2-h list posted 1d89c184.
- hd_ctl NOT-EQUIVALENT (727 pts). hd_mesh still running epyc9.
- epyc10 memory pressure killed 5 QC LECs (-9/-15); outputs moved to lec_routed_relec1122_killE10; kits copied (tar of top-level minus run/, + counted 6_final.v, sha checked) to epyc8 $L/mk/<tag>/kit; b12l.txt on epyc8, P=3, 128 GB/8 thr.
- slw_hc1 cle683a076 (b10) still running epyc10 at 96 GB.
- Next 2-h list ~03:45.

## 11:0x 11-23 (resume after 06:4x-10:40 limit)
- Codex posted the audit baseline 07:35: 116 EQ / 8 NOT-EQ / 20 UNPROVEN / 24 NO-NETLIST / 0 PENDING. Receipts in coord 615ed04c1a23.
- COORD rulings: no revocation without a classified cause. Cause classes are LEC-SETUP / WRONG-RTL / REAL. Revoke only when the type still fails against its own RTL after the LEC fix AND its base passes.
- Triage so far:
  - col774: the 96 clock pins were LEC-SETUP, fixed by main lec 14fb2c78. 78 points remain, the same in the base: hard-core tag inputs that are _NC in the routed netlist. REAL candidate.
  - slw_hc3 x2: the keep failure is relay_q[9] merged into its twin relay_q[8] (proved equal). Separately, 68/85 points differ in q[48..63]+q_bad across 3-4 of 8 identical leaves; main lec still fails.
  - coll_s: the base fails the same as the ECO (20 differs + 1 undecided), so the ECO did not cause it. Codex says async re capture.
  - attn_tr_x: main lec still gives 502.
  - rxsb: the full original kit (claude/s81-kits-c3-1024r kits_repin) is still NOT-EQ.
- hd_ctl (first, HEAD gate 13:00): HEAD-R18 patched lec (epyc9 head-r18/clone, staged to RELEC-1122/m2) left 101 points because lec mis-paired ek. The yosys FSM_RECODE table (fsm/ + fsm_c/, tmp/fsmhint.py) gives cube hints. Runs: ml/hdctl_r8_fsmhint (R8 ctl1) and ml/hdctl_counted_fsmhint (counted 092e72b3, kit copy mk/s81_head_type_hd_ctl_0ce42cbd), both epyc9, runner tmp/mlech.sh.
- LECGATE-R2 hc3 records 03bd0ee623f9/d5f3d7812269/827de5708c20/822d3873e2eb: same 51-68 differs. Rerun once the slw_hc3 cause is found.
- 2fa9961fbc78 = t52: proved EQ twice; no re-revoke (posted 7bd3d4a6).

## 15:5x 11-23 (resume after 11:40-15:40 limit)
- hd_ctl counted 092e72b3 with patched lec + 12/12 yosys FSM cube hints: still UNPROVEN, 101 points (st/ek gold bits unmatched). Superseded by the Codex binary rebuild (mapped LEC 69457/69457 EQ). The historic row stays revoked.
- hd_mesh historic: NOT-EQ, 9097 points (SRAM FIFO black box).
- Cause classes posted 3eb1993b. No revocations: no type fails after its LEC fix while its base passes.
- slw_hc3 (6 records): the failing leaf set changes with the LEC run on the same netlist, so this is LEC-SETUP. Points sit at the mux_rep16 last level, fed by kept select replicas g_c[].f, plus the merged-proposal re-choice. Posted aef0b3ec to FAM-QC-HCST-R3/FLOW-LECGATE-R2 with a suggested lec fix. Re-run all 6 once a fix lands; restore only on EQUIVALENT.
- Open: attn_tr_x (502, gold-only tr regs), rxsb (968; gate 546 inputs vs gold 99), col774 78 _NC tag inputs (REAL candidate, S81 owner).

## 16:0x 11-23
- hd_mesh REAL candidate posted to HEAD-R18 as a row item (1e8b71cc).
- Reviewed and OK'd the HCST-R3 combined lec.py set, intel1 FAM-QC-HCST-R3/pushwt:
  - 6b6f005aee: alias max 1:1 matching.
  - d9c258639b: next same-support candidate (max 4) tried after a refuted pick.
  - Push condition: from a host where test_lec actually runs (no test skip). HCST-R3 sends me the main sha, then I rerun the 6 records and restore EQUIVALENT ones only.
- attn_tr_x cause found, LEC-SETUP candidate:
  - The gate keeps tr bits 8..15 for every row. For the 10 bits shared across the 8 gx copies of a row group (low byte, mode bit 16, pad bit 17; elem() gives the same value for every x<16), opt_merge keeps ONE copy per group. Gate 4736 = 4096 + 640; gold-only = 4480 no-reset twins.
  - Every failing g_c[].e / col point is bits 0-7, 16 or 17. Bits 8..15 all prove.
  - merged_proposals found "0 of 4096", and 4096 is its cap, so the tr twins were truncated away.
  - Test run: epyc7 RELEC-1122/m3/lec.py (cap=20000), out trx3/, runner tmp/trx3.sh, via ot-run.
- rxsb: synthesis uses slang, while LEC gold uses read_verilog -sv by design. Failing points are FP datapath (a_sp, g_h[*].u_h.y/s2_prod/s3_pf).
  - Test run: --gold-frontend slang (epyc9 ml/rxsb_goldslang, tmp/mlechx.sh with EXTRA).
  - If it comes back EQ, the two frontends disagree and I find which one is right. If slang is wrong, that is REAL silicon.

## 20:0x 11-23: HANDOVER to LEC-AUTOFILL (owner order, one job per lane). RELEC keeps only the hc3 reruns + COUNT-REVOKED restores.
- LEC-MERGEPAIR-FIX is on main 096df89d (attn_tr_x EQ 14920/14920, no hints). Done.
- AUTO-FILL class is handed over (RELEC no longer touches it):
  - Patch: epyc9 /srv/opentallas-scratch2/claude/RELEC-1122/tmp/autofill.patch (142 lines, against origin/main 3e1a2180). It adds fill_proposals() + auto_fill() (OT_LEC_AUTO_FILL=0 disables), called right after auto_loaded, plus 2 unit tests. The related tests pass; the full suite was not run; NOT pushed.
  - Same code: epyc9 RELEC-1122/m6/lec.py (sha 912eca44) and the RELEC clone branch relec-fill (uncommitted). Apply it in your own lane clone.
  - Method: candidates = gold-only noreset_dropped constants that do not read their own Q. pred = the deepest candidate in D's register support, None = a chain root. Each hint is proved through apply_hints (fill form, LEC-FPREG-6); the hypotheses are restored if the refinement does not converge.
  - rxsb auto run (no hints) in progress: epyc9 RELEC-1122/ml/rxsb_autofill (docker relec1122-ml-rxsb_autofill, log runs.log MEND rxsb_autofill). Kit: RELEC-1122/rk2/dsfd_su_t_rxsb_c/dsfd_su_t_rxsb_c, netlist run/results/asap7/kr_dsfd_su_t_rxsb_c/base/6_final.v.
  - Hand-hint test ml/rxsb_fill: 755 -> 729 differs. Only the g_h[1] chain was kept: my hint script mis-keyed d_cut.genblk1.g_one.line[108], because lec drops genblk1; the auto version uses L.gp keys. Other chains still fail: m_l.s1_rows (120), a_sp.*, y; their causes are not traced yet.
  - Sweep list (dropped no-reset constants): hd_ctl 0ce42cbd (epyc8 ak/.../lec_routed_relec1122, 10728); hd_ctl counted (epyc9 ml/hdctl_counted_fsmhint, 10809); hd_mesh 22dcfc2f (epyc9 ak/..., 8606); slw_hc3 cld86 (epyc8 ml/slw_hc3_cld86_mainlec, 38081); slw_hc3 clccfc (epyc9 ml/slw_hc3_clccfc_mainlec, 153); t40 c01b49be73a8 (epyc8 ml/mp_c01b49be73a8, 63); coll_s (epyc9 ml/coll_s_eco_mainlec, 52); col774 (REAL RTL bug, 12). Also S81 kv_leaf ikw (ARCH-R2, 887 points / 107 regs in ot_hgi_fp4qdq).
  - Runner: <host>:RELEC-1122/tmp/mlech.sh TAG KIT NETREL MEM LECDIR HOST (docker via ot-run).
- RELEC continues: hc3 reruns on main 2ebb7b8e: r6_d5fde81d + r6_afda1e9d (epyc8), r6_00112d4e (epyc9). Restore only EQUIVALENT ones. 822d3873e2eb / 827de5708c20 have no kit or netlist anywhere and stay revoked.

## 00:4x 11-24: hc3 reruns done; corrections a0b89e11 supersede earlier sections
- r6_* on main 2ebb7b8e: d5fde81d 51, afda1e9d 68, 00112d4e 68 differs, all NOT EQUIVALENT (kept missing 0, alias_unassigned 33). 0 restored. Leaf cause UNPROVEN.
- 827de5708c20: NOT gone (earlier line wrong). Autopilot id, not store id; store record 58a694414806. Kit restored from AGIdock signed-1106/epyc9 (347/347 sha OK) to epyc9 ak/qwen_compute_type_slw_hc3_pvcca9ff41_827de5708c20/kit; run ml/r6_22ee41ca, lec 096df89d.
- 822d3873e2eb: store record c7902930b0a3, netlist + config but no RTL in the record; archive kit dir has no rtl/. Blocked.
- hd_mesh "all FIFO" wrong (500 of 9377 listed: 320 g_fifo_safe, 180 g_rb_safe); MERGEPAIR census partial; rxsb wrong-RTL not ruled out; auto_fill restore guard in my patch was wrong (LEC-AUTOFILL owns the fix).

## CODEX notes, 11-24 takeover
- Historical hc3 c7902930b0a3 exact netlist sha 291c2520bfc1. Recovered archived kit_rtl_paths.json with source digests (sha 66bc2db5f6aa) in epyc11 LEC-AUTOFILL/tmp/hc3_c790_restore. Seven of nine HDL files match the available pvfd488b8f kit. Exact generated wrappers b1104b98332c and dfaab911f73f differ. Archived kit holds no RTL and all surviving v1r6 bind replicas only have bind_report.json, so row stays revoked. No substitute source used.
- Full targeted hc3 rerun on exact available successor netlist pending in LEC-AUTOFILL. All four historical records maintain their status.
