# QC L2 publication: parked for Claude reset 2026-11-16 19:50 PST

No Kf tuple/apply/hold changes. Scope is preparing l2 source/context for QC-PLAN-R.

Running jobs:
- E8 oth-ubuntu-515839-1794887290, intel2 client PID2111615; log ~/qc-plan-r-l2-logs/publish_s4q9l2_epyc8.log. Script E8 /srv/opentallas-scratch2/claude/tools-converge/qc/l2_closure_1116/publish_s4q9l2.py: data_pack (DONE) then delta_apply (RUNNING at handback), publish. Source57GB copied, not hardlinked. Target kw45/src_qc_pin_eb1e73448bd0_s4q9l2.
- E7 oth-ubuntu-1886480-1794887361, intel2 client PID2134273; log ~/qc-plan-r-l2-logs/publish_s4q9l2_epyc7.log. Script /srv/opentallas-scratch2/claude/tools-converge/qc/publish_s4q9l2_epyc7.py: copies E8 delta, applies/publishes, then copies raw context and runs relocate_bind_s4q9l2.py epyc7 automatically.
- E2 raw context staging DONE exit0: oth-ubuntu-4160735-1794887290, client2111617; log ~/qc-plan-r-l2-logs/l2_stage_raw_1116.log. Copied553 raw bind files and166 treeJ reference hashes to E8 l2_closure_1116/raw_bind_s29q103S4Q9L2BQ. Raw bind original untouched.

Delta has exactly3 added files: plan physical/die_plan/qwen_compute/plan_of_record/zz_s29_qc103_s4q9l2.json SHA19be3f0a3bb42d8ea1a388412843e1d80e98563041d169899e54c22a47dffe82; its cland_bin_sites53455fa4; kit_pricing a4b65fb1 copied from qualified Kf against unchanged portable manifest65000b.

Manifest reuse evidence: raw KFBQ/L2BQ injected manifests differ ONLY clock_landing_table, land_r8, land_r8_extra path names. All4 payload hashes match (c71a3feb/38336cfa/60098047/46a62e7f). Raw compiled asbuilt.json ec5fb2617e746d758e0196accf2bef60a752b35936634fc82552013a7ccb4142 and asbuilt_sources.json ed45aca575c36289e8cd206f403675f7af377d7c013fef9aeb568f6ecc0e7e0e are byte-identical KFBQ/L2BQ. Reusing existing asbuilt_jkf_portable.json65000b and Kf runtime asset names is intentional. No new CM semantics, no ELAB/bind/LATCHECK replay.

Next: collect publication receipts. E8 context relocation MUST be launched manually after publication:
python3 -I /srv/opentallas-scratch2/claude/tools-converge/qc/l2_closure_1116/relocate_bind_s4q9l2.py epyc8 (through ot-run from intel2). It was adapted from the qualified Kf relocation: native_contract equality and bind_matches130 required; uppercase L2 runtime paths map to existing Kf names only on matching payload SHA. E7 auto-runs the same script after its publication. Context target kw45/qcbind_pin_eb1e73448bd0_s4q9l2/bind_s29q103S4Q9L2BQ. Then current normal tree guard E7/E8, candidate tuple preserving holds, parent QC-PLAN-R applies after Kf.

Initial direct remote-self ot-run launch wrappers on E8/E2 refused DNS self-alias before admission (NOT RUN), logs retained in remote stage dirs. Intel2 launches above are the only admitted jobs. No live job patched or cancelled. No git operation in owner checkout.
