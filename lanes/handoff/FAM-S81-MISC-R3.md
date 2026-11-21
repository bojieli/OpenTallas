# FAM-S81-MISC-R3 handoff (11-21 ~13:30 PST), successor of FAM-S81-MISC-R2
Work dir epyc10 /srv/opentallas-scratch2/claude/fam-s81-misc/ (export OT_LANE; ot-run on epyc10). Trees in s81-j6/candMISC*.
## t5 / vp_sr (J7 Layer A)
- misc3 (t5_nostn_delta_v1f.json, candMISC3) GATE PASS: bind 0, LATCHECK 873/873, LAT diff 0, G0 0 new (87 inherited), PRE PASS -> posted to R4, J7-ready alone.
- misc4 (full t5 delta + kv_leaf define op): bind rc 1 LF_CS_DEPTH t5 ho 2 vs 1 (a per-type define does not change bound RTL).
- misc5 (mk5.sh): candMISC4 plan + 75 leaf define ops (misc5_leaf_define_ops.json) + manifest define + reprove32_vp_sr + SR ho stage 78 types / 9190 rows (misc5_ho_stage.receipt.json): bind rc 1, 30 ho rows plan = bound + 1, because the J5 asbuilt.* elaboration was reused (hard links) without the define.
- misc5e: fresh elab refused (svc PORTFIX stale check, rt 2ddb19c08ba6 on J5 base). misc5d = donor SR=1 elab adopted (same inputs): GATE PASS (bind 0, LATCHECK 873/873, LAT diff 0, G0 0 new, PRE PASS). Package posted to R4: fam-s81-misc/vp_sr_t5_layerA_package.json (6 steps; fresh ELAB required; ho stage as GEN after the LEAF-R6 re-grid).
- Asked LEAF-R6 to confirm that kv_leaf t5 stays with this lane (their 11:58 claim includes it).
## eng__t1
- View re-exported (export_view.py) at fam-s81-misc/engrr_view/dsdv_eng_rr_e (LEF, tt/ff lib, netlist, signoff, LOCAL_PASS_NEEDS_PARENT). 1-op lib row posted to R4 (a314c25d). Verify the eng__t1 dry_gen once it is applied.
## t2 part B
- epyc10 fam-s81-misc/t2b_piece_map_v2.json: 28 pieces <=350k placed (8 pool lane + 2 cn_write, 4 kvq x4 + kveA, 9 kveA x6/x4, 3 kveB, 4 misc), sum = yosys 2,031,431 generic x 4.58. The _draft.json there is stale (undercounted). Next event: regions + 405 um cut-face stations, reach.
## Not started: private t5 kit (after the Layer-A gate), phy gen (J6 r1 not applied yet).
## Cleanup owed: epyc7 /srv/opentallas-scratch2/claude/fam-s81-misc-r3/ partial copy (~32 GB, aborted under the epyc7 no-staging notice) -> ot-delete.
