# QC-INHOLD-BUDGET handoff (Opus 5.5, split from QC-STATION-REGEN 11-23 23:2x)
Job: QC boundary input-port hold (port -> u_bin), die-level margin + structural/contract row.
## Contract (stated)
plan clock.seam_hold sender 25 / seam 110 -> kit vclk 250 TT, set_input_delay -min -85 on non-ring inputs; die_sta_related = register model at common 250 unless --kit views.
## Measurement (01:0x, posted 9cf4825494c9)
Exact pairs, kits reproduce own OT_CTS_POST_TIMING: A slw_fw_v2__cl8537f156 <-> slw_stm_v2__cl1ca9c415, B sle_fw_v1__clf58b4dfb <-> sle_stm_v1__cl27746664.
TT >= +5 all buses; FF fw->stm x_fw_i/x_fw_p1_i -10..-21 (103-216 bits), stm->fw B x_fe -5.9, l9_wi -2.7. No CPPR, no seam wire, placement RC.
Data: epyc10 /srv/opentallas-scratch2/claude/QC-INHOLD-BUDGET/{kits,io2,tools}; tools/pair2.py combiner; tools/io_dump2.tcl (kit RC, no platform setRC).
00:13 table WITHDRAWN (platform setRC re-source bug), correction 0840f644.
## Row (draft 01:2x)
epyc7 /srv/opentallas-scratch2/claude/QC-INHOLD-BUDGET/row/ROWS_QC-INHOLD-BUDGET.py + guarantee.json: measured sender out_hold_check_ps = max(0, FF min(out arrival - vclk) - 20) (fw 0, stm 9.4/9.6); receivers with all fw/stm senders measured -> clock.io_hold sender_min (4 types). plan_inhold.json on C1-noSU base. PRE queued (row/pre.sh, ot-run epyc7).
Pin-face tap (b) rejected: PINFACE-TAP 00:28 measured pin flops at bound worsen internal crossings (stm CORE->PIN 109->618).
Residual FF -21 real -> receiver port-path hold ECO under the measured contract (needs FABLE-RC-QC accept; OT_GRT_NONPORT_HOLD excludes port paths today).
## 02:1x update
Row A (contract): row/ROWS_QC-INHOLD-BUDGET.py -> plan_inhold.json 13cedebaf33c.
Row B (COORD ruling, structural, no kit port repair): ROWS_QC-INHOLD-HB4.py: hold_hb4=2 on x_fw_i/x_fw_p1_i of all 9 *_stm_* -> plan_inhold_hb4.json 20f6859d4f4e. What-if: die FF worst -21.2 -> +38.4 at 29.8 ps/HB4; die TT setup 673 -> ~575. Lockup/early-tap rejected (posted).
Row C (COORD cbf_q11 item): ROWS_QC-INHOLD-CBF.py: cbf_q11 reset.pin_entry_delay 10+10 BUFx4 -> plan_inhold_abc.json 5da137fdf245 (FINAL combined). cbf kit re-read epyc8 io2/cbf11 (hold -104.80 TT/-48.5 FF, setup +771 TT).
Gates running epyc7: PRE row/pre*.sh (logs row/pre*.log); scoped strict bind bindS (4 fw/stm types, plan hb4; mirror dir of plan_of_record because relative refs) and bindC (cbf_q11, plan abc). Next: private-spec --plan abc --tree QC-ALLFIX/cC/tree --bind-out bindS/bind or bindC/bind --goal cts --rt 70b6f0430ea9, run-item; read HB4/BUFx4 delays + internal hold.
## 03:2x CORRECTION
Row A v1 (out_hold_check_ps 0/9.4) WITHDRAWN: FF vclk is 250 in kits (not 202.5); output min SDC +32.3 (=-25+W 57.3). v2 = io_hold sender_min, no out_hold_check_ps (in_min +37.5 plan contract) on 18 fw/stm types.
Final plan v2_abc.json a471e0ccfff2 (row/ROWS_QC-INHOLD-BUDGET.py v2 + HB4 + CBF). PRE row/pre_v2.sh; full strict bind bindG (rt 70b6, no --types: probe-only binds lack bound_top so kit_rtl fails; scoped binds also hit LATCH_EXCEPT unless cb types included).
Then: kit_wave.py private-spec qwen_compute <type> --plan bindG/mirror/qwen_compute/plan_of_record/v2_abc.json --tree QC-ALLFIX/cC/tree --bind-out bindG/bind --host epyc7 --goal cts --rt 70b6f0430ea9; run-item (rt/8a8a.. printed). Types slw_stm_v2__cl1ca9c415, cbf_q11.
Budget table post 52ca44df; class row for C1i pending C1i path from QC-ALLFIX.
