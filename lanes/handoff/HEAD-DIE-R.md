# HEAD-DIE-R handoff (successor of FABLE-DIE-HEAD), 2026-11-16
Lane dirs: epyc10 /srv/opentallas-scratch2/claude/head-die-r (pack/smoke/proof), epyc7 same path (NF15c compose, M8 report). intel2 ~/hdr (guard launcher, candidates, ot-run logs).
## NF15b tree (task 1)
- Tree E10 kw45/src_head_pin_d0ee4a2afb10_nf15b_pgr1, manifest bb999e2b6fe275e0..., = NF15a tree abec1ec3 + NF15b prep (canonical plan 8fc6cba9, in-tree 1a85ef11; sidecar 6fcd1d3d exact) + exact rt d0ee tools/+physical/common_flow (171 files). RTL unchanged. Script head-die-r/pack_nf15b.py, tuple nf15b_published_tuple_1116.json.
- Normal guard: ~/coord/autopilot/tree_checks/c4817b6ddee3494b422a... state ok full_ok.
- Smoke: head-die-r/nf15b_smoke.sh (tree_smoke_assert, plan_gate_pre, kit_rtl 26/26).
- Candidate intel2 ~/hdr/nf15b_candidate.json; apply via tools-converge/apply_reviewed_tree_marker_1116.py --expect-source <kw45/src_head_pin_eb1e73448bd0_d1> --expect-event head_rp21z20NF13a.
## Lever 6 / NF15c (tasks 2+3 next delta)
- NF15b has no die.layer_budget.type_m8_grant. M8 report all 26 types: epyc7 head-die-r/nf15b_m8_all (hd_tile = 8aeed4bed8315661 exact). Guide = fable-die-head/base/head/fdh_st/grt_st_TT/route_TT.guide (sha16 a8dcf2f554252553).
- NF15c = NF15b + type_m8_grant{enable,guide:die_m8_guide_a8dcf2f554252553.guide (in prep),ndr 4w}; compose epyc7 head-die-r/prep21z20NF15c (semantic diff = grant only).
- 12-PMA G0 error: check.py needs --native-reset-receipt; old receipt (results/head_native_release_1107) bound l48uo plan + 11-07 RTL. Proof re-run on current RTL: E10 head-die-r/native_release_proof (positive 204 checks/3 epochs 66/68 PASS; early_hold, ignore_lock, leaf_reset, v2 leaf_clock DETECTED; v1 leaf_clock escape = known posedge-only observer, not used).
- pack_nf15c.py builds tree kw45/src_head_pin_d0ee4a2afb10_nf15c_pgr1 with receipt results/head_native_release_nf15c bound to in-tree NF15c plan.
## STATE 2026-11-16 ~18:5x PST
- ADOPTED: NF15b (receipt lanes/handoff/s81_head_atomic_apply_1794881745240949632.json, commit ebf9eeb7) then NF15c (receipt s81_head_atomic_apply_1794881931134245048.json, commit 7c41a383). Current: event head_rp21z20NF15c, tree kw45/src_head_pin_d0ee4a2afb10_nf15c_pgr1 a51810b5, plan cef70ef0 (canonical e471b074), gen_hosts [epyc10], 3 holds kept, physical_qualified false. Guard dirs tree_checks/c4817b6d (NF15b), baf2004e (NF15c).
- NF15c gates E10 head-die-r/nf15c_gate (G0 PASS 0 err with receipt; 1 err without) + nf15c_gate2 (bind PASS, cohort 26/26, LAT 329/329). Bind --out must be repo-relative: use ../../head-die-r/... from the tree.
- FABLE-REVIEW-NF15C ADOPT-WITH-CHANGES (gate rerun done). Advisories: die clock re-route must run --m8-grant-lock; hd_serdes grant low yield (1525 tracks, ~0 in tap rows); 8/776 clock sites without guide gcell.
- Any HEAD die G0 must pass --native-reset-receipt <tree>/results/head_native_release_nf15c/native_release_receipt.json (receipt binds plan digest; new plan = new receipt via head_native_release_receipt.py --proof-dir head-die-r/native_release_proof).
- TP2: E10 head-die-r/tp2/gen/hd_tile (gen.py phys on NF15c, profile = die_gen_env + item_env minus reach0, in-tree SIGNED_VIEW_SHA, OT_FLOW_TAG head-die-r-tp2), m8_grant 8aeed4bed8315661/7209 tracks, MAX M8, preflight PASS, mask LOOKED (scratchpad nf15c_m8_masks.png). Handed to HEAD-TYPES-R to launch run_kit.sh via ot-run. tp1 failure + signed tile untouched.
- Stand-ins (7): hd_spn, hd_serdes, hd_mesh, hd_lep0N, hd_ctl, hd_host_e, hd_host_w (epyc2 scratch3 fable-die-head/fdh_st/real_sta/coverage.json). None signed at 18:5x (wave: ENQUEUED/FAIL). Replace each in real_sta parts/ as it signs (export to AGIdock+rtx-pro first), rerun die STA.
- FLEET-OPS-R told to replicate NF15c tree (not d1) to E8 before adding epyc8 to gen_hosts.
