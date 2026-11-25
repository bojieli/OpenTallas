# QC-STACLK-RE handoff to QC-STA-PROBE (11-25)
Row CORE-TAP-EARLY-STA on C1o v13 aa3a14fb7484 / sidecar a142fe516f24.
- Patched plan 9339ff774fe6 (44 taps = 11 st_a types x u_r0-3.ck insertion_ps/insertion_ff_ps; diff vs v13 is those keys only; old values all 250/202.5).
- Files (epyc12): /srv/opentallas-scratch2/claude/QC-STACLK-RE/ct/row_coretap_v13.json, ct/plan_v13_ct.json; generator ct_v13.py (tap-name rebase, v2 values from the _bt3 views copied to root2/).
- PRE PASS: epyc12 --die, rt b7165c47a452, v13 drops, launch_b716_sul1 tree, findings 0, RRDRV 0, CABIND ok (preCT.sh, pre_ct_v13.log).
- Bind steps (not run): after hub line "BIND-PASS C1o v13 aa3a14fb7484" and bind_v13/latcheck.json with 0 errors (re-bind ETA 08:45), run the scoped strict bind of 9339ff774fe6 on a private copy of the fixed launch_c1o_bind (bindO.sh form), via ot-run --crit --priority die. Then ROW-READY with bind result.
- 24 v1 keys (6 v1 types x 4): re-measure after QC-RC97V1 signs the 4 _bt3 v1 masters (RC97V1 composes first), re-run ct_v13.py on the composed plan, publish a v1 delta row.
- RC97-V1 facts are in the hub post QC-STACLK-RE HANDOFF RC97-V1.
Waiters stopped; nothing of this lane is running.
