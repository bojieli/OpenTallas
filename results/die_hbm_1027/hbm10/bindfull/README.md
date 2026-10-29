# DIE-HBM-10 bindfull (10-28): SU/SFU release slices bind full RTL; opt-in no-stub check

## Diagnosis: no stub was bound (CHECKED)
- **Bound forms.** In sbind_canon (die-hbm-7, plan c20j), the 8 SU slices (su_NE0-3 / su_NW0-3) bind `ot_hbm_su_static_pgslice_lg_s` and the 2 SFU slices (sfucore_NE/NW) bind `ot_hgi_sfu_core_split3_sp2`. Both come from manifest `alias` entries in results/die_hbm_1027/hbm7/bind/asbuilt_canon.json.
- **They are full RTL, not stubs.** Elaborated from asbuilt.json:
  - each SU slice: 3568-3607 glue cells plus 68 leaf instances (32 lane_pinreg, 32 pinned_bank, 2 vm_bank_leaf, pretree_s, lg_pair_tap);
  - each SFU slice: 65 glue cells plus 35 leaves (16 su12_sfu_sp2, 16 lane_map, operand_store, rst_relay, vm_static_bridge).
- **Every module under them resolves to a full RTL body.** That is 49 modules for SU and 50 for SFU, the SRAM behavioural models included; see release_full.json.
- **Leaf references are by design.** The binder elaborates leaves as interfaces (asbuilt_lib_stubs.sv); the partitions instantiate the real leaf files, which are listed in bind.f.
- **Why "stub" was reported.** DIE-HBM-9 read only the first hierarchy level:
  - lg_s = `$dff` + `g_tap_r8b.u_tap` + `u_slice`;
  - split3_sp2 = 1 instance of split2_sp2, a pure port re-slice.
  - Its slice-rule paths were also wrong: the real paths are `u_slice.g_lane[k].g_pr.u_lane`, `u_slice.g_bank[k].u_bank` and `g_tap_r8b.u_tap`.
- **The aliases are the RELEASE forms.**
  - `_s` carries PIN_REG=1 and the side cut `ot_hbm_su_static_side_s` (side_softplus | side_rest). The plan slices `pgslice_lg__side_rest` / `__side_softplus` exist only in `_s`; canonical pgslice_lg has no side_s.
  - `_sp2` is the store-side pin-register twin with the `ot_su12_sfu_sp2` lanes.
  - Preferring the canonical masters would therefore bind RTL that does not match the plan, so the alias stays.

## Fix: opt-in, default byte-identical
- **Check.** `tools/die_plan/bind_elab.py` adds `release_full_check`. Manifest key `release_full: [die master]`; `release_full_allow` is an optional regex list.
  - After `alias`, it walks every module under each release master.
  - It FAILS CLOSED on an undefined module, a `_bb.v` black box, or a stub body (no always/assign/initial/gate and no instance).
  - It records the full-RTL manifest (repo-relative files) in asbuilt_sources.json as `release_full`.
- **Declared.** asbuilt_canon.json now sets `release_full = [ot_hbm_su_static_pgslice_lg, ot_hgi_sfu_core_split3]`.
- **Tests.** `test_bind_release_full.py`: 4 tests (pass, stub, _bb, undefined, no key). All 26 `test_bind*.py` files PASS.

## Runs (intel2, CHECKED)
- **elab** on C24 3ab76af4 with release_full: rc=0 (logs/elab.log). The release_full record is in elab_asbuilt_sources.json.
- **Negative test** (rf_run.py): a header-only lane_pinreg put first in `prefer` gives "selects a STUB body" and fails closed.
- **strict bind**: 476 errors vs 473 before (strict_counts.json, logs/bind_strict.log.gz).
  - 0 errors mention the SU/SFU slices, before or after.
  - The +3 come from C24's PHY split: the canon map still sends phy_NW to PHY_N, and the new PHY_NW / PHY_NE partitions are empty. This is a map update owed with C23q/C24.
- **verify** (bind_verify) was not run: it runs only after a strict PASS. run_bind.sh wires elab, then bind --strict, then verify, and keeps the logs.

## What remains before a strict-clean current bind
- 201 UNMAPPED: hb_idx__s_* scorer cells. The IDX quarter source needs an RTL owner ruling (b102/b103).
- 200 TIED: idx slice inputs.
- 30 UNPLANNED: fold/root nets, hub<->hub.
- 28 TYPE_SPLIT: NW/NE ft lane mirror order.
- 10 LOCAL_NAME_CLASH: fold halves need __q0/__q1.
- EMPTY_PARTITION: NW/NE_mca, plus the PHY split map (3).
- 1 EMIT, 1 TIED_TOTAL.
- After that come the unified top and a compiling static programme. Not built here.

## TOK-HBM-4 (10-28): S roles on their own q0 halves + PHY split, re-bound on C25b

COORD ruling TOK-HBM-4 (default YES). Opt-in, HBM only: new map / manifest files, no tool change; other dies byte-identical.

- `mk_c25b_instmap.py` -> `asbuilt_map_c25b.json` (bind map_file) + **`instance_map_c25b.json`** (top -> plan instance map).
  - 45 hub instances renamed to their OWN plan half wherever C25b has distinct `__q0`/`__q1` hard cores:
    S role (SW/SE) -> `__q0`, N role (NW/NE) -> `__q1` (calendar, hb_idx op/q/qctl, hb_vms both roles; cij, cxij_q,
    hb_dbk, hcollgi/gl, pgp, sfup/sfus, smw, sucore, wbk, xl_ctl, hb_quant u_dec N role). No S role aliases an N instance,
    no request queue is shared, 8 SMs unchanged. The script fails on any hub local-name clash.
  - per instance: partition, plan type, plan inst, half, plan module, plan params, as-built module + params
    (103 module differences are all plan `__pvN` param variants of the same master).
  - the 88 S-role fold nets (die inputs of the composed top today), from the C25b fold map + TOK-HBM-2 census:
    - 20 `Q0_PLAN_INSTANCE_NO_ASBUILT_DRIVER` (hb_dbk 2, smw 16, xl 2): C25b has the q0 copy; the composed top has no S producer.
      Emit it with the plan leg params (QID ...), never the N template's (template params recorded).
    - 60 `PLAN_HAS_NO_Q0_COPY` (hcollks 8, hcollrs 2, hleaf 18, su 16, vmdel 16): C25b carries these families once.
      A plan event must add the q0 copy before any bind can emit it. The bind cannot invent a plan instance.
    - 8 `NO_PROVIDER_8SM` (svg_SW0-7 sm_packet): the 8-SM release has no S-role SM.
- `phy_split_top.py` (2): rewrites only `phy_NW` (one 32-PC `ot_hbm3e_phy_rc_e8p5`) into `phy_NW_pc0_9` / `_pc10_21` / `_pc22_31`.
  - The slices are rc_slice macros: `phy_slices/*_bb.v`, generated by `tools/mem_compiler/hbm_phy_gen.py --variant rc_slice`, byte-equal to the C23q views.
  - Each PC keeps exactly its nets (32-item p31..p00 concatenations checked); clk/rst_n are shared.
  - Mapped to PHY_NW / PHY_NC / PHY_NE `u_phy_Q`. Report: `phy_split_top_report.json`.
- Manifest `asbuilt_c25b.json` = canon manifest + new map + split top + slice files.
  - The netlist is the split of the composed top sha256 50d55436, which is not on main (same as the canon manifest netlist).

### Strict bind on C25b (plan sha256 6b3a80cd), run_bind.sh (elab + release_full + bind --strict; verify only if strict passes)

| | strict errors | by kind |
|---|---|---|
| before: canon map, unsplit top | 476 | UNMAPPED 201, TIED 200, UNPLANNED 30, TYPE_SPLIT 28, LOCAL_NAME_CLASH 10, EMPTY_PARTITION 4, MAP_PARTITION 1, EMIT 1, TIED_TOTAL 1 |
| after: asbuilt_map_c25b + phy split | **463** | UNMAPPED 201, TIED 200, UNPLANNED 30, TYPE_SPLIT 28, EMPTY_PARTITION 2, EMIT 1, TIED_TOTAL 1 |

- Removed: 10 LOCAL_NAME_CLASH, MAP_PARTITION phy_NW -> PHY_N, EMPTY_PARTITION PHY_NW/PHY_NE. EMIT now lists only NW_mca/NE_mca.
- Changed: the hub-to-hub UNPLANNED rows grow. NE->NW goes from 1233 to 2775 b and NW->NE from 1188 to 2730 b, against 2838 b planned on direct lanes.
  - The S-role instances no longer collapse onto the N names, so all their crossings are counted.
  - This is the same error count, but the lane budget must cover those crossings.
- Verify is not run: the strict bind still fails closed.
- Logs: `logs_c25b/`.
