# NP4 key replay slices — CODEX

## CODEX notes 2026-10-29 01:03 PDT
Root assigned structural source/proof after CTLX sizing packet. Own branch codex/keybuf-np4-1029@f3c8405b9 (main base e93e45262), WT /srv/opentallas-scratch/claude/wt/codex-keybuf-np4-1029, clean/pushed.
New opt-in modules ot_hnx_idxn_keybuf_sliced_np4 (NP4/RS0,pbase runtime; RS1 failclosed) and ot_hnx_idxn_quarter_with_keybuf_sliced. Existing packed/fixed-eight/default modules byte-unchanged. Quarter scorer/TP/DELIVERED_RESET/ports unchanged after explicit module+keybuf-selector normalization. Active paths quarter.keybuf.gp[0..3].u_line.

PASS: actual repository SRAM, golden17 packed vs candidate20 sliced; 13,824checks/3,456cycles/full4,396b/all171addresses/pbase0,4/698writes/1,720replays/16faultcases. PRE-next/replay-current overlap, same-address read-before-write, clear/live precedence, warmreset retaining SRAM. Wrongpbase/data/PREphase mutants caught; RS1 rejected at elaboration. Added core/data/reset/token cycles0.
Model:20vs17SRAM perquarter,80vs68 across4roles(+17.65%),+543controlFF/quarter(+2172 total). Old32reserved slices/160SRAM ->16active/80SRAM; leave remaining16 slots RESERVED until HBM jointVP4plan. Two241.92x293.76 slots+17.28street have501.12x311.04 envelope, adjacency/capacity owned HBM.

Job epyc2:/srv/opentallas-scratch2/claude/codex-keybuf-np4-1029, unit oth-ubuntu-197241-1793260509 EXIT0, allownjobs terminal. First model FAIL address128 diagnosed signed8-bit arrayindex; golden/candidate lockstep equal, model fixed mask255, failures preserved results/hbm_keybuf_np4_1029/failures. No RTL correction for it.
Receipts results/hbm_keybuf_np4_1029, runner tools/hbm_b2/run_keybuf_np4_miter.sh. ROOT-MERGE and HBMbind notified. Next: merge approved source, explicit C25c sourcealias/select, actual4roles+HCOLmapping, VP4jointplan, normalphysical/token gates. No G5/signoff/adoption claim. OWNER? none.
