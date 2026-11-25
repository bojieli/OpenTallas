# QC-TTCTLM-PROBE handoff (lane memory), child of QC-ALLFIX, started 11-24 22:00 PST
Job: tt_ctlm private kit (goal route) on resynth core 2c21ec82950f (depth 71->21, QC-TTCTLM-DEPTH) without waiting for C1n.
Dir: intel1 /srv/opentallas-scratch2/claude/QC-TTCTLM-PROBE. Plan plan_ttc.json sha 3854ae7ced25 = C1m-rc dffd12ce2cfe + dead_inputs[tt_ctlm].module_sha256 -> df62aafd98db (1 leaf). Guard PASS 0 silent.
Chain (chain.sh, setsid): fork.sh (ot-tree-fork epyc11 QC-CB-C1L/m/tree -> tree) -> bind.sh (2 overlays + plan, PRE, scoped strict bind --types tt_ctlm, rt f3a64f1250d1, out s/bind) -> kit.sh (private-spec --goal route --rt f3a64f1250d1 --ab OT_TAP_ESCAPE_CLEAR_UM=0.30 OT_GRT_PORT_HOLD_PORTS=1 OT_GRT_PORT_HOLD_MARGIN_PS=10; run-item).
Logs: fork.log, bind.out, pre.log, s/bind.log, kit.out.
Posts due: launch (plan, unit, host, ETA); GRT (setup/hold/depth); sign-off verdict. GRT setup < -150 -> structural cause, no retry.
