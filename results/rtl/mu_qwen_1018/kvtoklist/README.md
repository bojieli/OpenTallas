# MU-KV-TOKLIST: per-token KV stage-start lists (option b) vs the F2 frame (option a), Qwen ROM 4 users

Lane MU-KV-TOKLIST, 10-19, branch `claude/mu-kv-toklist-1019` (from origin/main f573a6d2b). **Not merged, no kit gated:
the coordinator chooses between (a) and (b).** Static schedule only: no credit, ready or stall. Opt-in: `TOKLIST` defaults
to 0. With TOKLIST 0, the GAP mode and MU 0 behave as before; the MU-KV-BOOT bench and its 4 mutants re-run identically
(`runs/gapmode/`).

## 1. Decision table

| | (a) F2, one GAP table per user (MU-KV-BOOT) | (b) F16 TOKLIST (this lane) | (b') F14 TOKLIST |
|---|---|---|---|
| aggregate tok/s (KV-consistent frame, measured in RTL) | 11,982.4 | **13,480.2** (+12.5 %) | 13,351.8 (+11.4 %) |
| per user (u0 / u1 / u2 / u3) | 4,792.9 / 2,396.5 / 2,396.5 / 2,396.5 | 4,792.9 / 4,493.4 / 2,396.5 / 1,797.4 | 4,792.9 / 4,450.6 / 2,396.5 / 1,711.8 |
| tokens a frame (u0..u3) | 2 / 1 / 1 / 1 | 16 / 15 / 8 / 6 | 14 / 13 / 7 / 5 |
| KV target-1 boot words | 471 | 676 (header + 348 list words) | 628 (300 list words) |
| KV layer-programme storage | 144 x 32 GAP flops (4,608 flops) | 2 x `ot_sram_1rw_256x64_m4_r2c2` (2 x 1,181.7 um²) + about 200 flops; the GAP flops are not built | same |
| compute-die leaf ROM (`mu_opcal.leaf_list`, 4,096 words) | 442 entries | **4,435 entries: does NOT fit. It needs a 2nd `ot_rom_4096x72_m8` (+2,392 um²) or a 2-macro leaf** | 3,792 entries: fits the one ROM |
| risk | lowest. Built and benched (MU-KV-BOOT) | new SRAM leaf + prefetch in lprg_mu; benched; die generator not yet wired; compute leaf over capacity | as (b), no compute ROM change |

All three rows share the same KV-die constraints and the same user 0: the latency user keeps 4,792.9 tok/s (the token
is padded to a multiple of 768, as in F2).
- The constraints are `kv_frame_params`: kv.lp edges, the attention busy span 1,789, launch-phase legality, and the
  token pad.
- The F16 frame of record, 13,708 tok/s, is **not** KV-consistent.
  - With the KV constraints and default starts, F16 gives 15 / 8 / 5 = 13,180.6 tok/s.
  - With 48 seeded starts, the best is 15 / 8 / 6 = 13,480.2, at starts (4409, 4066, 4308), the same as `KV_FRAME_STARTS`.
  - (b) costs −1.7 % against 13,708.
- Both options also need the compute-die playback, the leaf ROM image, to be re-compiled for the chosen frame, because
  both dies must play one frame.

**Recommendation: (b') F14 TOKLIST.** It gives +11.4 % over F2 with no compute-die macro change. F16 adds a further
+1.0 % but needs a second leaf ROM.

## 2. Sizing (per F16 frame)

- Entries: 36 stage-start gaps for each filler token, 29 filler tokens → 1,044 entries. User 0 is hard-wired to 0 and
  stores none.
- Each user has 1 (u0) / 15 / 8 / 6 distinct patterns; every filler token is different.
- Gaps reach 208,521 cycles in F16 and 239,095 cycles with the default starts, when a filler waits most of a token.
  - That needs 18 bits, so entries are **20-bit, 3 to a 64-bit word**, with bits [63:60] = 0.
  - A token table is then exactly 12 words.
  - Capacity is 512 words = 42 filler tokens.
- Store: an SRAM, not a ROM, because the frame is chosen at boot.
  - The store is 2 x `ot_sram_1rw_256x64_m4_r2c2`: 66.3 x 17.8 um each, clk→q about 0.22 ns, 1-edge read.
  - The read path is the macro → a 3:1 lane mux → a 20-bit register, with the 0.833 ns period.
  - Flops instead would be 20,880 flops, about 6,100 um² plus the read mux. That was rejected.
- Net area against the GAP mode: +2,363 um² of SRAM + about 200 flops − 4,608 GAP flops ≈ +1,100 um² (~0.001 mm²).
- Boot plane: target 1 = 0..325 as before, then:
  - 326: the header {ntok3, ntok2, ntok1, ntok0 = 0}, 8 bits each;
  - 327..326+NW: the list (NW = 12 Σ ntok);
  - then the seal.
  - F16 has 676 words and F14 has 628. Both are ≤ 1,024, the 10-bit `boot_pr` address and the HOST class-8 limit.
  - `program_target_frames.encode_image(..., mu='toklist')` takes the target-1 count from the header. The die generator
    still emits the GAP form; wiring an `OT_KV_TOKLIST` flag is an adoption step, about 3 lines in `kv_static.py`,
    `kv_static_boot_join.py` and `kv_static_programme.compile_all`.

## 3. RTL (`rtl/qwen_sys/mu_qwen_20261018/`)

- `qkd_static_kv_layer_programme_mu` gains `TOKLIST` (MU 1 only) and `TLMUT`.
  - Each filler context holds its next gap in a prefetch register.
  - Consuming the gap requests the next entry. Consumers are a start (stage 1) and a stage end before stage 36.
  - One shared read port serves the requests: 2 edges each, the lowest user first.
  - The per-user pointer walks [wbase, wend) and wraps there, so the list is frame-periodic.
  - A consume before its entry has landed is a sticky `fault_code[5]`. A refill takes ≤ 6 edges, and stages are
    thousands of edges long.
  - Boot: header at 326, list words streamed at 327 (counted), seal at 470. The programme checks ntok0 = 0, NW ≤ 512,
    bits [63:60] = 0, and count = NW at the seal.
- `qkd_static_kv_boot_dispatch_mu` gains `TOKLIST`.
  - It takes every target-1 word from 326 on, in order: header, list, then the seal.
  - The seal reaches the unchanged original as its word 326, so the original's 327-word count is unchanged.
  - Order, epoch and early-seal faults behave as in the GAP mode.
- Compiler (`tools/qwen_static_schedule/mu_calendar.py`):
  - `kv_token_lists`, `kv_toklist_words`, `kv_layer_image_toklist`, `kv_toklist_frame`, `kv_toklist_receipt`.
  - `check_kv_programme`, `kv_programme_events` and `kv_ownership_roots_mu` accept per-token lists.
  - The assertions are the same: user 0 all 0; no same-edge event of two users; disjoint attention windows; the
    META_HOLD launch spacing; launch phase legality; no start while a token is active. They run periodically and on the
    unwrapped 2-frame bench window.
  - Emitter: `kv_static_programme.py --mu-from results/arch/qwen_kv_static_programme_1017/die --toklist [--tl-frame 14]
    --out DIR`.
  - Tests: `test_mu_kv_toklist.py`, 7 tests, plus `test_mu_kv_gap.py`, 11 tests: all pass (`runs/test_mu_kv_toklist.log`).

## 4. Bench (Verilator 5.050, fleet ot-epyc5; `rtl/test/mu_qwen_1018/run_all_toklist.sh`, files in `lists/tb_mu_kv_toklist.f`)

- `tb_mu_kv_toklist`, derived from `tb_mu_kv_boot`, uses DUT `qkd_kvs_ctl` from the `_mu` tile file. The run script sets
  `.TOKLIST(1)` on u_boot and u_lprg in the bench copy; the committed tile file is unchanged.
- Targets 1 (TOKLIST), 2 and 3 (the MU ownership roots from the lists) go through `boot_pr`.
- Then 2 whole frames play: every pulse is compared with the compiler's list, and user 0 is checked in lockstep with the
  original single-user lprg.
- Tokens done per user in frame 2 give the measured tok/s.

| case | result | fail regex |
|---|---|---|
| `tb_mu_kv_toklist` (F16) | **PASS**: 676 words; 90 starts; 24,018 event edges = the compiled list; 90 tokens done; user 0 == MU 0 on 8,096 edges; **13,480.2 tok/s measured** | |
| `tb_mu_kv_toklist` F14 (`TL_DIR=.../kvtoklist/f14`) | **PASS**: 628 words; 78 starts; 20,796 edges; **13,351.8 tok/s measured** | |
| `kt_sealwrong` (327-word single-user image) | FAIL | `layer programme not configured .*lprg fault 04` |
| `kt_listnot` (wrapper WMUT 1) | FAIL | `layer programme not configured .*lprg fault 01` |
| `kt_u0hdr` (header ntok0 = 1) | FAIL | `layer programme not configured .*lprg fault 04` |
| `kt_short` (last list word dropped) | FAIL | `layer programme not configured .*lprg fault 04` |
| `kt_collide` (u1 token 0 stage 1 on a u0 edge, `+NOLIST`) | FAIL | `layer programme / dispatcher fault .*lprg fault 10` |
| `kt_nowrap` (TLMUT 1: no list wrap) | FAIL in frame 2 (rel 4,010,813) | `event kinds differ from the compiled list` |
| `kt_lane` (TLMUT 2: lane off by one) | FAIL | `event kinds differ from the compiled list` |
| GAP-mode regression `tb_mu_kv_boot` + `kb_*` (TOKLIST 0) | PASS / 4 FAIL, the same lines as `kvboot/runs` | as kvboot README |

Witness logs are in `runs/`, `runs/f14/` and `runs/gapmode/`, with the summary in `runs/summary.txt`.

Note: the benches' `+IMG` registers hold 128 characters, so a long absolute path is truncated silently. The TOKLIST
script passes relative paths, and `run_all_toklist.sh` keeps the GAP-mode OUT short.

## 5. Open for adoption (only if (b) or (b') is chosen)

1. Re-compile the compute-die leaf image for the same frame. F14 fits the ROM; F16 needs a second macro.
2. Add the die generator flag (`OT_KV_TOKLIST`), then the kvs_ctl gate with the 2 SRAM macros.
3. Ownership: user 3 tokens span up to 544,459 cycles, which is the MU target-3 deadline. The `_mu` calendar takes the
   max; this is already checked in the bench.
