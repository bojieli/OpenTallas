# DIE-LAYOUT-HBM 11-11: scorer planned positions (folded into the CPL-HBM-B1 d6 positions event)

DIE-HBM-100 asked for planned positions of the soft `hb_idx_s_*_scorer` groups. Without them, TOOLS-2's
kit_bus_bitgroups cannot site the bank-bus bits those groups read or launch. COORD ruled that the rows go into
the CPL-HBM-B1 d6 event.

The change is positions only, with 0 cycles. It changes no RTL, no register count and no bus depth: each
scorer row has exactly the bus's current depth, and `apply_scorer.py` refuses any other depth.

## What the bound RTL says (t19 bind, `trace/*.jsonl`, `trace_readers.py`)

| type / bus | owner of the unresolved bits on t19 | rows here |
|---|---|---|
| q_b001 L14_i (+pv1) | bits 0-2776 go to `g_hb_idx_s_SE_scorer_ge_1_gc_0_leaf_*` (pv1: `SW_`), then soft pipeline (depth 4-6) to the 8 r1c0 hcol cores. Bits 2777-2805 go through `u_hcb_Q1_u_c` regs to the 8 pairs. Bits 2806-4126 go through the pd2 dly pads (TOOLS-2 -2 makes them pass-through) to the pairs. | 1 scorer row, 2777 b |
| q_b000 L14_o (+pv1) | bits 0-2776 come from `hb_idx_s_SE_scorer` (pv1: `SW_`), a soft bus-to-bus stage (`L160m_i_q` -> procdff_71770 -> u_bout). No hard core reaches it. Bits 2806-4126 come from `u_hcb_Q0_u_c` regs fed by the 8 pairs. | 1 scorer row, 2777 b |
| q_b002 L42_i, q_b011 L43_i | No scorer on t19. Bits go to `g_u_hcb_Qx_procdff_*` / `u_c` control regs, broadcast to all 8 pairs. | none |
| q_b010 L11_i | No scorer on t19. Bits go through `u_hcb_Q7_u_c(_u_b)` regs to all 8 pairs (broadcast). | none |
| q_b011 L11_o | No scorer on t19. Each 512-b slice is one pair's `sum_out` at depth 1. | none |

The scorer ranges TOOLS-2 reported for q_b002, q_b010 and q_b011 came from plan 29333b2b with bindrtl_k5d, not from t19.

## Site rule (`scorer_rows.py`)

- **Group reaches hard cores:** the site is the point nearest the bus face on the box around the hard cores the
  group reaches (box grown by 2 x halo), moved out of every core box. This places the group between its cores
  and the face it serves.
- **Group reaches no hard core:** the site is the midpoint of the source-bus face and this bus's face.

The stations are the bus depth, spread along an HV or VH Manhattan path from the face to the site, avoiding core
boxes. `apply_scorer.py` appends the row. To fix the stale attribution it also rescales the bits of the other rows
on the same bus so the bus total stays the same (largest remainder, at least 1 per row). It changes only their
`bits` and appends to their note.

| type | bus | group | bits | site (um) | depth | max hop |
|---|---|---|---|---|---|---|
| q_b001 (d6) | L14_i | hb_idx_s_SE_scorer_ge_1_gc_0_leaf | 2777 | 1564.70, 1334.88 | 10 | 73 |
| q_b001__physical_v1 (d6) | L14_i | hb_idx_s_SW_scorer_ge_1_gc_0_leaf | 2777 | 1624.32, 1300.32 | 10 | 57 |
| q_b000 | L14_o | hb_idx_s_SE_scorer | 2777 | 237.60, 3248.08 | 9 | 108 |
| q_b000__physical_v1 | L14_o | hb_idx_s_SW_scorer | 2777 | 237.60, 3208.77 | 9 | 108 |

The q_b001 sites depend on the d6 r1c0 frame (CPL-HBM-B1 6d5ebe21). If d6 moves again, re-run
`scorer_rows.py PLAN t19-rtl OUT q_b001:L14_i q_b001__physical_v1:L14_i q_b000:L14_o q_b000__physical_v1:L14_o`.

## Gates

- **Base:** d6 = CPL-HBM-B1 lad/c4apply die_plan 6d5ebe219622. Base + rows = f4da37bcfcbe (`plans.sha256`).
- **G0 (main check.py):** 552 -> 552, 0 new and 0 lost messages (`g0main_d6_vs_d6sc.txt`).
- **chainchk (TOOLS-2 `bus_bitgroups_report.py`, fecdddfb tool), unresolved bits:**
  - q_b000 L14_o: 2777 -> 0
  - q_b001 L14_i: 4098 -> 1321. The 1321 left are the pd2-pad bits; TOOLS-2 -2 (efdab72) resolves those.
  - The scorer group's planned hop is <= 108 um. The worst group hop is still the pair rows: 367 / 359 um.
- **Not run:** the -2 branch is not on the hub remote (efdab72 is unadvertised there), so the -2 tool was not run.

## TOOL finding (for TOOLS-2, not part of this delta)

On t19, `core_of_entry` cuts captures at the first dot. Every `u_hcb_Qx.ot_hbm_hc_bank128_pairN.*` row therefore
becomes ONE core, `u_hcb_Qx`, which matches every `u_hcb_Qx_*` RTL token, so there is no per-pair split.
`chainchk_tool_p_d6.tsv` shows cores = 1 on every bank bus. The 349-402 um figures were measured on 29333b2b.

With a 2-line dot fix (`kit_bus_bitgroups_dotfix.diff`), the 8 pairs separate. But the in-bus bits reach the pairs
only through `u_hcb_Qx_u_c` soft regs, which the one-level reader match does not resolve ("no-owners").
On t19 those bits are broadcast to all 8 pairs, so no per-pair split exists for them.
