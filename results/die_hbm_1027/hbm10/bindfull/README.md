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
