# QC-TTCTLM-PROBE handoff (lane memory), child of QC-ALLFIX, started 11-24 22:00 PST
Owns: tt_ctlm probe + (COORD 00:50) the QC STALE group: slw_fe_v1, sle_st_b_v2. Status line per item every 30 min while chains run.
## tt_ctlm (intel1 /srv/opentallas-scratch2/claude/QC-TTCTLM-PROBE)
- Plan plan_ttc.json 3854ae7ced25 = C1m-rc dffd12ce2cfe + dead_inputs[tt_ctlm].module_sha256 -> df62aafd98db (1 leaf; guard 0 silent). Tree = ot-tree-fork of E11 QC-CB-C1L/m/tree + core 2c21ec82950f + proof d5d6178d1718.
- chain.sh: bind.sh (unit oth-ubuntu-2709870-1795588418, rt 6e9705f7fe67): PRE 22:33-23:42 ROWS-NO-PROOF only; elab OK 00:45; scoped strict bind --types tt_ctlm from 00:46 -> kit.sh (private-spec goal route, --ab TAP_ESCAPE 0.30, PORT_HOLD_PORTS=1, PORT_HOLD_MARGIN_PS=10) -> runitem-tt_ctlm on intel1. Logs bind.out, s/bind.log, kit.out.
- RSTREACH WARN = PRE plan-only false positive (QC landing_local_resets fstart_0..3, worst 76 um site->pin, 290 um relay->site). Confirm: rst.sh (RSTREACH-only PRE --elab-dir s/bind) queued on intel1 memory -> rst.out.
- Posts due: launch line; GRT (setup/hold/depth); sign-off. GRT setup < -150 -> structural cause, no retry.
## slw_fe_v1 (00:57 post): no relaunch, no SETUP_TRIAGE stop. cl08d14f0d C1h kit alive E9 detail route (owner QC-FEV1-CL08 -> C1n-r2); cl95cd1d0c alive intel1 GRT; cldb4efe33 E9 placed 18:32 no process (flagged).
## sle_st_b_v2: plan 44a145a65013 (C1k + STB-SPLIT ring row), full strict bind epyc2 scratch3 QC-STB-SPLIT/bind. My probe clfde1249e: runitem-sle_st_b_v2__clfde1249e on epyc2, spec (epyc2 ~/coord) private_specs/QC-TTCTLM-PROBE/qwen_compute_sle_st_b_v2__clfde1249e_1125005649, script epyc2 /srv/opentallas-scratch3/claude/QC-TTCTLM-PROBE/stbkit.sh. QC-STB-SPLIT own probe pvcd986c42 in route.
