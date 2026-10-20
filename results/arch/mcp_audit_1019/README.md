# Four-release-die exception audit, 2026-10-19

Status: source-pinned bounded inventory; two release proof gaps remain open. This is not physical signoff.

Actual manifests: S81 mu2 6050bfac9 case_mu2/case.json; Qwen dv2f18dh2 SOURCE_COMMIT 0d4c9808f chain/bind.json; KV kvs14r-219049242-mu libs/views.json; HBM GEN2c b1e9a0734 vplan_pre/views.json. Copies are adjacent. HBM ROUTED_UNBOUND candidates remain labelled as such. KV current route is diagnostic after native-chain refusal.

| Die | Owner | Constraint/path | Proof or disposition |
|---|---|---|---|
| S81 | S81-SAFE-FIX/GUNIT | physical/ref_tile/dsdv_gunit_l5/{clock,signoff,signoff_ffrepair}.sdc and physical/ref_tile_specs/s81dv/gunit_sinkh_mcp.sdc | MASK: setup9/hold8 Sinkhorn destination exception at mu2 source. Superseded by safe pipelined core-clock successor afa31fbae, +55 HC edges; next GEN must exclude old kit. No newly qualified pass claimed. |
| Qwen | SAFE-QW-LAND / MU-DIE-QW2 | physical/qwen_fwd_lane/fwd_lane_clocks.tcl; eleven bound land/rly kits clock.sdc | OPEN COVERAGE: bidirectional clock-wide false paths lane_ckf/core delegate ring-to-output timing to parent. Current die landing.sdc constrains incoming a/ea; this alone does not prove internal ring capture. Safe lane owner notified; exact age/overwrite/selector proof and bounded tile constraints required. |
| KV | MU-DIE-KV2 | 49 selected physical views including child views | No data exceptions found in available selected-kit SDCS. 33 standalone specs; aliases share views. Current diagnostic source binding problems are separate blockers. |
| HBM | HBM refcfg | hbm_refcfg_q_1018/{clock_entry,clock,signoff}.sdc | Tagged loaded->ls[0]->ls[1] and prst->rel_seen_s1->rel_seen two-flop level synchronizers, 250ps bound; no blanket clock exemption. |
| HBM | COLSU-2 | hdie_col_su_r1/{clock_entry,clock,signoff}.sdc | Gray h_seq through x1/x2/x3; payload capture only x2!=x3 and stable>=2 serial periods; 250ps sync/833ps held payload. Separate two-flop reset crossing. Source structure is represented by existing structural CDC lint profile. |
| HBM | HBMA-SVC | hdie_svc_stack_fault/{clock_entry,clock,signoff}.sdc | async_gray_fifo fingerprinted protocol, exact Gray/online/reset stage pairs, max773.333ps/min0; second sync stage and ordinary data paths remain timed. |
| HBM | ckgen owner | hbm_ckgen_cl/clock.sdc:46,signoff.sdc:163 | por_n/refclk false paths belong to behavioural clock/reset macro boundary, no accelerator payload path found. |
| All | ref_tile generator | tile_id* false path | Static tile-ID strap; guarded absent port, not dynamic payload. |

PGSTREAM-B successor review (3b75581c1, not yet bound): bank-request write4n/read4n+{4,5,6}/rewrite4n+8 proves setup4q hold2q. Injection write12m+{0,3,9},read+{4,8,12},rewrite+12 proves setup3q hold7q. Return early stage claims2q/4q and remains linked to the bridge bench. Arbitrary fault/reset changes are NOT covered by these windows. Old pgf_s is combinational OR of sticky sources, fs[0] the first sync stage; root is adding a registered source. rq_s/rs_s are direct2ff reset-release synchronizers. Mixed seam+exact CDC tooling is next, never a blanket cross-clock waiver.

Each *_scan.json records every inspected constraint/spec file hash and matching line. scan.py uses only selected kit paths, follows sdc_extra/boundary_tcl paths, does not decompress a whole repository, and reads exported scripts as well as specs. This is an inventory, not semantic proof of arbitrary Tcl. Structural lint receipts and physical gate results remain authoritative. S81 declared child views are included even where parent itself is still a stand-in.

Per-kit inventory:

| Scan | Kits | Inspected files | Missing kit paths |
|---|---:|---:|---:|
| s81 | 23 | 386 | 0 |
| s81_children | 29 | 470 | 0 |
| qwen | 18 | 298 | 0 |
| kv | 49 | 596 | 0 |
| hbm | 71 | 1134 | 0 |
