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
## 19:xx PST update
- Receipt auto-pick: branch claude/head-die-r-receipt-1116 @910164988b7 (epyc7 fable-die-head/repo clone): check.py finds results/*/native_release_receipt.json matching plan digest; READY posted, awaiting gate/merge; then tools refresh of HEAD tree. Until merged pass --native-reset-receipt explicitly.
- M8-lock note posted to all HEAD lanes.
- Die proto NF15c: epyc7 fable-die-head/base/head/fdh_nf15c (runner head-die-r/run_nf15cdie.sh, ot-run log intel2 ~/hdr/nf15cdie.log). Kit PASS 45100 clock cells, GRT st TT/FF + off TT EXIT 0 no overflow, route guide sha16 = a8dcf2f554252553 (identical to grant guide -> m8 lock holds). STA = NF14 numbers: intra TT setup +569.52, seam TT +654.88, die clock gate BLOCKED(kits) (585476 hold pairs without signed real views), landed FAIL -861 (plan-defined landed hops, info), skew 1277.6 WARN. CA chain bind fails in old src count_align_bind (FREG-DECL-1, same as fdh_nf14 harness); authoritative CA = nf15b_bind 0/2000 with e7 tool, unchanged by NF15c.
- Next: real-view die STA (epyc2 real_sta) when stand-ins sign; CA chain should be re-pointed to tree tools.
## r400 follow-up
- Receipt branch approved r400 (merge service lands it). gen_hosts live [epyc10, epyc8] (FLEET-OPS-R e6d8e17); marker aligned (e4acaec7); guard tree_checks/b5a1297e ok full_ok on both. Apply helper: candidate key keep_gen_hosts:true keeps current gen_hosts (backup .bak-hdr-1116). Use it on every future HEAD switch.
- READY claude/head-die-r-proto-ca-tools-1116 @2285df35d0a: repo proto_die.sh CA steps use the plan's own tree tools. After merge, run the HEAD die proto with repo proto_die.sh (PW=<tree>), not the lane-local proto_die_fdh.sh/ca_chain.sh (old d1 src).
- Types successor: HEAD-TYPES-R2 (7 stand-ins).
- r401: proto-ca-tools approved. keep_gen_hosts ported in-repo: READY claude/head-die-r-keep-gen-hosts-1116 @f10d24deb26 (stacked on 215be2f r398). After merge use ONLY tools/autopilot/apply_reviewed_tree_marker.py (--keep-gen-hosts; pilot hold applies, use --pilot-item or --no-pilot).
## 21:xx PST update (resume)
- Branches receipt-1116, proto-ca-tools-1116, keep-gen-hosts-1116 MERGED to main (19:17-19:27). Use in-repo apply_reviewed_tree_marker.py --keep-gen-hosts; 1116 tools-converge copy retired for my use.
- 3 unowned stand-ins SIGNED+ARCHIVED-BOTH (sha verified both stores, provenance/ in each entry):
  hd_ctl_n -> s81_head/hd_ctl_n__rminimal_1116 (same routed DB E8 type-hdctln/pregrt, ODB 41050a6e; legacy NOT SIGNED = setup -25.82/DRV/io_hold advisory; R-MINIMAL judge SIGNED, internal FF core_n 0).
  hd_turn_b -> s81_head/hd_turn_b__viewexp_1116, hd_spn_wshim_tx -> s81_head/hd_spn_wshim_tx__viewexp_1116 (run dirs gone; V+SPEF regenerated from archived ODB, E7 head-die-r/standin3/export_view.{tcl,sh}).
- NF15c real-view die STA real3: E7 head-die-r/nf15c_real3 (21 real, stand-ins ctl/host_w/lep0N/mesh/serdes), unit oth-ubuntu-2640521-1794891723, log intel2 ~/hdr/nf15c_real3.log, results run/die_sta.json.
- NF15d plan event (u_chn 1548.0,109.44; FABLE-PD-HEAD-2045 lever 3): E10 head-die-r/pack_nf15d.py -> kw45/src_head_pin_d0ee4a2afb10_nf15d_pgr1 (+ fresh receipt results/head_native_release_nf15d, + main check.py/proto_die.sh). Gate head-die-r/gate_nf15d.sh (G0 no flag = auto-pick proof). Then Fable review + switch (--keep-gen-hosts).
## 22:xx PST update
- NF15d (E10 kw45/..._nf15d_pgr1, u_chn only) SUPERSEDED: 96 G0 errors (hd_serdes reset tree re-solved). Do not adopt.
- NF15d2 GREEN (E10 head-die-r/pack_nf15d2.py, gate_nf15d2.sh -> nf15d2_gate): tree kw45/src_head_pin_d0ee4a2afb10_nf15d2_pgr1 manifest d96604a2, plan 700ea298 (stage d1a52b1b); u_chn 1548.0,109.44 + head_reset_exports fix (6 rows) + republished hd_serdes wrapper (E10 head-die-r/nf15d_reset/pub) + receipt results/head_native_release_nf15d2. G0 0 err (auto receipt), bind PASS, cohort 26/26, LAT 329/329. Waiting: Fable review, FLEET-OPS-R copy to epyc8, then switch (in-repo apply_reviewed_tree_marker.py --keep-gen-hosts).
- Die top with landing network: E7 head-die-r/nf15c_real4/add_landing_top.py (landing_route.network(P)); top bb9323c4e229; die STA real4 (21 real) E7 nf15c_real4, split tool E7 head-die-r/seam_split.py -> nf15c_real4/seam_split.json.
- Lever 2 tap windows: E7 head-die-r/tapwin (exact clock SPEF LE15; rows_head.json draft), proof E9 head-die-r/meshproof (cross_tap 12346 -> 6791 with tol SPEF+10). Rows go into the NEXT event with seam in_min/out_min re-derived.
## 22:3x PST
- real4 DONE (E7 head-die-r/nf15c_real4/seam_split.json): untimed 379 -> 22 (all stand-in launched); real-real 1062/1062 timed. Real: TT setup -396.17 (sp4->sp3/start_i), hold TT -2023.58 / FF -1518.85 (nst3_turn->nst4/u1_i landed ring, capture fclk +2.1 ns). OPEN: diagnose landed-ring hold class (forwarded clock model) before any fix.
- Branch claude/head-die-r-sta-landing-1116 @1d07c5de34e (tools/die_plan/sta_landing_top.py + test) READY; validated identical to real4 top (E10 head-die-r/slt_top.v).

## CODEX takeover NF15d2r1 ADOPTED 2026-11-16
- Correctedimmutable successor src_head_pin_d0ee4a2afb10_nf15d2_pgr1_d1 manifestbdd769da096619bcbe67188b844b3952d4f28070ef73af80308702796f57ac1c, plan47948a9f7ee996d8c678c45772ab2cda8434f444ff75b0406c3398a075e3d05b, eventhead_rp21z20NF15d2r1. Fixedstale published-wrapper receipt8a2e0eed; currentprep rootprefixrelocationonly, nativeproof rebound. Originald2d966 NOTADOPTABLE(stalewrapperSHA), E10originalretained,E8/i1unusedcopiesguardretired.
- Actual kit_rtl bootstrap+assetdigests+publishedSHA+tokencomparePASS21files; G0zero/bindPASS/cohort26EQUAL/LAT329delta{} atE10head-die-r/nf15d2r1_gate. IndustryimagesLOOKED E10head-die-r/results/geom_review/NF15d2_codex_1116,samegeometryprovenrootprefix-onlyplan diff. Fablefollowup nonblockingperCOORD.
- Sourceguard3f8675ae full_ok all3hosts; publishgate bdd769 PASSschema/pre_g0/hashes/contained/dry_gen (PUSHED4f81218c). InitialE8drycontroller wasunstarted below100GBfloor; exactowncontrollers1289786/1301551/waiter1302332 cancelled, capacityevidencepreserved; E10drygenpassed androamedlint/preflighti1. No physicaljobcancelled/nofloorrelax.
- Runtimeatomicapply keeps all3hosts/inheritedphysicalholds; pilothd_serdes; physicalqualifiedfalse. Receipt /home/ubuntu/coord/lanes/handoff/s81_head_atomic_apply_1794902357004072501.json.

## CODEX 00:24 physical192 recovery successor
- First sinkless192 removal route E8 fclk_recovery_u1/route FAILED DRT0206 at unchanged cland_fstart_in_u1_i -> hold23029/A pin contact; original and afterGRT net both111wireops/exactboundingbox, so wireloss NOT demonstrated. Failedlog/checkpoint retained.
- Successor E8 head-die-r/fclk_recovery_u1/route_contact_r2 routes changed2clockroots plus exact legacycontact net using established SDK prd_route_keep/eco_grt_pre park+restore helpers from entry_phase_context. Input dry2/unpadded.odb/reference originalinput6_final.odb, no newcells/pinmoves/constraintchanges. Review results/geom_review/contact_r2.json; original removal192 image retained.
- Intel2client1965116 ~/hdr/fclk_route192_contact_r2.log, unitoth-ubuntu-3667957-1794903876. Collect DRT/RCX then localTTsetup+internalFFhold and minimumu1 actualpair; d1actualSerDespeer still absent. Originalsignedarchive untouched.
- NF15d2r1 newlaunch TOOL-SKEW4c852e87ef64 check.py/proto_die.sh is assigned root/holds semanticcomparison; no blindallowlist or liveimmutableedit.

### 00:3x continuation
- Current 192 successor unit still progressing through track assignment; no terminal, previous failed DRT0206 retained. Prepared UNSTARTED run_signoff_contact_r2.sh requires separate export_contact_r2 canonical DB/V/SPEF + EXPORT_ALIAS_PASS marker, then original SDC and TT/FF nominal signoff. Child SPE owns canonical exporter output_net_identity.tcl BEFORE DB/V and regenerate SPEF on renamed nets; raw OpenROAD writer is not inherently alias-safe. Raw route outputs remain preserved.
- Incoming reset/start 2-bit falling-entry coupon E8 head-spe-export/entry_phase_context still DRT iteration0 progressing; actual shared-root baseline FF hold -269.780, not scalar -225.
- Separate sp4->sp3/start_i setup failure has minimum actual-root measurement TT -487.665 / hold +861.821, FF setup -282.655 / hold +714.246. SPE child owns counted J2 existing-CA window/boot/start contract measurement, no MCP/window waiver.
- Fresh NF13a attempt5 n3_turn DRC3 is stale rst_start_raw_2 M7 partial-overlap geometry already superseded by signed NF15 pin_pg view; no second ECO.
