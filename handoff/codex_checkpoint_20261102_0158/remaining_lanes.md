# Remaining lanes worker checkpoint — 2026-11-02

Worker: `/root/remaining_lanes`. This is a checkpoint, not a stop/reset. No owned runtime/CAD jobs are active. Original jobs/controllers were preserved; no foreign worktree was edited or foreign job killed.

## Historical lane coverage and current tables

- Reconciled remaining lanes against `/home/ubuntu/coord/tmp/codex-takeover-2032/all-lanes-inventory.txt` (494 lane files) and `handoff-lanes.txt` (493 handoff sections), routing meaningful current tasks to the six owning parents. Avoided rerunning superseded archives.
- Collected historical DIE-CI `origin/claude/die-ci-results:results/die_ci/2026-10-27_262d07038412`: S81 overflow 7,062,724; KV overflow0 but hub_Ei station geometry failure; QC overflow9; retired HBM B2l G0C7712/xdie202. STA NOT RUN. KV exit1 missing raw log remains explicitly unqualified; committed reports survived deleted raw paths.
- Current staging helper initial `db86f9bf9` reuses canonical `/home/ubuntu/coord/tools/release_tree_plan.py` materializers, with explicit SHA/nonempty-dir refusal and STATIC-only argv. Static run in `/srv/opentallas-scratch/claude/codex-current-ci-2049`: S81 G0C1 oversized kv_leaf__t2; KV27 cuts; HBM250 failures. All routed to current owners. FLOW disabled only future stale nightly timer; active service PID187808 was preserved.
- Base compiler tables `95c7bbfc7`, `results/current_plan_latency_1101`: S81 873 lanes digest7bf83d029cc5ffb7; KV2404 d4710b2e4571100a; HBM357 dac93bceaf90640c. Native KV join `b9a2c7194` all2404 base costs match. S81 canonical table `cc25a7f88` paired with DS consumer5bdc9d371. KV current native R8 candidate `7191a31ce`: 6167 member joins;393 padded lanes; maxpad116; final max121; no pricing/calendar activation.
- HBM exact old staged input: `.../codex-current-ci-2049/physical/die_plan/hbm/plan_of_record/d44c/por__die_plan.json`. Sent HBM owner shared command `python3 tools/die_plan/gen.py latency EXACT_NEW_PLAN --out OUT` for its new coherent event; no old357-table adoption implied.

## Protected-folder incident and actual deployed fix

- User-authorized transcript recovery: main Claude JSONL `/home/ubuntu/.claude/projects/-home-ubuntu-OpenTallas/b7f906df-7fae-44f7-85c4-22c768baf49f.jsonl`, nested subagents.
- SS20 `agent-ad8801f90f87c865d.jsonl` did NOT launch CAD/controller/VSW jobs. PRUNE-H `agent-a8dd5822b5de97ca1.jsonl` only scanned disks/processes.
- KVFN actor `agent-ab8937fb00a3b056c.jsonl`: own prune deleted b_es145/b_fx at18:29:52 PST; retirement record/removal followed at18:31:14, approximately82 seconds later. Do not reverse this ordering. Coord retirement commit `a04cee8bc4d49dad06075db19a863858e31ae24b`; current veh60 preserved, obsolete vehicles need no rebuild.
- Root cause of subsequent false MISSING alerts: SS19 append-only manual extra cache resurrected the two owner-retired rows.
- Shared helper `tools/fleet/protected_extras.py`, final source `3a2d785ce`, merged main `0725cdcb532c7676a4427539def6d7b00fc50e24`. Exact manual retirement filter preserves automatic SIGNED/NEARCOUNT priority and ordinary missing checks;3 targeted cases passed.
- Retirement receipt `/home/ubuntu/coord/lanes/RETIRED-PROTECTION-EXTRAS.tsv`, coord commit2fa959842.
- Deployment DONE using fresh central helper: locked manual cache41→39; normalized4 unambiguous legacy space rows to TAB preserving annotations. All231 automatic rows unchanged; manual unique40→38; final269 paths; unchanged audits all3hosts0 MISSING. No heavy recount forced.
- Own compatible successor hooks: `/srv/opentallas-scratch/claude/codex-protection-cycle-2159/hooks/{cycle.sh,regen_protect.sh}`; backups/audits/receipts nearby, `.keep`. Original private SS19 controller/scripts untouched. Coord deployment milestone `f12ebc3ef`.

## Independent source reviews and closed bugs

- MODEL-CORR acedd3ef7/947dd4bf1 is content-absorbed: current model_corr.py/golden/test_clk_cell_cal.py/buf_master_cal results byte-identical. QBS owner confirmed no new calibration need; real blocker is PG/row/site/orient legality. No duplicate NLDM/QBS runs.
- GRT final-full helper `d89be7729`:7 focused tests PASS; reviewed pinned ORFS hook order read-only. Standalone/defaultOFF diagnostic approved. It must be sourced LAST after post-mutators; count of CLOCK nets is not full physical-clock qualification. No RED CAD duplicated.
- Reset recognizer cf7ed4b9b initially accepted two invalid actual graphs: functional data added to final reset FF; extra mask-output capture. Exact repro `/home/ubuntu/coord/tmp/codex-reset-mask-review-2321/repro.py`. HBM owner hardened to mandatory native typed cone (`f9b5acad0`). Independent test-only `5aafc2ea4`, branch `codex/reset-physical-controls-2340`: native9-positive + original mutants + typed-only and coherent typed/untyped D/RESETN/SETN/CLK rewires all behave correctly. Semantic reset errors asserted, not merely receipt mismatch. registration_release=false; no gate integration.
- R8 projector held141a86bae had global same-name instance ambiguity. Corrected `3d3b86703` checks exact owning instances and raw plan type; independent12tests PASS. Root integrated. No cap relief:903118>400000 remains failure.
- Optional inverse-cube proof `0c84369b0`:11 tests PASS, no must-fix soundness issue found. BASE uses raw native ternary reset from unknown initial state, restored profiles rechecked; STEP re-proves relation jointly with all hypotheses; inversion/X handling consistent. Actual native NF2 proof remains FLOW-owned.

## QC private two-peer model and SerDes domain diagnosis

- Private packet `af80487c7` + final `bd08c4063`, branch `codex/qc-phy-pair-2345`, `results/qc_phy_pair_1101`. Exact authority: frozen bd55b15b452761be8ceefeae7b97abdf4a915bd4; acceptance82190c1ff/paired-plan f79c1e228 are COMMIT prefixes, not counts. Actual epyc2 `codex-qc62-collect-1101/bind_complete4`:377parts/119types/790393bits,639 top ports; canonical plan SHA913be9b7f5ee612824f323d3d476999a36e2f224f1c3139f163d1b6558cdaab7.
- Intel2 job `oth-ubuntu-4087940-1793606663` completed exit0 at2GB/1T. UCIE FW1043/LAT4 generated1000ps: accepted324/227, delivered222/318. SerDes FW597/LAT223 configured833ps: accepted699/489, delivered222/318. Both active peers, bursts/gaps/all bits, exact latency/UP behavior,2 async resets. Payload mutants reject cycle5/224; unchanged stale UCIE combinational-TX model rejects between-edge TX. Final2fs settle ensures last reset assertion executes before finish. No full hierarchy/runtime mission/adoption/global model swap.
- Selected UCIE remains MODEL_ONLY/physical_qualification_eligible=false, no real hard/lclk provider. Canonical coll_ucie still old non-lclk abstract. SerDes metadata1GHz vs configured vehicle-policy833ps is explicit, not qualified physical timing.
- Precise source-domain packet `3c1869bd8`, branch `codex/qc-serdes-clocktrace-0010`, `results/qc_phy_pair_1101/clock_trace/{README.md,capture.py,trace.json}`.
- TWO generator causes: bind.py emits FDI bin/bout/FT on default `.clk(clk)` (core for mixed-domain faces); clock_landings.py rewrites every default including bare PHY native serdes to regional, and verifier expects regional. Native qfd_static_ch546 already implements core↔FDI CDC inside each face; added transport lies outside it.
- Actual inventory:15 FDI boundary groups/3606 payload+epoch FFs;95 third-path FT groups/22838 FFs in c_W5_bf_00/01, excluding CA/control.15 lanes: direct PHY0/1 costs2, third TX26/RX+up28. Native PHY roots pll_serdes0/1/2 alias explicitly to existing serdes; native codec/TX-read/RX-write retain that source.
- Disabled typed proposal refuses RTL emission: three hard-pin bindings alone are insufficient. Need per-bus FDI roles through boundary/FT/CA/FCLK/FSTART/reset plus domain-unit calendar repricing, preserving mission833. No naive3-port fix or slow regional root. Fresh complete vehicle without START correctly refused313pst inputs; no fake provider or compile.

## DPI top linker review — final hardened review NEXT

- Original `c01e8d80a`, branch `codex/hbm-top-link-0015`, `tools/hbm_layer_vehicle/link_generated_hier_top.py`.
- Frozen SOURCE13 old downstream42 ONLY, not disabled47. Actual child cache Intel1 `/srv/opentallas-scratch2/claude/tok-qk-2-hbmsrc-1101/source13/elab13/obj`;86 completed child frontends/~37GB untouched. Original parent32GB OOM; standalone resolved parent frontend passed4.92s/166052KiB. No archive/link/runtime/TB/numeric mission credit.
- Inputs copied at `/home/ubuntu/coord/tmp/codex-source13-top-0010/input` (31MB selected_preprocessed.sv, raw top, obj wrappers/args). Runtime packet Intel1 `/srv/opentallas-scratch2/claude/codex-source13-top-0010/linked_native`.
- Independent original guard replay:90 instances/82 direct variants/1083 effective assignments; all original top/PP/args/linked-top/wrapper hashes and row graph EXACTLY match published structural_join.json. Actual685 formal declarations fixed packed/integer after inherited context; no untyped formal or escaped top identifiers. Unconnected `.y()` preserved; duplicate/missing/unknown-module controls reject. Actual wrong8'h7f→7e rejectsNW_mcb; real DPIclk rename rejectsNE_b000.
- Found actual reusable-guard bugs: integer-only params conflate width/sign/type (`P=1'b1` vs override32'd1 changes $bits/body); comma multi-instance declaration checks onlyfirst; selectedPP hash recorded but no frozen cached-source epoch enforcement; duplicate wrapper names silently overwrite. Owner informed and fixing. Repros `review_repro.py`, `review_grammar.py`; exact actual receipts `review_actual_0035/` in coord tmp.
- Latest owner tip **8c64782b4** (supersedes468710c02), not yet independently reviewed here. Owner says fixed numeric formal/inherited typing, literal coercion, no untyped forms; finite declaration/instance accounting; duplicate/trailing/control/initializer rejection; all86 actual VerFiles PP path/inode/size/mtime/ctime + exact wrapper T-record + child -G/command/argument-age checks. Actual owner90/82 pass, linked_top bytes identical; no frontend rerun. Updated receipt `linked_final/receipt.json` remotely and `typed_structural_join.json` committed.
- NEXT: inspect8c64782b4, run focused width/type/grammar/cache-epoch negative controls and exact linked-top/port graph parity. Keep general reuse/root merge held until final review. Coordinate `/root/kv_qwen_token`; owner holding further changes unless real issue found.
- Own clean review WT `/srv/opentallas-scratch/claude/wt/codex-hbm-link-review-0030`, branch `codex/hbm-link-review-0030` currently basedc01. Earlier PHY/trace WT `/srv/opentallas-scratch/claude/wt/codex-qc-phy-pair-2345`. No own runtime jobs active.

## Other steering retained

S81 cap_rt A first async reset path is MET+313.88, not the TT failure. Actual worst TT−108.98 is la_gs[1]→fa_kh data/control; owner is collecting corridor identities. Do not retain a reset-repair-next classification; no duplicate CAD.

No new OWNER question beyond root's existing real-UCIE-hard-provider question. Continue work after checkpoint; user has not said Claude's limit reset.
