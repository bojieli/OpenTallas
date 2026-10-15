jog10 screen (S81 die lead r7, 2026-10-14 ~22:00 PT), EPYC4 ot-run unit oth-ubuntu-80953-1792037854, exit 0.
Source: src_jog9 (Codex jogfix 910ad6671 tree) + generator patch ee08a78f6 only; recipe s81_layer1_jog8.opts + --cfifo-colck, OT_S81_PAIR_GATE=1.
Result: legality 0/0/0; hop reach 0 bits > 500 (max 495 um); pin_align FAIL 261 -> 3 (WARN 69,426, OK 46,281).
Hop gate verdict FAIL only from 8 forward-hold pairs on UNBOUND end-relay capture masters (owed tile items, OT_HOP_HOLD_OWED).
Remaining 3 FAIL: hb_hc_s_hc_t d8 (3,056 b, jog 157.7 in 60.8), hb_collective_vm d10 (2,100 b, 108.4 in 86.7), hr_W2 -> sp_gather.rW2 (759 b, 255.3 in 21.4).
