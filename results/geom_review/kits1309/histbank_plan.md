# S81 native histbank current-main plan review

Kit epyc1:/srv/opentallas-scratch2/claude/codex-s81-kits-1309/histbank_main/ot_s81ph_native_sel_hist_bank_hb1309m, hash4652a55892f843e4, generated after integrating main427fea2689 and the failclosed modernlegacy gates. Viewed exact image epyc1:/srv/opentallas-scratch2/claude/codex-s81-kits-1309/histbank_main_plan.png.

Planning direction PASS-COND only: compact64.8x54 macro-free outline, W162/E176 data faces, N31 outputs/controls, S66 including64gsel +clock/reset. Scontrol zoom shows individual clock/reset sites with no overlap. Every face minimum centre spacing0.096um, zero duplicate pin centres. Pin sites, IO, PDN, track, face-flop and SDC bytes match the independently reviewed prepared5396e9868e58c444 kit. No macro wall or long unregistered crossing is introduced; standard PDN has no macro interruption. W/E near-track-capacity bins still require actual pin-access proof.

No physical result or route token: ordinary current canary admission is FAIL/HOLD, and fresh LEC/face/fanout/SDC gates must pass. Actual placement/postCTS images and TT/FF insertion/hold review are required before GRT/DRT. Only a SIGNED child can replace the16 BANK0 children of bksel_q; its parent must adopt435pin OT_HB_PINCOPY contract.
