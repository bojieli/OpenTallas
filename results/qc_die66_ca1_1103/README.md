# DIE-QC-66/CLK: QC count-aligned +1 cycle value event (30 crossings, v3 die clock)

This is ONE plan delta on origin/main f31a5bdcd7. It applies after the windows event 1e5ed443cd and the RED event 8247ff4ce2.
Base plan_qc52 sha256 6331b0559332; new plan d1469f690993.

## What changes

- **Plan:** in `clock.landing_network.count_aligned_cycles`, 30 ports move +1 (3 to 4), listed in `delta_ca1.json`
  (= `results/qc_die66_clk_1103/ca_v3/judge_v3_delta.json`). They are:
  - `x_su_l0_ctl` ×12
  - `x_su_l0_sc` ×12
  - `sl_E*_st_a__x_st_a_fe__4` ×6

  `latency.lanes` is recomputed with main `gen.latency_table` (`results/qc_die57_1031/relat57.py --write`). On the 30 lanes,
  `cycles`, `natural` and `clock_landing` each move +1. Nothing else changes: DEPTH, tree ports and geometry stay as they are,
  so this event is orthogonal to the DIE-QC-66/PLAN CB-row y-shrink.
- **Sidecar:** `bind/sidecar.json` is the as-built sidecar of record (`qc_die63_red_1102/bind/sidecar.json`) with
  sched_lat / K / added_cycles moved +1 on the 30 ports (`mk_sidecar66.py`, the DIE-QC-57 recipe). The script checks
  that sidecar cycles equal the base plan cycles on 2525/2525.
- **As-built manifest:** `bind/final_asbuilt.json` is `qc_die63_red_1102` final with a fresh R8 (`bind/r8/`), a fresh CB16
  (`bind/cb16_pads.json`) and the new sidecar.
- **Chain:** `run66.sh`, which is the DIE-QC-57 `run57.sh` chain plus a fresh elab, base-of-record bind and G0C;
  `base66.sh` reruns the base with the plan copied in place.

## R8 effect (fresh table vs qc_die57 r8 of record)

- The 30 event lanes: bound +1, landed +1, pad 0.
- 42 sibling lanes in the same bus groups (`x_su_l0_su_c`, `x_su_l0_su_c_p1`, `x_su_l0_stm`, `x_st_a_ctl`): landed +1 via pad +1.
  That adds 12,720 pad flops (920,300 to 933,020); max_pad goes 22 to 23.
- 1188 members change in all; no member is added or dropped.
- CB16 pads: identical except the `r8_table` path.

## Checks

| Check | Result |
|---|---|
| Strict bind final | 1 error = `EMIT collector rst_n_t24: raw reset parent rst_rl_121 absent`; 119 types, 0 splits, unbound 0 |
| Strict bind, base of record | 1, the same error, so 0 new |
| G0C | base 9 errors / new 9 errors, an identical sorted set (the pre-existing sc_v* hard_cores errors); 601 warnings each, so 0 new |
| CA judge on the new plan (`results/qc_die66_clk_1103/ca_v3/ca_judge66.py`, v3 proof, gate interval model) | 0 fail of 2525. TT lo +100.4 / hi +137.8, FF lo +154.2 / hi +321.6 (`judge_ca1.log`). Before the event: 30 fail (TT −169.1). |

## TOK-VERIFY-1 must re-run

1. **Schedule / latency:** `latency.lanes` changes on 72 lanes:
   - the 30 event lanes (cycles/natural/clock_landing +1);
   - the 42 R8-sibling lanes, which land +1 through pads.

   Re-derive the static schedule / pipeline-latency table (`gen.py latency`, `schedule_check`) for su_l0 → fe/su_c/stm and st_a → fe/ctl.
2. **LEC/EQ:** re-run on the bound landing RTL of the receiving types:
   - 9 fe types: `sle_fe_v1__cl1cbb7497`, `sle_fe_v1__cl8210183c`, `sle_fe_v2`, `sle_fe_v3`, `slw_fe_v1__cl95cd1d0c`,
     `slw_fe_v1__clfe325744__cl08d14f0d`, `slw_fe_v1__clfe325744__cldb4efe33`, `slw_fe_v2__cle312294d`, `slw_fe_v2__clf110fab2`;
   - plus the su_c / stm / st_a ctl sink types of the 42 sibling lanes (54 sink partitions in all).

   Ring K and pad depth move, so EQ is expected to differ by exactly that +1 cycle; the bound landing netlist vs the RTL of record must be re-proved.
3. **tok:** re-run the QC token sim and the tok/s re-baseline. Under owner 12.21, tok/s loss from closure fixes is accepted.
   The SU l0 → fe / su_c / stm and st_a → fe/ctl paths each gain +1 cycle.

## Note (not covered)

The START-tree skew and cleanliness on the v3 proof are not re-timed: the as-built START ports have no proof timing,
because the start_plan56 of DIE-QC-56/57 is gone. Kept as a note, as DIE-QC-66 ruled.
