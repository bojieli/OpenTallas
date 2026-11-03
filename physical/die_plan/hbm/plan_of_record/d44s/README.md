# HBM plan event d44s = mu1-3sram (TOK-HBM-2, from TOK-HBM-1's event; 2026-11-02)

OWNER 2026-11-02 19:19 PST ("agree with 3-SRAM layout", mu1 option A): mu1 = 3-SRAM. This replaces the 4-SRAM
(vec6293 / r2048 grown bank) plan of record.

Base: d44q (die_plan 3171b0fc3732, core_macros 3bca79b4624e, clock_entries 8883cf02258f, core_conns e689ac2475d8).
Tool: `tools/hbm_b2/mu1_3sram_event.py <d44q plan dir> <out dir>` (re-run byte-identical on all four rewritten files).

## Change
- The 16 hard cores `u_vmb_Q0..7_mu1` of `q_hub_nw` (8) and `q_hub_ne` (8) change module
  `hnx_vms_bank_q0_faces__vec6293` -> `hnx_vms_bank_q0_faces__vecd4ae` (the 3-SRAM bank, 3 x
  `ot_sram_1r1w_1024x256_m2_r2c2`).
- Same origin, orient and 270 x 403.92 um outline. Each instance keeps its own pin faces: its old pins file minus the
  14 pins that exist only on the 4-SRAM bank (`clk_macro3`, `rq0..4[17]`, `dq/kq/wq0/wq1[281]`, `pq[285]`,
  `eg/xq/xq2[276]`). That gives 3933 -> 3919 pins, which is exactly the vecd4ae pin-name set. There are 2 new pins
  files (`cores/*__mu1s3__*`: 12 instances in MY, 4 in R0).
- clock_entries: 16 entries now vecd4ae, with `clk_macro3` removed. Clock taps with budget_owner vec6293 -> vecd4ae.
  Mesh core island folded into vecd4ae (identical rects).
- core_macros: the vec6293 entry (4 SRAM) is dropped. Result: -16 SRAM macros, -16 macro clocks, -224 bank pins,
  and module type vec6293 is gone from the plan (32 vms banks, all vecd4ae).
- pin_windows: the vec6293 record is retyped, with pin counts recomputed.
- core_conns: unchanged. The base has no entry on any `_mu1` bank, and no dropped pin is referenced. The mu1 clients
  are the open S-role ports of the 8SM->4-role fold, which is pre-existing and not changed here.

## Equivalence / sim gate
- SOURCE: all 32 bound banks in the selected source (stage11/13 selected_preprocessed.sv, 32 instances
  `u_u_vmb_Q*` / `u_u_vmb_Q*_mu1` in two hubs) instantiate the single module `hfd_vms_bank_native_q0_faces` (3-SRAM).
  So plan-vs-source equivalence holds by identity. The 4-SRAM r2048 bank was never in the selected source
  (tools/hbm_b2/vms_current_native_kit.py already rejects a vec6293/r2048 alias). No RTL change.
- Capacity: the compiled programme VM is 262,144 words = 32 banks x 1024 rows x 8 words. Static high-water is
  255,168, plus the 1,024-word scratch at 261,120. No instruction addresses a regular row >= 1024.

## G0 / G0C (tools/die_plan/check.py at origin/main 7cf44d5c0d3, same tools on d44q and d44s)
- G0: d44q 184 ERROR / 1003 WARN; d44s 184 / 1003.
- G0C (--completeness): d44q 250 ERROR / 128 pending / 1162 WARN; d44s 250 / 128 / 1162.
- Message-set delta: exactly 2 messages change and no message is new or gone. These are the pre-existing core_faces
  findings on `q_hub_nw u_vmb_Q6_mu1` / `u_vmb_Q7_mu1` port dq (face away from u_vmdel_Q6/7), where the count goes
  282 -> 281 pins because dq[281] is dropped.
- The larger absolute counts versus the committed d44q reports (6 / 14 ERROR) come from the newer check.py. They are
  the same on both plans, and both runs' reports are kept in g0/.

## Consumers
- mu1 kits: build only from the vecd4ae (3-SRAM) recipe, one design per mu1 pins file (2 designs). Build no
  vec6293 kit.
- Plan dir with all sidecars (hard links): intel1:/srv/opentallas-scratch2/claude/tok-hbm-2-1102/mu1/plan (.keep).
