# FAM-KV-IOPC-R2 handoff (11-21 10:2x PST)
Work dir epyc7 /srv/opentallas-scratch2/claude/fam-kv-iopc-r2 (repo = lane clone, tmp/, views_d27b/ = the 4 D27b exact-OBS pc views, tree_pc = cp -al of D26 src kw45/src_kv_pin_eb1e73448bd0_hg14_a9f605cb_tbbcc7f0_d26 with those 4 LEFs swapped; source tree untouched).
Predecessor dirs: epyc7 /srv/opentallas-scratch2/claude/fam-kv-iopc (proof_A, tree_d26, gate_d26*, scripts).

## Running
- io_cor_v1 variant A route: unit oth-ubuntu-2072529-1795271645 epyc7 (run_kit.sh proof_A/gen/kv3_io_cor_v1 route). GRT final TT +8.24/tns 0, GRT hold guard +38.5. Read signoff/FAIL_* when done. Proof tree is not src_manifest: if it signs, hand the 41 bank_taps rows (fam-kv-iopc/br2) to KV-PLAN-R6 for the D27/D28 sign-off build.
- pc_v3 place proof (PDN-0006 fix): private spec ~/coord/autopilot/private_specs/FAM-KV-IOPC-R2/qwen_kvsys_kv3_pc_v3_1121101204 (run_item.log there; work epyc7 kw43-wave-1109/.../KV-D26/private/FAM-KV-IOPC-R2/kv3_pc_v3_1121101204). Check 2_4_floorplan_pdn.log: PDN-0006 gone? Known later risks: tap density (TAP-GRID-R4), efault -1,492 path (D27 r6 efault_stage).

## PDN-0006 facts
- KV-PLAN-R2 re-exported pcc/pcf/h_head_p 11-21 04:37 (abstract_detail.py splice: M1-M5 blanket, M6/M7 exact) into the D27b tree; D27c/d inherit. D26 kits still carry the 11-19 views (pcc f964552bdfe8).
- M5 PG share under M6+M7 OBS: 11-19 views 0.30-0.46; D27b views 0.06-0.10; pv_pair 0.05-0.07 (pdngen 3.3 %), head_eighth 0.13-0.14 (7.7 %). qkd_hr_core_peer (kvd23_hr_views_1118) 0.51: at risk.

## Tool (lever 7)
- commit 6944a8b367 (ot-push-main): view_export.pg_crossing_report / pg_crossing_published, choose_abstract exact_pg / OT_VIEW_EXACT_OBS=1, view_export exit 6 on PG FAIL, export_provenance.finalize gate after every transform. Env OT_VIEW_PG_CROSS (M5:M6+M7), OT_VIEW_PG_BLOCK_MAX (0.25).
