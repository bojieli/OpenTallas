# KV qkd_hr_core_tx one-block fix (DIE-KV-47-HR, 2026-10-30)

Baseline: kit ba6778f278fa (kv-kits-15 qkd_hr_core_tx__164.16x164.16, RTL 939e8a15, pins r26q14 e6042969) routed TT -215.25 / 2744 EP.
DIE-KV-46 13:55 diagnosis: (1) did_q -> tk8 lane write enable, (2) rp -> 512-bit head mux + wide header compares -> tk8,
(3) reset recovery (resizer chain on u_ctrl__rst_n). Plan/pins/outline unchanged, 0 added cycles.

## Change (KV-only, shared originals byte-identical)
- (a) core wrapper `qkd_hr_core_tx_wrapper_clw1.sv` = kv-kits-9 wrapper + `.CONST_LANE_WRITES(1)` (Codex onehot, on main).
- (b) `rtl/qwen_sys/mu_qwen_20261018/hr_tx_predecode/qkd_host_ctrl_token_service_packet_collected_mu.sv` (same module name, drop-in for the
  core_tx elaboration file list only). `HDR_PREDECODE=1`: header flags `qf[wp]<=hflags(rd)` beside `q[wp]<=rd`; rp mirrored by RP_REPL+1=5
  kept one-hot copies (reset 1, rotate on take) driving 4x128-bit head-mux slices + 1 copy for header [47:0] and flags; sequence check
  compares rs to seq_rx[k]+1 per source in parallel. `HDR_PREDECODE=0` = original expressions.
- (c) balanced reset trees: Codex `results/codex_kv_hr_1029/reset_tree.py --apply` on the placed DB (788 BUFx24, 5 levels, 0 cycles).
  Measured here as an ODB edit on 3_place; NOT yet a kit hook.

## Evidence
- `run_bench.sh <repo> 400000 1..6` -> `bench_1030.log`: ref = origin/main MU with CONST_LANE_WRITES=0 vs variant CONST_LANE_WRITES=1 (HP 1 and 0),
  core_tx params (STRAPPED, SERVICE, TOKEN, HCW 39), every output every cycle: 12/12 PASS (~17-18k accepted RX frames per seed).
  Mutant M1 (hflags[11] 511:264) FAIL, M2 (one rp copy rotates backwards) FAIL.
- Core RTL regen (`regen_inner.sh`, Codex tx_current recipe + hr_face_ports.py, retime-in package_abort): face proof post rc 0, mutant rc 1,
  emitted .v rc 0 (`eq_face_rc_1030.txt`). Kit RTL sha256 c14c6bdb45758ec4.
- Placed STA census (`census.tcl`: TT libs, kit setRC, placement parasitics, ideal clock; `census_classify.py`):

| DB | WS ps | TNS ps | EP | rp cone | reset | did_q->tk8 |
|---|---|---|---|---|---|---|
| baseline kit 3_place | -422.95 | -702267 | 2802 | 2231 / -423.0 | 380 / -102.2 | 36 / -80.6 |
| baseline + reset tree | -422.95 | -674084 | 2428 | 2231 / -423.0 | 6 / -32.7 | 36 / -80.6 |
| fix (a)+(b) 3_place | -272.66 | -49586 | 834 | 158 / -57.0 | 675 / -272.7 | 0 |
| fix (a)+(b)+(c) | -56.98 | -6649 | 162 | 158 / -57.0 | 3 / -24.1 | 0 |

  Residual worst: g_rp[4].oh (header/flag copy) -> tk8 write enable, -57.0 at placement before CTS/GRT repair.
