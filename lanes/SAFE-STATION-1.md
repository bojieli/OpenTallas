# SAFE-STATION-1 (FIXED-BAY station safe form, S81 + QC; successor of S81-PROUTE-2) -- started 2026-11-03 06:28 PST
Worktree intel1 /srv/opentallas-scratch2/claude/wt/safe-station-1 (branch claude/safe-station-1-1102). Work dir intel1 /srv/opentallas-scratch2/claude/s81-fbay-1 (.keep).
## log
- Collected: predecessor's lockup FIXED-BAY t30__cl1653104c build ran 05:43 -> FAIL_PREFLOOR face_guard unregistered 1059 (out-face lockup DLLx1 drives the ports) = STRIKE 1. Lockup v2 (out-face plain) prepared but NOT launched (OWNER TWO-STRIKES: no tweak).
- Conservative form = relay at every <=300-um hop, +cycles declared (tools/die_plan/relay_bay.py). Hop grid: OpenSTA TT/FF, RCX ladder M5/M7, L 100-300/5, BUFx4 pitch 100/75/62/50/40/33/25 (relay_bay_hop_rows.json). pitch 100 at 245 um: hold +67 (FAIL); pitch 50: +91.4.
- Pilot build t30__cl1653104c relay-bay (gen3): ot-run intel1 mem 24, client on intel2 pid in ~/ss1/t30_relaybay.pid, log ~/ss1/t30_relaybay.log.
- Dry pre-build over 26 latest station kits (S81 t6/t7/t12/t14/t17/t20/t23/t29/t30/t41/t48/t50/t51, QC sle_fw/slw_fw/sle_stm): 26/26 PASS (stm needs pitch 33 for 204-um hops). QC *_fe_* kits: no generated kit on disk yet.
- e811e9d1807: kit_wave class default (RELAY_BAY_RE s81 ^slice_station__, qwen_compute ^sl[ew]_(stm|fw|fe)_v\d), stage relay_bay after gen, FAIL_PREBUILD relay_bay -> PLAN.
- 2026-11-03 06:53 PST main a37abb76a7c has relay_bay (afd014b6528 + RM25 advisory 06c4755d4e8). COORD ruling: miss still applies form -> READY claude/safe-station-1-adv-1103@58ae155b338.
- 2026-11-03 10:46 PST PILOT gen4 RESULT: GRT gate FAIL TT -46.02 = ft2_i in-face plain-seam IO budget (599.7 ext + 2 HB4 input pads, capture early -100 tap source) ; bay hops closed (FF hold +25.12, no hop setup viol). Probes: s81-fbay-1/ss1_hold_probe.tcl, ss1_tt_probe.tcl. READY adv-1103@9b1f9b278ec. No live units. Next owner of face class: DIE-S81-51 + FLOW.
