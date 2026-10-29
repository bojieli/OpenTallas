# FLOW-HOLD takeover 2026-10-29

Shared source fixes: e6d564618 scopes sender-min core obligations to their exact plan and receiver module, with core-in-partition parent receipt selection. S81-029 still needs the first routed col_h9 parent with real CFG7 views (u_r2.u_s13); no such parent kit exists. The real flat/ILM parent summary can then be passed to io_hold_parent.py PLAN STA --core-instance u_r2.u_s13 --core-kit CFG7_KIT --out RECEIPT. A missing view, missing input or stale plan stays incomplete.

65bb9a7ca fixes the existing RC calibration runner for modern exact-library loading. First native probes failed with missing BUFx4 because grep selected no libraries; preserved *_rc_missinglibs outputs on intel1. The corrected prefix reads the exact signoff-selected libraries and isolates its receipt.

## Q3 hold closure

Inherited intel1 flow-hold-3-v1/q3_holdeco is actually eco_from=grt (OT_HOLD_FORM default pre_drt), despite the preceding post-route description. Its clock-freeze log has zero routed clock wires and it is still in hold repair. Left untouched. Its source q3 is a stable copy of kv-kits-20 q3_t2.

A fresh real post-route variant now runs at intel1:/srv/opentallas-scratch2/claude/codex-flow-hold-0830/q3_post2_holdeco, unit oth-ubuntu-1644745-1793288469. Source own worktree /srv/opentallas-scratch2/claude/wt/codex-flow-q3-post-0838 @65bb9a7ca0; OT_HOLD_FORM=post_route, OT_DRV_LAST=1, margin15 under OWNER12.19 because measured routed-clock drift exceeds10ps. Original routed geometry was viewed in geometry.png before submission (review in results/geom_review/codex_flow_hold_1029). DRC, frozen clock geometry, TT setup and FF hold remain required. Earlier prelaunch missing-bundle and existing-directory failures are retained in q3_post_missing_bundle.log / q3_post_existingdir.log; no physical result was generated in those attempts.

## Risk sweep (own measurements, UNCHECKED by independent number review)

One existing routed sample per die; this is a risk sample, not a completeness census. Current RC script ran read-only with the same exact FF libraries and each kit SDC. Clock arrival comparisons use matching register clock-pin names and source latency zero. Values in risk/summary.json: KVq3 max41.40/mean17.67ps routed minus GRT; QC BTAB max57.14/mean14.63; S81 CFG7 max10.55/mean1.16; HEAD turn_a max7.44/mean-2.27. HBM HNX last probe still live at this checkpoint. Full artifacts intel1+intel2:/srv/opentallas-scratch2/claude/codex-flow-hold-0830/*_rc/ff*.tsv. No new route or release follows from this diagnostic.

Q3 routed-wire fit over351clocknets recovers R(M3)=31.214, R(M4)=17.9997, R(M5)=18.982ohm/um with meanR residual0.054%. A fit against GRT guide lengths gives meanR error52%/p95+153% and is rejected as a transferable correction. Actual GRT M5 clock legs become M3 in detailed route (mp_ck_Tpq_br_out: guideM5 26.79um vs routedM3 26.85um, plus vias). Thus a blanket1.8 RC multiplier does not fix the underlying layer assignment. No globalRC default changed.

## Canary collection

Main a592 QC, HBM SRAM and KVtype completed NO-REGRESSION with their original absolute design stops retained. HEAD a445 is canonical stage PASS but REGRESSION: TT-33.83/FF-6.63,109holdEP vs74baseline, FFclockmean193.06 vs175.72, DRV332vs185. Its own HEAD owner was notified. The old hd_turn_a type outline and type clock fields are unchanged relative to the05f9baseline; the current margin10 reduces earlier241holdEP to109, and its measuredGRTclock drift stays below10ps. No HEAD tag authorized. HEADa592, KVcorea445 and AB81f9 are still live. No repeated canary.
