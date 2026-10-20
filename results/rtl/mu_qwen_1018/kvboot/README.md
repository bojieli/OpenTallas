# MU-KV-BOOT: the KV layer programme GAP table and the MU boot image through the KV boot plane (Qwen ROM 4 users)

Lane MU-KV-BOOT, 10-19, branch `claude/mu-kv-boot-1019` (from origin/main f3647da82, with MU-KV-PROG 8944224e1 merged).
Static schedule only: no credit, ready or stall. MU 0 files are untouched.

## 1. Compiler (`tools/qwen_static_schedule/mu_calendar.py`, `kv_*`; tests `test_mu_kv_gap.py`, 11 PASS)

- `kv_gap_table(cal)`: GAP[u][s] (4 x 36) from the calendar's KV service (`kvs`) windows. It is the extra spacing of user
  u's window over user 0's, at the same stage index (stage 1: from the token start). It refuses:
  - user 0 gaps that are not all 0;
  - a negative gap;
  - a user whose tokens need different tables. The RTL plays ONE table per user, every token.
- `check_kv_programme(rows, gaps, starts, H)` runs on the KV programme's own event set: the image rows of record,
  stage frames 7,070 / 6,836 / 6,835. It asserts:
  - no edge carries two users' events (stage_start, the 8 roots, stage_done). This is the RTL's sticky `fault_code[4]`.
  - the attention programme busy windows [issue, run + 1784] of different users are disjoint (MU-KV-PROG §2);
  - two users' launches (ctrl_go / kgo / vgo) are more than META_HOLD_CORE 8 edges apart (phase launch held metadata);
  - every launch sits inside the phase launch SAFE window [200, 600] u at its frame cycle. This is the die profile of
    the image; frame cycle 0 is user 0's token start at HBM-beat phase 0.
  - a user's next start comes after its previous token's last stage_done.
- Epoch convention (in the receipt): user = `authority_epoch[1:0]` = epoch[1:0] of every lprg event, from
  allocator_mu {seq14, user2}. The writer and PC calendars take the stage user from that epoch, at row 64 + l + 256u.
- `kv_layer_image_mu`: target 1 has 471 words. 0..323 are rows, 324 the digest, 325 the epoch, 326 + 36u + (s-1) the
  GAP words, and 470 the seal.
- `kv_ownership_roots_mu`: target 3 for `qkd_static_kv_ownership_calendar_mu`, which re-arms on every go. It is
  [3, max leave, max deadline, seal]. User 0 alone gives the single-user roots 0x3b0e3 / 0x3c239 (test).

## 2. Finding: the op-granular frame of record cannot be played by one GAP table per user

In `mu_opcal.compile_frame(16)` (13,708 tok/s), users 1 / 2 / 3 run 15 / 8 / 7 tokens a frame, and every token has
its own KV stage pattern. `kv_gap_table` refuses it, and F = 3..16 likewise. Only F = 2 gives every filler one token a
frame.

Compiled on the image frame, F = 2 still collides without the KV programme's own constraints:
- users 2 and 3 lock one stage apart, so user 3's stage start lands on user 2's stage done;
- the attention windows of stage 1 and the later stages differ by 38 cycles;
- about 48 % of launch phases are illegal.

These are now opt-in calendar resources, set by `kv_frame_params`:
- `kv.lp` unit edges, with launches 9 wide; same-user overlap is allowed (`SELF_OK`);
- `kv.att`, the attention busy span;
- launch-phase stepping of filler KV stages (`kv_phase_quantum`);
- `token_pad`: the latency token is padded to a multiple of 768, 250,368 cycles (as the single-user image's 249,600).

The KV-consistent frame of record is `kv_frame_of_record()`: F = 2, filler first starts (4409, 4066, 4308)
(`kv_frame_search` seed 1), giving **11,982.4 tok/s** (user 0 4,792.9; fillers 2,396.5 each).

Defaults are unchanged: without the new params, `mu_calendar` and `mu_opcal` emit what they did before (all their tests
PASS).

**Decision needed (coordinator):** pick one of these.
- (a) Adopt this F = 2 KV-consistent frame for the compute-die playback too: −12.6 % vs F16, and user 0 +0.3 % for the
  token pad.
- (b) RTL: per-token GAP lists. This would be a KV stage-start list ROM, like the compute die's op-start leaf; it does
  not fit the 1,024-word boot target.

Also: `mu_calendar` SOURCED `layer_period` 6,886 ≠ the KV image's 6,836 (link calendar). The KV frame uses 6,836.

## 3. Boot plane

- `rtl/qwen_sys/mu_qwen_20261018/qkd_static_kv_boot_dispatch_mu.sv` has the same ports as the original, plus `MU` and
  `WMUT`. At MU 0 it is the original.
  - At MU 1 the unchanged original still sequences, checks and seals every target.
  - The wrapper takes the GAP block (326..469: in order, only after the original wrote word 325, at the installed
    epoch) onto the same layer bus.
  - It passes the seal (470) to the original as its word 326, so the original's 327-word count is unchanged, and
    re-addresses its write to 470.
  - A single-user image on the MU path is refused (bench `kb_sealwrong`).
- No per-user base or tag register is boot-programmed. The KV row is a bit insertion of epoch[1:0] (MU-ADOPT-KV).
- Generator: `tools/qwen_kv_die/kv_static_programme.py`.
  - Under `OT_KV_MU=1`, `compile_all` emits targets 1 and 3 in MU form, and the bundle is encoded with
    `program_target_frames` `mu=True` (TARGET_WORDS_MU {1: 471}).
  - `--mu-from DIR --out DIR` writes the MU images, the receipt and the bench lists from a compiled die directory.
    That is how this directory was made, reproducibly.

## 4. Die generator (`OT_KV_MU=1`)

- `kv_static.py`: `layer_programme` → `qkd_static_kv_layer_programme_mu #(.MU(1))`.
- `kv_static_boot_join.py`: `boot` → `qkd_static_kv_boot_dispatch_mu #(.MU(1), .WMUT(0))`.
- `qkd_kvs_tiles_hroot_ff_k_mu.sv`, regenerated with `kvj-g2-env.sh` + `OT_KV_HROOT=1 OT_KV_FANFOLD=1
  OT_KV_TILE_KITS=1 OT_KV_ATTN_LAND=1 OT_KV_MU=1`, differs from main in exactly 3 lines in `qkd_kvs_ctl`: `u_boot`,
  `u_lprg`, and `u_own` (MU-KV-PROG).
- MU 0 `_hroot_ff_k` regenerates equal to the committed file except the known pre-existing `D_QK 28→57` line; not
  committed.
- Consumer audit: as MU-KV-PROG `kvprog/README.md` §2. Every consumer latches at its pulse. The ownership calendar is
  the only consumer that needed a `_mu`. The phase launch also needs the launch spacing and phase legality above,
  which are now compiler checks.

## 5. Bench (Verilator 5.050, fleet ot-epyc4; `rtl/test/mu_qwen_1018/run_mu_kv_boot.sh`, files in `lists/tb_mu_kv_boot.f`)

`tb_mu_kv_boot`, DUT `qkd_kvs_ctl` from the `_mu` tile file. Boot targets 1 (MU, 471 words), 2 (die writer
programme) and 3 (MU ownership roots) go through the boot_pr word stream and `boot_image_ready`, with no preload. Then
10 starts (4 users, 2 frames) are driven at the compiled cycles.

| case | result | fail regex |
|---|---|---|
| `tb_mu_kv_boot` | **PASS**: 2,660 event edges equal the compiled list (kinds, user = epoch[1:0], stage); 10 tokens done; user 0 == the original single-user lprg on 1,012 edges; no fault | |
| `kb_sealwrong` (327-word single-user image) | FAIL | `layer programme not configured .*lprg fault 04` |
| `kb_gapnot` (wrapper WMUT 1: GAP not forwarded) | FAIL | `layer programme not configured .*lprg fault 01` |
| `kb_u0gap` (GAP[0][5] = 7) | FAIL | `user 0 differs from MU 0` |
| `kb_collide` (user 1 stage 1 on a user-0 event edge, `+NOLIST`) | FAIL | `layer programme / dispatcher fault .*lprg fault 10` |

Witness logs are in `runs/`, and `runs/summary.txt` has the summary.
