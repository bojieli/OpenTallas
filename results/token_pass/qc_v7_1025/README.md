# QC token cost of the v7 CB16 phase candidate (TOK-QK-QCV7, 2026-10-25 23:41 PDT)

Source: claude/tok-qk-qcv7-1025@5832e6722 = main cfea7b3a1 + codex/qc-phase-2209@13f33606a (v7: strict PASS 377 parts / 79 types, 0 errors).

## Result (cycles per token, 1 user, 36 layers, composer toksim_compose.py at the QCL measured-age tree)
| case | cycles/token | tok/s | chained/layer | L0 cold |
|---|---|---|---|---|
| frozen plan 441d1401 base R8 (QCL measured ages, reproduced exactly) | 288,025 | 4,168.0 | 7,898 | 8,410 |
| v7 final bind (this qualification) | **289,321** | **4,149.3** | 7,934 | 8,446 |
| price of record (results/arch/token_path_1018) | 249,431 | 4,810.9 | | |

Delta v7 vs frozen 441: **+1,296 cycles/token (+0.45 %)** = +9 cycles per matvec pass x 4 matvecs x 36 layers.
- CB16 phase pads alone (v7 base -> v7 final): **+0** on the critical path (cluster roots +1 on 12 clusters, 6 -> 7, below the max 8).
- All +9 comes from the v7 physical pipeline stages (405-um hops) already in the v7 priced base: x broadcast bc/bcf lanes +4 (Max),
  hc cws/cwn x-in lanes +1..+4, tree a/b lanes, root->slice rs lanes +2. Max-path (x-in -> c16 root -> slice rs): 441 = 7, v7 base = 16, v7 final = 16.
- Other changed lane class: sl_*_su_l*__flt -8 (fault lane, not on the token path). No other lane of the 1918 differs.

## Method
1. cb16_path.json: roots.py (cb16_dag.baseline from codex/qc-phase-2209, per cluster root phase + rs lane added stages from bind_sinks)
   on the three binds, run via ot-run (units oth-ubuntu-1185339-1792996747 epyc1, -996795/-996792-1792996722 intel1). Reproduces Codex
   cluster_output_delta (base 8/6/-7, final 8/7/-7).
2. lane_delta.py on bus_groups_{ref441,v7base,v7}.json.gz (committed here): per-lane landed-stage deltas by class.
3. compose_edges.py = TOK-QK-QCL compose.py + one appended ledger die edge (edges_v7_vs_441.json: +9 at pre_qkv/pre_o/pre_gu/pre_down);
   run.sh via ot-run intel2 unit oth-ubuntu-4006188-1792996857: q_none.json (288025, identical to QCL measured.json) and q_v7_vs_441.json.

## Not qualified / scope
- The composer's own ledger die edges (g5r2b landings, slice2 536) are still the 10-20 PRICED list, not re-derived from the 441 or v7 bind;
  this receipt prices the bind-relative v7 delta only. No RTL stage rerun was needed: no slice/vec/stn stage-internal age changed (only die lanes).
- Bind inputs (runtime dirs) are named above; their bus_groups are committed here gz. The full bind_sinks (240-270 MB) are not committed.
- No whole-die RTL token run on the v7 bind; native hard views / G2 / clock-provider ownership remain open (Codex README).
