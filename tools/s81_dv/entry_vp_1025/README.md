# S81 entry-port mechanism gate (TOK-DS/ENTRY 2026-10-25)

Regenerated from current sources after the 10-21 entry benches
(`/srv/opentallas-scratch/claude/codex-entry-vp-1021/tb_entry_vp*.sv`, absolute paths, deleted) were lost.
It feeds `tools/s81_dv/layer_prog/entry_mechanism.py`, whose receipt `entry_boot.py` consumes.

Cut (one slice, one beat leaf, one common bench clock):

    entry pin ot_s81sl_rstopt.{ri_w | ri_e | vi}
      -> ot_s81sl_xrt1 (production C1 control-plane master)
      -> ot_s81sl_rly W594 down / W667 up, 4 edges (the leaf glue of ot_s81sl_slice_c1x_k8_cap5r_lp:
         DLK 1 + one landed crossing of +3 edges on leaves 0/1/3/4, DLK 4 on leaf 2)
      -> ot_s81sl_vp leaf store (2 x ot_sram_1r1w_512x128_m4_r2c2)

Stimulus is the real entry image of the chosen (sid, leaf): `entry_inputs.compile_inputs(die, fixtures)` target-5 row
writes at the two-edge `entry_boot` cadence, then the leaf's own VP HLOAD / GAIN readers and an RDOUT of its delayed-pre
row, all encoded with `dv_layer_compile` (ctl_payload / ctl_line_beat / vp_cmd). The bench checks every commit's data,
reads every row back through the VP's own read path and requires no fault, no stray write and no other leaf touched.
The payload mutant flips one row-data bit at the entry pin and must fail.

Measured (parsed from the logs, never supplied): per write, entry pin edge -> SRAM `w_ce_in` edge; HLOAD pin -> last
`hw_v`; GAIN pin -> last `wl_v`.

```sh
# W cut (ri_w) and E/VI cut (ri_e, vi); ROOT = the tree holding this file (sources are hashed repo-relative)
python3 tools/s81_dv/entry_vp_1025/gate.py --cut w  --tree <die tree> --fixtures <fix/L0> --out <new dir>
python3 tools/s81_dv/entry_vp_1025/gate.py --cut ev --tree <die tree> --fixtures <fix/L0> --out <new dir>
python3 tools/s81_dv/layer_prog/entry_mechanism.py --w-result <w>/result.json --ev-result <ev>/result.json --out <receipt>
```

Fleet only (Verilator 5.050 + the in-tree `tools/verilator_nba_guard.py`), through `ot-run`. Default slices: ri_w sid 11 (u_s_5N), ri_e sid 5
(u_s_2N), vi sid 9 (u_s_4N), leaf 0; the gate asserts `ctl_path(die, slice)['entry_port']` equals the port.
Open: die route phases / regional clocks, the xgt_xo ring-stop variant (rstopt, ring +0), vn / vq / vs consumers;
the native-job cut replay (`tools/s81_dv/tokfunc/run_entry_replay.py`) is the runtime proof.
