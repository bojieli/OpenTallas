# OPUS-FIX-QC-V4-R2 handoff (Opus 5.5; succeeds FABLE-FIX-QC-V4, Fable 429 until 11-29: do NOT message it). Started 11-22 22:3x PST.
Briefs: scratchpad succ_brief_1123.txt -> family_brief.txt, rules.txt, fable_fix_brief.txt. Predecessor handoff: lanes/handoff/FABLE-FIX-QC-V4.md (layers, scripts, rulings).
Goal: V4 layer handed to QC-PLAN-R13 for the 06:00 PST 11-23 cut; V5 (su re-seat v5b, + sink-bin taps v5c) bind clean -> probe-through + sealed --goal route kits -> sign-off.

## Adopted jobs (22:4x PST)
- epyc8 /srv/opentallas-scratch2/claude/fable-fix-qc-v4 (97% disk): l1a bind unit oth-ubuntu-452174-1795397490 (R8 pass 2 since 18:47 PST); l1r bind unit oth-ubuntu-3488884-1795402191 (pass 2 since 20:16 PST). SLWSLE l0su (theirs) oth-ubuntu-3443682-1795402107.
- epyc10 same path (96% disk, keep new forks off it): v5b bind oth-ubuntu-239184-1795413599 (plan pre b71e4cb7bd36); v5c bind oth-ubuntu-578698-1795414438 (pre 2ce554682f4c; TAPNAME v5c fails 0 warns 0).
- v5a orphan statics: ot-run clients 172541/172543 TERMed by exact PID 22:4x; units 177233/177320 were still alive, re-check.
- l0b_bound (epyc8) = V4 core, clean, handed to R13 17:4x.

## COORD rulings (11-22 22:3x)
- 13 residual over-cap taps stay unless a probe shows clock/timing failure. Soft types: outline growth or relaxed tap spacing (whichever faster); core types: core growth/re-shape.
- SLWSLE's clcc9d0155 re-seat candidates = separate parallel kit, coordinate with SLWSLE.
- v5d cancelled; fold sle_su_c clk_t181 (254.368, 286.304) into the next change (taps/rows2.json on epyc10).
- After V4 applies, clf4365a62 hold released by SLWSLE (abe4ea21d93765caf).

## NEXT
1. l1a / l1r end -> read CHAIN_DONE in l1a.log / l1r.log; if clean: plan_gate_pre rt 312978162669 on l1r (Wadv/launch) for ADV-PORT-PIN strap_r8pad; hand the highest clean layer to QC-PLAN-R13 before 06:00.
2. v5b / v5c clean -> kit_wave.py private-spec qwen_compute slw_su_l1__clcc9d0155 and sle_fw_v2__cl6740750e --tree <bound>/launch? (check private-spec flags) --goal route, plus OT_PROBE_THROUGH=1 probe kit; host via admission (not epyc10).
