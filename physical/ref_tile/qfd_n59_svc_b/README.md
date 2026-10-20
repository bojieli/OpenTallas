# qfd_n59_svc (QW-N59-4, 10-19) -- service child of the hardened native59 split (Q.STA.N59)

Why: see physical/ref_tile/qfd_n59_qbank/README.md (safe4 / safe4b one-root CTS stall, spread 145 / 127, SS setup -635).
RTL rtl/qwen_split/qfd_native59_svc.sv: the same text as qfd_native59_dv_service (SAFE 2, ROOTS 1, RST_FOREST 1; NU 4,
MCTX 1, EMB_RELAY 1) with the Q-seat section replaced by the bank child's registered qb_* words; dd_i / layer_context_v /
command_stage arrive as the bank's one-edge relays.  Lockstep vs qfd_native59_dv_service_r1: run_native59_split_bench.sh
(mutants m2 / m3 / m5 FAIL; witnesses results/rtl/mu_qwen_1018/n59_split4).  Kit _b = unclustered H-tree CTS (fallback).

## SAFE-DESIGN checklist (owner 10-19)
1 Pins: PASS -- every input lands in a p_* pin register; outputs are flops (native_tx / completed: the r1 2-slot AND-OR of
  slot flops, unchanged); rst_n 2 landing stages x 32 copies + the r1 kept reset forest (top 48 copies: Q state moved out).
2 Reach: PASS by construction -- 518.4 x 216; emb_code_q and dr_o both on the E face (the EMB relay hop stays local), link
  ports N, command / host / status W, bank words S.  Measured on the CTS gate layout.
3 Fanout: PASS -- r1 kept copies (emb select 16 + 16, reset forest); the 512-seat Q logic left with the bank.
4 Depth: PASS -- r1 logic (ideal-clock STA at safe3c: every non-dr_o / non-Q class >= +22 ps); the Q word now arrives
  registered from the bank.
5 Storage: PASS -- no SRAM; no runtime-indexed flop array > 2 kb.
6 Floorplan: PASS -- std-cell only, pin-bound (4,690 pins, max 4.83 pins/um on the E face), 518.4 x 216 (aspect 2.4:1:
  the slot width; pin faces need it), full-width rows.
7 Clock: PASS -- one root ck at the N-face centre, its own region in the landed parent (ck_svc); io_hold_margin 0.03.
8 Schedule: static; the service runs 1 (split) + 3 (landing) edges behind the bank ports: compiler NOTICE in lanes/QW-GEN3.md.
