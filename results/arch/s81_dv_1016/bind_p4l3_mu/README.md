# MU-S81/DIE: multi-user p4l die variants, strict bind (10-19)

Branch `claude/mu-s81-die-1019`: the MU branch (`claude/mu-s81-1019`) merged with the S81 die base
`codex/s81-recovery-2323` (p4l3 bind tables, PHY ck_hbm 900 ps).

## Variants

All variants share one plan command: `tools/s81_dv/dv_plan.py --layout p4 --p4l --tier-w 276 --lanes 4 --p4h-drop 6 --frame-w 1436.832 --mu N`.

| `--mu` | Plan | Bind table | Strict DIE_PORT_BIND |
|---|---|---|---|
| 0 | `p4l/plan.json`, byte-identical | `bind_table_p4l3.json`, unchanged | PASS, 40 masters / 8,391 instances. `die.v` sha256 6949328418dc… is identical to the same run at the base `1cb62f92a`. |
| 1 | `p4l_mu` | `bind_table_p4l3_mu.json` | PASS, 41 / 8,951 (see `port_bind_mu.log`) |
| 2 | `p4l_mab` | `bind_table_p4l3_mab.json` | PASS, 44 / 9,042 (see `port_bind_mab.log`) |

`--mu 2` is the copy-A/B variant for the 64 pre-group and post-group rank dies.

Every PASS line reports 0 for each of: unbound, stub, port_not_in_rtl, width_mismatch, input_unconnected, input_tied, undriven, multi-driven and unresolved.

## Hardware

- **seqhost**: `dsdv_seq_host_mux` = `dsdv_seq_host_mu`.
  - Parameters: NSLOT 47, NEV 8, 4 end slices, NRT 2.
  - `dsdv_mu_hslot` NEV > 0 fires per-start events at a fixed offset D from each start:
    - TX tag windows `mu_c`;
    - landing replays `mu_rc`.
  - `mu_rt` RX tags are checked against the outstanding `{user, pos}`.
  - Boot config `f_mc` comes from the host stream as CSR 0x15, decoded from `f_host`, so it needs 0 die wires. The ingest ignores class-0 index 0x15.
- **End slices**: the `_mu` / `_mus` / `_mab` masters in `ot_s81sl_slice_lep.sv`, with `dsdv_mu_land` inside each MU cluster.
- **Wiring**:
  - s_7N: mu rides in `ht_7N` bits 131..175 and rt in `hf_7N_l2` bits 20..51.
  - s_0N: `mu_0N` / `rt_0N` lanes (276 b).
  - s_0S / s_7S: `mu_0S` / `mu_7S` lanes.
  - Landing K: these lanes take the default K 1. They are not yet in the land plan.
- **AB variant**: s_0N gets a second lane pair to `lk_WN2` / `lk_WN3`, two extra `ot_pdie_serdes` on the W edge.

## Costs and open items

- **Plan**: bit-mm goes from 364,117 to 395,325 (+8.6%) and worst cut from 0.536 to 0.566. Each lane carries only 45 / 32 of its 276 b. A narrower 70-b E/W relay view would cut most of that.
- **Owed**:
  - S-tier `mu_rt` is not returned to the seqhost: the column-4 margin has only 2 free tracks below the seqhost.
  - `t_mf` stays open, like the other block fault outputs; the die status fold is still owed.
  - AB vertical relay masters `dsfd_dvrlyh_512_NS/SN` and `562_NS` are RTL stand-ins with no closed view.
  - The AB PHY slot runs along a 40-µm frame/PHY gap and needs a COORD decision, shared with AD-S81-LINK.
  - Kits for `dsdv_mu_land`, `ot_s81sl_lep_mu` and the hslot leaf belong to MU-S81/KIT.

## Benches (Verilator 5.050)

- `results/rtl/mu_s81_die_1019/win`: MU_WIN_GATE PASS.
  - 32 starts and 80 fires, all exact.
  - A bad RX tag raises a fault.
  - RTL mutants 3 and 4 FAIL, as required.
- `host_regr`: MU_HOST_GATE PASS. The NEV 0 slot table is unchanged, and the user-0 trace matches single-user.
- `lep`: LEP_MU_GATE PASS on ot-epyc5 at 36ebf5d02 (MU seeds 1 and 5; TAGDROP, WRONGCOPY and OVR FAIL; single-user regressions lep s1/s7, nh, host PASS; SWAP FAIL).
