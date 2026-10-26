# KV MU833 boot image (F=2) on the strict bind of record b19 -- TOK-QK 2026-10-25 23:46 PDT

Recipe (RECIPE): commit 9bb86c4467, dirty 0, BIND = physical/die_plan/qwen_kvsys/bind/kvbind1025/b19 (repo-relative, committed bus_groups of
the b19 strict bind; b20 full verify PASS 2552344/2552344, lint 0). Run: ot-run unit oth-ubuntu-1564263-1792997118 (epyc1) exit 0,
OT_KV_MU_FRAME_F=2 bash physical/die_plan/qwen_kvsys/boot_v36/run_mu833.sh <BIND> OUT; NC32=HEAD bash results/rtl/kv_img_mu833_1025/token_gate.sh OUT GATE.

- Boot ages fit the raised bounds (main 453dda0d: PV FIRST_INPUT_AGE <= 255, VPORT_RT <= 63, 0 added schedule cycles): PV FIA 131/131,
  vport RT 44..50, DQ <= 15 (0 pad stages), D_QK 0, D_RL 111, F_DLY 55, PV_LEAD 38 (prep/boot_ages_bound_padded.json).
- Profile: KST 56,56,54,54,54,55,55; rx/kvn/groups 56 (one landed depth per seam bus); QK age 34, V RL 130; emb_fill PASS margin 1147.
- Compiler token (layer schedule) 290059 cycles; MU frame F2 = 471-word MU image, 2/1/1/1 tokens per frame, aggregate 10223.6 tok/s.
- KV_TOKEN_GATE PASS: static schedule 1800 events / 1494 event cycles / 180 service windows / 0 collisions, all launches legal;
  native MU471 installed; DIECFG AGES96 sealed fault 0; default AGES0 lockstep PASS; negatives caught (MU327 fault 80, old 77-word fault 08).
- All 14 targets byte-identical to Codex ca1808f6c6 (results/rtl/kv_img_mu833_b19_1025, compiled from a scratch BIND path) -> that image is now
  reproduced from repo-relative inputs.
- Not claimed: whole-die E boot/HOST replay (setup_ready), physical re-close of the PV vport/ctl kits at RT63/FIA255, TYPE-REDUCE strap e1+e3/e5+e7 token condition.
