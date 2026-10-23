# KV-P3-LEAF 10-23: plan leaf variants (no straps) + plan ID / landing-check cells

Source die: case_kv/die.v @ e33504a6f (13,082 constant leaf-input bits on 41 ports; values in
kv-p3-1023/strap_values_rtl6.json). This step removes two strap classes at source level. The original leaf files are
not modified.

- Generator: `tools/qwen_kv_die/plan_leaf_variants.py`. It writes `rtl/qwen_sys/kv_plan_leaves_1023/*.sv`, the benches
  `rtl/test/kv_plan_leaves_1023/tb_*.sv` and `run.sh`. Its `--check` mode regenerates everything and requires
  byte-identical output. Each variant header records the sha256 of its original, so editing an original makes
  `--check` fail until the variants are regenerated.
- Transform:
  - The header is re-emitted with one port per line.
  - **Class A:** the port becomes `parameter [same range] UPPER`, and the body reads the parameter. Identifiers are
    substituted outside comments and named-port labels.
  - **Class C (chain head):** the predecessor ports are removed. The body sees each one as `localparam [range] <name> = 0`
    of the same name. This choice is deliberate. Each predecessor term enters through pin registers or child ports whose
    cones it shares with the live terms, so pruning it by hand would fork the body or the child modules. Synthesis folds
    the zero.
  - **Registers whose every assignment is a replaced constant:** their `(* keep *)` is dropped, so the constant flop
    folds and no tie cell returns. Each variant header lists these registers.
  - **eo:** `eo = EO_E*e + EO_RL*(e + e/2)` with `e = sq[2:0]`. This is the qkd_astk_strip_st instantiation
    `.eo(8'(9*e + RL*(e + e/2)))` with RL = 3 in the release strip (die: 0,12,27,39,54,66,81,93). `sq` stays an input.
- Benches (Verilator 5.050):
  - The original module, with the constant on its port (or 0 on the head inputs, or eo = 9e+3(e+e/2)), runs in lockstep
    with the variant.
  - Both receive the same random stimulus on every other input, including resets at cycles 0-11, 800-805 and 1700-1701.
  - Every output is compared every cycle for 2,400 cycles.
  - The mutant must FAIL: class A uses a wrong value on the original, a head uses random predecessor inputs, and eo uses
    eo+1.
  - Lint: `verilator -Wall` warnings of the variant must equal the original's, apart from DECLFILENAME and the module
    name.

| variant | original (source) | ports removed | parameters | runs (2,400 cyc each) | PASS | mutant |
|---|---|---|---|---|---|---|
| ot_qkh_lane8_p | ot_qkh_lane8 (rtl/hdc/nearhbm/ot_qkh_subtiles.sv) | bsel[1:0] | BSEL | BSEL 0,1,2,3 | 4/4 | 2 vs 1 caught |
| ot_qkh_head_frontq_native_p | ot_qkh_head_frontq_native (split_20261014/ot_qkh_head_native_r4.sv) | hid[1:0] | HID | 0,1,2,3 | 4/4 | 3 vs 0 caught |
| ot_qwen_tp8_pv_wide_ctl_tbf_p | ot_qwen_tp8_pv_wide_ctl_tbf (rtl/hdc/nearhbm/) | pair_id | PAIR_ID | 0,1 (die params TRUNK_D 54, FLAG_D 58, RESET_PIN 1) | 2/2 | 0 vs 1 caught |
| qkd_astk_ctl_s_p | qkd_astk_ctl_s (split_20261014/qkd_astk_static_leaves.sv) | st[1:0] | ST | 0,1,2,3 | 4/4 | 1 vs 0 caught |
| qkd_astk_zn_p | qkd_astk_zn (kv_die_20261009/qkd_astk_leaves.sv), zn_1..3 | zc[3:0] | ZC | 4,9,15 | 3/3 | 4 vs 5 caught |
| qkd_astk_zn_head_p | qkd_astk_zn, zn_0 | zc[3:0], fi | ZC | 0,3 | 2/2 | 0 vs 8 + fi caught |
| qkd_astk_ep_s_e | qkd_astk_ep_s (split_20261014/qkd_astk_static_leaves.sv), ep_1..7 | eo[7:0] | EO_E=9, EO_RL=3 | e = sq 0..7 | 8/8 | eo+1 caught |
| qkd_astk_ep_s_head_e | qkd_astk_ep_s, ep_0 | eo[7:0], xi[266:0], zi[650:0] | EO_E, EO_RL | e 0..7 | 8/8 | random xi/zi + eo+1 caught |
| qkd_astk_er_owner_st_head | qkd_astk_er_owner_st (split_20261014/), owner_0 | prev_v, prev_addr, prev_data, prev_fault | (N=4) | 1 | 1/1 | random prev_* caught |
| qkd_host_pc_slice_die_head | qkd_host_pc_slice_die (= die masters qkd_hslice and qkd_hslice_dn, same RTL), hsl_*S_31 / hsl_*N_0 | ci, ai, fault_i, ski, sdi, soi, sfi | - | 1 | 1/1 | random chain inputs caught |
| qkd_static_kv_landing_seg_p | qkd_static_kv_landing_seg (static_kv_20261014/); die master qkd_kvs_grp_h_r2c = mapped copy of qkd_kvs_grp_h_r2 -> qkd_kvs_grp_h.u_slg | cfg_group[2:0] | CFG_GROUP | 4 (die), 0 | 2/2 | 4 vs 5 caught (internal probe group_q*) |
| qkd_static_kv_pc_path_fan_nc_b_head_p | qkd_static_kv_pc_path_fan_nc_b (static_embedding_20261014/); die master qkd_kvs_pc_h = tile ..._n32_pj[_nc32].sv u_pc; u_chain -> qkd_kv_pc_chain_station_b_p #(.PC(PC)) | pc[4:0], fi | PC | 0 (die), 17 (MU=1) | 2/2 | 0 vs 1 caught |
| qkd_kv_pc_chain_station_b_p | qkd_kv_pc_chain_station_b (static_embedding_20261014/), u_chain of the pc_path; kept pin register spc folds (keep dropped) | pc[4:0] | PC | 0, 5, 17 | 3/3 | 0 vs 1 caught (probe spc) |
| **qkd_kvs_pc_h_head_p** (tile) | qkd_kvs_pc_h (static_kv_die_20261017/qkd_kvs_tiles_hroot_ff_k_hl_mu_ba_n32_pj.sv); u_pc -> qkd_static_kv_pc_path_fan_nc_b_head_p #(.MU(1), .PC(PC)) | pc__pc[4:0], pc__fi | PC | 0 (die), 17 | 2/2 | 0 vs 1 caught (probe u_pc.u_chain.spc) |
| **qkd_kvs_grp_h_p** (tile) | qkd_kvs_grp_h (same tile file); u_slg -> qkd_static_kv_landing_seg_p #(.CFG_GROUP(CFG_GROUP)) | slg__cfg_group[2:0] | CFG_GROUP | 4 (die), 0 | 2/2 | 4 vs 5 caught (probe u_slg group_q*) |
| **qkd_kvs_grp_h_r2_p** (tile) | qkd_kvs_grp_h_r2 (static_kv_die_20261017/qkd_kvs_grp_r2.sv, blob of e33504a6f); u_core -> qkd_kvs_grp_h_p #(.CFG_GROUP(CFG_GROUP)) | slg__cfg_group[2:0] | CFG_GROUP | 4 (die), 0 | 2/2 | 4 vs 5 caught (probe u_core.u_slg group_q*) |

Tile variants (KV-P3b-TILE 10-23). As-built sources, from case_kv/gen_source_ports.json @ e33504a6f:
- **qkd_kvs_pc_h** comes from `qkd_kvs_tiles_hroot_ff_k_hl_mu_ba_n32_pj_nc32.sv`. That file is not on this branch. Its
  qkd_kvs_pc_h and qkd_kvs_grp_h module texts are byte-identical to the ones in `..._n32_pj.sv`, which is on this branch
  (same blob as e33504a6f). The generator reads `..._n32_pj.sv`.
- **qkd_kvs_grp_h_r2c** is the mapped structural copy (kv_grp_safe5.py, 104,854 lines of ASAP7 cells) of
  qkd_kvs_grp_h_r2 in `qkd_kvs_grp_r2.sv`. That file is taken unchanged from e33504a6f (sha256 28ea75ab...). Its
  u_core is qkd_kvs_grp_h of `..._n32_pj.sv`.
- A mapped netlist cannot take a parameter, so the plan form of the die master is the RTL variant qkd_kvs_grp_h_r2_p. A
  die that adopts it must re-synthesise the group (and redo the r2c bounded-driver copy, if that copy is kept).
- Transform: the class A and C rules apply at tile ports. In addition, each `children` entry rebinds one instance to
  its plan variant. The generator adds `#(.PARAM(expr))`, removes the named connections, and asserts that each removed
  connection was exactly the replaced expression. A head port that was read only by the rebound child keeps no
  localparam.
- Lint: `-Wall` of the variant is compared with the original after child-variant names are renamed back to their
  originals.

Cells:
- `rtl/lib/ot_dp_id.sv` holds ot_dp_id_src (y = V), ot_dp_id_add (y = a + K mod 2^W) and ot_dp_id_rot (o = a[W-1:0];
  y rotated by one element).
- `rtl/lib/ot_dp_efault.sv` holds ot_dp_efault (saturating AGE counter after release, then a sticky
  `fault |= ~&eq`, async clear).
- Their benches are tb_ot_dp_id and tb_ot_dp_efault. Each PASSes and its mutants are caught (add K 2 / rotate the wrong
  way; non-sticky / AGE+3). `-Wall` lint is clean for (W 24), (W 40, K -3), (N 8), (N 3, AGE 6) and (N 1, AGE 0).

Result (Verilator 5.050, 10-23 10:15 PDT, KV-P3b-TILE): **SUMMARY pass 52 mutants_caught 20 lint_clean 21 fail 0**
- PASS: 50 variant runs and 2 cell benches.
- Mutants caught: 16 variant and 4 cell.
- Lints clean: 16 variant and 5 cell.

The full lines are in `bench_summary.txt`. The earlier run (10-23 08:07 PDT, 12 variants) was pass 43 / caught 16 /
lint_clean 17 / fail 0.

Limits:
- Below the rebound children, hierarchical leaves still pass the parameter or zero into child ports:
  - pc_path: `.pc(PC)` goes to u_pce, and `.fi(fi = 0)` goes to u_pce. u_chain now takes PC as a parameter.
  - landing_seg: `.cfg_group(CFG_GROUP)` goes to the 4 u_pc.
  - slice: ci / ai / fault_i go to the inner qkd_host_pc_slice.
- In these leaves the constant is a parameter expression inside the flattened partition, not a partition pin.
- The kept constant flop `qkd_kv_pc_chain_station_b.spc <= pc` is **gone in the plan form**. u_chain of
  pc_path_fan_nc_b_head_p (and so of qkd_kvs_pc_h_head_p) is qkd_kv_pc_chain_station_b_p, where spc is `spc <= PC` with
  the keep dropped. pc_sr in pc_path is likewise unkept.
- Deeper kept registers of the constant remain, because their children still take it as a port:
  - grp_h: qkd_static_kv_landing_pc `(* keep *) group_q <= cfg_group` (PRE_REG 0), 4 x 3 flops under u_slg.
  - pc_h: the controller chain under u_pce (qkd_static_kv_pc_path_nc -> qkd_ctrl_pc_host_static_nc / qkd_ctrl_pc_nc)
    holds pc strap registers (`pc_q <= pc`; `(* keep *)` pc_q / pc_core_q in qkd_ctrl_pc_host_static_core). Which of
    these are in the elaborated pc_h hierarchy has not been censused.
  - The same `children` rebind would remove them. A synthesis census (constant-D flops of the plan tiles) should list
    them first.
- Not done here: the die generator (kv_static_die.py) does not bind the `_p` / `_head_p` masters yet, and the
  qkd_kvs_grp_h_r2c mapped copy is still built from the strapped qkd_kvs_grp_h_r2.
