# TOK-DS/COMP: S81 per-stage component benches on main RTL (2026-10-24)

Main `8a5d1f3dab`. Branch `claude/tok-ds-comp-1024`. No RTL was changed. Two bench tools got inventory/parse fixes;
these are listed below. Verilator 5.050. The NBA guard is not installed on the new fleet, so every obj dir was scanned
explicitly with `tools/verilator_nba_guard.py` (0 findings everywhere). One receipt per bench: `*.json`
(schema `opentallas.tokds.comp_receipt.v1`, readable by `compose_tok_ds.py --components`). The receipts carry no `op`
binding: these are mechanism-shape components, not production-shape stage replacements.

| bench | verdict | mutant(s) | bit-exact compare | cycles (main) | 10-21 record | delta | run dir |
|---|---|---|---|---|---|---|---|
| owner fold (VP+VS op11 RB) | PASS | MUT2 CAUGHT (4 mism) | 4/4 FP32 words, 0 mism | 20/20/20 per RB cmd->last result | 20/20/20 | 0 | epyc2:/srv/opentallas-scratch/claude/tok-ds/comp/owner_fold |
| dense XS4->frame->capc5r | PASS | input corruption CAUGHT (4 returns + 4 CAP) | 12/12 returns, 4/4 CAP vs checkpoint | cfg 390, GO 453, returns 726..752, last CAP 825 (GO->CAP 372), shift 322 | same, shift 322 | 0 | epyc3:/srv/opentallas-scratch/claude/tok-ds/comp/dense |
| KV VP (real VP + D512 KV bank) | PASS | exp-drop CAUGHT (8 mism) | 26 events / 52 pair writes, 0 mism, 190/190 ext resp @4 | results 266..285; GK/KV cmd->done 1028/1133 (drain 1024+104) | same (R3) | 0 | intel2:/srv/opentallas-scratch/claude/tok-ds/comp/kv_vp |
| rstop (rstopt_xo, 16-stop ring) | PASS | xooff/xoall/xonoflag/tiercol CAUGHT | sid 144/144, xo 138/138; 80/80 egress exactly once | inject->s_0N egress 7..23, egress +0 edges | 7..23 | 0 | epyc2:/srv/opentallas-scratch/claude/tok-ds/comp/rstop |

Notes
- Owner fold: the first attempt failed in tooling. `owner_fold_bench.py` read `${S81_VS_EXTRA_SOURCES:-}` (prepended in
  `vs_bench.sh` since 11ed229e0b) as a file name. Fix: expand the token as the shell would (empty).
- Dense: the old vectors (gold1 `vec_B_kv_landed_current`, die 86dd02b2) were wiped. They were regenerated with the 10-21
  recipe on the fc31 die tree and the L0 fixtures on epyc3. `lower_xs` refuses main's `ot_s81sl_xrt.sv` (sha 0ec7a8db,
  not in `xr_timing.XRT_MODEL`). Generation therefore used the parent lane's root30 for that whole-die transport check
  only; the bench has no XRT. On main, `run_dense_xs_cap.sh` failed with MODMISSING twice: `ot_pl_land_reset_forest.sv`
  and then `ot_pl_land_field_copies.sv` were missing from its inventory. Both were added. Attempts 1-3 are preserved
  in `dense/attempt*`.
- KV: the kv_bank_1021 baseline output is lost. The baseline was rebuilt from the committed R3 vectors (sha-matched)
  with main's source hashes. Main differs from the R3 pins in ot_reset_sync, ot_s81sl_kv_bank and ot_s81sl_kv_leaf
  (`kv_vp/baseline_pin_diff.json`), and the numbers are unchanged. `gate.py` itself is unchanged; a private HOME
  supplies the guard. kvleaf_prog/kvleaf_check (the same leaf driven through a whole G9 cut) was not run, because it is
  not the minimum component.
- None of these is a production-shape throughput bench in the AGENTS.md "throughput qualification" sense.
