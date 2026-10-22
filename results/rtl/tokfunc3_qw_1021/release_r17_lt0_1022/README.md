# TOK.QW release compose: current r17 KV attention + SU_LT=0 stg, all on the c0f8097f3 source assembly (TOKc-QW2, 10-22)

The verdict is **TOKEN PASS**: all 9 stages PASS, `problems []`, `qualified_full_token` true.
- 1 user: **268,838 cycles = 4,465.4 tok/s**, +1.41% vs the 4,403.2 model.
- 4 users: **11,811.3 tok/s**, +0.52% vs the model.

| stage | run (RUNROOT) | grade | key real cycles |
|---|---|---|---|
| stg | stg5lt0, gold1 `tokfunc-qw-1021/stg5lt0` (stg4 tools 293bc034f, VF `-GSU_LT=0` = slice2_w kit PARAMS=()) | RTL-functional (source assembly) | 527/527 cases, gold 1032336/1032336; resid 1044, qk 926 (pos 958), silu 814, qkv 441, gu 433, od 1555 |
| kv | ep5 `tokqw-r17asm-1022/kv`, `stage_kv.sh --explicit-r17` (96109f0e7) | RTL-functional (source assembly) | start_to_retire 1782, status 1997, work 1746 (ctx-independent), u4 period 2025; 7/7 mutants FAIL as required; T32768 refused |
| chain | ep5 `tokqw-r17asm-1022/chain` on that kv vehicle | RTL-functional (source assembly) KV vehicle = stage kv build c0f8097f3 | 36/36 layers + 9 u4 groups bit-exact vs TP8-native, goldflip control FAILs as required, hand-off 288/288; every layer retires at 1782 |
| xt1 / xdie / tp8 / ovl4u_rel / ctx4u / head | unchanged gold RUNROOT stages | RTL-functional (source assembly) | as in the earlier compose |

The KV vehicle is the current selected attention (`qkd_kvs_attn_r17` / `qkd_kvs_attn_fl_r17`, RETIRE_STATIC 1, STATUS_DELAY 213). c0f8097f3 carries those two files byte-identical to the approved r17 sources. The vehicle uses the ROOT-approved explicit genuine-archive binding b0cc8cdca, so the top frontend took 0.64 s / 106 MB. The 35 child archives were admitted because their sha256 matched the approved table and every one of the 53 child-readset files is byte-identical in the assembly (see `kv/explicit_build.json`). The binary sha is b7829094c4a8.

`report_stg4_su_lt1.json` is the same compose with the old stg4 (SU_LT=1, older ML1 hard lane): 279,731 cycles = 4,291.6 tok/s. That build is not the die configuration and is kept for comparison only.
