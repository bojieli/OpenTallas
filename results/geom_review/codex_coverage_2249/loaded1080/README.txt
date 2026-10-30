2026-10-29 23:58 PDT retained native LN7 lane40..43 proof

Exact original kit/AIG source: intel1 /srv/opentallas-scratch2/claude/hbm-cores-kits-24/k2/kits/ot_hbm_su_static_pgslice_lg__lanes8_11_b9339253674f-_k26. Original lec/lec.json NOT EQUIVALENT 66265/67345 remains unchanged. No RTL, netlist, clock, latency or plan edits.

1080 untrusted conditional loaded-valid hints: lane0.p0=0 under ldp_v, lanes0..3.p2=0 under ldp_v, lanes0..3.q2=0 under ldq_v. Each 5 streams x24 bits. Reset guard starts false; joint induction proves each loaded constant from actual source. Outside guard Q remains free. No unconditional power-up zero.

Positive nominal_metadata: all 9369 retained hypotheses restored, zero re-sided/dropped; exact retained gold.aliases.json restores 872 gate Q aliases plus packed off0/off1 array keys. 14359 expanded joint claims proved. All 68425 final compares proved (original 67345 +1080 new loaded checks). 1080 loaded retained, zero drops. elapsed155.02s.

Wrong-value mutant_metadata: ONLY lane0.g_s[0].p0[0] loaded value 0->1. Joint induction drops that exact claim; remaining claims prove. Final 68400 proved /24 differ; mutant caught. elapsed191.38s.

Replay invocation: python3 retained_loaded_native_1080.py --input ORIGINAL/lec --kit ORIGINAL --out nominal_metadata --tool lec.py --restore-native-profile --restore-keymaps --metadata-keymaps-only; mutant adds --mutant. Existing native metadata keymap functions and prove_profile prove all old/new claims jointly. No geometric or LEC thresholds changed. Full canonical kit/KEEP/implementation authority remains the ordinary fresh kit LEC flow; use loaded_hints.json through existing --hints on the exact semantic family, never overwrite old FAIL.

Diagnostic failures retained under intel1 codex-coverage-2249/loaded1080/{nominal,mutant,nominal_profile,mutant_profile}: initial custom reconstruction omitted gold.aliases.json, losing native keymaps and introducing1184 downstream false differences. All1080 new claims themselves proved. These failed attempts are not adoption evidence. Slower nominal_fresh/mutant_fresh (without aliasmetadata, launched earlier) and nominal_keymaps/mutant_keymaps (full heuristic relayout) may still run; authoritative bounded replay above is complete. Do not delete or conflate artifacts.
