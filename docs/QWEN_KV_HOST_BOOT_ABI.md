# Qwen KV/system die: HOST boot image ABI

KV-TOK, 2026-10-26. Implements COORD RULING KV-TOK boot (2026-10-26 12:32 PDT). It covers the class-8 boot images that
the board host sends to the HOST program loader on hub_Wi (`u_host.g_mu.u_rank.g_mu.u_program`,
`qkd_host_program_loader_target`). The loader replays each image to the die dispatcher
(`qkd_static_kv_boot_dispatch_mu_*`, instance `u_boot` in `qkd_kvs_ctl_nc32`).

## 1. Image length per target (one source)

The image builder defines the program word count of every target once, in
`tools/qwen_static_kv/program_target_frames.py` (`TARGET_WORDS`, `TARGET_WORDS_MU`, `die_cfg_ages`).
`tools/qwen_static_kv/boot_abi.py:image_words(mu, ages)` returns that table:

| target | words | note |
|---|---|---|
| 1 | 327 (MU 0) / **471** (MU 1) | layer programme. MU form = 326 rows/digest/epoch + 144-word GAP block + seal at 470 |
| 2 / 3 | 181 / 4 | |
| 4, 5 | 192 | |
| 6..9 | 1024 | |
| 10 | 32 + NRST + 1 + DIECAP + 19·AGES = 77 (AGES 0) / **96** (AGES 1) | pre-boot die configuration; NRST 43, DIECAP 1 |
| 11 / 12 / 13 | 66 / 1024 / 8 | link calendar / PC players / join4 calendar |

The two RTL tables are not copied by hand. Each is a function of the die's own parameters:

* **Dispatcher**: `word_count(t)` of the inner dispatcher, evaluated with the `u_boot` instance parameters. With MU 1,
  target 1 = seal address + 1 = 471.
* **Loader**: `target_words(t)` with parameters `MU`, `AGES`, `NRST`, `DIECAP`. Defaults MU 0 / AGES 0 keep the legacy
  327/77 table for older benches. In the OBSX rank services, the loader is instantiated `#(.MU(MU),.AGES(BOOT_AGES))`.
  `BOOT_AGES` (default 0) is threaded through `qkd_host_root_admission_obsx` and `qkd_host_root_admission_obsx_bo1_c45`.
  The value of `BOOT_AGES` at the HOST instance is **set by the native mission preparation**
  (`tools/qwen_layerbench/kv_dieslice/prepare_native_mission.py`, through `native_host_boot_abi.py`). It is copied from the
  `AGES` parameter of the die's own `u_boot` dispatcher, which is the same value `native_boot_ages.control` writes. It is
  never hand-set.

**Build-time check (fail closed).** `prepare_native_mission.py` stops if the dispatcher, loader and image tables differ
for any target the dispatcher builds. The standalone check runs on staged vehicle sources:

    python3 tools/qwen_layerbench/kv_dieslice/native_host_boot_abi.py check --ctl qkd_kvs_ctl_nc32.sv \
      --face qkd_kv_ctl_nc32_face.sv --loader qkd_host_program_loader_target.sv \
      --obsx qkd_host_root_admission_obsx.sv --c45 qkd_host_root_admission_obsx_bo1_c45.sv --host kv3_hub_Wi_part.sv

Results on the B48 staged sources (vehicle4 + build2 top_s; CHECKED 2026-10-26):

* As built: FAIL, target 1 = 471/327/471 and target 10 = 96/77/96 (dispatcher/loader/image). This is the B33
  BOOT_FAULT@655 cause.
* Threaded with `BOOT_AGES(1)`: PASS on all 13 targets.
* Threaded without `BOOT_AGES`: FAIL on target 10.

Unit tests: `tools/qwen_static_kv/test_boot_abi.py`.

## 2. Host pacing contract (static host schedule)

The host is the off-die elastic boundary. The die gives no feedback for image pacing, and no credit or ready signal is
used. Board-port credits are only the port's local IBUF, so they do not show whether the loader has finished a replay.
The loader treats a BEGIN that arrives while an image is still replaying (`REPLAY_P`/`REPLAY_D`) as a designed sticky
fault. B33 hit this as BOOT_FAULT@923 when the next BEGIN came 1 cycle after AUTH.

In host send time, with every quantity in core cycles:

    send(BEGIN n+1) >= send(AUTH n) + HOST_LINK_LAT_MAX + pw(n) + dw(n) + REPLAY_FIXED

* `REPLAY_FIXED` = 16 is the loader's fixed replay overhead after AUTH.
* **`HOST_LINK_LAT_MAX` = 160 core cycles** is the declared bound on the host-to-loader one-way latency (board port, PHY,
  HOST ingress). The measured value is 122 (B33 vehicle: first BEGIN sent at cycle 531, at the loader at 653; CHECKED).
  The bound holds because AUTH(n) arrives no later than send + 160 and BEGIN(n+1) arrives no earlier than its send time.
* Encoded as `boot_abi.next_begin_min()`. The vehicle bench `tb_kvslice.sv` applies it when it sends the AUTH frame:
  `hold = cyc + HOST_LINK_LAT + pw + dw + 16`.
* A host or board whose measured one-way latency exceeds 160 must change this declared bound here. Slack per image is
  not to be tuned.

## 3. Evidence

* Unit replay of the exact B33 frames: `results/rtl/kv_host_boot_abi_1026`. Legacy and mu_only fail at frame 0,
  ages_only fails at target 1, and native passes 14/14 with all expected digests.
* Whole-die private vehicle `epyc1:/srv/opentallas-scratch2/claude/kvtok-bootabi-1026`: build9 + threaded hub_Wi +
  paced join2 tb, results in `run5`.
* B48 gate `epyc1:/srv/opentallas-scratch2/claude/kvtok-b48gate-1026/summary.txt`. Form (a) is as built, form (b) has
  the loader fix + join2 + paced tb.
