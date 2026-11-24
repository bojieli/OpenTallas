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
