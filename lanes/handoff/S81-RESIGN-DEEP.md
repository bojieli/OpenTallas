# S81-RESIGN-DEEP handoff (11-15 08:1x UTC)
Scope: re-sign dsdv_idx_tx_n32, ot_s81_kp4_dchn, dsdv_bksel_q, qxpq_w10_gb_he/gb_hw with lower clock insertion.
Done: idx_tx_n32 forms idxA (vclk TT 400 / FF 324, CTS cluster 30/60, buffer dist 100) and idxB (TT 340 / FF 275.4, +-no_insertion_delay), kits at epyc*:/srv/opentallas-scratch2/claude/s81-resign-deep/{idxA,idxB}, chain.sh = run_kit + eco_loop. Base = signed s81-idx-b5 eco_vg/i1 (insertion 722.7 TT).
Findings: sdc_lint.json insertion fields must be patched with config.mk/SDC (done). First run failed GRT: OT_IO_HOLD_PAD needs 9 HB4 > cap 7; cap raised to 16; resumed on epyc9 (logs intel2 ~/rd-logs/idx?.otrun2.log). Measured pin-reg insertion unknown until signoff core_latency.
Not started: kp4_dchn (signed kit epyc2 head-serdes-2/e13a), bksel_q (S81-CORES-2 owns nsesc form on epyc8; no signed record in INDEX), gb_he/gb_hw (kits only in AGIdock opentallas-signed-1106/epyc5 s81-romq-b4/he_tgt, s81-romq-b5/hw_x8; RTL/run_kit not in archive subset, need regen).
Next: on sign, archive to AGIdock + rtx-pro with INDEX row, tell DIE-S81-92.

11-15 08:20 all 8 forms launched (idxA/B, kp4A/B, heA/B, hwA/B); bksel_q left to S81-CORES-2 (ETA asked).

11-15 14:45 state: heA/heB/hwA/hwB stopped at GRT hold structural (vclk below real insertion); idxA/B/C measured; faceA/faceB (kp4_dchn +1 cycle) running; bksel_q read posted. See lanes/FABLE-TRIAGE-S81.md RESULT 14:45.
