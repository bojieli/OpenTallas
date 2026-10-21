# QW-S5-LP 10-21: slice2 W/E master w6 / w6b / e6 / e6b (Q.STA.SLICE.3 / .4)

Successor of w5/w5b/e5/e5b. The e5/e5b gates stopped at the pre-gate native census (QW-SLICE2E6 10-21 03:35): e5 had 9,224
drivers above 32 loads, e5b 10,003. This is a CRITICAL prefix (`qfd_dv_slice2*`), so there is no REVIEW.json and no submit.
The PNGs and the checklist go to lanes/COORD-REVIEW-QUEUE.md.

## What changed (structural)

| e5 census class | loads | fix here |
|---|---|---|
| `ot_pl_land_r` read select `rc[1]/exp_` (+ sel decode) | 6,275 / 3,135 per landing, ~6.9k violations | `landing_chunk_bits 24` (kept per-chunk selectors) |
| lp regional reset run `u_lpr_r_*` | 83 / 35 | `regional_reset_copies true` (kept last-stage copies <= 32 loads) |
| landings > 32 chunks (hw 1,567 b, chu/own_ch 1,095, st/so 1,088, chd 1,038, tw/xt 1,024: 15 landings) | refused by lp.py | new opt-in `ot_pl_land_split_w/_r`: same chunk logic, one rsi bit per 32 chunks |
| `u_fdn / u_fup .u_rl.rst` | 3,858 / 2,357 | `qfd_dv_s6_fdn/_fup`: only valid/control bits are reset (20 / 15 loads); the second landing stage is a kept copy; release edge unchanged |
| `u_tap` (s1_v 1,051, q_v 150, e4_m 128, rst 91, p_sp 33) | | `qfd_dv_s6_tap` / `qfd_dv_s6_xs_tap`: a fixed copy of `ot_qfd_xs_tap` (STATIC 1, AFFINE 1, attention unused, sw_m all ones). Valid kept per lane (<= 17 loads), q_v x4, e4_m kept per lane, p_sp x2, reset 4 kept copies |
| `u_ctl` soft (4,143 reset) | | CLOSED ctl5 view (`qfd_dv_s5_ctl_repair4_leaf`) |
| `u_suvm` soft (u_vm 1,024) | | `qfd_dv_s5_suvm_su8p3` = CLOSED su8_rst3 422d006e2 + VM8 P3 `qfd_dv_s5_vm8q` (7 closed split leaves; group glue soft until the vm8q/vm8qb gate closes) |
| `u_stm` soft (rst 2,353, tld 64) | | Codex `qfd_dv_s5_stm_closed`: CLOSED stream c3r + tload ns4 (the wrapper reset now has 3 loads) |
| `u_btab` soft (1,024) | | CLOSED btab_s4 (`qfd_dv_s6_btab` port adapter) |
| `u_lrly*` soft (1,005 / 366 / 64) | | CLOSED lrly (w6/e6) / lrlyb (w6b/e6b) views |
| st[44] / st[60] TIELO | | st now leaves the hard ctl5 pin register. These bits are su_rows[15] / su_prog[15], and the SU counter wrap rule (`done_n[15] ? 0 : done_n`) holds them at 0 by construction. The port stays at 107 b (die interface). Read the parent census `constant_output_bits` |

## Benches (fleet, Verilator 5.050, `rtl/test/qwen_dv/s5/run_s6.sh`)

Lockstep: `qfd_dv_s6_lp` / `qfd_dv_s6b_lp` against their lagrefs, 6,000 cycles. Witness logs are in `bench/`.

- s6 MUT0 PASS (125,202 compares); MUT1 (landing bypass) FAIL; MUT2 (read K+1) FAIL. MUT4 (u_ctl reset run +1) PASS: it is not observable, because the closed ctl is idle-zero through the reset window.
- s6b MUT0 PASS (125,160 compares); MUT1 FAIL.
- Lint of `qfd_dv_s6_flat` and `qfd_dv_s6_lp`: 0 errors.

## Price (static schedule)

- Landing options (chunks, reset copies, split): +0 edges. Landing flops: 131,629 (D4) / 227,019 (D8).
- s6 face and tap leaves: +0 (same edges, same release edge).
- Closed children, as recorded by their owners: SU8 command visible +4, reset +1. VM8 P3 against P2: VM reads/writes +1, reset +2. c3r: +1 per pass/tap, -1 on own write.
- Cross-region reader pins: +E+1 (lp lag_pins, unchanged from s5).

## Floorplan: enlarged, not squeezed

The outline grows from 2462.376 to 4060.776 x 2591.976 um:

- +907.2 um for the SU centre, so the VM8 group (1425.6 x 993.6) fits above su8.
- +691.2 um for two 345.6-um lrly strips. The 8 closed lane relays do not fit the full 345.6 lane cells.

This changes the die slot for the die GEN owner.

Open items, which the gate measures:

- The fdn<->fup face pass crossings are now about 3.5 mm, longer than the E2 / E4 landing window. They need a priced relay pad stage in the next GEN.
- The su8 -> lrly gb/pd1 group relay runs up to about 1.2 mm.
