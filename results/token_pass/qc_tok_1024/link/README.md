# QC-TOK link token tests on the Qwen compute bound_r8 bind (KV peer kv41), 2026-10-24

Source assembly = `git archive` main 3e05af806b (rtl/tools/configs/macros), fixtures by commit (`tools_bound/stage_local.sh`,
sha256 in `link_fixtures.sha256`), Verilator 5.050, intel1. Bound constants from `physical/die_plan/qwen_compute/bind/bound_r8/regen/constants.json`
(`bound_constants.json` copy): COLL LS 389 (`--relays 0 7 8 8 --lanes 2 2 10 2 2 10 --lx 12 4 12`), xdie pair image
`D2D_DIE_STAGES 2,2,2,3,2,2/34,34,32,32,32,31,31` (TXDP C 0a010308 / K 03030443 = kv41), ovl4u `--release-masters` on the same seam.

| test  | positives | mutants / negatives | verdict |
|-------|-----------|---------------------|---------|
| tp8   | 3/3 PASS (cal, cal_seqsu, mu window 61,440 words mm 0 + user-0 ref) | 9/9 FAIL as required | PASS |
| xdie  | 9/9 PASS (cur_bound_image, +sfm3, +t8192, pair, pair_l0, pair_phy9, pair_t8192, kseam d22bu route_r, shift_only_sd0) | 13/13 FAIL as required | PASS |
| ovl4u | 2/2 PASS (codec1, codec2: 4 users, 13,708 tok/s bench aggregate) | 8/8 FAIL as required | PASS |

tp8 first run (`tp8/r1_mu378/`): the 3 MU cases stopped before simulation with `mu-cal collision: msg 3 and msg 2 on ucie at
3753`. Root cause: the fixture MU window `results/rtl/mu_qwen_1018/coll/mu_cal.json` was compiled by
`tools/qwen_static_schedule/mu_calendar.py` at ls 378 (dv2f14bi); on the bound collective (LS 389) the same command cycles
book one UCIe frame twice (the bench re-checks the compiler's collision assertion). Fix: recompile the static MU calendar at
the implemented LS (`tp8/mu_cal_ls389.json` = `compile_calendar(dict(users=4, occupancy='measured', head_chunks=8, ls=389),
tokens=3, policy='priority'); bench_cases(cal)`; ls 378 reproduces the committed fixture byte-for-byte in its commands;
at 389 one filler command moves 11 cycles: 255327 -> 255338). `stage_tp8_bound.sh` takes it as `MU_CAL=`.
