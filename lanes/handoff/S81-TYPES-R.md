# S81-TYPES-R handoff (successor of FABLE-FIX-S81-COLTAP, FABLE-FIX-S81-CONG, S81-IFN0-HALVES; started 11-16 17:1x PST)

Owns S81 col (216), strip leaves, IFN0 halves. Three tracks:
- COL (this file): five pilots under epyc10 /srv/opentallas-scratch2/claude/fable-fix-s81-coltap/countable_F2s4tapfix1 (current819 / D3).
- IFN0: notes in S81-TYPES-R-IFN0.md (fork worker). he_splitclk1 epyc2, CTS done; hw split form to build.
- STRIP (bg_bare, eight-leaf constructor, t34 VQ +43.2, t43): notes in S81-TYPES-R-STRIP.md (fork worker).

## 17:2x COL state
- GEN client intel2 4018771 / E10 unit oth-ubuntu-1482040-1794876086 still running (4 of 5 kit dirs present, r2 last). No physical launch yet.
- Plan per kit: transport off E10 by ot-run --stage, run to cts (place image in run/layout_review/place + OT_TAP_CORE + an/stage_sta.sh cts), LOOK, then route -> sign-off.
- ROM-read class (r2: rd_out -> s q -57 at sequencer lead 100): kit core_latency.txt u_s1x clk[0] 371.22 -> 311.22 (lead 40, ROM 255) on r2 / r1 / h10_r2 pilots; row core_pin_lead_ps cfg7_seq 100 -> 40 goes to S81-DIE-R when measured.
- Reset-chain class: v5 hook (epyc10 + localhost reset_chain_spread_v5_candidate.tcl; epyc9 copy is stale) = source from gp_noconverge_gate.tcl + export OT_RESET_CHAIN_SPREAD = 1 in config.mk. Staged only; needs post-DPL hop + CTS proof on the current r2 kit, then tools/die_plan integration + gate.
