# QC-TTCTLM-S handoff (2026-11-25 08:16 PST)
Job: Form S (pipeline stage + token fix) for tt_ctlm on RESYNTH core 2c21ec82950f (C1o v13 aa3a14fb7484).
State: FINDING posted 08:15 (post 87dd914a). No Form S row: broadcast loop u_11071/u_11072 is a 158-flop SCC with 1 endpoint >=19 levels (fanout class, Form R lever).
Deep ends >=19 levels: 332 in 4536-SCC (u_81536 loop), 136 in 1250-SCC, 318 self-loop, 30 feedforward. Stage in SCC = schedule change, needs RTL+program recompile (F5 recipe epyc7 QC-F16-PRODUCER/harness_src/.../witness_f5_1515/gi; XPF margin 23=23).
Trigger to resume: Form R placed probe (QC-TTCTLM-RE) misses on an in-SCC class.
Files: intel1 /srv/opentallas-scratch2/claude/QC-TTCTLM-S/tmp (an*.py, g.pkl flop graph), sparse clone ../clone (unmodified).
Token bench: epyc7 QC-F16-PRODUCER/tok/tt_ctlm_token_bench.py (ttb_runs.sh R1 form for a netlist).
