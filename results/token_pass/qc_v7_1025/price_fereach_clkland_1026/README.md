# QC token price of D-QC-FE-REACH stations + landed clock-region crossings (TOK-QK-PRICE, 2026-10-26)

Base: claude/tok-qk-qce-1026@1121cb654, v7 bind re-derived (law) = 296,341 cyc/token = 4,051.0 tok/s (1 user, 36 layers,
833 ps). Method: add the new cycles to the bind lanes (`landed_stages += n` in bus_groups_v7), re-derive the die edges with
`rederive_edges_ext.py` (= ../rederive_edges.py + opt-in flags), compose with ../compose_edges.py (QCE engine tree, QCL S8
ages). Control `v7ctl` and `v7ctl_ext` (the flags with nothing added) both give 296,341 exactly.

## Result
| case | cyc/token | tok/s | delta | e2e loss | per layer (chained) |
|---|---|---|---|---|---|
| control v7 (QCE) | 296,341 | 4,051.0 | 0 | 0 | 8,129 |
| **(a) FE-REACH, generator n** | **302,965** | **3,962.4** | **+6,624** | **2.186 %** | +184 |
| (a) with only the 10-20 hop port set (lower bound) | 302,569 | 3,967.6 | +6,228 | 2.058 % | +173 |
| **(b) landed seams, aligned splits (PROVISIONAL)** | **297,637** | **4,033.4** | **+1,296** | **0.435 %** | +36 |
| **(a)+(b) aligned** | **304,261** | **3,945.6** | **+7,920** | **2.603 %** | +220 |
| (b) on the current tree split lines (upper bound) | 313,945 | 3,823.9 | +17,604 | 5.607 % | +489 |
| (a)+(b) current split lines (upper bound) | 320,569 | 3,744.8 | +24,228 | 7.558 % | +673 |

Every added cycle lands on the chained critical path: the per-layer chained delta equals the summed die-edge delta in all
cases, so none of it hides in slack.

## (a) D-QC-FE-REACH, per port
The per-port values come from the generator latency table, not the PLAN-DELTA lower bounds. Source:
claude/path-qc-fereach-1026@87bdf5071 `fe_reach_report.json`, copied to `fe_reach_lane_rows.json`.
- Rule: n = ceil(L/393) - 1 - core FIRM. 111 stations, 188 lanes, worst hop 384.6 um.
- n goes on the lane that lands on the FE in-bus. One value per port role over the slw/sle mirror pair.

| FE in-bus (out families) | n | ledger term that reads it | per layer |
|---|---|---|---|
| x_stm_i / x_stm_p1_i (x_stm_o/_p1_o, st_eo/st_wo) | +2 | slice2 pass, st (stm->fe st_up_c): 2 passes x 10 hops | +40 |
| x_fw_i / x_fw_p1_i (x_fw_o, cmd/dr/hr_eo) | +2 | slice2 pass, ch (fw->fe chr_c): 2 x 10 | +40 |
| x_sc_i (sc_eo) | +2 | slice2 pass, sc (sc->fe sc_up_c): 4 x 10 | +80 |
| st_Xi / sc_Xi inter-slice (st_dn_i / sc_dn_i) | +2 | dv chain hops, 11 x max (`--hop-ext`, the other direction of the same hop) | +22 |
| ag / ard / arl / arm / art / arv / dd_Xi (ch_up_i, ag_up_i) | +1 | dv chain hops (dominated by the +2 above; 10-20 port set only: 11 x 1) | (+11) |
| x_st_a_i (l9_eo / rd / rr / rv) | +2 | qkv L9 pair word @pre_qk | +2 |
| x_st_b_i (l9_eo sle_fe_v2 / v3) | +3 | L9 st_b path (5 < st_a 14): not binding | 0 |
| x_fw_p2_i (cmd_q / hr_c / treq_c: hr / rd / l9 / treq_eo) | +2 | not on the 10-20 path: cmd is issued ahead (law (b)) | 0, hidden in the static schedule |
| flt_e_i | +1 | fault lane | 0, off the token path |

Total +184 per layer x 36 = +6,624 cycles per token.

Where the generator differs from the PLAN-DELTA lower bounds:
- dd: generator +1, spec +2 (the u_fup core register takes one hop).
- x_stm_o: generator +2, spec +1.
- x_st_a: generator +2, spec +1.
- l9: generator +3 on x_st_b for sle_fe_v2, as the spec says.

## (b) Landed clock-region crossings: PROVISIONAL
COORD 01:22 ruled that seams crossing the root and level-1/2 split lines become landed crossings. CLOCK-MESH-2 has not
posted a crossing list yet, so these are candidate sets.
- **Cost per crossing:** one landing = K + 1 edges, with K = 2, giving +3. This is the 10-18 landed-parent standard,
  tools/landed_parent/specs ('E = K = 3 (+4 edges per landing, was +3)').
- **Region of a partition:** the centroid of its clock taps in the CLOCK-MESH QC tree (plan 2dd204af,
  epyc1 clock-mesh-2355/qc/kit/clock/tree.json, summarised in `part_taps.json`).
- **lit:** the tree's current split lines, x 7804.08 / 15608.16 / 23412.24 and y 13132.8.
  - They cut straight through the slice row (y split 13132.8 runs between slice ctl and fw/stm/fe) and through slices W0/W3/E2.
  - 26 cluster tiles straddle a split line: c_W0_*_1x, c_E2_*_1x, ... These are the same tiles as the CLOCK-MESH worst
    intra pairs (c_W0_tn_11 t24/t25, c_W0_bf_10 ...), and no landing can fix those.
  - 427 lanes cross. The slice pass law (max x 10 hops) turns this into an upper bound.
- **aln:** the same tree topology with every split moved to the nearest column or row boundary.
  - x 8981.28 (W3|W2), 16394.4 (W0|E0), 23807.52 (E2|E3); y 15820.7 (slice row | top cluster row).
  - 0 tiles straddle; 137 lanes cross.
  - CB16 x-in to the top clusters (cwn) +3 plus rs back +3 = +6 per matvec pass x 4 = +24.
  - 3 dv-chain seam hops x 3 = +9.
  - L9 pair E3 -> E2 = +3.
  - Total +36 per layer.

## Accepted-cost rule (owner 10-13: <= 5 % per unit, <= 15 % per design)
- **FE-REACH:** 2.186 % e2e, under the 5 % unit limit.
- **Landed seams (aligned):** 0.435 %, under the limit. The current split lines would give 5.6 %, OVER the unit limit, so
  the splits must be aligned.
- **Running QC (qwen_rom) total:** origin/main results/arch/accepted_cost_ledger_1013.json has 8.592 % (accepted 1.065 +
  proposed 7.527). Adding these two units gives **11.195 %**, which is <= 15 % (11.0 % if the two rows are summed
  separately: 8.592 + 2.186 + 0.435 = 11.213 %).
- **Not ledger rows:** the QCE re-derivation (+7.0k vs the 10-20 control) and v7 (+1,296).

## Files
- `price.py prep|rederive|report`, `rederive_edges_ext.py`, `run_compose.sh`
- `cases.json`, `add_*.json`, `regions_{lit,aln}.json`, `part_taps.json`, `fe_reach_lane_rows.json`
- `out/` (edges, lane ages, per-edge tables), `compose/q_*.json` + logs, `result.json`
