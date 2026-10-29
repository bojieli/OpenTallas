## Handoff to Claude 2026-10-29 14:04 PDT — GQ stale-recipe regen helper

Explicit reset received from parent at14:02. Parked immediately. No GEN, synthesis, LEC, P&R or STA jobs were launched; no RTL/tool/recipe changes were made and no main merge occurred.

Prepared own clean sparse worktrees:
- localhost:/srv/opentallas-scratch/claude/wt/codex-hbm-gq-regen-1355
- epyc2:/srv/opentallas-scratch2/claude/wt/codex-hbm-gq-regen-1355
Both are codex/hbm-gq-regen-1355@fb1fc79593ba9a9e4d968b80f2cd75dc44f1a056. Branch pushed to GitHub and intel2 hub. Remote checkout completed successfully before parking; mk_c20.py is present. No long-running process or ot-run unit owned here.

Collected source diagnosis (not a new proof): PATH-HBM11:04 and13:42 identify old K13 tree13 SHA3dae1fc99a13 as pre-f437090e0. The1056 fmt and1024 gq_issue differences are stale-recipe failures, not a f437 arithmetic bug. Fix40235e1f116 is already merged in this exact main: fmt recipes_b2 and gq_issue harden/recipes_other pin tree13 to f437090e018c13d87f7854d83b40be0578f80b2a. The die owner previously checked fresh fmt synthesis+LEC16081/16081PASS. Those are inherited results, not rerun here.

Exact pending three views, all from old current catalog intel1:/srv/opentallas-scratch2/claude/hbm-cores-kits-13/k23/views.json:
- ot_hgi_coll_gq_issue@5c09aa5b506c,237.6x237.6,4032pins, q1 R0 table.
- ot_hgi_coll_gq_issue@c8c240c460d3,237.6x237.6,4032pins, q0 base table.
- ot_hbm_xp_aq_tree13_fmt@ed62ddb93a97,183.6x108,1807pins.
Plan snapshot intel1:/srv/opentallas-scratch2/claude/hbm-cores-kits-13/c25c_d16 contains275files, including clock_entries.json and canonical pin tables. No copy or regeneration was performed after reset.

Next authorized work after resumption: copy the applicable plan snapshot into own scratch (or use die owner's newer plan with these unchanged interfaces), run current views_b2r2 then mk_c20 for the two modules (three views), with ft-pin-dx1.08 and current hold defaults, all heavy GEN/SYNTH/LEC through ot-run. Verify generated tree13 reads the corrected recipe pin; fresh synthesis and canonical LEC are required. No cached old AIG proof and no blind copy-over. Render/view/record the current plan/pins before any P&R/STA. Parent cores_a owns remaining coordination.

OWNER? None. No failed verdict overwritten. The remote-source setup initially failed because epyc2 origin hub:OpenTallas sees hub local branches, while git fetch on intel2 only created a remote-tracking ref. Resolved by pushing the own branch into the hub local ref, then fetching on epyc2. Setup session41384 completed exit0.
