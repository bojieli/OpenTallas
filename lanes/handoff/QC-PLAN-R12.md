# QC-PLAN-R12 handoff (11-21 12:5x -> ; succeeds QC-PLAN-R11). Updated 11-21 19:4x PST. Read QC-PLAN-R11.md (gate recipe) + QC-PLAN-R10.md (V2 apply recipe) + lanes/handoff/QC-PLAN-R12-V3-INTAKE.md (ledger).
Cut 11-22 06:00 PST; apply >= 11:16. Codex (14:23-18:1x) built V3p3 under this lane; adopted as-is.
## Build chain (epyc7 /srv/opentallas-scratch2/claude/qc-plan-r12/)
- V3p3 f5d51696a2eb (ctl_strap/, rt 55344f311cde): rows 1, 2a/2b/2c, 3 (289 sited FT), 6, 6c; static G0 0. Strict bind ctl_strap/bind_v3p3.client.log (bash pid 3907503, bind.py pid 3948713) ran 2h+ stuck after TAP-LIMIT-INFO at 100% CPU (v3t took 27 min) -> diagnostic only.
- v3p4/: compose_v3p4.py (V3p4a = V3p3 + hc3_projection/v3p3_hc3_overlay + CTL rprog/hard-tap retaps + SU C cap clock from ctl_strap/suc_cap_trial/suc_cap_only.json), stage_v3p4.sh -> static_a; add_suc_slot.py (V3p4b = + SLWSLE su_c x_su_l1_ctl slots on slw_su_c cl92142dac/cl19bb38ef) stage_v3p4b.sh -> static_b; add_taps.py + stage_v3p5.sh (V3p5 = + clock.tap_balance_to slowest on st_a/glue/sle_ctl + tap_split.py --over, rt 3c2f3758f4c1 launch v3p4/v3p5_launch) -> static_p5. Logs stage_{a,b,p5}.log.
- Next: add coll package (FABLE-FIX-QC-COLL / FAM-QC-COLL-R3: wall + rebind 508->477 + faultpipe 8->11 + 92-group stations with sites) and calendar -8 overlay (token lane) when posted; then strict bind with rt 3c2f3758f4c1 (adapt ctl_strap/bind_v3p3_after_static.sh: plan, rt, out dir) + LATCHECK -> post-bind G0 vs b20 -> census -> pack/seal/apply (QC-PLAN-R10 recipe).
## Verdicts
- tt_ctlm: owned by R12 (Codex private RAE TT -36.34 / FF -121.93, qc-plan-r12/ttctlm*); not in V3.
- FEFW-V3-2 rejected (V2 already 2 stations). sle_su_c SLWSLE row = no-op vs V2.
- COORD rulings: faultpipe 8->11 approved; coll rebind 508->477 rides V3; calendar K-C = -8 (not a plan key; bound RTL).
