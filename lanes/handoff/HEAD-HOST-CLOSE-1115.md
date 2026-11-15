# HEAD-HOST-CLOSE-1115 handoff 11-15 14:30 PST
- hd_host_e: cause = u_epc macro internal clock 488 ps on grid tap (eff 791 vs 450); fix = plan row early core tap. Private variant v1: epyc7 /srv/opentallas-scratch2/claude/head-host-close-1115/v1 (plan copy+republish+kit_rtl+gen; script /tmp/v1gen_hhc.sh VNAME "X Y"), kit epyc10 head-host-close-1115/v1k2 (run_kit.sh route 90 8, log ../v1k2_run.log). STA diag scripts: epyc10 head-host-close-1115/diag*.tcl, out/; intel1 hw5/.
- hd_host_w: logic-depth families in u_hbc loader (RTL) + 64-load BUFx2 select fanout; hd_serdes: tap trees over 470 ps (t8 822). Posted RESULT 14:30 in COORD-REVIEW-QUEUE.
- Next: read v1k2 post-CTS gate; if setup_est >= -42 continue to route/sign-off; check serdes a4 / host_w a6 post-CTS on intel1.
