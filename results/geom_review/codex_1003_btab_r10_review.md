# [QC-BTAB-CODEX R10 final GRT] PASS geometry

Reviewed exact final checkpoint intel1:/srv/opentallas-scratch2/claude/codex-qc-btab-0828/btab_m0_r10/run/results/asap7/kq_qfd_dv_s8x_btab_mif0r7/base/5_1_grt.odb. Read-only diagnostics, no P&R or STA rerun.

Full connected all-timed census: 3,442 FFs, 3,450 timed inputs, 3,235 source/capture pairs, maximum Manhattan reach 366.174um, zero above405um, zero loops. Rail-row audit covers all11,230 CORE standard cells including clock buffers: zero bad; MX5683/R05547. Actual nonPG pin census1322, zero missing shapes, E281/S1036/area5, peak E5.3/S5.0 pins perum in closed10um face windows.

Personally viewed codex_1003_btab_r10_placed.png rendered from this exact final ODB: four SRAMs retain open horizontal escape channels, aligned nearby S/E data bands, open centre entry and continuous vertical PG corridors. No cell wall or new geometric blocker seen. PASS permits FF hold-only continuation and normal DRT progression after existing source/canary gates. This is geometry review, with no new timing/signoff claim; existing author early-CTS window failure remains historical, final-GRT timing results remain author-owned.
