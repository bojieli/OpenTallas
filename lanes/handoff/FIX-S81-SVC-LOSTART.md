# FIX-S81-SVC-LOSTART handoff (Opus, started 11-23 02:1x PST by FIX-LEDGER; ledger rc25)
Goal: row SVC-LO-START-INTERIOR for svc_lo_dsdv_svc_rs t1-t7 + rs_w t1, J9 S81 (Wave A gated by 10:30, hard stop 12:30).
Co-owner/reviewer: FABLE-UNC-S81-SVC (ad36422a39196fd09). Peers: OPUS-FIX-S81-SVC-R9 (acbf5f53765607888), S81-J6-ASSEMBLY-R5.
Agreed with R9 (02:3x): my row REPLACES R9 j8_start_residue sidecar for lo types; R9 keeps hi rs t4_att.
Compose order (R9): SPLIT-F65F, replayed rows, YTRADE, ES1, WESTRIP, tapfix, THEN this tool. Test on R9 rebase plan
epyc10 /srv/opentallas-scratch2/claude/opus-fix-s81-svc-r9/rebase/plan_f65f_svc.json (sha from R9).
Findings on J8 f65f: all 8 lo types have NO landing_reader/writer_start (START hops 259-4087 um); reset tree depth 16
(t6 17) is Manhattan-bound (NE entry -> SW tap / 275 um), 75-80% of reset relays already interior -> reset tree not changed.
Macro sea: x gaps 15.12 (A rows) / 8.64 (B rows), y gaps 8.64, a 17.28 y street at 1304-1322, N block 2430-2820 no gaps.
fix_start corridor keeps 8.82 um off cores -> all closed -> perimeter. Kit needs only 6.48 (window 4.32 + margin 4.32).
Tool: epyc10 /srv/opentallas-scratch2/claude/fix-s81-svc-lostart/tool/svc_lo_start_interior.py (A* over kit-legal sites,
Manhattan hop 340, monkeypatches reach_rules._trunk, rest = _fix_start).
Work dir epyc10 /srv/opentallas-scratch2/claude/fix-s81-svc-lostart (tree fork treeJ8 in progress). NOTE: an3.py wrote a
stray file geo_j8.json into the protected s81-j6-r5/j8_cut_tree root (reach_rules._load chdir); ot-delete refused (protected).
## 03:4x status
- R9 ruling: compose SPLIT-F65F -> atto -> YTRADE -> ES1 -> tapfix -> LOSTART -> PRE. Rebase plan 189008ce34df.
- Tool b77f35d5f692 FIXED all 8 on J8 (p8 28066369eb73, ops o8 81ae6df82e6f) and on rebase (e15f03443e27 / e72e9b40a7e0).
- PRE --baseline J8 PASS 0 findings, adv 84 (gate/pre.log). ROW-DRAFT posted 03:4x.
- Gate script tool/gate.sh (fixtaps scan, G0 vs intake g0_j8, strict elab+bind EMIT_J=4, LATCHECK) via ot-run --mem 260 --disk 15
  --priority die on epyc10, log gate/gate.otrun.log. On green: post ROW-GATED to FIX-LEDGER + R5 + FABLE-UNC-S81-SVC.
- epyc9 + epyc10 tree forks abandoned (cross-host 0.7 MB/s; epyc10 disk <100 GB); PRE/gate read J8 tree read-only (-B, no writes found).
