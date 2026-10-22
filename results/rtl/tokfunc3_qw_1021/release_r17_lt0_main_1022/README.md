# TOK.QW release compose reproduced FROM MAIN tools (TOKc-QW3, 10-22)

The verdict is **TOKEN PASS**: all 9 stages PASS, `problems []`, `qualified_full_token` true.
- 1 user: **268,838 cycles = 4,465.4 tok/s** (+1.41% vs the model).
- 4 users: **11,811.3 tok/s** (+0.52%).

These numbers are identical to `../release_r17_lt0_1022` (TOKc-QW2). `cycles_tokfunc.json`, `inputs_tokfunc.json` and `kv/explicit_build.json` are byte-identical. Other differences:
- chain: only the wall-clock `time` fields differ.
- kv: only `log_dir` differs.
- stg: the receipt label differs. rtl_ref is `a4cf9a360` (main's normalizer pin) instead of `origin/main 13f90bb4d`. The overlay file `rtl/qwen_dv/qfd_dv_redstn2.sv` has the same bytes (e049f2fa).

## Recipe (tools = main 0d44fa1b2 + claude/tokc-qw3-1022 9a3da660a `stage_stg.sh --su-lt`)
Every input was re-derived from git:
- **src:** `git archive c0f8097f3 rtl tools configs physical/asap7_memory_macros`, freshly extracted on each host.
- **kv/fx:** 10 bench files, byte-identical to `0e597ed1c`.
- **stg/fx_res:** 115 files, byte-identical to `c0f8097f3`.
- **stg overlay:** main's `qfd_dv_redstn2.sv`.
- **chain/in fx:** byte-identical to the stg3 fixtures (288 files).

| stage | run | result |
|---|---|---|
| kv | `stage_kv.sh RUNROOT --explicit-r17 <35 approved archives>`, run twice: ep5 `/srv/opentallas-scratch2/claude/tokqw3-main-1022` and ep9 `/srv/opentallas-scratch/claude/tokqw3-ep9-1022` | EXPLICIT_BUILD_PASS on both. Binary sha **b7829094c4a8** is the same bytes as the released vehicle. start_to_retire 1782, status 1997, work 1746, u4 period 2025, u4 first->last 7857. 7/7 mutants FAIL as required; T32768 refused. |
| chain | `stage_chain.sh RUNROOT --kv-obj RUNROOT/kv/out --par 46` (ep9, bound first) | 36/36 layers + 9 u4 groups bit-exact. Goldflip control FAILs as required. Hand-off 288/288; every layer retires at 1782. |
| stg | `stage_stg.sh RUNROOT --stage stg6r --su-lt 0 --reuse-objs <stg5lt0 rel/pos/mut objs> --fx <stg3 fx> --overlay <main redstn2>` (gold1) | Main's `--object-manifest verify` gives VERIFY OK x6 on the stg5lt0 objects. The objects are materialised in the stage dir (sha == vtb.sha256). 527/527 cases, gold 1032336/1032336, build receipt verified. |
| xt1/xdie/tp8/ovl4u_rel/ctx4u/head | unchanged gold RUNROOT stages, as in the released compose | PASS |

Compose command:
`TOKFUNC_KVHOSTS=ot-epyc9 run_tok_func_qw.sh --asm c0f8097f3 --collect-only --runroot /srv/opentallas-scratch/claude/tokfunc-qw-1021 --stage-dir stg=<G>/stg6r --stage-dir ovl4u=ovl4u_rel --stage-dir kv=<ep9>/kv --kvroot <ep9>`

## Findings (tooling only, no RTL or numeric change)
1. **SU_LT selection.** Main's `stage_stg.sh` hard-coded SU_LT=1. The released stg5lt0 (SU_LT=0, the die kit) ran on a hand-edited tool copy, so main could not reproduce it. Fixed by `--su-lt 0|1` (default 1 unchanged).
2. **Collection across RUNROOTs.** `collect_files.py` only fetches stage evidence that resolves inside the stage, or fx links inside the stage's parent. A stage that links `--fx` or `--reuse-objs` into another RUNROOT therefore collects as INCOMPLETE/DIAG. The fix is to keep the fixtures and objects inside the same RUNROOT; here they are byte-identical copies, sha-checked.

A fresh stg rebuild (`--su-lt 0`, gold1 `stg6lt0`) was still running when this receipt was committed. See the HANDOVER in lanes/STEWARD-TOK.md.
