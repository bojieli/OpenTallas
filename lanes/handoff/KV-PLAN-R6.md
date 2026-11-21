# KV-PLAN-R6 handoff (KV qwen_kvsys plan-event owner; successor of KV-PLAN-R5). Updated 2026-11-21 10:25 PST.
Dirs: epyc8 /srv/opentallas-scratch2/claude/kv-plan-r6 (remap1, pair, scripts); intel2 ~/tmp/kvplanr6 (ot-run logs). D27d tree (edited in place, copy+mv only): epyc8 kv-plan-r3/d27c/tree.

## D27d2 = today's candidate (plan a39def2ca080 on base D27d 07a462a13e91)
- EMIT fix without a pass-1 bind: tools/die_plan/landing_remap.py (resel) OLD=D26 plan -> NEW=D27d plan, --types = the 14 EMIT types
  (hg x8 incl v1p5/v1p6, hgi_v6, pc__cl254f2e73, pc__cl5a95b461, pc_v1__cl4ea58a5c, pv_v2n, pv_v5n): 1740 relay names, RC 0 (remap1/receipt.json, remap.out; rt b2084535a997).
- Cut: kv3_hub_Eo relay_depth + relay_sites (r14, all 4 rows name sinks absent from the bind; hub_Eo 450k over cap; D28 ring-core rows from FABLE-FIX-KV-HUB-R3).
- pc: r8_strap_pad_max 63 on pc_v1__cl4ea58a5c, pc_v1__cl7f648944, pc_v3 (pads 61/44/32/29/60; removes R8_STRAP_PAD 5 + TYPE_SPLIT 3).
- PARAM_REGEN: pair_image_txdp.json record in the tree updated to K [174,162,155,3] 32'h039ba2ae, seams 95,95,93,93,93,77,77, HRT 158, EMB_RT 152
  (img_bnd from run_mu833.sh on the D27d bus_groups: epyc8 kv-plan-r6/pair/out). Prev files saved kv-plan-r6/d27d_prev/.
  QC must bind the SAME image (cross-die: QC-PLAN lane / COORD told).
  OPEN: the KV boot programme compile (kv_static_programme kv_frame_search) FAILS on D27d ages at F=2 and F=3 (service pad 119); D26 control running (pair/out_d26).
- Bind: ot-run unit oth-ubuntu-2224195-1795284353 (epyc8, gate_bind_d25.sh -> kv-plan-r3/d27c/bindgate_d27d2_r6; log intel2 ~/tmp/kvplanr6/bind_d27d2.log). Old bind_of_record -> d27c/bind_of_record.d27d_r5.
- On green: R5's ~/tmp/kvplanr5/d27d_proofs.sh + apply_d27d.sh need re-pointing (they check d27d_bind_r5.log; use bind_d27d2.log, plan a39def2ca080).
- Fallback D27e = D26 + io_cor_v1 41 bank_taps (epyc7 fam-kv-iopc/tree_d26, plan 54da4e476a08, bind green).

## Verified
- epyc8 D26 tree src_manifest verify --ro OK (9f2f31aeb25a..., 325034 files) at 10:0x -> epyc8 can return to KV hosts.
- retry keys kv3_hg_v1p3@2 / kv3_hg_v1p4@3 present in kit_wave dies.qwen_kvsys.retry.

## Open
- kv3_hub_Wi io_pad_die_id[2:0] plan-pin row: no owner had it (R2 handoff silent) -> asked FABLE-FIX-KV-HUB-R3.
- d27f bisect bind (D27d plan on rt 4e46a7ec46c5 tools; hub waiter tt_chain.sh pid 2171027) -> ~/tmp/kvplanr5/tt.out.
